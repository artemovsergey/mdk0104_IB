"""Сборка презентации из Markdown-исходника колоды."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from pptx import Presentation
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

from coursekit.config import CourseConfig
from coursekit.render_pptx import (
    ACCENT,
    CODE_BG,
    FONT_BODY,
    FONT_TITLE,
    NAVY,
    SLIDE_H,
    SLIDE_W,
    WHITE,
    add_rect,
    code_box,
    header_band,
)


@dataclass
class Slide:
    title: str
    subtitle: str = ""
    bullets: list[str] = field(default_factory=list)
    code: list[str] = field(default_factory=list)
    image: str | None = None
    notes: str = ""


_FENCE = re.compile(r"^\s*(`{3,})")
_NOTES = re.compile(r"<!--\s*notes:(.*?)-->", re.DOTALL)
_IMAGE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")


def _clean(text: str) -> str:
    text = text.replace("`", "")
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"__(.+?)__", r"\1", text)
    return text.strip()


def _split_blocks(text: str) -> list[str]:
    blocks: list[str] = []
    current: list[str] = []
    fence: str | None = None
    for line in text.splitlines():
        match = _FENCE.match(line)
        if match:
            marker = match.group(1)[0]
            if fence is None:
                fence = marker
            elif fence == marker:
                fence = None
        if fence is None and line.strip() == "---":
            blocks.append("\n".join(current))
            current = []
            continue
        current.append(line)
    blocks.append("\n".join(current))
    return [block for block in blocks if block.strip()]


def parse_deck(text: str) -> list[Slide]:
    blocks = _split_blocks(text)
    slides: list[Slide] = []
    for index, block in enumerate(blocks):
        notes_match = _NOTES.search(block)
        notes = notes_match.group(1).strip() if notes_match else ""
        block = _NOTES.sub("", block)
        lines = block.splitlines()

        if index == 0:
            title = next((line[2:].strip() for line in lines if line.startswith("# ")), "Презентация")
            subtitle = " ".join(
                _clean(line) for line in lines
                if line.strip() and not line.startswith("#") and not line.startswith("**Подзаголовок")
            )
            slides.append(Slide(title=_clean(title), subtitle=subtitle, notes=notes))
            continue

        title = ""
        start = 0
        for number, line in enumerate(lines):
            if line.startswith("## "):
                title = _clean(line[3:])
                start = number + 1
                break
        slide = Slide(title=title, notes=notes)
        in_code = False
        code: list[str] = []
        for line in lines[start:]:
            if _FENCE.match(line):
                in_code = not in_code
                if not in_code and code:
                    slide.code = code
                continue
            if in_code:
                code.append(line)
                continue
            image = _IMAGE.search(line)
            if image:
                slide.image = image.group(1).strip("<>")
                continue
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if re.match(r"^([-*+]|\d+\.)\s+", stripped):
                stripped = re.sub(r"^([-*+]|\d+\.)\s+", "", stripped)
            slide.bullets.append(_clean(stripped))
        slides.append(slide)
    return slides


def _words(slide: Slide) -> int:
    return sum(len(item.split()) for item in slide.bullets)


def _title_slide(slide: Slide, cfg: CourseConfig, prs: Presentation) -> None:
    page = prs.slides.add_slide(prs.slide_layouts[6])
    add_rect(page, 0, 0, SLIDE_W, SLIDE_H, NAVY)
    add_rect(page, Inches(0.8), Inches(1.55), Inches(0.12), Inches(2.5), ACCENT)
    box = page.shapes.add_textbox(Inches(1.15), Inches(1.45), Inches(11.2), Inches(1.7))
    frame = box.text_frame
    frame.word_wrap = True
    run = frame.paragraphs[0].add_run()
    run.text = slide.title
    run.font.size = Pt(38)
    run.font.bold = True
    run.font.name = FONT_TITLE
    run.font.color.rgb = WHITE
    sub = page.shapes.add_textbox(Inches(1.15), Inches(3.2), Inches(11.2), Inches(1.0))
    text = sub.text_frame
    text.word_wrap = True
    run = text.paragraphs[0].add_run()
    run.text = slide.subtitle or cfg.title
    run.font.size = Pt(20)
    run.font.name = FONT_BODY
    run.font.color.rgb = WHITE
    footer = page.shapes.add_textbox(Inches(1.15), Inches(6.35), Inches(11.2), Inches(0.5))
    run = footer.text_frame.paragraphs[0].add_run()
    run.text = f"{cfg.code} · {cfg.group} · {cfg.year}"
    run.font.size = Pt(14)
    run.font.name = FONT_BODY
    run.font.color.rgb = WHITE


def _content_slide(slide: Slide, cfg: CourseConfig, prs: Presentation) -> None:
    page = prs.slides.add_slide(prs.slide_layouts[6])
    header_band(page, cfg.code, slide.title)

    top = Inches(1.45)
    if slide.code:
        if slide.bullets:
            box = page.shapes.add_textbox(Inches(0.7), top, Inches(11.9), Inches(1.2))
            frame = box.text_frame
            frame.word_wrap = True
            frame.paragraphs[0].text = " · ".join(slide.bullets)
            frame.paragraphs[0].font.size = Pt(16)
            frame.paragraphs[0].font.name = FONT_BODY
            top = Inches(2.55)
        avail = SLIDE_H - top - Inches(0.45)
        size = 14 if len(slide.code) <= 10 else 11
        # панель кода по высоте фрагмента, а не до низа слайда
        needed = int(Inches(len(slide.code) * size * 1.35 / 72 + 0.45))
        height = min(int(avail), needed)
        code_top = Emu(int(top) + (int(avail) - height) // 2)
        code_box(page, Inches(0.7), code_top, Inches(11.9), Emu(height), slide.code, size=size)
        return

    if slide.image:
        path = Path(slide.image)
        if path.exists():
            # вписываем по обеим сторонам: широкая схема не должна уезжать за край
            pic = page.shapes.add_picture(
                str(path), Inches(1.4), top, height=SLIDE_H - top - Inches(0.5)
            )
            max_w = SLIDE_W - Inches(1.4)
            if pic.width > max_w:
                ratio = max_w / pic.width
                pic.width = int(pic.width * ratio)
                pic.height = int(pic.height * ratio)
            pic.left = int((SLIDE_W - pic.width) / 2)
            avail_h = SLIDE_H - top - Inches(0.5)
            pic.top = int(top + max(0, (avail_h - pic.height) / 2))
        return

    size = 24 if len(slide.bullets) <= 6 else 20 if len(slide.bullets) <= 9 else 17
    box = page.shapes.add_textbox(Inches(0.75), top, Inches(11.8), SLIDE_H - top - Inches(0.4))
    frame = box.text_frame
    frame.word_wrap = True
    for index, item in enumerate(slide.bullets):
        paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
        paragraph.text = f"•  {item}"
        paragraph.font.size = Pt(size)
        paragraph.font.name = FONT_BODY
        paragraph.space_after = Pt(10)
        paragraph.line_spacing = 1.15


def build_deck(
    markdown: str,
    cfg: CourseConfig,
    out: Path,
    base_dir: Path | None = None,
) -> list[str]:
    slides = parse_deck(markdown)
    warnings: list[str] = []
    if not 12 <= len(slides) <= 24:
        warnings.append(f"слайдов {len(slides)}: норма 12–24 на 2 часа")
    base = base_dir or Path(".")
    for index, slide in enumerate(slides, start=1):
        if _words(slide) > 70:
            warnings.append(f"слайд {index}: больше 70 слов ({_words(slide)})")
        if len(slide.code) > 12:
            warnings.append(f"слайд {index}: код длиннее 12 строк ({len(slide.code)})")
        if slide.image:
            path = Path(slide.image)
            if not path.is_absolute():
                path = base / path
            if not path.exists():
                warnings.append(f"слайд {index}: нет файла {slide.image}")
            slide.image = str(path)

    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H
    for index, slide in enumerate(slides):
        if index == 0:
            _title_slide(slide, cfg, prs)
        else:
            _content_slide(slide, cfg, prs)
        if slide.notes:
            prs.slides[index].notes_slide.notes_text_frame.text = slide.notes

    out.parent.mkdir(parents=True, exist_ok=True)
    prs.save(out)
    return warnings
