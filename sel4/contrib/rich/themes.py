from typing import Tuple

from rich.terminal_theme import TerminalTheme


def rgb(r, g, b) -> Tuple[int, int, int]:
    return r, g, b


DRACULA_TERMINAL_THEME = TerminalTheme(
    rgb(40, 42, 54),
    rgb(248, 248, 242),
    [
        rgb(40, 42, 54),
        rgb(255, 85, 85),
        rgb(80, 250, 123),
        rgb(241, 250, 140),
        rgb(189, 147, 249),
        rgb(255, 121, 198),
        rgb(139, 233, 253),
        rgb(255, 255, 255),
    ],
    [
        rgb(40, 42, 54),
        rgb(255, 85, 85),
        rgb(80, 250, 123),
        rgb(241, 250, 140),
        rgb(189, 147, 249),
        rgb(255, 121, 198),
        rgb(139, 233, 253),
        rgb(255, 255, 255),
    ],
)
