"""Сборка презентаций PPTX из модели документа."""

from __future__ import annotations

import re
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

from coursekit.config import CourseConfig
from coursekit.model import Document, Section

NAVY = RGBColor(0x14, 0x2D, 0x4E)
NAVY2 = RGBColor(0x1F, 0x3A, 0x5F)
ACCENT = RGBColor(0x2E, 0x7D, 0xB5)
ACCENT_LIGHT = RGBColor(0xE4, 0xF1, 0xFA)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
INK = RGBColor(0x21, 0x25, 0x29)
MUTED = RGBColor(0x55, 0x66, 0x77)
LINE = RGBColor(0xD8, 0xE0, 0xE8)
CONSPECT_FILL = RGBColor(0xFF, 0xF7, 0xE1)
CONSPECT_BORDER = RGBColor(0xE8, 0xA3, 0x1D)
CONSPECT_TEXT = RGBColor(0x6E, 0x4F, 0x00)
CODE_BG = RGBColor(0xF2, 0xF4, 0xF8)

SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)

FONT_TITLE = "Segoe UI Semibold"
FONT_BODY = "Segoe UI"
FONT_CODE = "Consolas"


# ---------------- low-level helpers ----------------
def _set_fill(shape, color):
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()


def _no_line(shape):
    shape.line.fill.background()


def add_rect(slide, x, y, w, h, color, line_color=None, line_w=None, shadow=False, round_=False):
    shp_type = MSO_SHAPE.ROUNDED_RECTANGLE if round_ else MSO_SHAPE.RECTANGLE
    shp = slide.shapes.add_shape(shp_type, x, y, w, h)
    if round_:
        try:
            shp.adjustments[0] = 0.06
        except Exception:
            pass
    _set_fill(shp, color)
    if line_color is None:
        _no_line(shp)
    else:
        shp.line.color.rgb = line_color
        shp.line.width = line_w or Pt(1)
    shp.shadow.inherit = False
    return shp


def add_text(slide, x, y, w, h, anchor=MSO_ANCHOR.TOP):
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = Inches(0.05)
    tf.margin_right = Inches(0.05)
    tf.margin_top = Inches(0.03)
    tf.margin_bottom = Inches(0.03)
    return tb, tf


def _add_runs(p, text, size, color, bold=False, italic=False, font=FONT_BODY):
    """Parse **bold** inline markup into runs."""
    parts = re.split(r"(\*\*.*?\*\*)", text)
    for part in parts:
        if not part:
            continue
        is_bold = part.startswith("**") and part.endswith("**") and len(part) >= 4
        actual = part[2:-2] if is_bold else part
        r = p.add_run()
        r.text = actual
        r.font.size = Pt(size)
        r.font.color.rgb = color
        r.font.bold = bold or is_bold
        r.font.italic = italic
        r.font.name = font
    return p


def para(tf, text, size=18, color=INK, bold=False, italic=False, align=PP_ALIGN.LEFT,
         space_after=6, space_before=0, font=FONT_BODY, first=False, level=0, line=None):
    p = tf.paragraphs[0] if first and not tf.paragraphs[0].runs else tf.add_paragraph()
    p.alignment = align
    p.space_after = Pt(space_after)
    p.space_before = Pt(space_before)
    p.level = level
    if line:
        p.line_spacing = line
    _add_runs(p, text, size, color, bold=bold, italic=italic, font=font)
    return p


def bullets(tf, items, size=16, color=INK, bullet_char="\u2022", space_after=4,
            space_before=0, first=False, line=1.0, bold_lead=False):
    first_done = first
    for item in items:
        p = tf.paragraphs[0] if (first_done and not tf.paragraphs[0].runs) else tf.add_paragraph()
        first_done = False
        p.alignment = PP_ALIGN.LEFT
        p.space_after = Pt(space_after)
        p.space_before = Pt(space_before)
        p.line_spacing = line
        # bullet char run
        rb = p.add_run()
        rb.text = bullet_char + "  "
        rb.font.size = Pt(size)
        rb.font.color.rgb = ACCENT
        rb.font.bold = True
        rb.font.name = FONT_BODY
        # text: support leading **bold** term then rest
        if bold_lead and item.startswith("**"):
            m = re.match(r"^(\*\*.*?\*\*)(.*)$", item, re.S)
            if m:
                _add_runs(p, m.group(1), size, color, bold=True, font=FONT_BODY)
                _add_runs(p, m.group(2), size, color, bold=False, font=FONT_BODY)
            else:
                _add_runs(p, item, size, color, bold=False, font=FONT_BODY)
        else:
            _add_runs(p, item, size, color, bold=False, font=FONT_BODY)
    return tf


def header_band(slide, kicker, title, accent=ACCENT):
    """Top navy band with kicker + title."""
    band = add_rect(slide, 0, 0, SLIDE_W, Inches(1.18), NAVY, round_=False)
    # accent underline
    add_rect(slide, 0, Inches(1.18), SLIDE_W, Inches(0.06), accent)
    _, tf = add_text(slide, Inches(0.55), Inches(0.14), Inches(12.2), Inches(0.4), anchor=MSO_ANCHOR.MIDDLE)
    para(tf, kicker, size=12, color=RGBColor(0x9F, 0xC5, 0xE6), bold=True, first=True, space_after=0)
    _, tf2 = add_text(slide, Inches(0.55), Inches(0.52), Inches(12.2), Inches(0.6), anchor=MSO_ANCHOR.MIDDLE)
    para(tf2, title, size=27, color=WHITE, bold=True, first=True, space_after=0)


def conspect_box(slide, items, y=Inches(5.35), h=Inches(1.75), x=Inches(0.55), w=Inches(12.25)):
    """ЧТО ЗАКОНСПЕКТИРОВАТЬ callout box."""
    box = add_rect(slide, x, y, w, h, CONSPECT_FILL, line_color=CONSPECT_BORDER, line_w=Pt(1.25), round_=True)
    # left accent bar
    add_rect(slide, x, y, Inches(0.09), h, CONSPECT_BORDER)
    _, tf = add_text(slide, x + Inches(0.3), y + Inches(0.12), w - Inches(0.55), h - Inches(0.24),
                     anchor=MSO_ANCHOR.TOP)
    para(tf, "ЧТО ЗАКОНСПЕКТИРОВАТЬ \u2014 запомни и запиши в конспект:", size=13, color=CONSPECT_BORDER,
         bold=True, first=True, space_after=4)
    bullets(tf, items, size=13, color=CONSPECT_TEXT, bullet_char="\u25AA", space_after=3,
            space_before=0, first=False, line=1.0)
    return box


def code_box(slide, x, y, w, h, code_lines, size=10.5):
    """Monospace code block on a slide, split if too tall."""
    box = add_rect(slide, x, y, w, h, CODE_BG, line_color=LINE, line_w=Pt(0.75), round_=True)
    _, tf = add_text(slide, x + Inches(0.25), y + Inches(0.18), w - Inches(0.5), h - Inches(0.36),
                     anchor=MSO_ANCHOR.TOP)
    tf.word_wrap = False
    first = True
    max_lines = max(1, int(h.inches * (72 / (size * 1.25))) - 2)
    for ln in code_lines:
        if not first:
            p = tf.add_paragraph()
        else:
            p = tf.paragraphs[0]
            first = False
        p.alignment = PP_ALIGN.LEFT
        p.space_after = Pt(1)
        p.line_spacing = 1.0
        r = p.add_run()
        r.text = ln
        r.font.size = Pt(size)
        r.font.color.rgb = RGBColor(0x1F, 0x2D, 0x3D)
        r.font.name = FONT_CODE
    return box


# ---------------- markdown parsing ----------------
def clean_md(text):
    return re.sub(r"\*\*", "", text).strip()


def extract_conspect(text_blocks):
    """Pull bolded terms and short definition-ish sentences for the конспект box."""
    terms = []
    for (_t, content) in text_blocks:
        if isinstance(content, list):
            joined = " ".join(content)
        else:
            joined = content
        for m in re.finditer(r"\*\*(.+?)\*\*", joined):
            t = clean_md(m.group(1))
            if 3 < len(t) < 60 and t not in terms:
                terms.append(t)
    # definition sentences
    defs = []
    for (_t, content) in text_blocks:
        if isinstance(content, list):
            joined = " ".join(content)
        else:
            joined = content
        for sent in re.split(r"(?<=[.!?])\s+", joined):
            s = clean_md(sent).strip()
            if len(s) < 120 and any(k in s.lower() for k in ["\u2014 это", "это ", "представляет", "является", "зачем", "обязателен", "нормальный способ"]):
                if s not in defs:
                    defs.append(s)
    items = []
    for d in defs[:4]:
        items.append(d)
    for t in terms:
        if len(items) >= 7:
            break
        if t not in items:
            items.append(t)
    return items[:7]

def _bullet_slide(prs, layout, section_title, items, num):
    for start in range(0, len(items), 12):
        chunk = items[start : start + 12]
        s = prs.slides.add_slide(layout)
        header_band(s, f"Раздел лекции {num}", section_title)
        _, tf = add_text(s, Inches(0.55), Inches(1.5), Inches(7.6), Inches(3.9), anchor=MSO_ANCHOR.TOP)
        bullets(tf, chunk, size=15 if len(chunk) <= 8 else 13, first=True, space_after=5, line=1.05)
        conspect_items = extract_conspect([("bullets", chunk)])
        conspect_box(s, conspect_items if conspect_items else ["Ключевые термины раздела."],
                     y=Inches(5.55), h=Inches(1.55))
    return s


def _para_slide(prs, layout, section_title, paras, num):
    s = prs.slides.add_slide(layout)
    header_band(s, f"Раздел лекции {num}", section_title)
    _, tf = add_text(s, Inches(0.55), Inches(1.5), Inches(7.6), Inches(3.9), anchor=MSO_ANCHOR.TOP)
    first = True
    for p in paras:
        if p.strip():
            para(tf, p, size=15, first=first, space_after=7, line=1.1)
            first = False
    conspect_items = extract_conspect([("para", paras)])
    conspect_box(s, conspect_items if conspect_items else ["Ключевые термины раздела."],
                 y=Inches(5.55), h=Inches(1.55))
    return s


def _table_slide(prs, layout, section_title, rows, num):
    s = prs.slides.add_slide(layout)
    header_band(s, f"Раздел лекции {num}", section_title)
    _, tf = add_text(s, Inches(0.55), Inches(1.5), Inches(12.25), Inches(4.0), anchor=MSO_ANCHOR.TOP)
    first = True
    for row in rows:
        cells = [c.strip().strip("|").strip() for c in row.strip().strip("|").split("|")]
        line = " | ".join(cells)
        para(tf, line, size=13, first=first, space_after=3, line=1.05)
        first = False
    conspect_box(s, ["Таблица \u2014 справочник ключевых значений раздела."], y=Inches(5.55), h=Inches(1.55))
    return s


def _code_slides(prs, layout, section_title, lines, num):
    """Split code into chunks; each chunk = one slide with header + code + conspect."""
    chunk_size = 24
    for start in range(0, len(lines), chunk_size):
        chunk = lines[start:start + chunk_size]
        s = prs.slides.add_slide(layout)
        header_band(s, f"Раздел лекции {num}", section_title + (" \u00b7 код" if start == 0 else " \u00b7 код (продолжение)"))
        code_box(s, Inches(0.55), Inches(1.5), Inches(12.25), Inches(3.9), chunk, size=10.5)
        conspect_box(s, ["Пример кода \u2014 повторить структуру и имена сущностей в конспекте."],
                     y=Inches(5.55), h=Inches(1.55))

_SKIP_SECTIONS = {
    "План лекции",
    "Цель лекции",
    "Аудитория",
    "Материалы",
    "Резюме",
    "Контрольные вопросы",
}


def _clean_items(body: str) -> list[str]:
    items: list[str] = []
    for line in body.splitlines():
        line = line.strip()
        if not line:
            continue
        line = re.sub(r"^[-*+]\s+", "", line)
        line = re.sub(r"^\d+[.)]\s*", "", line)
        line = clean_md(line)
        if line:
            items.append(line)
    return items


def _blocks(body: str) -> list[tuple[str, list[str]]]:
    blocks: list[tuple[str, list[str]]] = []
    fence = False
    code: list[str] = []
    bullets: list[str] = []
    paras: list[str] = []
    table: list[str] = []

    def flush(kind: str) -> None:
        nonlocal code, bullets, paras, table
        if kind == "code" and code:
            blocks.append(("code", code))
            code = []
        elif kind == "bullets" and bullets:
            blocks.append(("bullets", bullets))
            bullets = []
        elif kind == "para" and paras:
            blocks.append(("para", paras))
            paras = []
        elif kind == "table" and table:
            blocks.append(("table", table))
            table = []

    for raw in body.splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            if fence:
                flush("code")
                fence = False
            else:
                flush("para")
                flush("bullets")
                flush("table")
                fence = True
            continue
        if fence:
            code.append(line)
            continue
        if not stripped:
            flush("para")
            flush("bullets")
            flush("table")
            continue
        if stripped.startswith("|"):
            flush("para")
            flush("bullets")
            table.append(stripped)
            continue
        match = re.match(r"^[-*+]\s+(.*)$", stripped)
        if match:
            flush("para")
            flush("table")
            bullets.append(clean_md(match.group(1)))
            continue
        flush("bullets")
        flush("table")
        paras.append(clean_md(stripped))

    flush("para")
    flush("bullets")
    flush("table")
    flush("code")
    return blocks


def _canonical(doc: Document, name: str) -> Section | None:
    for section in doc.sections:
        if section.canonical == name:
            return section
    return None


def _plain(section: Section | None, fallback: str = "") -> str:
    if not section:
        return fallback
    text = " ".join(_clean_items(section.body))
    return text or fallback


def _document_to_data(doc: Document, cfg: CourseConfig) -> dict:
    goal = _plain(_canonical(doc, "Цель лекции"), "Цель лекции не указана в источнике.")
    audience = _plain(
        _canonical(doc, "Аудитория"),
        f"Студенты специальности {cfg.specialty}, группа {cfg.group}.",
    )

    plan_items = _clean_items(_canonical(doc, "План лекции").body) if _canonical(doc, "План лекции") else []
    content = [section for section in doc.sections if section.canonical not in _SKIP_SECTIONS]
    if not plan_items:
        plan_items = [re.sub(r"^\d+[.)]\s*", "", section.title) for section in content]
    plan = [(index + 1, title, "") for index, title in enumerate(plan_items)]

    sections = [
        {"title": section.title, "blocks": _blocks(section.body)} for section in content
    ]

    return {
        "number": doc.number,
        "title": doc.title,
        "goal": goal,
        "audience": audience,
        "plan": plan,
        "sections": sections,
        "summary": _clean_items(_canonical(doc, "Резюме").body) if _canonical(doc, "Резюме") else [],
        "questions": _clean_items(_canonical(doc, "Контрольные вопросы").body)
        if _canonical(doc, "Контрольные вопросы")
        else [],
        "materials": _clean_items(_canonical(doc, "Материалы").body)
        if _canonical(doc, "Материалы")
        else [],
    }


def _add_notes(prs) -> None:
    for slide in prs.slides:
        text = "\n".join(
            shape.text for shape in slide.shapes if shape.has_text_frame and shape.text.strip()
        )
        slide.notes_slide.notes_text_frame.text = text[:4000]


def build_pptx(doc: Document, cfg: CourseConfig, out: Path) -> Path:
    data = _document_to_data(doc, cfg)
    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H
    blank = prs.slide_layouts[6]

    num = data["number"] or 0
    title = data["title"]

    slide = prs.slides.add_slide(blank)
    add_rect(slide, 0, 0, SLIDE_W, SLIDE_H, NAVY)
    add_rect(slide, 0, Inches(4.6), SLIDE_W, Inches(0.06), ACCENT)
    _, tf = add_text(slide, Inches(0.9), Inches(1.5), Inches(11.5), Inches(1.2), anchor=MSO_ANCHOR.MIDDLE)
    para(
        tf,
        f"{cfg.code} \u00b7 {cfg.title} \u00b7 2 академических часа (90 мин)",
        size=15,
        color=RGBColor(0xBF, 0xD4, 0xE8),
        bold=True,
        first=True,
        space_after=0,
    )
    _, tf = add_text(slide, Inches(0.9), Inches(2.35), Inches(11.5), Inches(1.6), anchor=MSO_ANCHOR.MIDDLE)
    para(tf, f"Лекция {num}", size=40, color=RGBColor(0x9F, 0xC5, 0xE6), bold=True, first=True, space_after=2)
    para(tf, title, size=30, color=WHITE, bold=True, space_after=0)
    _, tf = add_text(slide, Inches(0.9), Inches(6.35), Inches(11.5), Inches(0.8), anchor=MSO_ANCHOR.TOP)
    para(
        tf,
        "Каждый слайд содержит выделенный блок \u201cЧТО ЗАКОНСПЕКТИРОВАТЬ\u201d "
        "\u2014 определения и ключевые термины, которые студенты записывают в конспект.",
        size=13,
        color=RGBColor(0xD8, 0xE4, 0xF0),
        first=True,
        space_after=0,
        line=1.1,
    )

    slide = prs.slides.add_slide(blank)
    header_band(slide, "Цель лекции", data["goal"][:90] + ("\u2026" if len(data["goal"]) > 90 else ""))
    _, tf = add_text(slide, Inches(0.55), Inches(1.55), Inches(12.25), Inches(3.6), anchor=MSO_ANCHOR.TOP)
    para(tf, data["goal"], size=19, color=INK, first=True, space_after=0, line=1.15)
    conspect_box(slide, [data["goal"]], y=Inches(5.5), h=Inches(1.55))

    slide = prs.slides.add_slide(blank)
    header_band(slide, "Аудитория", "Кому предназначена лекция")
    _, tf = add_text(slide, Inches(0.55), Inches(1.55), Inches(12.25), Inches(3.4), anchor=MSO_ANCHOR.TOP)
    para(tf, data["audience"], size=18, color=INK, first=True, space_after=0, line=1.15)
    conspect_box(slide, ["Требования: пройдены предыдущие лекции курса."], y=Inches(5.35), h=Inches(1.6))

    slide = prs.slides.add_slide(blank)
    header_band(slide, "План лекции", "О чём пойдёт речь")
    items = [f"{n}. {t}" for (n, t, _b) in data["plan"]]
    _, tf = add_text(slide, Inches(0.55), Inches(1.55), Inches(12.25), Inches(3.5), anchor=MSO_ANCHOR.TOP)
    bullets(tf, items, size=17, first=True, space_after=8, line=1.05)
    conspect_box(
        slide,
        ["План лекции \u2014 последовательность тем, которые разбираются на паре (90 мин)."],
        y=Inches(5.35),
        h=Inches(1.6),
    )

    for sub in data["sections"]:
        slide = prs.slides.add_slide(blank)
        header_band(slide, f"Раздел лекции {num}", sub["title"])
        _, tf = add_text(slide, Inches(0.55), Inches(1.6), Inches(12.25), Inches(3.3), anchor=MSO_ANCHOR.TOP)
        para(tf, sub["title"], size=20, color=ACCENT, bold=True, first=True, space_after=8, line=1.1)
        para(
            tf,
            "Ниже \u2014 разбор по пунктам с примерами кода. Каждый слайд содержит блок конспекта.",
            size=14,
            color=MUTED,
            space_after=0,
            line=1.1,
        )
        conspect_box(slide, [f"{sub['title']} \u2014 ключевая тема раздела."], y=Inches(5.35), h=Inches(1.6))

        pending_para: list[str] = []
        pending_bullets: list[str] = []
        pending_table: list[str] = []
        pending_code: list[str] = []

        def flush_pending() -> None:
            nonlocal pending_para, pending_bullets, pending_table, pending_code
            if pending_bullets:
                _bullet_slide(prs, blank, sub["title"], pending_bullets, num)
                pending_bullets = []
            if pending_para:
                _para_slide(prs, blank, sub["title"], pending_para, num)
                pending_para = []
            if pending_table:
                _table_slide(prs, blank, sub["title"], pending_table, num)
                pending_table = []
            if pending_code:
                _code_slides(prs, blank, sub["title"], pending_code, num)
                pending_code = []

        for btype, content in sub["blocks"]:
            if btype == "bullets":
                if pending_para:
                    flush_pending()
                pending_bullets.extend(content)
            elif btype == "para":
                if pending_bullets:
                    flush_pending()
                pending_para.extend(content)
            elif btype == "table":
                flush_pending()
                pending_table.extend(content)
                flush_pending()
            elif btype == "code":
                if pending_para or pending_bullets:
                    flush_pending()
                pending_code.extend(content)
                if len(pending_code) >= 22:
                    flush_pending()
        flush_pending()

    slide = prs.slides.add_slide(blank)
    header_band(slide, "Резюме", "Что запомнить с лекции")
    conspect_items = [clean_md(item) for item in data["summary"]]
    if not conspect_items:
        conspect_items = [
            "Основные определения лекции см. в блоках \u201cЧТО ЗАКОНСПЕКТИРОВАТЬ\u201d на слайдах выше."
        ]
    _, tf = add_text(slide, Inches(0.55), Inches(1.55), Inches(12.25), Inches(3.5), anchor=MSO_ANCHOR.TOP)
    bullets(tf, conspect_items, size=16, first=True, space_after=6, line=1.08, bold_lead=True)
    conspect_box(slide, conspect_items[:7], y=Inches(5.35), h=Inches(1.6))

    slide = prs.slides.add_slide(blank)
    header_band(slide, "Контрольные вопросы", "Для самопроверки")
    questions = data["questions"] or ["Нет контрольных вопросов в источнике."]
    _, tf = add_text(slide, Inches(0.55), Inches(1.55), Inches(12.25), Inches(3.5), anchor=MSO_ANCHOR.TOP)
    bullets(tf, questions, size=15, first=True, space_after=5, line=1.05, bullet_char="\u2794")
    conspect_box(
        slide,
        ["Ответить на все вопросы \u2014 критерий завершения лекции."],
        y=Inches(5.35),
        h=Inches(1.6),
    )

    slide = prs.slides.add_slide(blank)
    header_band(slide, "Материалы презентации", "Исходники и ссылки")
    materials = data["materials"] or ["Полный код примера \u2014 в репозитории курса."]
    _, tf = add_text(slide, Inches(0.55), Inches(1.55), Inches(12.25), Inches(3.4), anchor=MSO_ANCHOR.TOP)
    bullets(tf, materials, size=16, first=True, space_after=6, line=1.08)
    conspect_box(
        slide,
        ["Материалы презентации \u2014 ссылки и код для самостоятельного изучения."],
        y=Inches(5.35),
        h=Inches(1.6),
    )

    _add_notes(prs)
    out.parent.mkdir(parents=True, exist_ok=True)
    prs.save(out)
    return out
