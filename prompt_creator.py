from pathlib import Path


_BASE_DIR = Path(__file__).resolve().parent
_PROMPT_TEMPLATE_PATH = _BASE_DIR / "templates" / "prompt-template.txt"
_COVER_TEMPLATE_PATH = _BASE_DIR / "templates" / "cover-letter-template.txt"


def _read_template(path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    raise FileNotFoundError(f"Template not found: {path}")


def get_main_prompt_text(french: bool = False) -> str:
    path = _PROMPT_TEMPLATE_PATH
    if french:
        path = _BASE_DIR / "templates_vf" / "prompt-template.txt"
    return _read_template(path)


def get_cover_prompt_text(french: bool = False) -> str:
    path = _COVER_TEMPLATE_PATH
    if french:
        path = _BASE_DIR / "templates_vf" / "cover-letter-template.txt"
    return _read_template(path)
