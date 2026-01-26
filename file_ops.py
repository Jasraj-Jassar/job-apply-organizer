"""File operations for job folder creation."""

import shutil
import textwrap
from pathlib import Path


def ensure_job_folder(base_dir, folder_name):
    path = Path(base_dir) / folder_name
    path.mkdir(parents=True, exist_ok=True)
    return path


def _wrap(text, width=80):
    lines = []
    for raw in (text or "").splitlines():
        ln = raw.strip()
        if not ln:
            lines.append("")
        else:
            lines.extend(textwrap.fill(ln, width, break_long_words=False, break_on_hyphens=False).splitlines())
    return "\n".join(lines)


def write_description(folder, filename, description, width=80, source_url=None):
    path = folder / filename
    parts = []
    if source_url:
        parts.extend([f"Source: {source_url.strip()}", ""])
    if text := _wrap(description, width).rstrip():
        parts.append(text)
    path.write_text("\n".join(parts).rstrip() + "\n", encoding="utf-8")
    return path


def write_prompt_file(folder, filename, prompt, description, width=80):
    path = folder / filename
    parts = [p for p in [_wrap(prompt, width).rstrip(), _wrap(description, width).rstrip()] if p]
    path.write_text("\n\n".join(parts).rstrip() + "\n", encoding="utf-8")
    return path


def copy_template(template_path, target_dir, target_name=None):
    if not template_path.exists():
        return None
    target = target_dir / (target_name or template_path.name)
    if not target.exists():
        shutil.copyfile(template_path, target)
    return target
