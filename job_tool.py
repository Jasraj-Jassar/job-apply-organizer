#!/usr/bin/env python3
import argparse
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import url2pathname

import processor
import scraper


def _compile_resume_pdf(tex_arg: str, output_stem: str = "Resume") -> Path:
    tex_path = _normalize_tex_path(tex_arg)
    if tex_path.suffix.lower() != ".tex":
        raise ValueError("Input must be a .tex file.")
    if not tex_path.is_file():
        raise FileNotFoundError(f"LaTeX file not found: {tex_path}")

    # Clean leftovers from any previous run for the same jobname
    _cleanup_latex_aux(tex_path.parent, output_stem)

    cmd = [
        "pdflatex",
        "-interaction=nonstopmode",
        f"-jobname={output_stem}",
        tex_path.name,
    ]
    try:
        result = subprocess.run(
            cmd,
            cwd=tex_path.parent,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            "pdflatex not found. Install TeX Live / MacTeX / MiKTeX to build PDFs."
        ) from exc

    # Always clean up aux files, even if pdflatex reports errors
    _cleanup_latex_aux(tex_path.parent, output_stem)

    if result.returncode != 0:
        raise RuntimeError(
            f"pdflatex failed with exit code {result.returncode}:\n{result.stdout}"
        )

    return tex_path.parent / f"{output_stem}.pdf"


def _normalize_tex_path(value: str) -> Path:
    lower = value.lower()
    if lower.startswith("file://"):
        parsed = urlparse(value)
        path = parsed.path or ""
        if parsed.netloc and parsed.netloc not in {"", "localhost"}:
            path = f"//{parsed.netloc}{path}"
        value = url2pathname(path)
    return Path(value).expanduser().resolve()


def _cleanup_latex_aux(directory: Path, stem: str) -> None:
    """Remove common LaTeX aux files for the given jobname stem."""
    exts = [
        ".aux",
        ".log",
        ".out",
        ".toc",
        ".nav",
        ".snm",
        ".fls",
        ".fdb_latexmk",
        ".synctex.gz",
        ".lof",
        ".lot",
    ]
    for ext in exts:
        candidate = directory / f"{stem}{ext}"
        try:
            candidate.unlink()
        except FileNotFoundError:
            continue
        except OSError:
            # Ignore cleanup issues; PDF is already produced.
            continue


def _open_folder_in_vscode(folder_path: Path) -> bool:
    """Best-effort attempt to open the created folder in VS Code."""
    code_cmd = shutil.which("code") or shutil.which("code.cmd") or shutil.which("code.exe")
    if not code_cmd:
        return False
    try:
        subprocess.Popen(
            [code_cmd, str(folder_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        return False
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Create a job folder and description file from a job posting link, "
            "or compile a LaTeX resume to Resume.pdf."
        )
    )
    parser.add_argument(
        "url",
        nargs="?",
        help=(
            "Job posting link (Indeed supported) or path to a .tex resume. "
            "Leave blank to paste when prompted."
        ),
    )

    # french option
    parser.add_argument(
        "-vf",
        action="store_true",
        help="Setup the application in French mode (default is English).",
    )

    args = parser.parse_args()

    target = (args.url or "").strip()
    if not target:
        try:
            target = input("Job posting link or .tex resume path: ").strip()
        except EOFError:
            target = ""

    if not target:
        parser.error("Job posting link or .tex path is required.")

    if target.lower().endswith(".tex") and not target.lower().startswith(("http://", "https://")):
        try:
            pdf_path = _compile_resume_pdf(target)
        except Exception as exc:
            raise SystemExit(str(exc))
        print(f"Created PDF: {pdf_path}")
        return

    job_data = scraper.scrape_job(target)
    result = processor.process_job(job_data, Path.cwd(), target, french=args.vf)

    print(f"Created folder: {result['folder_path']}")
    print(f"Wrote description: {result['file_path']}")
    if _open_folder_in_vscode(result["folder_path"]):
        print(f"Opened in VS Code: {result['folder_path']}")
    else:
        print("VS Code CLI not found; enable the `code` command to auto-open folders.")
    resume_template = result.get("resume_template_path")
    if resume_template:
        print(f"Copied LaTeX template: {resume_template}")


if __name__ == "__main__":
    main()
