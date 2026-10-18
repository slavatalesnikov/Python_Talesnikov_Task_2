# Практическая работа № 2, вариант 24

Тема: HTTP API для асинхронного преобразования Markdown в Docx.
Требования варианта 24: CLI с файлом на входе и stdout на выходе;
Flask, XML и Basic Auth; SQLite через ORM SQLAlchemy.

## Этап 1

Утилита принимает путь к файлу Markdown в UTF-8 и выдаёт байты Docx в stdout.
Поддерживаются заголовки, абзацы, выделение, списки, ссылки и блоки кода.
Цитаты сохраняются обычными абзацами. Пять примеров находятся в `examples`.
`main` читает файл; `convert` создаёт документ; `add_block` оформляет блоки;
`add_inline` переносит текст и выделение.

## Подготовка

```sh
cd ~/Desktop/task2
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
mkdir -p output
```

Сборка не требуется. `run.sh` запускает Python из окружения проекта.

## Инструкция для защиты

### Этап 1: файл → стандартный вывод

```sh
./run.sh -m src.converter examples/01-heading.md > output/example.docx
./run.sh -m pytest tests/test_converter.py -v
```

Первая команда передаёт входной файл утилите, а `>` сохраняет бинарный stdout
в Docx. Вторая команда проверяет все пять примеров. Служебный текст в stdout
не выводится, иначе документ был бы повреждён.
