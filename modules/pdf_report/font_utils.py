# Регистрация шрифта DejaVuSans и подготовка стилей с этим шрифтом.
from pathlib import Path
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


DEFAULT_FONT = "DejaVuSans"


def register_fonts(font_path: str = "fonts/DejaVuSans.ttf", font_name: str = DEFAULT_FONT) -> str:
    """
    Регистрирует TTF шрифт и возвращает имя шрифта.
    Если файл не найден — не падаем, просто оставляем шрифт по умолчанию ReportLab.
    """
    p = Path(font_path)
    if p.exists():
        try:
            if not pdfmetrics.getFont(font_name):
                # Если уже зарегистрирован, getFont не бросит, но на всякий регистрируем.
                pass
        except Exception:
            pdfmetrics.registerFont(TTFont(font_name, str(p)))
    return font_name


def make_styles(font_name: str = DEFAULT_FONT):
    """
    Возвращает набор стилей, где всем основным стилям проставлен выбранный шрифт.
    """
    styles = getSampleStyleSheet()

    # Базовые
    for key in ("Normal", "BodyText", "Title", "Heading1", "Heading2", "Heading3", "Heading4"):
        if key in styles:
            styles[key].fontName = font_name

    # Немного более жирный заголовок без обращения к Bold-версии (если её нет)
    # Можно варьировать размером:
    styles["Title"].fontSize = 24
    styles["Heading2"].fontSize = 16
    styles["Heading3"].fontSize = 14
    styles["Heading4"].fontSize = 12

    # Центровка заголовков — удобно иметь отдельные варианты
    styles.add(ParagraphStyle(name="TitleCenter", parent=styles["Title"], alignment=1))
    styles.add(ParagraphStyle(name="H2Center", parent=styles["Heading2"], alignment=1))
    styles.add(ParagraphStyle(name="H3Center", parent=styles["Heading3"], alignment=1))
    styles.add(ParagraphStyle(name="H4Center", parent=styles["Heading4"], alignment=1))

    return styles

