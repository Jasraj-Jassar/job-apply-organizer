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
    folder_path: Path, filename: str, description: str, width: int = 80
) -> Path:
    file_path = folder_path / filename
    payload = _wrap_text(description, width).rstrip() + "\n"
    file_path.write_text(payload, encoding="utf-8")
    return file_path
