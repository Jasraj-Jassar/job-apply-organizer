"""Job posting scraper with support for Indeed, LinkedIn, and local HTML files."""

import gzip
import http.cookiejar
import json
import platform
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib
from html.parser import HTMLParser
from pathlib import Path

COOKIES_FILE = Path(__file__).parent / "cookies.txt"

_CHROME_VER = "131"
_UA_WIN = f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{_CHROME_VER}.0.0.0 Safari/537.36"
_UA_LINUX = f"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{_CHROME_VER}.0.0.0 Safari/537.36"


class _ScriptCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts = []
        self._depth = 0
        self._type = None
        self._buf = []

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            self._depth = 1
            self._type = dict(attrs).get("type")
            self._buf = []
        elif self._depth:
            self._depth += 1

    def handle_data(self, data):
        if self._depth:
            self._buf.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self._depth:
            self.scripts.append((self._type, "".join(self._buf).strip()))
            self._depth = 0


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self._parts = []

    def handle_starttag(self, tag, attrs):
        if tag in ("br", "p", "li"):
            self._parts.append("\n")

    def handle_endtag(self, tag):
        if tag in ("p", "li", "ul", "ol"):
            self._parts.append("\n")

    def handle_data(self, data):
        self._parts.append(data)

    def text(self):
        return "\n".join(ln.strip() for ln in "".join(self._parts).splitlines() if ln.strip())


class _MetaExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.meta = {}

    def handle_starttag(self, tag, attrs):
        if tag == "meta":
            d = dict(attrs)
            key = d.get("property") or d.get("name")
            if key and d.get("content"):
                self.meta[key] = d["content"]


class _IndeedExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = self.company = self.description = ""
        self._title_d = self._company_d = self._desc_d = 0
        self._t_buf, self._c_buf, self._d_buf = [], [], []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if self._title_d:
            self._title_d += 1
        if self._company_d:
            self._company_d += 1
        if self._desc_d:
            self._desc_d += 1

        if not self._title_d and tag == "h1":
            self._title_d = 1
        if not self._company_d and self._is_company(a):
            self._company_d = 1
        if not self._desc_d and self._is_desc(a):
            self._desc_d = 1
        if self._desc_d and tag in ("br", "p", "li"):
            self._d_buf.append("\n")

        cn = a.get("data-company-name") or a.get("data-companyname")
        if cn and any(c.isalpha() for c in cn):
            self._c_buf.append(cn)

    def handle_endtag(self, tag):
        if self._desc_d and tag in ("p", "li", "ul", "ol"):
            self._d_buf.append("\n")
        if self._title_d:
            self._title_d -= 1
        if self._company_d:
            self._company_d -= 1
        if self._desc_d:
            self._desc_d -= 1

    def handle_data(self, data):
        if self._title_d:
            self._t_buf.append(data)
        if self._company_d:
            self._c_buf.append(data)
        if self._desc_d:
            self._d_buf.append(data)

    def finalize(self):
        self.title = " ".join("".join(self._t_buf).split()).strip()
        self.company = " ".join("".join(self._c_buf).split()).strip()
        self.description = "\n".join(ln.strip() for ln in "".join(self._d_buf).splitlines() if ln.strip())

    @staticmethod
    def _is_company(a):
        if "data-company-name" in a or "data-companyname" in a:
            return True
        tid = (a.get("data-testid") or "").lower()
        if "company" in tid and "name" in tid:
            return True
        cls = (a.get("class") or "").lower()
        return "companyname" in cls or "company-name" in cls

    @staticmethod
    def _is_desc(a):
        if a.get("id") == "jobDescriptionText":
            return True
        tid = a.get("data-testid") or ""
        if tid in ("jobDescriptionText", "job-description"):
            return True
        return "jobDescriptionText" in (a.get("class") or "")


def _strip_html(html):
    ext = _TextExtractor()
    ext.feed(html or "")
    return ext.text()


def _load_cookies():
    if not COOKIES_FILE.exists():
        return None
    try:
        jar = http.cookiejar.MozillaCookieJar(str(COOKIES_FILE))
        jar.load(ignore_discard=True, ignore_expires=True)
        return jar
    except Exception:
        return None


def _headers():
    is_win = platform.system().lower().startswith("win")
    ua = _UA_WIN if is_win else _UA_LINUX
    plat = '"Windows"' if is_win else '"Linux"'
    return {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-CA,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Sec-Ch-Ua": f'"Google Chrome";v="{_CHROME_VER}", "Chromium";v="{_CHROME_VER}"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": plat,
        "Upgrade-Insecure-Requests": "1",
    }


def _decompress(data, encoding):
    if encoding == "gzip":
        return gzip.decompress(data)
    if encoding == "deflate":
        try:
            return zlib.decompress(data)
        except zlib.error:
            return zlib.decompress(data, -zlib.MAX_WBITS)
    if encoding == "br":
        try:
            import brotli
            return brotli.decompress(data)
        except ImportError:
            pass
    return data


def _http_get(url, jar=None):
    handlers = [urllib.request.HTTPCookieProcessor(jar or http.cookiejar.CookieJar())]
    opener = urllib.request.build_opener(*handlers)
    hdrs = _headers()
    parsed = urllib.parse.urlparse(url)
    hdrs["Referer"] = f"{parsed.scheme}://{parsed.netloc}/"

    req = urllib.request.Request(url, headers=hdrs)
    with opener.open(req, timeout=30) as resp:
        data = resp.read()
        enc = resp.headers.get("Content-Encoding", "").lower()
        try:
            data = _decompress(data, enc)
        except Exception:
            pass
        return data.decode("utf-8", errors="replace")


def _local_path(value):
    if value.lower().startswith("file://"):
        parsed = urllib.parse.urlparse(value)
        path = parsed.path or ""
        if parsed.netloc and parsed.netloc not in ("", "localhost"):
            path = f"//{parsed.netloc}{path}"
        p = Path(urllib.request.url2pathname(path))
        return p if p.exists() else None
    p = Path(value).expanduser()
    return p if p.exists() else None


def fetch_html(url):
    lp = _local_path(url)
    if lp:
        return lp.read_text(encoding="utf-8", errors="replace")

    jar = _load_cookies()
    is_linkedin = "linkedin.com" in url.lower()
    is_indeed = "indeed.com" in url.lower() or "indeed.ca" in url.lower()

    for attempt in range(2):
        try:
            if attempt:
                time.sleep(1)
            return _http_get(url, jar)
        except urllib.error.HTTPError as e:
            if e.code not in (403, 429, 999):
                raise
            if attempt == 1:
                if e.code == 999 and is_linkedin:
                    raise ValueError("LinkedIn blocked (999). Export cookies or save page as HTML.") from e
                if e.code == 403 and is_indeed:
                    raise ValueError("Indeed blocked (403). Refresh cookies or save page as HTML.") from e
                raise
    raise RuntimeError("Failed to fetch HTML")


def _extract_json_ld(html):
    col = _ScriptCollector()
    col.feed(html)
    for typ, content in col.scripts:
        if typ and typ.lower() != "application/ld+json":
            continue
        try:
            yield json.loads(content)
        except json.JSONDecodeError:
            pass


def _find_job_posting(data):
    if isinstance(data, dict):
        jt = data.get("@type")
        if jt == "JobPosting" or (isinstance(jt, list) and "JobPosting" in jt):
            return data
        for v in data.values():
            if found := _find_job_posting(v):
                return found
    elif isinstance(data, list):
        for item in data:
            if found := _find_job_posting(item):
                return found
    return None


def _normalize_ld(job):
    title = job.get("title") or job.get("name") or ""
    org = job.get("hiringOrganization")
    company = ""
    if isinstance(org, dict):
        company = org.get("name", "")
    elif isinstance(org, list):
        for o in org:
            if isinstance(o, dict) and o.get("name"):
                company = o["name"]
                break
    desc = _strip_html(job.get("description", ""))
    return {"title": title.strip(), "company": company.strip(), "description": desc.strip()}


def parse_json_ld(html):
    for payload in _extract_json_ld(html):
        if job := _find_job_posting(payload):
            return _normalize_ld(job)
    return None


def parse_linkedin(html):
    meta = _MetaExtractor()
    meta.feed(html)

    og = meta.meta.get("og:title", "")
    title = company = ""

    if m := re.match(r"^(.+?)\s+hiring\s+(.+?)\s+in\s+", og):
        company, title = m.group(1).strip(), m.group(2).strip()
    else:
        title = re.sub(r"\s*\|\s*LinkedIn\s*$", "", og).strip()

    desc = ""
    if m := re.search(r'show-more-less-html__markup[^>]*>(.*?)</div>', html, re.DOTALL | re.I):
        desc = _strip_html(m.group(1))
    desc = desc or meta.meta.get("og:description", "") or meta.meta.get("description", "")

    if not company:
        if m := re.search(r'topcard__org-name-link[^>]*>([^<]+)</a>', html, re.I):
            company = " ".join(m.group(1).split())

    if title or company or desc:
        return {"title": title.strip(), "company": company.strip(), "description": desc.strip()}
    return None


def parse_indeed(html):
    ext = _IndeedExtractor()
    ext.feed(html)
    ext.finalize()

    if not ext.title or not ext.company:
        meta = _MetaExtractor()
        meta.feed(html)
        ext.title = ext.title or " ".join((meta.meta.get("og:title") or "").split())

    if not ext.description:
        meta = _MetaExtractor()
        meta.feed(html)
        ext.description = "\n".join(ln.strip() for ln in (meta.meta.get("og:description") or "").splitlines() if ln.strip())

    if ext.title or ext.company or ext.description:
        return {"title": ext.title, "company": ext.company, "description": ext.description}
    return None


def _is_auth_wall(html):
    lower = html.lower()
    return any(s in lower for s in ("sign in to view", "join now to see", "authwall", '"isloggedin":false'))


def scrape_job(url):
    is_linkedin = "linkedin.com" in url.lower()
    html = fetch_html(url)

    job = parse_json_ld(html)
    if not job and is_linkedin:
        job = parse_linkedin(html)
    if not job:
        job = parse_indeed(html)

    if not job:
        lower = html.lower()
        if "captcha" in lower or "verify you are a human" in lower:
            raise ValueError("Blocked by CAPTCHA. Save page as HTML and pass file path.")
        if is_linkedin and _is_auth_wall(html):
            raise ValueError("LinkedIn auth wall. Export cookies or save page as HTML.")
        raise ValueError("No job data found. Try saving page as HTML.")

    return job
