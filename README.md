# Job Apply Organizer

Tool to automate organizing the positions I apply to. It takes a job posting
and creates a folder plus a wrapped description text file in the
directory you run it from.

## Features
- Pulls `JobPosting` data from JSON-LD on the page
- Builds a folder name from the title and company (title words shortened to 4 chars)
- Writes the description to `<folder>/<folder>.txt` wrapped at 80 chars

## Usage
```
python job_tool.py "<job_url>"
```

Long URLs should be quoted so your shell does not split them. If you hit a 403,
save the page as HTML and pass the file path instead:
```
python job_tool.py "/path/to/saved_page.html"
```

## Output Example
Input:
- Title: `PLC Programmer`
- Company: `Automation Integrators Inc`

Output folder:
```
PLC-Prog-Automation-Integrators-Inc/
PLC-Prog-Automation-Integrators-Inc/PLC-Prog-Automation-Integrators-Inc.txt
```

## Modules
- `scraper.py`: fetches HTML and extracts job data
- `processor.py`: builds folder names and coordinates output
- `file_ops.py`: filesystem and text wrapping
- `job_tool.py`: CLI entrypoint
