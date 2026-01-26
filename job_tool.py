#!/usr/bin/env python3
"""CLI for creating job application folders from job postings."""

import argparse
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import url2pathname

import processor
import scraper


def _compile_resume(tex_arg):
    path = _parse_path(tex_arg)
    if path.suffix.lower() != ".tex" or not path.is_file():
        raise ValueError(f"Invalid .tex file: {path}")

    stem = "Resume"
    _cleanup_aux(path.parent, stem)

    try:
        result = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", f"-jobname={stem}", path.name],
            cwd=path.parent, capture_output=True, text=True
        )
    except FileNotFoundError:
        raise RuntimeError("pdflatex not found. Install TeX Live.") from None
    finally:
        _cleanup_aux(path.parent, stem)

    if result.returncode != 0:
        raise RuntimeError(f"pdflatex failed:\n{result.stdout}")

    return path.parent / f"{stem}.pdf"


def _parse_path(value):
    if value.lower().startswith("file://"):
        parsed = urlparse(value)
        path = parsed.path or ""
        if parsed.netloc and parsed.netloc not in ("", "localhost"):
            path = f"//{parsed.netloc}{path}"
        value = url2pathname(path)
    return Path(value).expanduser().resolve()


def _cleanup_aux(directory, stem):
    for ext in (".aux", ".log", ".out", ".toc", ".nav", ".snm", ".fls", ".fdb_latexmk", ".synctex.gz"):
        try:
            (directory / f"{stem}{ext}").unlink()
        except OSError:
            pass


def _open_in_vscode(path):
    code = shutil.which("code") or shutil.which("code.cmd")
    if code:
        try:
            subprocess.Popen([code, str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except OSError:
            pass
    return False


def main():
    parser = argparse.ArgumentParser(description="Create job folder from posting URL or compile .tex resume.")
    parser.add_argument("url", nargs="?", help="Job posting URL or .tex file path")
    parser.add_argument("-vf", action="store_true", help="French mode")
    args = parser.parse_args()

    target = (args.url or "").strip()
    if not target:
        try:
            target = input("Job posting link or .tex path: ").strip()
        except EOFError:
            pass

    if not target:
        parser.error("URL or .tex path required.")

    # .tex file → compile PDF
    if target.lower().endswith(".tex") and not target.lower().startswith(("http://", "https://")):
        try:
            pdf = _compile_resume(target)
        except Exception as e:
            raise SystemExit(str(e)) from e
        print(f"Created: {pdf}")
        return

    # URL → scrape and process
    job = scraper.scrape_job(target)
    result = processor.process_job(job, Path.cwd(), target, french=args.vf)

    print(f"Created: {result['folder_path']}")
    if _open_in_vscode(result["folder_path"]):
        print("Opened in VS Code")
    if tpl := result.get("resume_template_path"):
        print(f"Template: {tpl}")


if __name__ == "__main__":
    main()
