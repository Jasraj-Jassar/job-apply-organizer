"""Template loading for prompts."""

from pathlib import Path

_BASE = Path(__file__).parent
_TPL = _BASE / "templates"
_TPL_VF = _BASE / "templates_vf"


def _read(path):
    if not path.exists():
        raise FileNotFoundError(f"Template not found: {path}")
    return path.read_text(encoding="utf-8").strip()


def get_main_prompt(french=False):
    return _read((_TPL_VF if french else _TPL) / "prompt-template.txt")


def get_cover_prompt(french=False):
    return _read((_TPL_VF if french else _TPL) / "cover-letter-template.txt")
