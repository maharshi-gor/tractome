from pathlib import Path


def load_style_sheet():
    """Load the stylesheet for the app.

    Returns
    -------
    str
        String value of the stylesheet.
    """
    style_path = Path(__file__).resolve().parent / "assets" / "style.qss"
    with style_path.open("r", encoding="utf-8") as f:
        return f.read()
