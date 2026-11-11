# Конвейер учебных материалов: план реализации

> **Для агентов:** ОБЯЗАТЕЛЬНЫЙ НАВЫК: используйте `superpowers:subagent-driven-development` (рекомендуется) или `superpowers:executing-plans`, чтобы выполнять план задача за задачей. Шаги отмечаются чекбоксами (`- [ ]`).

**Цель:** один воспроизводимый конвейер, который из markdown-исходников курса МДК 01.04 собирает DOCX, PDF, PPTX и схемы, проверяет структуру и работает локально и в GitHub Actions.

**Архитектура:** markdown нормализуется в `build/normalized/` (исходники не меняются), затем независимые рендереры читают каноническую модель и пишут в `dist/`. QA — отдельный шаг, падает только на структурном браке. Всё запускается одной командой `python -m coursekit build`.

**Стек:** Python 3.12, pytest, PyYAML, python-docx, python-pptx, pandoc 3.1, Typst, Mermaid CLI (Node 20), GitHub Actions.

**Спецификация:** `docs/superpowers/specs/2026-11-09-course-pipeline-design.md`

## Глобальные ограничения

- Исходники в `course/**` не изменяются ни одним шагом конвейера; вся запись — в `build/` и `dist/`.
- Артефакты и промежуточные файлы не коммитятся: `.venv/`, `build/`, `dist/`, `__pycache__/`, `.pytest_cache/` в `.gitignore`.
- Все сообщения CLI, отчёты и документация — на русском.
- Имена артефактов — ASCII-слаги: `<repo>-r<N>-<kind>-<NN>.<ext>`, например `mdk0104-ib-r1-lecture-01.docx`.
- Версии: Python ≥ 3.11, pandoc ≥ 3.1, Typst ≥ 0.11, Node ≥ 20.
- Оформление DOCX/PDF: A4, поля 3/1,5/2/2 см, кегль 14, интервал 1,5, абзацный отступ 1,25 см, выключка по ширине.
- Ошибки QA уровня ERROR валят сборку; WARN и INFO только попадают в отчёт.

## Фокус ревью

Пять мест, где спецификация молчит, а сломаться может незаметно. Для каждого в плане есть тест.

1. **Строки `#` внутри блоков кода** (примеры `readme.md` в четырёхбэктиковых блоках) не должны становиться заголовками — иначе структура документа рассыплется. Тест в задаче 2.
2. **Идемпотентность нормализации:** повторный прогон не меняет файл. Иначе CI будет вечно грязным, а диффы — шумными. Тест в задаче 2.
3. **Отсутствующие изображения:** 13 ссылок ведут в пустоту; сборка обязана продолжиться с заметным плейсхолдером. Тесты в задачах 4 и 5.
4. **Длинные строки кода в PDF:** строка на 120 символов не должна уезжать за поля или ронять Typst. Тест в задаче 6.
5. **Переполнение слайдов PPTX:** текст не должен выходить за границы слайда. Тест в задаче 7.

---

## Структура файлов

| Путь | Ответственность |
|------|-----------------|
| `tools/pyproject.toml` | Пакет `coursekit`, зависимости, конфиг pytest |
| `tools/coursekit/__main__.py` | Точка входа `python -m coursekit` |
| `tools/coursekit/cli.py` | Разбор аргументов и оркестрация |
| `tools/coursekit/config.py` | `course.yml`, слаги, имена артефактов |
| `tools/coursekit/normalize.py` | Канонизация markdown, идемпотентность |
| `tools/coursekit/model.py` | Профили, разбор документа, синонимы заголовков |
| `tools/coursekit/qa.py` | Проверки, отчёт, код возврата |
| `tools/coursekit/render_docx.py` | pandoc + `reference.docx` |
| `tools/coursekit/render_pdf.py` | pandoc → Typst → PDF |
| `tools/coursekit/render_pptx.py` | python-pptx, порт существующего генератора |
| `tools/coursekit/render_figures.py` | mermaid → SVG/PNG |
| `tools/coursekit/render_book.py` | Склейка сборника |
| `tools/coursekit/make_reference.py` | Сборка `templates/reference.docx` |
| `tools/coursekit/templates/gost.typ` | Шаблон PDF |
| `tools/coursekit/templates/titlepage.md` | Титульный лист DOCX |
| `tools/coursekit/tests/` | Тесты pytest |
| `course.yml` | Метаданные курса |
| `.github/workflows/materials.yml` | CI |
| `docs/pipeline.md` | Как пользоваться |

---

## Задача 1: Скелет пакета и окружение

**Файлы:**
- Создать: `tools/pyproject.toml`, `tools/coursekit/__init__.py`, `tools/coursekit/__main__.py`, `tools/coursekit/cli.py`, `tools/coursekit/config.py`, `course.yml`, `tools/coursekit/tests/test_config.py`, `tools/coursekit/tests/test_cli.py`
- Изменить: `.gitignore`

**Интерфейсы:**
- Даёт: `CourseConfig` (поля `code, title, specialty, group, year, teacher, repo_slug, docx, pdf, pptx, figures, book`), `load_config(path: Path) -> CourseConfig`, `slugify(text: str) -> str`, `artifact_name(cfg: CourseConfig, doc: Document) -> str`.

- [ ] **Шаг 1: Установить системные зависимости**

```bash
sudo apt-get update
sudo apt-get install -y pandoc poppler-utils python3-venv python3-pip fonts-liberation
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
```

Ожидается: `pandoc --version` ≥ 3.1, `pdfinfo -v` работает.

- [ ] **Шаг 2: Создать `tools/pyproject.toml`**

```toml
[project]
name = "coursekit"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "PyYAML>=6,<7",
  "python-docx>=1.1,<2",
  "python-pptx>=1.0,<2",
]

[project.optional-dependencies]
dev = ["pytest>=8,<9"]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["."]
include = ["coursekit*"]

[tool.setuptools.package-data]
coursekit = ["templates/*"]

[tool.pytest.ini_options]
testpaths = ["coursekit/tests"]
markers = ["integration: требует внешний бинарник (pandoc, typst, mmdc)"]
```

- [ ] **Шаг 3: Создать `course.yml`**

```yaml
course:
  code: "МДК 01.04"
  title: "Системное программирование"
  specialty: "09.02.07, ИБ"
  group: "ИБ-243"
  year: "2026/2027"
  teacher: "<ФИО преподавателя>"
  repo_slug: "mdk0104-ib"
build:
  docx: true
  pdf: true
  pptx: true
  figures: true
  book: false
```

- [ ] **Шаг 4: Написать падающий тест конфигурации**

`tools/coursekit/tests/test_config.py`:

```python
from pathlib import Path
from coursekit.config import load_config, slugify

def test_load_config_reads_course_fields(tmp_path: Path):
    p = tmp_path / "course.yml"
    p.write_text(
        'course:\n  code: "МДК 01.04"\n  title: "Системное программирование"\n'
        '  specialty: "09.02.07, ИБ"\n  group: "ИБ-243"\n  year: "2026/2027"\n'
        '  teacher: "Иванов И. И."\n  repo_slug: "mdk0104-ib"\n'
        'build:\n  docx: true\n  pdf: false\n  pptx: true\n  figures: true\n  book: false\n',
        encoding="utf-8",
    )
    cfg = load_config(p)
    assert cfg.code == "МДК 01.04"
    assert cfg.teacher == "Иванов И. И."
    assert cfg.pdf is False

def test_slugify_transliterates_cyrillic():
    assert slugify("Лекция 1. Основы C# и .NET") == "lekciya-1-osnovy-c-i-net"
    assert slugify("Раздел 3. Многопоточность и асинхронность") == "razdel-3-mnogopotochnost-i-asinhronnost"
```

- [ ] **Шаг 5: Запустить тест и убедиться, что он падает**

```bash
PYTHONPATH=tools .venv/bin/python -m pytest tools/coursekit/tests/test_config.py -v
```

Ожидается: `ModuleNotFoundError: No module named 'coursekit.config'`.

- [ ] **Шаг 6: Реализовать `config.py`**

`CourseConfig` — frozen dataclass. `load_config` читает YAML через `yaml.safe_load`, берёт секции `course` и `build`, подставляет значения по умолчанию для отсутствующих ключей сборки. `slugify`: нижний регистр, таблица транслитерации (`а→a, б→b, в→v, г→g, д→d, е→e, ё→e, ж→zh, з→z, и→i, й→y, к→k, л→l, м→m, н→n, о→o, п→p, р→r, с→s, т→t, у→u, ф→f, х→h, ц→c, ч→ch, ш→sh, щ→sch, ъ→"", ы→y, ь→"", э→e, ю→yu, я→ya`), всё не-алфанумерическое → `-`, схлопывание дефисов, обрезка по краям.

- [ ] **Шаг 7: Написать падающий тест CLI**

`tools/coursekit/tests/test_cli.py`:

```python
import subprocess, sys

def test_cli_help_lists_commands():
    out = subprocess.run(
        [sys.executable, "-m", "coursekit", "--help"],
        capture_output=True, text=True, check=True,
    )
    for cmd in ("normalize", "build", "qa", "clean"):
        assert cmd in out.stdout
```

- [ ] **Шаг 8: Реализовать `__main__.py` и `cli.py`**

`__main__.py`: `from coursekit.cli import main; raise SystemExit(main())`.
`cli.py`: `argparse` с подкомандами-заглушками `normalize`, `figures`, `docx`, `pdf`, `pptx`, `qa`, `clean`, `build`; каждая печатает `"<команда>: не реализовано"` и возвращает 2. `main(argv=None) -> int`. Общие флаги: `--section N`, `--book`, `--only`, `--check`, `--strict`.

- [ ] **Шаг 9: Установить пакет и прогнать тесты**

```bash
.venv/bin/pip install -e "tools[dev]"
python -m coursekit --help
.venv/bin/python -m pytest tools/coursekit/tests -v
```

Ожидается: `--help` печатает команды, 3 passed.

- [ ] **Шаг 10: Обновить `.gitignore` и закоммитить**

Добавить в конец `.gitignore`: `.venv/`, `build/`, `dist/`, `__pycache__/`, `.pytest_cache/`, `*.pyc`.

```bash
git add .gitignore course.yml tools/pyproject.toml tools/coursekit
git commit -m "feat: скелет coursekit и конфигурация курса"
```

---

## Задача 2: Нормализация markdown

**Файлы:**
- Создать: `tools/coursekit/normalize.py`, `tools/coursekit/tests/test_normalize.py`
- Изменить: `docs/superpowers/specs/2026-11-09-course-pipeline-design.md` (уточнение §5.5)

**Интерфейсы:**
- Даёт: `normalize_text(text: str) -> tuple[str, list[str]]` (текст и список предупреждений), `normalize_file(src: Path, dst: Path) -> list[str]`, `normalize_tree(src_root: Path, dst_root: Path) -> dict[str, list[str]]`, `check_normalized(src_root: Path, dst_root: Path) -> list[Path]` (файлы, которые изменились бы; для `normalize --check`).
- Потребляет: ничего.

- [ ] **Шаг 1: Написать падающие тесты**

`tools/coursekit/tests/test_normalize.py`:

```python
from coursekit.normalize import normalize_text

def test_bold_heading_becomes_canonical():
    out, _ = normalize_text("### **План лекции:**\n")
    assert out == "## План лекции\n"

def test_numbered_heading_without_bold():
    out, _ = normalize_text("### 1. Введение\n")
    assert out == "## 1. Введение\n"

def test_subsection_numbered_keeps_level_three():
    out, _ = normalize_text("### 1.1. Подраздел\n")
    assert out == "### 1.1. Подраздел\n"

def test_h1_with_bold_normalized():
    out, _ = normalize_text("## **1. Введение**\n")
    assert out == "## 1. Введение\n"

def test_hash_inside_fenced_code_is_untouched():
    src = "````markdown\n# Заголовок readme\n````\n"
    out, _ = normalize_text(src)
    assert "# Заголовок readme" in out
    assert out.count("````") == 2

def test_fence_without_language_is_left_bare_and_warned():
    src = "```\nConsole.WriteLine();\n```\n"
    out, warnings = normalize_text(src)
    assert "```\nConsole" in out
    assert any("язык" in w.lower() for w in warnings)

def test_horizontal_rule_removed():
    out, _ = normalize_text("Текст\n\n---\n\nЕщё текст\n")
    assert "---" not in out

def test_normalization_is_idempotent():
    src = "### **1. Введение**\n\nТекст\n\n### **План лекции:**\n"
    once, _ = normalize_text(src)
    twice, _ = normalize_text(once)
    assert once == twice

def test_body_text_not_rewritten():
    src = "Visual Studio больше не используется.\n"
    out, _ = normalize_text(src)
    assert out == src
```

- [ ] **Шаг 2: Убедиться, что тесты падают**

```bash
PYTHONPATH=tools .venv/bin/python -m pytest tools/coursekit/tests/test_normalize.py -v
```

Ожидается: `ModuleNotFoundError`.

- [ ] **Шаг 3: Реализовать `normalize.py`**

Алгоритм построчный, с состоянием «внутри блока кода»:
- Открывающая строка — regex `^\s*(`{3,}|~{3,})(.*)$`; запоминаем длину и символ; закрывающая — та же последовательность не короче.
- Внутри блока строки не трогаются.
- Вне блока: `^#{1,6}\s+(.*)$`; снять обрамляющие `**` и завершающее `:`; если заголовок нумерованный `N.` — уровень 2; `N.M.` — уровень 3; иначе сохранить исходный уровень, но не глубже 3 и не мельче 2 для документа.
- `---`, `***`, `___` отдельной строкой удаляются.
- Строки списков: `^\s*[*+]\s+` → `- ` с сохранением отступа, шаг 4 пробела.
- Предупреждения: пустой язык у блока кода, заголовок прыгнул через уровень, больше одного H1.
- Файл пишется в UTF-8 с `\n`.

`docs/superpowers/specs/...`: заменить в §5.5 строку про подстановку `text` на «язык не подставляется, чтобы QA отличал пропуск; рендереры трактуют пустой язык как `text`».

- [ ] **Шаг 4: Прогнать тесты**

```bash
PYTHONPATH=tools .venv/bin/python -m pytest tools/coursekit/tests/test_normalize.py -v
```

Ожидается: 9 passed.

- [ ] **Шаг 5: Прогнать нормализацию на реальном корпусе**

```bash
PYTHONPATH=tools .venv/bin/python -c "from pathlib import Path; from coursekit.normalize import normalize_tree; r=normalize_tree(Path('course'), Path('build/normalized')); print(len(r), sum(len(v) for v in r.values()))"
```

Ожидается: 18 файлов, предупреждения перечислены. Глазами сверить 3 файла: лекция 1, практика 3, практика 5.

- [ ] **Шаг 6: Коммит**

```bash
git add tools/coursekit/normalize.py tools/coursekit/tests/test_normalize.py docs/superpowers/specs/2026-11-09-course-pipeline-design.md
git commit -m "feat: нормализация markdown с сохранением блоков кода"
```

---

## Задача 3: Модель документа и профили

**Файлы:**
- Создать: `tools/coursekit/model.py`, `tools/coursekit/tests/test_model.py`

**Интерфейсы:**
- Даёт: `Section(level: int, title: str, canonical: str | None, line: int, body: str)`, `Document(path: Path, kind: str, number: int, title: str, sections: list[Section], raw: str)`, `PROFILES: dict[str, Profile]`, `detect_kind(path: Path) -> str`, `detect_number(path: Path) -> int`, `parse_document(text: str, path: Path) -> Document`, `canonical_title(title: str) -> str | None`, `missing_required(doc: Document) -> list[str]`.
- Потребляет: ничего.

- [ ] **Шаг 1: Написать падающие тесты**

```python
from pathlib import Path
from coursekit.model import detect_kind, parse_document, canonical_title, missing_required

def test_detect_kind_from_filename():
    assert detect_kind(Path("course/Раздел 1/Лекция 1. Основы.md")) == "lecture"
    assert detect_kind(Path("course/Раздел 1/Практическая работа 2. Поток.md")) == "practice"
    assert detect_kind(Path("course/Раздел 1/Самостоятельная работа 1. Калькулятор.md")) == "selfstudy"
    assert detect_kind(Path("course/examen.md")) == "exam"

def test_alias_maps_to_canonical():
    assert canonical_title("Краткая справочная информация") == "Теоретическая часть"
    assert canonical_title("Цель работы:") == "Цель работы"
    assert canonical_title("15 Вариантов заданий") == "Варианты заданий"
    assert canonical_title("Неизвестный раздел") is None

def test_parse_lecture_sections():
    md = "# Лекция 1. Основы\n\n## План лекции\n1. Введение\n\n## 1. Введение\nТекст\n\n## Резюме\nИтог\n"
    doc = parse_document(md, Path("Лекция 1.md"))
    assert doc.kind == "lecture"
    assert [s.title for s in doc.sections] == ["План лекции", "1. Введение", "Резюме"]

def test_missing_required_section_reported():
    md = "# Практическая работа 2. Поток\n\n## Краткая справочная информация\nТекст\n"
    doc = parse_document(md, Path("Практическая работа 2.md"))
    assert "Цель работы" in missing_required(doc)
    assert "Ход работы" in missing_required(doc)
```

- [ ] **Шаг 2: Убедиться, что тесты падают**

```bash
PYTHONPATH=tools .venv/bin/python -m pytest tools/coursekit/tests/test_model.py -v
```

- [ ] **Шаг 3: Реализовать `model.py`**

`PROFILES`: `lecture` (обязательные `План лекции`, `Резюме`, `Контрольные вопросы`; рекомендуемые `Цель лекции`, `Аудитория`, `Материалы`), `practice` и `selfstudy` (обязательные `Цель работы`, `Ход работы`, `Варианты заданий`, `Критерии оценки`; рекомендуемые `Теоретическая часть`, `Практический пример`, `Контрольные вопросы`, `Требования к репозиторию`), `exam` (обязательные `Варианты заданий`, `Критерии оценки`).

`ALIASES` — таблица из §5.4 спецификации, ключи сравниваются без учёта регистра, `**`, завершающего `:`, лишних пробелов. `canonical_title` возвращает канон или `None`.

`parse_document`: ищет H1 (`# `) как заголовок документа, затем H2 как разделы; тело раздела — до следующего H2. Если H1 нет — `kind` из пути, `title` из первого H2.

- [ ] **Шаг 4: Прогнать тесты и коммит**

```bash
PYTHONPATH=tools .venv/bin/python -m pytest tools/coursekit/tests/test_model.py -v
git add tools/coursekit/model.py tools/coursekit/tests/test_model.py
git commit -m "feat: модель документа и профили лекций и практик"
```

Ожидается: 4 passed.

---

## Задача 4: QA и отчёт

**Файлы:**
- Создать: `tools/coursekit/qa.py`, `tools/coursekit/tests/test_qa.py`

**Интерфейсы:**
- Даёт: `Issue(level, code, file, line, message)`, `run_qa(docs: list[Document], root: Path) -> list[Issue]`, `render_report(issues: list[Issue], out: Path) -> None`, `has_errors(issues) -> bool`.
- Потребляет: `Document`, `missing_required` из задачи 3.

- [ ] **Шаг 1: Написать падающие тесты**

```python
from pathlib import Path
from coursekit.model import parse_document
from coursekit.qa import run_qa, has_errors

def _doc(md: str, name: str = "Лекция 1.md"):
    return parse_document(md, Path(name))

def test_two_h1_is_error():
    doc = _doc("# Лекция 1\n\n# Ещё заголовок\n")
    issues = run_qa([doc], Path("."))
    assert any(i.level == "ERROR" and i.code == "H1_COUNT" for i in issues)

def test_unclosed_fence_is_error():
    doc = _doc("# Лекция 1\n\n```csharp\nvar x = 1;\n")
    issues = run_qa([doc], Path("."))
    assert any(i.level == "ERROR" and i.code == "FENCE_UNCLOSED" for i in issues)

def test_missing_image_is_warning(tmp_path: Path):
    doc = _doc("# Лекция 1\n\n![Скрин](images/none.png)\n")
    issues = run_qa([doc], tmp_path)
    assert any(i.level == "WARN" and i.code == "IMAGE_MISSING" for i in issues)
    assert not has_errors(issues)

def test_missing_section_is_warning():
    doc = _doc("# Практическая работа 2. Поток\n\n## Краткая справочная информация\nТекст\n", "Практическая работа 2.md")
    issues = run_qa([doc], Path("."))
    assert any(i.level == "WARN" and i.code == "SECTION_MISSING" for i in issues)

def test_bare_code_fence_is_warning():
    doc = _doc("# Лекция 1\n\n```\nConsole.WriteLine();\n```\n")
    issues = run_qa([doc], Path("."))
    assert any(i.level == "WARN" and i.code == "CODE_NO_LANG" for i in issues)

def test_stale_net8_is_warning():
    doc = _doc("# Лекция 1\n\nПроект на net8.0.\n")
    issues = run_qa([doc], Path("."))
    assert any(i.code == "STALE_STACK" for i in issues)

def test_broken_relative_link_is_error(tmp_path: Path):
    doc = _doc("# Лекция 1\n\n[файл](missing.md)\n")
    issues = run_qa([doc], tmp_path)
    assert any(i.level == "ERROR" and i.code == "LINK_BROKEN" for i in issues)
```

- [ ] **Шаг 2: Убедиться, что тесты падают**

```bash
PYTHONPATH=tools .venv/bin/python -m pytest tools/coursekit/tests/test_qa.py -v
```

- [ ] **Шаг 3: Реализовать `qa.py`**

Проверки: `H1_COUNT`, `FENCE_UNCLOSED`, `LINK_BROKEN` (локальные ссылки без `http`, не `#anchor`), `IMAGE_MISSING`, `SECTION_MISSING`, `CODE_NO_LANG`, `STALE_STACK` (`net8.0`, `net9.0`, `Visual Studio`, `ChromeDriver`, `Docker`), `LEN_SHORT` (< 300 знаков), `LEN_LONG` (лекция > 35 000), `DOUBLE_SPACE`, `TODO`, `QUOTES` (прямые `"` в русском тексте).

`render_report` пишет markdown: заголовок, сводка по уровням, таблица `Файл | Строка | Уровень | Код | Сообщение`, раздел «Долговой список» (недостающие разделы по файлам), раздел «Недостающие изображения».

- [ ] **Шаг 4: Прогнать тесты и реальный QA**

```bash
PYTHONPATH=tools .venv/bin/python -m pytest tools/coursekit/tests/test_qa.py -v
PYTHONPATH=tools .venv/bin/python -c "from pathlib import Path; from coursekit.normalize import normalize_tree; from coursekit.model import parse_document; from coursekit.qa import run_qa, render_report; normalize_tree(Path('course'), Path('build/normalized')); docs=[parse_document(p.read_text(encoding='utf-8'), p) for p in Path('build/normalized').rglob('*.md')]; issues=run_qa(docs, Path('build/normalized')); render_report(issues, Path('build/qa-report.md')); print(len(issues))"
```

Ожидается: ноль ERROR, WARN перечислены; отчёт открывается.

- [ ] **Шаг 5: Коммит**

```bash
git add tools/coursekit/qa.py tools/coursekit/tests/test_qa.py
git commit -m "feat: QA-проверки и отчёт по корпусу"
```

---

## Задача 5: DOCX

**Файлы:**
- Создать: `tools/coursekit/render_docx.py`, `tools/coursekit/make_reference.py`, `tools/coursekit/templates/titlepage.md`, `tools/coursekit/tests/test_docx.py`
- Изменить: `tools/coursekit/cli.py`

**Интерфейсы:**
- Даёт: `build_reference_docx(out: Path) -> Path`, `build_docx(doc: Document, cfg: CourseConfig, out: Path, workdir: Path) -> Path`.
- Потребляет: `Document`, `CourseConfig`, `artifact_name`.

- [ ] **Шаг 1: Написать падающий тест**

```python
import subprocess, pytest
from pathlib import Path
from docx import Document as Docx
from docx.shared import Cm
from coursekit.config import load_config
from coursekit.make_reference import build_reference_docx
from coursekit.model import parse_document
from coursekit.render_docx import build_docx

@pytest.mark.integration
def test_docx_has_gost_like_page_setup(tmp_path: Path):
    ref = build_reference_docx(tmp_path / "reference.docx")
    md = "# Лекция 1. Основы\n\n## План лекции\n1. Введение\n\n## 1. Введение\nТекст с кириллицей.\n"
    doc = parse_document(md, Path("Лекция 1.md"))
    out = build_docx(doc, load_config(Path("course.yml")), tmp_path / "l1.docx", tmp_path)
    d = Docx(out)
    s = d.sections[0]
    assert round(s.left_margin.cm, 1) == 3.0
    assert round(s.right_margin.cm, 1) == 1.5
    assert d.styles["Normal"].font.name == "Times New Roman"
    assert d.styles["Normal"].font.size.pt == 14

@pytest.mark.integration
def test_missing_image_becomes_placeholder(tmp_path: Path):
    md = "# Лекция 1\n\n![Схема работы](images/none.png)\n"
    doc = parse_document(md, Path("Лекция 1.md"))
    out = build_docx(doc, load_config(Path("course.yml")), tmp_path / "l1.docx", tmp_path)
    text = "\n".join(p.text for p in Docx(out).paragraphs)
    assert "Скриншот отсутствует" in text
```

- [ ] **Шаг 2: Убедиться, что тесты падают**

```bash
PYTHONPATH=tools .venv/bin/python -m pytest tools/coursekit/tests/test_docx.py -v
```

- [ ] **Шаг 3: Реализовать `make_reference.py`**

Создаёт A4 (21×29,7 см), поля 3/1,5/2/2 см. Стили: `Normal` и `Body Text` — Times New Roman 14, интервал 1,5, отступ первой строки 1,25 см, выключка по ширине; `Heading 1` — TNR 18 полужирный, по центру, интервал после 12; `Heading 2` — TNR 16 полужирный; `Heading 3` — TNR 14 полужирный курсив; `Source Code` — Consolas 10, одинарный, без отступа, светлая заливка; `Table` — границы 0,5 pt; `Title`/`Subtitle`/`Author` — по центру. В нижний колонтитул — поле `PAGE`.

- [ ] **Шаг 4: Реализовать `render_docx.py`**

Готовит `build/md/<slug>.md`: подставляет плейсхолдеры вместо ссылок на отсутствующие изображения (`![alt](path)` → блокquote `> **Скриншот отсутствует:** alt`), добавляет титульный лист из `templates/titlepage.md` через `--include-before-body`, заменяет маркер `<!-- pagebreak -->` на raw openxml:

````markdown
```{=openxml}
<w:p><w:r><w:br w:type="page"/></w:r></w:p>
```
````

Команда: `pandoc <md> -o <out> --reference-doc=<reference.docx> --toc --toc-depth=2 --highlight-style=tango`. Ошибка pandoc → `RuntimeError` с последними 20 строками stderr.

- [ ] **Шаг 5: Прогнать тесты**

```bash
PYTHONPATH=tools .venv/bin/python -m pytest tools/coursekit/tests/test_docx.py -v
```

Ожидается: 2 passed.

- [ ] **Шаг 6: Собрать DOCX пилота и посмотреть глазами**

```bash
PYTHONPATH=tools .venv/bin/python -m coursekit docx --section 1
```

Ожидается: 5 файлов в `dist/docx/`. Проверить: титул, оглавление, заголовки, код, таблицы, плейсхолдеры.

- [ ] **Шаг 7: Коммит**

```bash
git add tools/coursekit/render_docx.py tools/coursekit/make_reference.py tools/coursekit/templates/titlepage.md tools/coursekit/tests/test_docx.py tools/coursekit/cli.py
git commit -m "feat: сборка DOCX по шаблону методички"
```

---

## Задача 6: PDF через Typst

**Файлы:**
- Создать: `tools/coursekit/render_pdf.py`, `tools/coursekit/templates/gost.typ`, `tools/coursekit/tests/test_pdf.py`

**Интерфейсы:**
- Даёт: `build_pdf(doc: Document, cfg: CourseConfig, out: Path, workdir: Path) -> Path`.
- Потребляет: `Document`, `CourseConfig`.

- [ ] **Шаг 1: Установить Typst**

```bash
TYPST_VER=$(curl -fsSL https://api.github.com/repos/typst/typst/releases/latest | grep -oP '"tag_name": "v\K[^"]+')
curl -fsSL -o /tmp/typst.tar.xz "https://github.com/typst/typst/releases/download/v${TYPST_VER}/typst-x86_64-unknown-linux-musl.tar.xz"
sudo tar -xJf /tmp/typst.tar.xz -C /usr/local/bin --strip-components=1 typst-x86_64-unknown-linux-musl/typst
typst --version
```

- [ ] **Шаг 2: Написать падающий тест**

```python
import subprocess, pytest
from pathlib import Path
from coursekit.config import load_config
from coursekit.model import parse_document
from coursekit.render_pdf import build_pdf

def _pdfinfo(path: Path) -> str:
    return subprocess.run(["pdfinfo", str(path)], capture_output=True, text=True, check=True).stdout

@pytest.mark.integration
def test_pdf_is_a4_and_has_cyrillic(tmp_path: Path):
    md = "# Лекция 1. Основы\n\n## 1. Введение\nПроверка кириллицы: ёжик, щука, юла.\n"
    doc = parse_document(md, Path("Лекция 1.md"))
    out = build_pdf(doc, load_config(Path("course.yml")), tmp_path / "l1.pdf", tmp_path)
    info = _pdfinfo(out)
    assert "595" in info and "842" in info
    text = subprocess.run(["pdftotext", str(out), "-"], capture_output=True, text=True, check=True).stdout
    assert "ёжик" in text

@pytest.mark.integration
def test_long_code_line_does_not_break_layout(tmp_path: Path):
    md = "# Лекция 1\n\n## 1. Код\n\n```csharp\n" + "var x = " + "1 + " * 60 + "1;\n```\n"
    doc = parse_document(md, Path("Лекция 1.md"))
    out = build_pdf(doc, load_config(Path("course.yml")), tmp_path / "l1.pdf", tmp_path)
    assert out.exists() and out.stat().st_size > 1000
```

- [ ] **Шаг 3: Написать `templates/gost.typ`**

```typst
#set page(paper: "a4", margin: (left: 3cm, right: 1.5cm, top: 2cm, bottom: 2cm),
  numbering: "1", number-align: right)
#set text(font: "Liberation Serif", size: 14pt, lang: "ru")
#set par(justify: true, leading: 1.2em, first-line-indent: 1.25cm, spacing: 1.2em)
#set heading(numbering: none)
#show heading.where(level: 1): it => pagebreak(weak: true) + it
#show raw.where(block: true): it => block(fill: luma(245), inset: 6pt, radius: 2pt,
  width: 100%, text(font: "Liberation Mono", size: 9pt, it))
#show link: set text(fill: blue)

#align(center)[
  #text(size: 16pt, weight: "bold")[#sys.inputs.at("code", default: "")] \
  #text(size: 20pt, weight: "bold")[#sys.inputs.at("title", default: "")] \
  #v(1cm)
  #text(size: 14pt)[#sys.inputs.at("specialty", default: "")] \
  #text(size: 14pt)[#sys.inputs.at("group", default: "")] \
  #v(2cm)
  #text(size: 14pt)[#sys.inputs.at("teacher", default: "")] \
  #text(size: 14pt)[#sys.inputs.at("year", default: "")] \
  #v(1cm)
]
#pagebreak()

$body$
```

- [ ] **Шаг 4: Реализовать `render_pdf.py`**

1. `pandoc <md> -t typst --standalone --template=templates/gost.typ -o build/typst/<slug>.typ --toc --toc-depth=2 --highlight-style=tango`.
2. `typst compile --root . build/typst/<slug>.typ <out> --input code=... --input title=... --input specialty=... --input group=... --input teacher=... --input year=...`.
3. Если pandoc 3.1 не знает `-t typst` — `RuntimeError` с понятным сообщением «нужен pandoc ≥ 3.1.1».

- [ ] **Шаг 5: Прогнать тесты**

```bash
PYTHONPATH=tools .venv/bin/python -m pytest tools/coursekit/tests/test_pdf.py -v
```

Ожидается: 2 passed (при установленном Typst; иначе skip).

- [ ] **Шаг 6: Собрать PDF пилота**

```bash
PYTHONPATH=tools .venv/bin/python -m coursekit pdf --section 1
pdftoppm -f 1 -l 3 -png -r 80 dist/pdf/mdk0104-ib-r1-lecture-01.pdf /tmp/l1
```

Проверить глазами: титул, оглавление, поля, код не вылезает, таблицы не рвутся уродливо.

- [ ] **Шаг 7: Коммит**

```bash
git add tools/coursekit/render_pdf.py tools/coursekit/templates/gost.typ tools/coursekit/tests/test_pdf.py
git commit -m "feat: сборка PDF через Typst"
```

---

## Задача 7: PPTX

**Файлы:**
- Создать: `tools/coursekit/render_pptx.py`, `tools/coursekit/tests/test_pptx.py`
- Изменить: `tools/generate_lecture_pptx.py` (тонкая обёртка над `coursekit.render_pptx`)

**Интерфейсы:**
- Даёт: `build_pptx(doc: Document, cfg: CourseConfig, out: Path) -> Path`.
- Потребляет: `Document`, `CourseConfig`, `Section`.

- [ ] **Шаг 1: Написать падающие тесты**

```python
import pytest
from pathlib import Path
from pptx import Presentation
from coursekit.config import load_config
from coursekit.model import parse_document
from coursekit.render_pptx import build_pptx

MD = """# Лекция 1. Основы

## План лекции
1. Введение
2. Типы данных

## 1. Введение
Первый тезис.
- Второй тезис.
- Третий тезис.

## Резюме
Итог.

## Контрольные вопросы
1. Что такое CLR?
"""

@pytest.mark.integration
def test_pptx_structure(tmp_path: Path):
    doc = parse_document(MD, Path("Лекция 1.md"))
    out = build_pptx(doc, load_config(Path("course.yml")), tmp_path / "l1.pptx")
    prs = Presentation(out)
    texts = [" ".join(sh.text for sh in s.shapes if sh.has_text_frame) for s in prs.slides]
    assert any("План лекции" in t for t in texts)
    assert any("Резюме" in t for t in texts)
    assert any("Что такое CLR" in t for t in texts)

@pytest.mark.integration
def test_pptx_shapes_fit_slide(tmp_path: Path):
    doc = parse_document(MD, Path("Лекция 1.md"))
    out = build_pptx(doc, load_config(Path("course.yml")), tmp_path / "l1.pptx")
    prs = Presentation(out)
    w, h = prs.slide_width, prs.slide_height
    for slide in prs.slides:
        for sh in slide.shapes:
            assert sh.left >= 0 and sh.top >= 0
            assert sh.left + sh.width <= w + 10
            assert sh.top + sh.height <= h + 10

@pytest.mark.integration
def test_pptx_has_speaker_notes(tmp_path: Path):
    doc = parse_document(MD, Path("Лекция 1.md"))
    out = build_pptx(doc, load_config(Path("course.yml")), tmp_path / "l1.pptx")
    prs = Presentation(out)
    assert any(slide.notes_slide.notes_text_frame.text.strip() for slide in prs.slides)
```

- [ ] **Шаг 2: Убедиться, что тесты падают**

```bash
PYTHONPATH=tools .venv/bin/python -m pytest tools/coursekit/tests/test_pptx.py -v
```

- [ ] **Шаг 3: Перенести генератор**

Из `tools/generate_lecture_pptx.py` перенести константы палитры, `header_band`, `conspect_box`, `code_box`, `_bullet_slide`, `_para_slide`, `_table_slide`, `_code_slides` в `render_pptx.py`. Парсер заменить на `Document`/`Section` из задачи 3.

Структура колоды: титул → план → для каждого H2 разделитель → содержательные слайды (≤ 6 пунктов, ≤ 70 слов, код ≤ 14 строк) → резюме → вопросы. Заметки докладчика — полный текст раздела.

- [ ] **Шаг 4: Добавить проверку переполнения**

В `render_pptx.py` — `_assert_fits(slide, shape)`: оценка числа строк по ширине текстового поля и кеглю; если оценка превышает высоту, уменьшить кегль на 2 pt (до 12) или разбить слайд. Вызывать для каждого текстового блока.

- [ ] **Шаг 5: Прогнать тесты**

```bash
PYTHONPATH=tools .venv/bin/python -m pytest tools/coursekit/tests/test_pptx.py -v
```

Ожидается: 3 passed.

- [ ] **Шаг 6: Собрать колоды пилота и проверить глазами**

```bash
PYTHONPATH=tools .venv/bin/python -m coursekit pptx --section 1
python -c "from pptx import Presentation; p=Presentation('dist/pptx/mdk0104-ib-r1-lecture-01.pptx'); print(len(p.slides))"
```

Ожидается: 2 колоды; число слайдов сопоставимо с текущими; ни один текст не обрезан (проверить 5 случайных слайдов).

- [ ] **Шаг 7: Коммит**

```bash
git add tools/coursekit/render_pptx.py tools/coursekit/tests/test_pptx.py tools/generate_lecture_pptx.py
git commit -m "feat: генератор PPTX на модели документа"
```

---

## Задача 8: Схемы Mermaid

**Файлы:**
- Создать: `tools/coursekit/render_figures.py`, `tools/coursekit/tests/test_figures.py`, `tools/coursekit/templates/puppeteer.json`

**Интерфейсы:**
- Даёт: `extract_mermaid(text: str) -> list[str]`, `build_figures(doc: Document, out_dir: Path) -> dict[int, Path]`, `substitute_figures(text: str, figures: dict[int, Path]) -> str`, `prepare_doc(doc: Document, figures_dir: Path) -> Document` (копия документа, где блоки `mermaid` заменены ссылками на готовые SVG; её получают рендереры DOCX/PDF/PPTX).
- Потребляет: `Document`.

- [ ] **Шаг 1: Написать падающие тесты**

```python
from pathlib import Path
from coursekit.render_figures import extract_mermaid, substitute_figures

def test_extract_mermaid_blocks():
    md = "```mermaid\ngraph TD\nA-->B\n```\n\n```csharp\nvar x=1;\n```\n"
    assert extract_mermaid(md) == ["graph TD\nA-->B"]

def test_substitute_replaces_block_with_image():
    md = "До\n\n```mermaid\ngraph TD\nA-->B\n```\n\nПосле\n"
    out = substitute_figures(md, {0: Path("build/figures/x-1.svg")})
    assert "```mermaid" not in out
    assert "![Схема 1](build/figures/x-1.svg)" in out
```

- [ ] **Шаг 2: Убедиться, что тесты падают**

```bash
PYTHONPATH=tools .venv/bin/python -m pytest tools/coursekit/tests/test_figures.py -v
```

- [ ] **Шаг 3: Реализовать `render_figures.py`**

`extract_mermaid` — regex по блокам с языком `mermaid`. `build_figures` пишет `.mmd` во `build/figures/` и вызывает:

```bash
npx -y @mermaid-js/mermaid-cli@11 -i in.mmd -o out.svg -b transparent -p templates/puppeteer.json
```

`templates/puppeteer.json`: `{"args": ["--no-sandbox", "--disable-setuid-sandbox"]}`.
Дополнительно рендерит PNG 2x (`-s 2`) для DOCX/PPTX. Ошибка `mmdc` → `RuntimeError`.
`prepare_doc` возвращает `dataclasses.replace(doc, raw=substitute_figures(doc.raw, figures))` и пересобирает `sections` через `parse_document`, чтобы рендереры не зависели от mermaid.

- [ ] **Шаг 4: Прогнать тесты и проверить рендер**

```bash
PYTHONPATH=tools .venv/bin/python -m pytest tools/coursekit/tests/test_figures.py -v
```

Ожидается: 2 passed. Затем вручную: временный md с `graph TD; A-->B`, `build_figures`, открыть SVG.

- [ ] **Шаг 5: Коммит**

```bash
git add tools/coursekit/render_figures.py tools/coursekit/tests/test_figures.py tools/coursekit/templates/puppeteer.json
git commit -m "feat: рендер mermaid-схем в SVG и PNG"
```

---

## Задача 9: Сборник и манифест

**Файлы:**
- Создать: `tools/coursekit/render_book.py`, `tools/coursekit/manifest.py`, `tools/coursekit/tests/test_book.py`

**Интерфейсы:**
- Даёт: `build_book_md(docs: list[Document]) -> str`, `write_manifest(artifacts: list[Path], out: Path) -> None`.
- Потребляет: `Document`.

- [ ] **Шаг 1: Написать падающие тесты**

```python
from pathlib import Path
from coursekit.model import parse_document
from coursekit.render_book import build_book_md
from coursekit.manifest import write_manifest
import json

def _doc(md: str, name: str):
    return parse_document(md, Path(name))

def test_book_contains_docs_in_order_with_breaks():
    docs = [_doc("# Лекция 1\n\n## 1. А\n", "Лекция 1.md"), _doc("# Лекция 2\n\n## 1. Б\n", "Лекция 2.md")]
    book = build_book_md(docs)
    assert book.index("Лекция 1") < book.index("Лекция 2")
    assert book.count("<!-- pagebreak -->") == 1

def test_manifest_has_sha256(tmp_path: Path):
    f = tmp_path / "a.txt"
    f.write_text("привет", encoding="utf-8")
    out = tmp_path / "manifest.json"
    write_manifest([f], out)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["files"][0]["name"] == "a.txt"
    assert len(data["files"][0]["sha256"]) == 64
    assert data["files"][0]["size"] == 12
```

- [ ] **Шаг 2: Убедиться, что тесты падают**

```bash
PYTHONPATH=tools .venv/bin/python -m pytest tools/coursekit/tests/test_book.py -v
```

- [ ] **Шаг 3: Реализовать `render_book.py` и `manifest.py`**

`build_book_md`: титул книги (из `course.yml` передаётся отдельно), затем документы в порядке разделов и номеров, между ними `<!-- pagebreak -->`. `write_manifest`: JSON `{"generated": "<ISO>", "files": [{"name", "size", "sha256", "pages"?, "slides"?}]}`.

- [ ] **Шаг 4: Прогнать тесты и коммит**

```bash
PYTHONPATH=tools .venv/bin/python -m pytest tools/coursekit/tests/test_book.py -v
git add tools/coursekit/render_book.py tools/coursekit/manifest.py tools/coursekit/tests/test_book.py
git commit -m "feat: сборник и манифест артефактов"
```

Ожидается: 2 passed.

---

## Задача 10: Оркестрация build

**Файлы:**
- Изменить: `tools/coursekit/cli.py`, `tools/coursekit/qa.py`
- Создать: `tools/coursekit/tests/test_build.py`

**Интерфейсы:**
- Даёт: `build(section: int | None, only: set[str], book: bool) -> int`, `collect_docs(root: Path) -> list[Document]`.
- Потребляет: все рендереры и QA.

- [ ] **Шаг 1: Написать падающий тест**

```python
import os
import pytest
from pathlib import Path
from coursekit.cli import build

@pytest.mark.integration
def test_build_only_docx_section_one():
    root = Path(__file__).resolve().parents[3]
    os.chdir(root)
    code = build(section=1, only={"docx"}, book=False)
    assert code == 0
    assert list(Path("dist/docx").glob("mdk0104-ib-r1-*.docx"))

@pytest.mark.integration
def test_build_writes_qa_report():
    build(section=1, only={"qa"}, book=False)
    assert Path("dist/qa-report.md").exists()
```

- [ ] **Шаг 2: Убедиться, что тест падает**

```bash
PYTHONPATH=tools .venv/bin/python -m pytest tools/coursekit/tests/test_build.py -v
```

- [ ] **Шаг 3: Реализовать оркестрацию**

`collect_docs`: обход `course/**/*.md` + `course/examen.md`, сортировка по номеру раздела (regex `Раздел (\d+)`) и номеру документа. `build`: normalize → figures → выбранные рендеры → qa → manifest. `--section` фильтрует по номеру раздела. `--only` — множество из `docx,pdf,pptx,figures,qa`. `qa --strict` возвращает 1 и на WARN.

- [ ] **Шаг 4: Полный прогон пилота**

```bash
PYTHONPATH=tools .venv/bin/python -m coursekit normalize
PYTHONPATH=tools .venv/bin/python -m coursekit build --section 1 --book
```

Ожидается: `dist/docx` 5 файлов, `dist/pdf` 5, `dist/pptx` 2, `dist/qa-report.md`, `dist/manifest.json`.

- [ ] **Шаг 5: Коммит**

```bash
git add tools/coursekit/cli.py tools/coursekit/tests/test_build.py
git commit -m "feat: оркестрация сборки материалов"
```

---

## Задача 11: GitHub Actions

**Файлы:**
- Создать: `.github/workflows/materials.yml`, `tools/coursekit/tests/test_workflow.py`

**Интерфейсы:**
- Даёт: CI-job `build`, артефакт `materials`.
- Потребляет: `python -m coursekit build`.

- [ ] **Шаг 1: Написать падающий тест**

```python
from pathlib import Path
import yaml

def test_workflow_parses_and_has_build_job():
    data = yaml.safe_load(Path(".github/workflows/materials.yml").read_text(encoding="utf-8"))
    assert "build" in data["jobs"]
    steps = data["jobs"]["build"]["steps"]
    assert any("coursekit build" in str(s.get("run", "")) for s in steps)
    assert any("upload-artifact" in str(s.get("uses", "")) for s in steps)
```

- [ ] **Шаг 2: Создать workflow**

Триггеры: `push` по путям `course/**`, `tools/**`, `course.yml`, сам workflow; `pull_request`; `workflow_dispatch`.
Job `build` на `ubuntu-24.04`: checkout → setup-python 3.12 с кэшем pip → setup-node 20 с кэшем npm → `typst-community/setup-typst@v3` → `apt-get install pandoc poppler-utils fonts-liberation` → `pip install -e tools[dev]` → `python -m coursekit build --book` → `actions/upload-artifact@v4` с `dist/`.
Переменная `PYTHONPATH: tools` не нужна: пакет установлен.

- [ ] **Шаг 3: Прогнать тест**

```bash
PYTHONPATH=tools .venv/bin/python -m pytest tools/coursekit/tests/test_workflow.py -v
```

Ожидается: 1 passed.

- [ ] **Шаг 4: Коммит**

```bash
git add .github/workflows/materials.yml tools/coursekit/tests/test_workflow.py
git commit -m "ci: сборка материалов курса в GitHub Actions"
```

---

## Задача 12: Документация и финальная проверка

**Файлы:**
- Создать: `docs/pipeline.md`
- Изменить: `readme.md` (раздел «Сборка материалов»)

**Интерфейсы:**
- Потребляет: всё.

- [ ] **Шаг 1: Написать `docs/pipeline.md`**

Разделы: «Что собирается», «Установка» (apt, venv, typst), «Команды», «Куда кладутся файлы», «Как добавить новую лекцию», «Уровни QA», «Частые ошибки» (нет pandoc, нет typst, упал mmdc, кириллица в именах).

- [ ] **Шаг 2: Добавить в `readme.md` короткий раздел со ссылкой на `docs/pipeline.md` и командами `build`, `qa`.**

- [ ] **Шаг 3: Полная проверка**

```bash
PYTHONPATH=tools .venv/bin/python -m pytest tools/coursekit/tests -v
PYTHONPATH=tools .venv/bin/python -m coursekit clean
PYTHONPATH=tools .venv/bin/python -m coursekit build --book
PYTHONPATH=tools .venv/bin/python -m coursekit normalize --check
```

Ожидается: все тесты зелёные; `normalize --check` — код 0 и «изменений нет»; сборка — код 0; в `dist/qa-report.md` ноль ERROR.

- [ ] **Шаг 4: Визуальная приёмка**

Открыть 2 PDF, 2 DOCX, 2 PPTX. Проверить: титул, оглавление, поля, кириллицу, код, таблицы, схемы, заметки докладчика. Записать замечания в `docs/pipeline.md` → «Известные ограничения».

- [ ] **Шаг 5: Коммит**

```bash
git add docs/pipeline.md readme.md
git commit -m "docs: как собирать материалы курса"
```

---

## Самопроверка плана

- Покрытие спецификации: нормализация — задача 2; профили и синонимы — 3; QA — 4; DOCX — 5; PDF — 6; PPTX — 7; схемы — 8; сборник и манифест — 9; CLI и `--book` — 10; CI — 11; документация и проверка — 12. Этапы 0–6 спецификации покрыты.
- Фокус ревью: все пять пунктов имеют тесты в задачах 2, 4/5, 6, 7.
- Типы: `Document`, `Section`, `CourseConfig`, `Issue` используются согласованно; `build_*` возвращают `Path`.
- Пропорция: план описывает интерфейсы и проверки, а не тела функций.
