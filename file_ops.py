from pathlib import Path
import textwrap


def ensure_job_folder(base_dir: Path, folder_name: str) -> Path:
    folder_path = base_dir / folder_name
    folder_path.mkdir(parents=True, exist_ok=True)
    return folder_path


def _wrap_text(text: str, width: int) -> str:
    wrapped_lines = []
    for raw_line in (text or "").splitlines():
        line = raw_line.strip()
        if not line:
            wrapped_lines.append("")
            continue
        wrapped_lines.extend(
            textwrap.fill(
                line,
                width=width,
                break_long_words=False,
                break_on_hyphens=False,
            ).splitlines()
        )
    return "\n".join(wrapped_lines)


def write_description(
    folder_path: Path,
    filename: str,
    description: str,
    width: int = 80,
    source_url: str | None = None,
) -> Path:
    file_path = folder_path / filename
    header_lines = []
    if source_url:
        header_lines.append(f"Source: {source_url.strip()}")
        header_lines.append("")

    wrapped = _wrap_text(description, width).rstrip()
    if wrapped:
        header_lines.append(wrapped)

    payload = "\n".join(header_lines).rstrip() + "\n"
    file_path.write_text(payload, encoding="utf-8")
    return file_path


def write_prompt_file(
    folder_path: Path,
    filename: str,
    prompt_text: str,
    description: str,
    width: int = 80,
) -> Path:
    file_path = folder_path / filename
    prompt_block = _wrap_text(prompt_text, width).rstrip()
    description_block = _wrap_text(description, width).rstrip()

    parts = []
    if prompt_block:
        parts.append(prompt_block)
    if description_block:
        parts.append(description_block)

    payload = "\n\n".join(parts).rstrip() + "\n"
    file_path.write_text(payload, encoding="utf-8")
    return file_path
