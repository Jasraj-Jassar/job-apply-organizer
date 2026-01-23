# Job Apply Organizer

Small CLI that turns a job posting into a ready-to-work folder, plus a LaTeX build helper for resumes.

## What It Does
- Scrapes a job URL (or saved HTML), extracts title/company/description, and builds a clean folder name.
- Writes `<folder>/<folder>.txt` (includes source URL), `<folder>/prompt.txt`, and `<folder>/prompt-cover.txt`.
- Copies `templates/resume-template.tex` into the folder; auto-opens the folder in VS Code when `code` is on PATH.
- Builds `Resume.pdf` from any `.tex` file you pass (runs `pdflatex` and cleans aux files).

## Quick Start
```
python job_tool.py "<job_url>"          # scrape and generate the folder
python job_tool.py "/path/to/page.html" # use a saved HTML file
python job_tool.py /path/to/resume.tex  # build Resume.pdf next to the .tex
```
Tip: quote long URLs so shell characters (like `&`) don’t break the command.

## Output Snapshot
```
My-Role-My-Company/
My-Role-My-Company/My-Role-My-Company.txt
My-Role-My-Company/prompt.txt
My-Role-My-Company/prompt-cover.txt
My-Role-My-Company/resume-template.tex
```

## Platform Notes
- Windows: use `py -3 job_tool.py "<job_url>"` (PowerShell/cmd) or `python ...`; paths and reserved names are normalized. Install MiKTeX/TeX Live and ensure `pdflatex.exe` is on PATH for PDF builds.
- Linux/macOS: ensure `pdflatex` is installed if you need PDFs. VS Code auto-open works when the `code` CLI is available.
