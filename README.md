# Job Apply Organizer

Tool to automate organizing the positions I apply to. It takes a job posting
and creates a folder plus a wrapped description text file in the
directory you run it from.

## How It Works
1. Run the tool with a job URL (quote long URLs) or a saved HTML file.
2. It extracts the job title, company, and description from the page.
3. It creates a folder named from the title + company (shortened).
4. It writes `<folder>/<folder>.txt` (source URL on top), `<folder>/prompt.txt`
   (from `templates/prompt-template.txt`), and `<folder>/prompt-cover.txt`
   (from `templates/cover-letter-template.txt`).

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
PLC-Prog-Automation-Integrators-Inc/prompt.txt
PLC-Prog-Automation-Integrators-Inc/prompt-cover.txt
```

## Modules
- `scraper.py`: fetches HTML and extracts job data
- `processor.py`: builds folder names and coordinates output
- `file_ops.py`: filesystem and text wrapping
- `job_tool.py`: CLI entrypoint
