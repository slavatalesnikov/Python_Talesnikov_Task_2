# Практическая работа № 2, вариант 22

Тема: HTTP API для асинхронного преобразования Markdown в Docx.

Утилита читает Markdown из стандартного ввода и сохраняет Docx на диск.
Поддерживаются заголовки, абзацы, выделение, списки, ссылки, цитаты
(как обычные абзацы) и блоки кода. Пять примеров находятся в `examples`.

`convert(text, output)` преобразует текст; `add_inline` переносит выделение;
`main` обрабатывает аргументы командной строки.

## Подготовка

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Сборка не требуется. Проверка стиля: `.venv/bin/pycodestyle src tests`.

## Инструкция для защиты

### Этап 1

```sh
./run.sh -m src.converter output/example.docx < examples/01-heading.md
./run.sh -m pytest tests/test_converter.py -v
```

Первая команда преобразует Markdown из stdin в Docx; вторая проверяет
все пять примеров.
