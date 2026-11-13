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
python -m coursekit docs                 # методичка: титул, содержание, приложения, источники
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

## Базовая линия 2026-11-13

Замер перед работами по контракту `plan.yml` (ветка `feat/plan-contract`,
коммит `b659f1c`). Окружение: `~/work/.venv`, зависимости из
`pip install -e "tools[dev]"`, Python 3.12.

```bash
PYTHONPATH=tools ~/work/.venv/bin/python -m pytest tools/coursekit/tests -q
# 46 passed in 126.34s

PYTHONPATH=tools ~/work/.venv/bin/python -m coursekit qa
# 0 ERROR, 33 WARN
```

Предупреждения относятся к существующим материалам (нет раздела «Варианты
заданий», блоки кода без языка, прямые кавычки) и в этой работе не
исправляются — они фиксируются как известные.

## План курса

`plan.yml` — единственный источник правды о структуре курса: разделы,
занятия, часы, результаты, источники. Материалы и презентации ссылаются на
его `id`, поэтому план проверяется до написания текста.

```bash
python -m coursekit plan                      # сводка: разделы, часы, материал
python -m coursekit plan --check              # E/W, код 1 при ошибке
python -m coursekit plan --check --against ktp.yml --json dist/plan-report.json
python -m coursekit plan --scaffold           # создать файлы занятий с planned: true
python -m coursekit plan --import --from . --force         # собрать plan.yml из корпуса
python -m coursekit --version                 # coursekit 1.1 (plan schema 1)
```

Пример сводки:

```text
Курс: МДК 01.04 Системное программирование
Разделов: 4, занятий: 24
Материал есть: 18, запланировано: 6
Часы: total 190, теория 78, практика 92, курсовое 20, СРС 20
Раздел 1. Основы .NET и С# — 48 ч (lecture: 6, practice: 6)
E E-HOURS-KIND часы «theory» в шапке: 78, а по занятиям вида «lecture»: 76
```

Уровни: `E` — план невалиден (код 1), `W` — замечание, `D` — расхождение
с КТП (не влияет на код возврата). Сверка с КТП нужна, чтобы правки РП
были видны: `D-ADDED`, `D-REMOVED`, `D-MOVED`, `D-HOURS`, `D-COUNT`.

Тесты пакета:

```bash
~/work/.venv/bin/pip install -e "tools[dev]"
PYTHONPATH=tools ~/work/.venv/bin/python -m pytest tools/coursekit/tests -q
```

## План эталонного курса

`ktp.yml` собран из «КТП по МДК.01.04 (ИБ).docx» командой `coursekit ktp`,
`plan.yml` — командой `coursekit plan --import`, ссылки занятий перенесены
в `sources.yml`. Текущее состояние:

```text
PYTHONPATH=tools python3 -m coursekit plan --check --against ktp.yml
# 0 E, 0 W, 0 D
```

Отчёт для учебной части — `docs/ktp-diff.md` (перегенерируется той же
командой с `--json docs/plan-report.json`).

## Сквозной прогон 2026-11-13

Цепочка проверена на эталоне целиком, времена — на этом VPS.

| Шаг | Команда | Время | Результат |
|-----|---------|-------|-----------|
| План | `coursekit plan --check --against ktp.yml` | 0,10 с | 0 E, 0 W, 0 D |
| Заголовки | `coursekit normalize --check` | 0,10 с | без изменений |
| Корпус | `coursekit qa` | 0,11 с | 0 ошибок, 33 предупреждения |
| Раздел 1 | `coursekit build --section 1 --only docx,pdf,pptx,figures,qa` | 30,7 с | 10 файлов, 5 предупреждений |
| Методичка | `coursekit docs` | 13,7 с | `methodichka.md`, `methodichka.docx` (388 КБ) |
| Колода с визуалами | `coursekit deck-visual "slides/…Лекция 5….md"` | 13,7 с | pptx и pdf |
| Колода | `coursekit deck "slides/…Лекция 5….md" --out dist/pptx` | 0,5 с | pptx |
| Скриншот | `node scripts/shot.mjs --command "dotnet --version"` | 2,4 с | PNG 3200×1800 |

Содержание лекции в этом прогоне не перегенерировалось: у всех 18 занятий
плана есть файлы, а перезапись преподавательского текста — не проверка
пайплайна. Генерация проверена отдельно на скиллах `lecture`, `practice`,
`slides` (скиллы и агенты проходят `scripts/check-opencode.py`).

## Проверка корпуса в CI

`qa --strict` на текущем корпусе возвращает код 1: 33 предупреждения
в существующих материалах (прямые кавычки, блоки кода без языка,
отсутствующие «Варианты заданий»). Поэтому в `materials.yml` стоит `qa`
без `--strict`; строгий режим включается отдельным коммитом после чистки
корпуса.
