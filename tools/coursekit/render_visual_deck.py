"""Визуальная сборка колоды: Markdown → HTML → PDF/PNG → PPTX.

Каждый слайд рендерится как полноэкранное изображение 1600×900,
заметки докладчика переносятся в PPTX текстом. Нативный текстовый
рендер (render_deck.build_deck) этой модуль не затрагивает.

Зависимости от внешнего окружения: google-chrome, pdftoppm, pdfinfo.
"""

from __future__ import annotations

import html as html_mod
import re
import shutil
import struct
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from pptx import Presentation
from pptx.util import Inches

from coursekit.config import CourseConfig
from coursekit.render_deck import (
    _FENCE,
    _IMAGE,
    _NOTES,
    Slide,
    _split_blocks,
    parse_deck,
)

TEMPLATE_DIR = Path(__file__).parent / "templates" / "deck"

SLIDE_W_PX = 1600
SLIDE_H_PX = 900

_NUM_CLASSES = ["num-cyan", "num-orange", "num-green", "num-purple", "num-red", "num-blue"]
_N_CLASSES = ["n-cyan", "n-orange", "n-green", "n-purple", "n-red", "n-blue"]

_CHIPS = re.compile(r"<!--\s*chips:\s*(.*?)-->", re.DOTALL)
_FENCE_BLOCK = re.compile(r"^\s*`{3,}.*$|^\s*~{3,}.*$", re.MULTILINE)
_IMAGE_ALT = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
_WEEK = re.compile(r"(?:Неделя|week)[- ]*(\d+)", re.IGNORECASE)

_LAYERS_ICON = (
    '<svg class="icon-corner" width="58" height="58" viewBox="0 0 24 24" fill="none"'
    ' stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">'
    '<polygon points="12 2.6 21 7.3 12 12 3 7.3" stroke="#8B5CF6"/>'
    '<polyline points="3 12.2 12 16.9 21 12.2" stroke="#22D3EE"/>'
    '<polyline points="3 16.7 12 21.4 21 16.7" stroke="#3B82F6"/></svg>'
)
_TARGET_ICON = (
    '<svg width="34" height="34" viewBox="0 0 24 24" fill="none">'
    '<circle cx="12" cy="12" r="9.2" stroke="#B45309" stroke-width="1.8"/>'
    '<circle cx="12" cy="12" r="5" stroke="#B45309" stroke-width="1.8"/>'
    '<circle cx="12" cy="12" r="1.6" fill="#B45309"/></svg>'
)

# формула в панель кода титульного слайда, если в исходнике кода нет
_DEFAULT_TITLE_CODE = (
    '<span class="cmt"># контекст — это не «вся история»</span>\n'
    '<span class="var">context</span> <span class="op">=</span>'
    ' <span class="kw">system</span> <span class="op">+</span>'
    ' <span class="kw">rules</span> <span class="op">+</span>'
    ' <span class="kw">task</span> <span class="op">+</span>'
    ' <span class="kw">history</span> <span class="op">+</span>'
    ' <span class="kw">tools</span>'
)


# ---------------------------------------------------------------- разбор

def extract_chips(text: str) -> tuple[str, list[str]]:
    """Вырезает мета-комментарий ``<!-- chips: a, b -->`` из исходника."""
    match = _CHIPS.search(text)
    if not match:
        return text, []
    chips = [item.strip() for item in match.group(1).split(",") if item.strip()]
    cleaned = _CHIPS.sub("", text)
    return cleaned, chips


def _strip_code_fences(text: str) -> str:
    """Убирает содержимое fenced-блоков, чтобы не ловить картинки в коде."""
    lines: list[str] = []
    in_fence = False
    for line in text.splitlines():
        if re.match(r"^\s*(`{3,}|~{3,})", line):
            in_fence = not in_fence
            continue
        if not in_fence:
            lines.append(line)
    return "\n".join(lines)


def extract_image_alts(text: str) -> list[tuple[str, str]]:
    """Пары (alt, src) всех картинок исходника в порядке следования."""
    return [
        (alt.strip(), src.strip("<>"))
        for alt, src in _IMAGE_ALT.findall(_strip_code_fences(text))
    ]


_BULLET_MARK = re.compile(r"^([-*+]|\d+\.)\s+")


def raw_bullets_by_slide(text: str) -> list[list[str]]:
    """Пункты с сохранением инлайн-разметки: parse_deck вычищает её в _clean."""
    blocks = [block for block in _split_blocks(text) if block.strip()]
    result: list[list[str]] = []
    for index, block in enumerate(blocks):
        if index == 0:
            result.append([])
            continue
        block = _NOTES.sub("", block)
        lines = block.splitlines()
        start = 0
        for number, line in enumerate(lines):
            if line.startswith("## "):
                start = number + 1
                break
        bullets: list[str] = []
        in_code = False
        for line in lines[start:]:
            if _FENCE.match(line):
                in_code = not in_code
                continue
            if in_code:
                continue
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or _IMAGE.search(line):
                continue
            bullets.append(_BULLET_MARK.sub("", stripped))
        result.append(bullets)
    return result


# ---------------------------------------------------------------- макеты

def choose_layout(slide: Slide, index: int) -> str:
    if index == 0:
        return "title"
    title = slide.title.lower()
    if "план" in title:
        return "plan"
    if title.startswith("резюме"):
        return "summary"
    if title.startswith("вопросы"):
        return "questions"
    if slide.image:
        return "image"
    if slide.code:
        return "split-code" if len(slide.bullets) >= 2 else "code-full"
    if len(slide.bullets) >= 4:
        return "cards"
    if len(slide.bullets) >= 1:
        return "statement"
    return "cards"


def _kicker(cfg: CourseConfig, slides: list[Slide], source: Path | None) -> str:
    """Строка «Agentic SDLC · Неделя 2» для пилюли и титула."""
    sources = [slides[0].title if slides else ""]
    if source is not None:
        sources.append(str(source))
    for text in sources:
        match = _WEEK.search(text)
        if match:
            return f"{cfg.code} · Неделя {int(match.group(1))}"
    return cfg.code


def _auto_chips(slides: list[Slide]) -> list[str]:
    """Чипы титула по умолчанию — первые слова пунктов плана."""
    for slide in slides[1:3]:
        if slide.bullets:
            chips: list[str] = []
            for bullet in slide.bullets[:4]:
                word = bullet.split()[0] if bullet.split() else ""
                if word:
                    chips.append(word)
            if chips:
                return chips
    return []


# ---------------------------------------------------------------- текст

def esc(text: str) -> str:
    return html_mod.escape(text, quote=False)


def inline(text: str) -> str:
    """Экранирует и превращает **жирный** и `код` в HTML."""
    result = esc(text)
    result = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", result)
    result = re.sub(r"`([^`]+)`", r'<span class="inl-code">\1</span>', result)
    return result


def _h_class(title: str) -> str:
    if len(title) <= 46:
        return "h-size-lg"
    if len(title) <= 60:
        return "h-size-md"
    return "h-size-sm"


# ------------------------------------------------------------- подсветка

_CMD_LINE = re.compile(r"^(\s*)(\$\s*)?(dotnet|npm|npx|pnpm|yarn|git|cd|python3?|pip3?|docker|docker-compose|make|curl|pwsh|bash|sh|dotnet-test)(\s|$)")
_TOKEN = re.compile(
    r'(?P<str>"[^"]*"|\'[^\']*\'|`[^`]*`)'
    r"|(?P<flag>\s--?[A-Za-z][\w:.-]*)"
    r"|(?P<num>\b\d+(?:[.,]\d+)*\b)"
)
_STATUS = [
    (re.compile(r"Failed!|Error Message:|error CS\d+|Build FAILED|FAILED|\bActual:"), "fail"),
    (re.compile(r"Passed!|Build succeeded|\bExpected:"), "ok"),
    (re.compile(r"Skipped:|\bwarning\b|No test matches"), "warn"),
]


def _highlight_code(code: list[str]) -> str:
    """Упрощённая подсветка: команды, строки, флаги, числа, статусы."""
    out: list[str] = []
    for raw in code:
        if raw.lstrip().startswith("#"):
            out.append(f'<span class="cmt">{esc(raw)}</span>')
            continue
        line = raw
        prefix = ""
        match = _CMD_LINE.match(line)
        if match:
            prompt = match.group(2) or ""
            command = match.group(3)
            rest = line[match.start(4):]
            line = rest
            prefix = (
                f'{esc(match.group(1))}'
                + (f'<span class="dollar">{esc(prompt)}</span>' if prompt else "")
                + f'<span class="cmd">{esc(command)}</span>'
            )
        pieces: list[str] = [prefix]
        pos = 0
        for token in _TOKEN.finditer(line):
            pieces.append(esc(line[pos:token.start()]))
            kind = token.lastgroup
            pieces.append(f'<span class="{kind}">{esc(token.group())}</span>')
            pos = token.end()
        pieces.append(esc(line[pos:]))
        text = "".join(pieces)
        for pattern, cls in _STATUS:
            text = pattern.sub(lambda m, cls=cls: f'<span class="{cls}">{m.group(0)}</span>', text)
        out.append(text)
    return "\n".join(out)


def _code_filename(code: list[str]) -> str:
    """Имя файла для шапки панели: лог — если есть вывод, иначе скрипт."""
    text = "\n".join(code)
    lowered = text.lower()
    if "playwright" in lowered and ("passed" in lowered or "failed" in lowered):
        return "playwright.log"
    if "build succeeded" in lowered or "build failed" in lowered:
        return "dotnet-build.log"
    if "passed!" in lowered or "failed!" in lowered or "error message:" in lowered:
        return "dotnet-test.log"
    if "warning(s)" in lowered or "error(s)" in lowered:
        return "build.log"
    if any(line.lstrip().startswith("$") for line in code):
        return "terminal.log"
    first_words = set()
    for line in code:
        stripped = line.strip().lstrip("( ")
        if stripped:
            first_words.add(stripped.split(maxsplit=1)[0])
    if first_words and first_words <= {"dotnet", "cd", "npm", "npx", "pnpm", "yarn", "git", "python", "python3", "pip", "docker", "make", "#"}:
        return "commands.sh"
    if any(line.lstrip().startswith("#") for line in code):
        return "script.sh"
    return "console.log"


def _code_panel(code: list[str], name: str | None = None) -> str:
    label = name or _code_filename(code)
    return (
        '<div class="code-panel">'
        '<div class="code-panel-bar">'
        '<span class="dot dot-r"></span><span class="dot dot-y"></span><span class="dot dot-g"></span>'
        f'<span class="code-panel-name">{esc(label)}</span></div>'
        f"<pre>{_highlight_code(code)}</pre></div>"
    )


# ------------------------------------------------------------- слайды

@dataclass
class VisualSlide:
    slide: Slide
    layout: str
    alt: str = ""
    image_path: Path | None = None  # локальная копия для HTML
    raw_bullets: list[str] = field(default_factory=list)

    def texts(self) -> list[str]:
        """Пункты для отрисовки: с инлайн-разметкой, если она сохранилась."""
        return self.raw_bullets or self.slide.bullets


def _footer(title: str, number: int, total: int) -> str:
    return (
        '<div class="footer">'
        f'<span class="footer-title">{esc(title)}</span>'
        f'<span class="footer-page">{number} / {total}</span></div>'
    )


def _header(kicker: str, title: str) -> str:
    return (
        '<div class="header">'
        f'<div class="pill"><span class="pill-dot"></span>{esc(kicker)}</div>'
        f'<h1 class="{_h_class(title)}">{inline(title)}</h1></div>{_LAYERS_ICON}'
    )


def _light_open(extra: str = "") -> str:
    return f'<div class="slide slide--light{extra}">'


def _headline_split(headline: str) -> str:
    """Переносит «Неделя N. » за скобки и подсвечивает градиентом акцент."""
    week = re.match(r"^Неделя\s*\d+\s*[.—-]\s*", headline)
    if week:
        headline = headline[week.end():]
    if ":" in headline and len(headline.split(":")[0]) <= 30:
        head, tail = headline.split(":", 1)
        return f'{esc(head.strip())}: <span class="grad">{inline(tail.strip())}</span>'
    latin = re.search(r"[A-Za-z][A-Za-z0-9._/-]+(?:\s+[A-Za-z][A-Za-z0-9._/-]+)*", headline)
    if latin and latin.start() > 0:
        head, tail = headline[:latin.start()].rstrip(), headline[latin.start():]
        return f"{esc(head)}<span class=\"grad\">{inline(tail)}</span>"
    return inline(headline)


def _title_slide(vs: VisualSlide, cfg: CourseConfig, kicker: str, chips: list[str],
                 subtitle: str, number: int, total: int) -> str:
    headline = vs.slide.title
    plain = re.sub(r"^Неделя\s*\d+\s*[.—-]\s*", "", headline)
    size_class = "" if len(plain) <= 30 else " hd-md" if len(plain) <= 44 else " hd-sm"
    headline_html = _headline_split(headline)
    chip_html = "".join(f"<span>{esc(chip)}</span>" for chip in chips[:4])
    code_html = _DEFAULT_TITLE_CODE if not vs.slide.code else _highlight_code(vs.slide.code)
    badge = cfg.code.split()[0][:2].upper() if cfg.code else "CK"
    return (
        '<div class="slide slide--title">'
        f'<div class="title-kicker">{esc(kicker)}</div>'
        f'<h1 class="title-headline{size_class}">{headline_html}</h1>'
        f'<div class="title-copy"><p class="title-sub">{inline(subtitle)}</p>'
        f'<div class="title-chips">{chip_html}</div></div>'
        '<div class="title-ring title-ring--layers">'
        '<svg width="112" height="112" viewBox="0 0 24 24" fill="none" stroke="#22D3EE"'
        ' stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"'
        ' style="filter: drop-shadow(0 0 14px rgba(34,211,238,.55));">'
        '<polygon points="12 2.6 21 7.3 12 12 3 7.3"/>'
        '<polyline points="3 12.2 12 16.9 21 12.2"/>'
        '<polyline points="3 16.7 12 21.4 21 16.7"/></svg></div>'
        f'<div class="title-ring title-ring--badge"><div class="title-badge">{esc(badge)}</div></div>'
        f'<div class="title-code">{code_html}</div>'
        + _footer(cfg.title, number, total) + "</div>"
    )


def _plan_slide(vs: VisualSlide, cfg: CourseConfig, kicker: str, goal: str,
                number: int, total: int) -> str:
    bullets = vs.texts()
    n = len(bullets)
    if n <= 3:
        cols, rows = max(n, 1), 1
    elif n == 4:
        cols, rows = 2, 2
    elif n == 5:
        cols, rows = 5, 1
    else:
        cols, rows = 3, 2
    dense = " two-rows" if rows > 1 else ""
    cards = ""
    for i, bullet in enumerate(bullets):
        head, sep, desc = bullet.partition(" — ")
        if not sep:
            head, desc = bullet, ""
        body = f"<h3>{inline(head)}</h3>"
        if desc:
            body += f"<p>{inline(desc)}</p>"
        cards += (
            f'<div class="card"><div class="numb {_NUM_CLASSES[i % 6]}">{i + 1}</div>'
            + body + "</div>"
        )
    callout = ""
    if goal:
        callout = (
            '<div class="callout">' + _TARGET_ICON
            + f"<span><b>Цель:</b> {inline(goal)}</span></div>"
        )
    return (
        _light_open(" slide--plan")
        + _header(kicker, vs.slide.title)
        + f'<div class="plan-grid{dense}" style="--cols:{cols}; --rows:{rows}">{cards}</div>'
        + callout + _footer(vs.slide.title, number, total) + "</div>"
    )


def _image_slide(vs: VisualSlide, kicker: str, number: int, total: int) -> str:
    src = ""
    if vs.image_path is not None:
        src = f'<img src="assets/{esc(vs.image_path.name)}" alt="{esc(vs.alt)}">'
    caption = f'<p class="image-caption">{esc(vs.alt)}</p>' if vs.alt else ""
    return (
        _light_open() + _header(kicker, vs.slide.title)
        + f'<div class="image-body">{src}{caption}</div>'
        + _footer(vs.slide.title, number, total) + "</div>"
    )


def _split_code_slide(vs: VisualSlide, kicker: str, number: int, total: int) -> str:
    rules = "".join(
        f'<div class="card"><h3><span class="n {_N_CLASSES[i % 6]}">{i + 1} ·</span>'
        f" {inline(bullet)}</h3></div>"
        for i, bullet in enumerate(vs.texts()[:5])
    )
    return (
        _light_open() + _header(kicker, vs.slide.title)
        + f'<div class="output-cols">{_code_panel(vs.slide.code)}'
        f'<div class="output-rules">{rules}</div></div>'
        + _footer(vs.slide.title, number, total) + "</div>"
    )


def _code_full_slide(vs: VisualSlide, kicker: str, number: int, total: int) -> str:
    takeaway = ""
    if vs.texts():
        takeaway = (
            '<div class="takeaway"><span class="tk-dot"></span>'
            f"<span>{inline(vs.texts()[0])}</span></div>"
        )
    return (
        _light_open() + _header(kicker, vs.slide.title)
        + f'<div class="code-full">{_code_panel(vs.slide.code)}{takeaway}</div>'
        + _footer(vs.slide.title, number, total) + "</div>"
    )


def _cards_slide(vs: VisualSlide, kicker: str, number: int, total: int) -> str:
    n = len(vs.texts())
    font = 23 if n <= 4 else 21 if n <= 6 else 19
    cards = []
    for i, bullet in enumerate(vs.texts()):
        span = ' class="card span2"' if n % 2 == 1 and i == n - 1 else ' class="card"'
        cards.append(
            f"<div{span}><div class=\"numb {_NUM_CLASSES[i % 6]}\">{i + 1}</div>"
            f'<div class="card-text">{inline(bullet)}</div></div>'
        )
    return (
        _light_open() + _header(kicker, vs.slide.title)
        + f'<div class="cards-grid" style="--card-font:{font}px">' + "".join(cards) + "</div>"
        + _footer(vs.slide.title, number, total) + "</div>"
    )


def _summary_slide(vs: VisualSlide, kicker: str, number: int, total: int) -> str:
    cards = "".join(
        f'<div class="card"><div class="numb {_NUM_CLASSES[i % 6]}">{i + 1}</div>'
        f'<div class="card-text">{inline(bullet)}</div></div>'
        for i, bullet in enumerate(vs.texts())
    )
    return (
        _light_open() + _header(kicker, vs.slide.title)
        + f'<div class="summary-grid">{cards}</div>'
        + _footer(vs.slide.title, number, total) + "</div>"
    )


def _questions_slide(vs: VisualSlide, kicker: str, number: int, total: int) -> str:
    cards = "".join(
        f'<div class="card"><div class="numb {_NUM_CLASSES[i % 6]}">{i + 1}</div>'
        f'<div class="card-text">{inline(bullet)}</div></div>'
        for i, bullet in enumerate(vs.texts())
    )
    return (
        _light_open() + _header(kicker, vs.slide.title)
        + f'<div class="questions-grid">{cards}</div>'
        + _footer(vs.slide.title, number, total) + "</div>"
    )


def _statement_slide(vs: VisualSlide, kicker: str, number: int, total: int) -> str:
    bullets = vs.texts()
    main_num = (
        '<div class="numb num-cyan st-num">1</div>' if len(bullets) > 1 else ""
    )
    main = f'<div class="statement-main">{main_num}<div>{inline(bullets[0])}</div></div>' if bullets else ""
    side = ""
    if len(bullets) > 1:
        cards = "".join(
            f'<div class="card"><div class="numb {_NUM_CLASSES[i % 6]}">{i + 1}</div>'
            f'<div class="card-text">{inline(bullet)}</div></div>'
            for i, bullet in enumerate(bullets[1:], start=1)
        )
        side = f'<div class="statement-side">{cards}</div>'
    solo = " statement--solo" if len(bullets) <= 1 else ""
    return (
        _light_open() + _header(kicker, vs.slide.title)
        + f'<div class="statement{solo}">{main}{side}</div>'
        + _footer(vs.slide.title, number, total) + "</div>"
    )


# ------------------------------------------------------------- html

def render_html(visuals: list[VisualSlide], cfg: CourseConfig, kicker: str,
                chips: list[str], goal: str) -> str:
    total = len(visuals)
    parts: list[str] = []
    for number, vs in enumerate(visuals, start=1):
        slide = vs.slide
        if vs.layout == "title":
            subtitle = slide.subtitle or goal or cfg.title
            parts.append(_title_slide(vs, cfg, kicker, chips, subtitle, number, total))
        elif vs.layout == "plan":
            parts.append(_plan_slide(vs, cfg, kicker, goal, number, total))
        elif vs.layout == "image":
            parts.append(_image_slide(vs, kicker, number, total))
        elif vs.layout == "split-code":
            parts.append(_split_code_slide(vs, kicker, number, total))
        elif vs.layout == "code-full":
            parts.append(_code_full_slide(vs, kicker, number, total))
        elif vs.layout == "summary":
            parts.append(_summary_slide(vs, kicker, number, total))
        elif vs.layout == "questions":
            parts.append(_questions_slide(vs, kicker, number, total))
        elif vs.layout == "statement":
            parts.append(_statement_slide(vs, kicker, number, total))
        else:  # cards
            parts.append(_cards_slide(vs, kicker, number, total))
    return (
        '<!DOCTYPE html>\n<html lang="ru">\n<head>\n<meta charset="utf-8">\n'
        f"<title>{esc(cfg.title)}</title>\n"
        '<link rel="stylesheet" href="style.css">\n</head>\n<body>\n'
        + "\n".join(parts) + "\n</body>\n</html>\n"
    )


# ------------------------------------------------------- внешние бинарники

def _run(cmd: list[str], cwd: Path | None = None) -> str:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300, cwd=cwd)
    if result.returncode != 0:
        raise RuntimeError(
            f"не удалось выполнить {' '.join(cmd[:2])}: {result.stderr.strip()[:500]}"
        )
    return result.stdout


def _pdf_page_count(pdf: Path) -> int:
    info = _run(["pdfinfo", str(pdf)])
    match = re.search(r"Pages:\s+(\d+)", info)
    if not match:
        raise RuntimeError(f"pdfinfo не вернул число страниц: {pdf}")
    return int(match.group(1))


def _pdf_size(pdf: Path) -> tuple[float, float]:
    info = _run(["pdfinfo", str(pdf)])
    match = re.search(r"Page size:\s+([\d.]+)\s*x\s*([\d.]+)", info)
    if not match:
        return (0.0, 0.0)
    return (float(match.group(1)), float(match.group(2)))


def _png_size(png: Path) -> tuple[int, int]:
    data = png.read_bytes()[:24]
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        raise RuntimeError(f"не PNG-файл: {png}")
    width, height = struct.unpack(">II", data[16:24])
    return (width, height)


def _html_to_pdf(html_path: Path, pdf_path: Path, chrome: str = "google-chrome") -> None:
    binary = shutil.which(chrome) or chrome
    cmd = [
        binary,
        "--headless=new",
        "--no-sandbox",
        "--disable-gpu",
        "--disable-dev-shm-usage",
        "--hide-scrollbars",
        "--force-color-profile=srgb",
        "--virtual-time-budget=10000",
        f"--user-data-dir={pdf_path.parent / 'chrome-profile'}",
        "--no-pdf-header-footer",
        f"--print-to-pdf={pdf_path}",
        html_path.resolve().as_uri(),
    ]
    _run(cmd)
    if not pdf_path.exists():
        raise RuntimeError(f"chrome не создал PDF: {pdf_path}")


def _pdf_to_pngs(pdf: Path, out_dir: Path) -> list[Path]:
    # -scale-to-* фиксирует ровно 1600×900: из-за дробных пунктов в PDF
    # голый -r 96 даёт 901-й «лишний» ряд пикселей
    _run(
        [
            "pdftoppm",
            "-r",
            "96",
            "-scale-to-x",
            str(SLIDE_W_PX),
            "-scale-to-y",
            str(SLIDE_H_PX),
            "-png",
            str(pdf),
            str(out_dir / "slide"),
        ]
    )
    pngs = sorted(out_dir.glob("slide-*.png")) + sorted(out_dir.glob("slide_*.png"))
    return sorted(set(pngs))


# ------------------------------------------------------------- сборка

def build_visual_deck(
    markdown: str,
    cfg: CourseConfig,
    out_pptx: Path,
    base_dir: Path | None = None,
    work_dir: Path | None = None,
    chrome: str = "google-chrome",
) -> list[str]:
    """Собирает визуальную колоду; возвращает список предупреждений."""
    warnings: list[str] = []
    text, chips = extract_chips(markdown)
    slides = parse_deck(text)
    if not slides:
        raise RuntimeError("в исходнике нет ни одного слайда")
    base = base_dir or Path(".")
    work = work_dir or Path("build") / "deck-visual"
    work.mkdir(parents=True, exist_ok=True)

    # alt-тексты картинок читаем из исходника: parse_deck их не сохраняет
    alt_queue = extract_image_alts(text)

    layouts = [choose_layout(slide, index) for index, slide in enumerate(slides)]
    raw_bullets = raw_bullets_by_slide(text)
    visuals: list[VisualSlide] = []
    assets_dir = work / "assets"
    assets_dir.mkdir(exist_ok=True)
    for index, slide in enumerate(slides):
        vs = VisualSlide(slide=slide, layout=layouts[index])
        if index < len(raw_bullets) and len(raw_bullets[index]) == len(slide.bullets):
            vs.raw_bullets = raw_bullets[index]
        if slide.image:
            path = Path(slide.image)
            if not path.is_absolute():
                path = base / path
            if not path.exists():
                warnings.append(f"слайд {index + 1}: нет файла {slide.image}")
            else:
                alt = ""
                for position, (candidate_alt, candidate_src) in enumerate(alt_queue):
                    if Path(candidate_src).name == path.name:
                        alt = candidate_alt
                        alt_queue.pop(position)
                        break
                vs.alt = alt or path.stem.replace("-", " ")
                local = assets_dir / f"slide{index + 1:02d}-{path.name}"
                shutil.copyfile(path, local)
                vs.image_path = local
        visuals.append(vs)

    goal = slides[0].subtitle
    if not chips:
        chips = _auto_chips(slides)
    kicker = _kicker(cfg, slides, base)

    html_path = work / "deck.html"
    html_path.write_text(
        render_html(visuals, cfg, kicker, chips, goal), encoding="utf-8"
    )
    shutil.copyfile(TEMPLATE_DIR / "style.css", work / "style.css")
    (work / "fonts").mkdir(exist_ok=True)
    for font in (TEMPLATE_DIR / "fonts").glob("*.ttf"):
        shutil.copyfile(font, work / "fonts" / font.name)

    pdf_path = work / "deck.pdf"
    _html_to_pdf(html_path, pdf_path, chrome=chrome)
    pages = _pdf_page_count(pdf_path)
    if pages != len(slides):
        warnings.append(f"в PDF {pages} страниц, ожидалось {len(slides)}")
    width_pt, height_pt = _pdf_size(pdf_path)
    if abs(width_pt / height_pt - 16 / 9) > 0.02:
        warnings.append(f"размер страницы PDF {width_pt}×{height_pt} pts не 16:9")

    pngs = _pdf_to_pngs(pdf_path, work)
    if len(pngs) != len(slides):
        raise RuntimeError(
            f"pdftoppm вернул {len(pngs)} PNG, ожидалось {len(slides)}: {pdf_path}"
        )
    for png in pngs:
        px_w, px_h = _png_size(png)
        if (px_w, px_h) != (SLIDE_W_PX, SLIDE_H_PX):
            warnings.append(f"{png.name}: {px_w}×{px_h} вместо {SLIDE_W_PX}×{SLIDE_H_PX}")

    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank = prs.slide_layouts[6]
    for png, slide in zip(pngs, slides):
        page = prs.slides.add_slide(blank)
        page.shapes.add_picture(
            str(png), 0, 0, width=prs.slide_width, height=prs.slide_height
        )
        if slide.notes:
            page.notes_slide.notes_text_frame.text = slide.notes

    deck_title = slides[0].title or cfg.title
    props = prs.core_properties
    props.title = deck_title
    props.author = cfg.teacher or cfg.code
    props.subject = cfg.title

    out_pptx.parent.mkdir(parents=True, exist_ok=True)
    prs.save(out_pptx)
    out_pdf = out_pptx.with_suffix(".pdf")
    shutil.copyfile(pdf_path, out_pdf)
    return warnings
