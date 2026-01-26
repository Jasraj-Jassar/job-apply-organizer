"""Process job data into folder structure with templates."""

import os
import re
from pathlib import Path

import file_ops
import prompt_creator

_TEMPLATES = Path(__file__).parent / "templates"
_TEMPLATES_VF = Path(__file__).parent / "templates_vf"

_WIN_RESERVED = {"CON", "PRN", "AUX", "NUL"} | {f"{p}{n}" for p in ("COM", "LPT") for n in range(1, 10)}

_NOISE = {"webkit", "inline", "block", "flex", "display", "margin", "padding", "color", "inherit", "auto", "rem", "em", "px"}


def _words(text):
    return [w for w in re.sub(r"[^A-Za-z0-9]+", " ", text or "").split() if w]


def _is_noise(w):
    lo = w.lower()
    if lo in ("true", "false") or lo.startswith("css") or lo in _NOISE:
        return True
    if len(w) > 24:
        return True
    if len(w) > 4 and any(c.isdigit() for c in w) and any(c.isalpha() for c in w):
        return True
    return False


def _abbrev(title, max_len=4):
    return "-".join(w[:max_len] if len(w) > max_len else w for w in _words(title))


def _company_slug(company):
    words = _words(company)
    result = []
    for w in words:
        if _is_noise(w):
            if result:
                break
            continue
        result.append(w)
        if len(result) >= 6:
            break
    return "-".join(result or words[:4])


def _trim(slug, max_len=80):
    slug = re.sub(r"-+", "-", slug).strip("-")
    if len(slug) <= max_len:
        return slug
    parts, acc = [], ""
    for p in slug.split("-"):
        test = f"{acc}-{p}" if acc else p
        if len(test) > max_len:
            break
        acc = test
    return acc.strip("-") or slug[:max_len].rstrip("-")


def _safe_slug(slug):
    slug = slug.strip(" .")
    if not slug:
        return "Job-Posting"
    if os.name == "nt" and slug.split(".")[0].upper() in _WIN_RESERVED:
        slug = f"{slug}-job"
    return slug or "Job-Posting"


def make_folder_name(title, company):
    t, c = _abbrev(title), _company_slug(company)
    slug = f"{t}-{c}" if t and c else t or c or "Job-Posting"
    return _trim(_safe_slug(slug))


def process_job(job_data, base_dir, source_url=None, french=False):
    title = (job_data.get("title") or "").strip()
    company = (job_data.get("company") or "").strip()
    desc = (job_data.get("description") or "").strip() or "Description not found."

    if not title or not company:
        raise ValueError("Job title or company missing.")

    folder_name = make_folder_name(title, company)
    folder = file_ops.ensure_job_folder(base_dir, folder_name)

    tpl_dir = _TEMPLATES_VF if french else _TEMPLATES

    return {
        "folder_name": folder_name,
        "folder_path": folder,
        "file_path": file_ops.write_description(folder, f"{folder_name}.txt", desc, source_url=source_url),
        "prompt_path": file_ops.write_prompt_file(folder, "prompt.txt", prompt_creator.get_main_prompt(french), desc),
        "cover_prompt_path": file_ops.write_prompt_file(folder, "prompt-cover.txt", prompt_creator.get_cover_prompt(french), desc),
        "resume_template_path": file_ops.copy_template(tpl_dir / "resume-template.tex", folder),
    }
