# Конвейер учебных материалов

Markdown в `course/` — единственный источник. Из него собираются печатные
документы, презентации и схемы, а проверки качества не дают структурному
браку попасть в методичку.

## Что собирается

| Артефакт | Команда | Куда |
|---|---|---|
| DOCX (методичка) | `docx` / `build` | `dist/docx/` |
| PDF (Typst) | `pdf` / `build` | `dist/pdf/` |
| PPTX (лекции) | `pptx` / `build` | `dist/pptx/` |
| Схемы Mermaid | `figures` | `dist/figures/` |
| Сборник курса | `build --book` | `dist/docx/*-book.docx`, `dist/pdf/*-book.pdf` |
| Отчёт QA | `qa` / `build` | `dist/qa-report.md` |
| Манифест | `build` | `dist/manifest.json` |

Имена файлов: `<repo_slug>-r<раздел>-<вид>-<номер>.<ext>`, например
`mdk0104-ib-r1-lecture-01.pdf`. Экзамен — `<repo_slug>-exam`.

## Установка

```bash
sudo apt-get install pandoc poppler-utils fonts-liberation python3-venv python3-pip
# Typst 0.15+ — бинарником с github.com/typst/typst/releases в /usr/local/bin
python3 -m venv .venv
.venv/bin/pip install -e "tools[dev]"
```

Для схем нужен Node.js: `npx` сам скачает `@mermaid-js/mermaid-cli@11`.
Chrome для mermaid-cli запускается с `--no-sandbox` (см.
`tools/coursekit/templates/puppeteer.json`).

## Команды

```bash
python -m coursekit normalize            # перезаписать build/normalized
python -m coursekit normalize --check    # 1, если файлы изменились бы
python -m coursekit figures              # только схемы
python -m coursekit docx --section 1     # DOCX одного раздела
python -m coursekit pdf --section 1
python -m coursekit pptx --section 1
python -m coursekit qa                   # отчёт без сборки
python -m coursekit qa --strict          # 1 и на предупреждения
python -m coursekit build --section 1    # всё по разделу
python -m coursekit build --book         # весь курс + сборник
python -m coursekit clean                # удалить build/ и dist/
```

`build` принимает `--only docx,pdf,pptx,figures,qa` — можно собрать только
нужное. `--book` добавляет сборник, когда не задан `--section`.

## Как добавить материал

1. Положить файл в `course/Раздел N. Название/` с именем
   `Лекция N. Тема.md`, `Практическая работа N. Тема.md` или
   `Самостоятельная работа N. Тема.md`. Номер и вид берутся из имени.
2. Заголовок первого уровня — один, с номером и темой.
3. Разделы — `##`. Допускаются синонимы: «Краткая справочная информация»
   станет «Теоретической частью», «Структура репозитория» — «Требованиями
   к репозиторию». Полная таблица — в `tools/coursekit/model.py`.
4. Прогнать `python -m coursekit qa` и посмотреть `dist/qa-report.md`.

## Уровни QA

- **ERROR** — структурный брак: не один H1, незакрытый блок кода, битая
  локальная ссылка. Сборка возвращает 1.
- **WARN** — нет обязательного или рекомендуемого раздела, отсутствует
  картинка (в документе остаётся рамка-плейсхолдер), у блока кода нет
  языка, устаревший стек, слишком короткий или длинный текст, `TODO`,
  прямые кавычки в русском тексте.

Обязательные разделы: лекция — план, резюме, контрольные вопросы;
практика — цель, ход, варианты, критерии; экзамен — варианты и критерии.

## Частые ошибки

- `pandoc не найден` — установить `pandoc` (нужен 3.1+).
- `typst не найден` — положить бинарник в `PATH`.
- `mermaid-cli не смог отрисовать схему` — проверить синтаксис блока,
  наличие Node.js и `--no-sandbox` в `puppeteer.json`.
- Кириллица в именах файлов поддерживается, но в артефактах имена
  транслитерируются; исходники можно не переименовывать.
- `Syntax Error: Suspects object is wrong type (boolean)` от poppler —
  безвредное предупреждение Typst-PDF, `pdfinfo` и `pdftotext` работают.
