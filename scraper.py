import http.cookiejar
import json
import platform
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path


COOKIES_FILE = Path(__file__).parent / "cookies.txt"


class _ScriptCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.scripts = []
        self._in_script = False
        self._script_type = None
        self._buf = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "script":
            return
        self._in_script = True
        self._script_type = None
        self._buf = []
        for key, value in attrs:
            if key.lower() == "type":
                self._script_type = value

    def handle_data(self, data):
        if self._in_script:
            self._buf.append(data)

    def handle_endtag(self, tag):
        if tag.lower() != "script" or not self._in_script:
            return
        content = "".join(self._buf).strip()
        self.scripts.append((self._script_type, content))
        self._in_script = False
        self._script_type = None
        self._buf = []


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() in {"br", "p", "li"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag.lower() in {"p", "li", "ul", "ol"}:
            self.parts.append("\n")

    def handle_data(self, data):
        self.parts.append(data)

    def get_text(self) -> str:
        text = "".join(self.parts)
        lines = [line.strip() for line in text.splitlines()]
        return "\n".join([line for line in lines if line])


class _MetaExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.meta = {}

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "meta":
            return
        attrs_dict = dict(attrs)
        key = attrs_dict.get("property") or attrs_dict.get("name")
        value = attrs_dict.get("content")
        if key and value:
            self.meta[key] = value


class _IndeedHTMLExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title_parts = []
        self.company_parts = []
        self.description_parts = []
        self._title_depth = 0
        self._company_depth = 0
        self._desc_depth = 0

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        attrs_dict = dict(attrs)

        if self._title_depth:
            self._title_depth += 1
        if self._company_depth:
            self._company_depth += 1
        if self._desc_depth:
            self._desc_depth += 1

        if self._title_depth == 0 and tag == "h1":
            self._title_depth = 1

        if self._company_depth == 0 and _is_company_tag(attrs_dict):
            self._company_depth = 1

        if self._desc_depth == 0 and _is_description_tag(attrs_dict):
            self._desc_depth = 1

        if self._desc_depth and tag in {"br", "p", "li"}:
            self.description_parts.append("\n")

        company_attr = attrs_dict.get("data-company-name") or attrs_dict.get(
            "data-companyname"
        )
        if company_attr and _looks_like_name(company_attr):
            self.company_parts.append(company_attr)

    def handle_endtag(self, tag):
        tag = tag.lower()

        if self._desc_depth and tag in {"p", "li", "ul", "ol"}:
            self.description_parts.append("\n")

        if self._title_depth:
            self._title_depth -= 1
        if self._company_depth:
            self._company_depth -= 1
        if self._desc_depth:
            self._desc_depth -= 1

    def handle_data(self, data):
        if self._title_depth:
            self.title_parts.append(data)
        if self._company_depth:
            self.company_parts.append(data)
        if self._desc_depth:
            self.description_parts.append(data)

    def get_title(self) -> str:
        return _clean_text(" ".join(self.title_parts))

    def get_company(self) -> str:
        return _clean_text(" ".join(self.company_parts))

    def get_description(self) -> str:
        return _clean_lines("".join(self.description_parts))


def _read_local(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _local_path_from_arg(value: str) -> Path | None:
    lowered = value.lower()
    if lowered.startswith("file://"):
        parsed = urllib.parse.urlparse(value)
        path = parsed.path or ""
        if parsed.netloc and parsed.netloc not in {"", "localhost"}:
            path = f"//{parsed.netloc}{path}"
        candidate = Path(urllib.request.url2pathname(path))
        if candidate.exists():
            return candidate
        return None

    candidate = Path(value).expanduser()
    if candidate.exists():
        return candidate
    return None


def _load_cookies() -> http.cookiejar.MozillaCookieJar | None:
    """Load cookies from Netscape format cookies.txt if it exists."""
    if not COOKIES_FILE.exists():
        return None
    try:
        jar = http.cookiejar.MozillaCookieJar(str(COOKIES_FILE))
        jar.load(ignore_discard=True, ignore_expires=True)
        return jar
    except Exception:
        return None


def _build_header_sets() -> list[dict]:
    os_platform = platform.system().lower()
    is_windows = os_platform.startswith("win")
    # Updated to latest Chrome version (January 2026)
    ua_windows = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    )
    ua_linux = (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    )
    ua_primary = ua_windows if is_windows else ua_linux
    sec_platform = '"Windows"' if is_windows else '"Linux"'

    return [
        {
            "User-Agent": ua_primary,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "en-CA,en-US;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "max-age=0",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Sec-Ch-Ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": sec_platform,
            "Dnt": "1",
            "Priority": "u=0, i",
        },
        {
            "User-Agent": ua_primary,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-CA,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Ch-Ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": sec_platform,
        },
    ]


def _http_get(url: str, headers: dict, cookie_jar: http.cookiejar.CookieJar | None = None) -> str:
    import gzip
    import zlib

    handlers = []
    if cookie_jar:
        handlers.append(urllib.request.HTTPCookieProcessor(cookie_jar))
    else:
        handlers.append(urllib.request.HTTPCookieProcessor())
    opener = urllib.request.build_opener(*handlers)
    request = urllib.request.Request(url, headers=headers)
    with opener.open(request, timeout=30) as response:
        raw_data = response.read()
        encoding = response.headers.get("Content-Encoding", "").lower()

        # Decompress if needed
        if encoding == "gzip":
            try:
                raw_data = gzip.decompress(raw_data)
            except Exception:
                pass
        elif encoding == "deflate":
            try:
                raw_data = zlib.decompress(raw_data)
            except Exception:
                try:
                    raw_data = zlib.decompress(raw_data, -zlib.MAX_WBITS)
                except Exception:
                    pass
        elif encoding == "br":
            try:
                import brotli
                raw_data = brotli.decompress(raw_data)
            except ImportError:
                pass  # brotli not installed, try raw
            except Exception:
                pass

        return raw_data.decode("utf-8", errors="replace")


def _get_referer(url: str) -> str:
    """Get a plausible referer for the URL."""
    parsed = urllib.parse.urlparse(url)
    # Return the site's homepage as referer
    return f"{parsed.scheme}://{parsed.netloc}/"


def fetch_html(url: str) -> str:
    import time

    local_path = _local_path_from_arg(url)
    if local_path:
        return _read_local(local_path)

    # Load cookies from file if available
    cookie_jar = _load_cookies()

    # Detect site type
    is_linkedin = "linkedin.com" in url.lower()
    is_indeed = "indeed.com" in url.lower() or "indeed.ca" in url.lower()

    header_sets = _build_header_sets()

    # Add referer to all header sets
    referer = _get_referer(url)
    for headers in header_sets:
        headers["Referer"] = referer

    last_error = None
    for i, headers in enumerate(header_sets):
        try:
            # Small delay between retries to avoid rate limiting
            if i > 0:
                time.sleep(1)
            return _http_get(url, headers, cookie_jar)
        except urllib.error.HTTPError as exc:
            last_error = exc
            # 999 is LinkedIn's specific block code
            if exc.code not in {403, 429, 999}:
                break

    if last_error:
        if last_error.code == 999 and is_linkedin:
            raise ValueError(
                "LinkedIn blocked the request (HTTP 999). This usually means:\n"
                "1. LinkedIn requires authentication - export your cookies using a browser extension\n"
                "   (Cookie-Editor) to cookies.txt in Netscape format, or\n"
                "2. Save the job page as HTML in your browser and pass the file path instead."
            )
        if last_error.code == 403 and is_indeed:
            raise ValueError(
                "Indeed blocked the request (HTTP 403). This usually means:\n"
                "1. Your cookies.txt file may be expired - export fresh cookies from your browser\n"
                "   using Cookie-Editor extension (Netscape format), or\n"
                "2. Indeed is using enhanced bot protection - save the job page as HTML and pass\n"
                "   the file path instead."
            )
        raise last_error

    raise RuntimeError("Failed to fetch HTML.")


def _extract_json_ld(html: str):
    collector = _ScriptCollector()
    collector.feed(html)
    payloads = []
    for script_type, content in collector.scripts:
        if not content:
            continue
        if script_type and script_type.lower() != "application/ld+json":
            continue
        try:
            payloads.append(json.loads(content))
        except json.JSONDecodeError:
            continue
    return payloads


def _is_job_posting(data) -> bool:
    if not isinstance(data, dict):
        return False
    job_type = data.get("@type")
    if isinstance(job_type, list):
        return "JobPosting" in job_type
    return job_type == "JobPosting"


def _find_job_posting(data):
    if isinstance(data, dict):
        if _is_job_posting(data):
            return data
        for value in data.values():
            found = _find_job_posting(value)
            if found:
                return found
    elif isinstance(data, list):
        for item in data:
            found = _find_job_posting(item)
            if found:
                return found
    return None


def _strip_html(value: str) -> str:
    extractor = _TextExtractor()
    extractor.feed(value or "")
    return extractor.get_text()


def _clean_text(value: str) -> str:
    return " ".join((value or "").split()).strip()


def _clean_lines(value: str) -> str:
    lines = [line.strip() for line in (value or "").splitlines()]
    return "\n".join([line for line in lines if line])


def _looks_like_name(value: str) -> bool:
    cleaned = (value or "").strip()
    if not cleaned:
        return False
    lowered = cleaned.lower()
    if lowered in {"true", "false"}:
        return False
    return any(char.isalpha() for char in cleaned)


def _is_company_tag(attrs: dict) -> bool:
    if "data-company-name" in attrs or "data-companyname" in attrs:
        return True
    testid = (attrs.get("data-testid") or "").strip().lower()
    if testid in {"company-name", "companyname", "company-name-link"}:
        return True
    if "company" in testid and "name" in testid:
        return True
    class_attr = attrs.get("class") or ""
    class_lower = class_attr.lower()
    return "companyname" in class_lower or "company-name" in class_lower


def _is_description_tag(attrs: dict) -> bool:
    if attrs.get("id") == "jobDescriptionText":
        return True
    testid = (attrs.get("data-testid") or "").strip()
    if testid in {"jobDescriptionText", "job-description"}:
        return True
    class_attr = attrs.get("class") or ""
    return "jobDescriptionText" in class_attr or "jobsearch-jobDescriptionText" in class_attr


def _normalize_job(job_posting: dict) -> dict:
    title = job_posting.get("title") or job_posting.get("name") or ""
    org = job_posting.get("hiringOrganization")
    company = ""
    if isinstance(org, dict):
        company = org.get("name") or ""
    elif isinstance(org, list):
        for item in org:
            if isinstance(item, dict) and item.get("name"):
                company = item.get("name")
                break
    description_html = job_posting.get("description") or ""
    return {
        "title": title.strip(),
        "company": company.strip(),
        "description": _strip_html(description_html).strip(),
    }


def parse_indeed_job(html: str):
    for payload in _extract_json_ld(html):
        job_posting = _find_job_posting(payload)
        if job_posting:
            return _normalize_job(job_posting)
    return None


def parse_linkedin_job(html: str):
    """Parse LinkedIn job posting page."""
    import re

    meta = _MetaExtractor()
    meta.feed(html)

    # Extract title and company from og:title
    # Format: "Company hiring Title in Location | LinkedIn"
    og_title = meta.meta.get("og:title", "")
    title = ""
    company = ""

    # Try to parse "Company hiring Title in Location"
    hiring_match = re.match(r"^(.+?)\s+hiring\s+(.+?)\s+in\s+.+", og_title)
    if hiring_match:
        company = hiring_match.group(1).strip()
        title = hiring_match.group(2).strip()
    else:
        # Fallback: look for title in h1 or use og:title without "| LinkedIn"
        title = re.sub(r"\s*\|\s*LinkedIn\s*$", "", og_title).strip()

    # Extract description from show-more-less-html__markup div
    description = ""
    desc_match = re.search(
        r'show-more-less-html__markup[^>]*>(.*?)</div>',
        html,
        re.DOTALL | re.IGNORECASE
    )
    if desc_match:
        description = _strip_html(desc_match.group(1))
    else:
        # Fallback to meta description
        description = meta.meta.get("og:description") or meta.meta.get("description") or ""

    # Try to get company from page if not found in og:title
    if not company:
        # Look for company name in specific elements
        company_match = re.search(
            r'topcard__org-name-link[^>]*>([^<]+)</a>',
            html,
            re.IGNORECASE
        )
        if company_match:
            company = _clean_text(company_match.group(1))
        else:
            # Try another pattern
            company_match = re.search(
                r'class="[^"]*company[^"]*"[^>]*>([^<]+)<',
                html,
                re.IGNORECASE
            )
            if company_match:
                company = _clean_text(company_match.group(1))

    if title or company or description:
        return {
            "title": title.strip(),
            "company": company.strip(),
            "description": _clean_lines(description).strip(),
        }
    return None


def parse_indeed_html(html: str):
    extractor = _IndeedHTMLExtractor()
    extractor.feed(html)
    title = extractor.get_title()
    company = extractor.get_company()
    description = extractor.get_description()

    if not title or not company:
        meta = _MetaExtractor()
        meta.feed(html)
        if not title:
            title = _clean_text(
                meta.meta.get("og:title") or meta.meta.get("twitter:title") or ""
            )

    if not description:
        meta = _MetaExtractor()
        meta.feed(html)
        description = _clean_lines(
            meta.meta.get("og:description") or meta.meta.get("description") or ""
        )

    if title or company or description:
        return {
            "title": title.strip(),
            "company": company.strip(),
            "description": description.strip(),
        }
    return None


def _is_linkedin_auth_wall(html: str) -> bool:
    """Check if LinkedIn is showing a sign-in wall."""
    lower = html.lower()
    indicators = [
        "sign in to view",
        "join now to see",
        "authwall",
        "sign in or join",
        "login-form",
        '"isLoggedIn":false',
    ]
    return any(ind in lower for ind in indicators)


def scrape_job(url: str) -> dict:
    is_linkedin = "linkedin.com" in url.lower()
    html = fetch_html(url)

    # Try JSON-LD first (works for many sites)
    job = parse_indeed_job(html)

    # Try LinkedIn-specific parser
    if not job and is_linkedin:
        job = parse_linkedin_job(html)

    # Fallback to generic HTML parser
    if not job:
        job = parse_indeed_html(html)

    if not job:
        lower_html = html.lower()
        if "captcha" in lower_html or "verify you are a human" in lower_html:
            raise ValueError(
                "Blocked by Indeed. Save the page as HTML in your browser and pass the file path."
            )
        if is_linkedin and _is_linkedin_auth_wall(html):
            raise ValueError(
                "LinkedIn requires authentication to view this job posting.\n"
                "Options:\n"
                "1. Export your LinkedIn cookies using a browser extension (e.g., Cookie-Editor)\n"
                "   to 'cookies.txt' in Netscape format in the tool's directory, or\n"
                "2. Open the job page in your browser, save as HTML, and pass the file path."
            )
        raise ValueError(
            "No job posting data found in the page. Try quoting the URL or save the page as HTML."
        )
    return job
