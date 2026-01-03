import re
from pathlib import Path

import file_ops
import prompt_creator


def _split_words(text: str) -> list:
    cleaned = re.sub(r"[^A-Za-z0-9]+", " ", text or "")
    return [word for word in cleaned.strip().split() if word]


def _abbreviate_title(title: str, max_len: int = 4) -> str:
    words = _split_words(title)
    return "-".join([word if len(word) <= max_len else word[:max_len] for word in words])


def _company_slug(company: str) -> str:
    return "-".join(_split_words(company))


def make_folder_name(title: str, company: str) -> str:
    title_part = _abbreviate_title(title)
    company_part = _company_slug(company)
    if title_part and company_part:
        return f"{title_part}-{company_part}"
    return title_part or company_part or "Job-Posting"


def process_job(job_data: dict, base_dir: Path, source_url: str | None = None) -> dict:
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
        prompt_creator.get_prompt_text(),
        description or "Description not found.",
    )

    return {
        "folder_name": folder_name,
        "folder_path": folder_path,
        "file_path": file_path,
        "prompt_path": prompt_path,
    }
