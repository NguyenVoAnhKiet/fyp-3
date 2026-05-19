from PyQt5.QtGui import QFont


def _make_font(size: int, weight: int = QFont.Weight.Normal) -> QFont:
    font = QFont()
    font.setFamily("JetBrains Mono")
    font.setPointSize(size)
    font.setWeight(weight)
    return font


FONT_TITLE = _make_font(20, QFont.Weight.Bold)
FONT_STATUS = _make_font(16, QFont.Weight.Bold)
FONT_BODY = _make_font(14)
