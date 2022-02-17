from rich.console import Console
from ...conf import settings


def get_html_console() -> Console:
    return Console(
        force_terminal=True,
        color_system="truecolor",
        record=True,
        width=settings.HTML_WIDTH
    )