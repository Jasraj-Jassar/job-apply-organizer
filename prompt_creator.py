from pathlib import Path


_BASE_DIR = Path(__file__).resolve().parent
_PROMPT_TEMPLATE_PATH = _BASE_DIR / "Template" / "prompt-template.txt"
_COVER_TEMPLATE_PATH = _BASE_DIR / "Template" / "Cover-leter-template.txt"


def _read_template(path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    raise FileNotFoundError(f"Template not found: {path}")


def get_prompt_text() -> str:
    prompt_text = _read_template(_PROMPT_TEMPLATE_PATH)
    cover_text = _read_template(_COVER_TEMPLATE_PATH)

    parts = [part for part in (prompt_text, cover_text) if part]
    return "\n\n".join(parts).strip()
