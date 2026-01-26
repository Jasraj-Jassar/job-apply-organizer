import os
import re
from pathlib import Path

import file_ops
import prompt_creator

_LATEX_TEMPLATE_PATH = Path(__file__).resolve().parent / "templates" / "resume-template.tex"
_LATEX_TEMPLATE_PATH_VF = Path(__file__).resolve().parent / "templates_vf" / "resume-template.tex"
_WINDOWS_RESERVED_NAMES = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    "COM1",
    "COM2",
    "COM3",
    "COM4",
    "COM5",
    "COM6",
    "COM7",
    "COM8",
    "COM9",
    "LPT1",
    "LPT2",
    "LPT3",
    "LPT4",
    "LPT5",
    "LPT6",
    "LPT7",
    "LPT8",
    "LPT9",
}

def _split_words(text: str) -> list:
    cleaned = re.sub(r"[^A-Za-z0-9]+", " ", text or "")
    return [word for word in cleaned.strip().split() if word]


def _abbreviate_title(title: str, max_len: int = 4) -> str:
    words = _split_words(title)
    return "-".join([word if len(word) <= max_len else word[:max_len] for word in words])


def _company_slug(company: str) -> str:
    words = _filter_company_words(_split_words(company))
    if not words:
        words = _split_words(company)[:4]
    return "-".join(words)


def _filter_company_words(words: list, max_words: int = 6) -> list:
    filtered = []
    for word in words:
        if _is_noise_word(word):
            if filtered:
                break
            continue
        filtered.append(word)
        if len(filtered) >= max_words:
            break
    return filtered


def _is_noise_word(word: str) -> bool:
    lower = word.lower()
    if lower in {"true", "false"}:
        return True
    if lower.startswith("css"):
        return True
    if lower in {
        "webkit",
        "ms",
        "inline",
        "block",
        "flex",
        "display",
        "margin",
        "padding",
        "size",
        "color",
        "inherit",
        "vertical",
        "align",
        "start",
        "end",
        "auto",
        "rem",
        "em",
        "px",
    }:
        return True
    if len(word) > 24:
        return True
    if len(word) > 4 and any(ch.isdigit() for ch in word) and any(
        ch.isalpha() for ch in word
    ):
        return True
    return False


def make_folder_name(title: str, company: str) -> str:
    title_part = _abbreviate_title(title)
    company_part = _company_slug(company)
    if title_part and company_part:
        slug = _trim_slug(f"{title_part}-{company_part}")
    else:
        slug = _trim_slug(title_part or company_part or "Job-Posting")
    slug = _normalize_slug_for_platform(slug)
    return _trim_slug(slug)


def _trim_slug(slug: str, max_len: int = 80) -> str:
    cleaned = re.sub(r"-{2,}", "-", slug).strip("-")
    if len(cleaned) <= max_len:
        return cleaned
    parts = cleaned.split("-")
    trimmed = []
    for part in parts:
        if not trimmed:
            trimmed.append(part)
            continue
        candidate = "-".join(trimmed + [part])
        if len(candidate) > max_len:
            break
        trimmed.append(part)
    result = "-".join(trimmed).strip("-")
    return result or cleaned[:max_len].rstrip("-")


def _normalize_slug_for_platform(slug: str) -> str:
    cleaned = slug.strip(" .")
    if not cleaned:
        return "Job-Posting"
    if os.name == "nt":
        base = cleaned.split(".")[0].upper()
        if base in _WINDOWS_RESERVED_NAMES:
            cleaned = f"{cleaned}-job".strip(" .")
    return cleaned or "Job-Posting"


def process_job(job_data: dict, base_dir: Path, source_url: str | None = None, french: bool = False) -> dict:
    title = (job_data.get("title") or "").strip()
    company = (job_data.get("company") or "").strip()
    description = (job_data.get("description") or "").strip()

    if not title or not company:
        raise ValueError("Job title or company missing in scraped data.")

    folder_name = make_folder_name(title, company)
    folder_path = file_ops.ensure_job_folder(base_dir, folder_name)
    file_path = file_ops.write_description(
        folder_path,
        f"{folder_name}.txt",
        description or "Description not found.",
        source_url=source_url,
    )
    prompt_path = file_ops.write_prompt_file(
        folder_path,
        "prompt.txt",
        prompt_creator.get_main_prompt_text(french),
        description or "Description not found.",
    )
    cover_prompt_path = file_ops.write_prompt_file(
        folder_path,
        "prompt-cover.txt",
        prompt_creator.get_cover_prompt_text(french),
        description or "Description not found.",
    )

    template_path = _LATEX_TEMPLATE_PATH
    if french:
        template_path = _LATEX_TEMPLATE_PATH_VF
    resume_template_path = file_ops.copy_template_file(
        template_path, folder_path, "resume-template.tex"
    )

    return {
        "folder_name": folder_name,
        "folder_path": folder_path,
        "file_path": file_path,
        "prompt_path": prompt_path,
        "cover_prompt_path": cover_prompt_path,
        "resume_template_path": resume_template_path,
    }
