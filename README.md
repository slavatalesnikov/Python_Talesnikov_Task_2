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

## HTTP API и данные

Все маршруты начинаются с `/private/api/v2`. Ответы — JSON.
Заголовок `Accept: application/json` обязателен для любого метода;
для POST, PUT и PATCH также нужен `Content-Type: application/json`.
При нарушении возвращается 415, затем 406 в порядке таблицы задания.
Успешные запросы возвращают 200; некорректные поля и связи — 400,
ошибки типов параметров FastAPI — 422. Авторизации в варианте 22 нет.

| Метод | Маршрут после префикса | Параметры |
| --- | --- | --- |
| PUT | `/submit/actor/{uid}` | ключ в пути, поля в query |
| DELETE | `/pop/actor/{uid}` | ключ в пути |
| GET | `/show/actor` | фильтры в query |
| POST | `/revise/actor` | uid и новые поля в JSON |
| PUT | `/submit/instruction/{uid}` | ключ в пути, поля в query |
| DELETE | `/pop/instruction/{uid}` | ключ в пути |
| GET | `/show/instruction/{actor}` | участник в пути, фильтры в query |
| POST | `/revise/instruction` | uid и новые поля в JSON |
| GET | `/show/response/{instruction}` | задача в пути, фильтры в query |
| GET | `/show/report` | нет |

Поля соответствуют рисунку 22:

- Actor: `uid`, `datetime`, `platform`, `user_agent`.
- Instruction: `uid`, `datetime`, `input`, `actor`, `description`, `tags`,
  `stage`.
- Response: `uid`, `datetime`, `output`, `stage`, `failure`, `instruction`.

`uid`, `datetime` и внешние ключи — целые числа, остальные поля — строки.
`datetime` — секунды Unix; по умолчанию устанавливается текущее время.
`input` — текст Markdown, `output` — путь к созданному файлу.
Участник должен существовать до создания его задачи. При удалении
участника удаляются его задачи и результаты; при удалении задачи — результаты.
Поиск сравнивает все переданные поля на равенство. Пустой фильтр выбирает всё.

Задача сначала получает `stage=queued`. После отправки HTTP-ответа
FastAPI вызывает Worker, который запускает CLI через subprocess и stdin.
После выполнения stage становится `done` или `failed`; ошибка хранится
в `failure`. Результаты ищутся через `/show/response/{instruction}`.

Отчёт: выбрать Instruction с `datetime >= now - 6 * 60`, выполнить
INNER JOIN с Response по `Instruction.uid = Response.instruction`,
оставить `description` и `output`, убрать одинаковые пары.
У задач без результата строки в отчёте нет. Граница 6 минут включается.

## Функции и настройки

- `converter`: `main` читает stdin; `convert` сохраняет документ;
  `add_block` создаёт абзац; `add_inline` переносит текст и выделение.
- `Model`: `find`, `submit`, `revise`, `pop` — поиск, создание, изменение,
  удаление; `validate` проверяет поля и связи; `complete` сохраняет ответ;
  `report` вычисляет формулу 22.
- `JsonStorage`: `load`, `save`, `close` — операции с JSON-файлом.
- `Worker.execute` выполняет CLI; таймаут процесса — 60 секунд.
- `create_app` собирает приложение; `check_headers` проверяет заголовки;
  `bad_request` оформляет ошибки модели. Функции `routes` соответствуют
  строкам таблицы API и вызывают модель.
- `ApiClient` содержит десять методов вида `put_actor_submit`,
  `get_report_show` и т. д.; имена соответствуют методу, таблице и действию.
  `request` отправляет HTTP-запрос, `close` закрывает соединение.
- `demo.main` демонстрирует API; `show` печатает ответ;
  `wait_result` опрашивает результат до 10 секунд.

`src.server` принимает `--database` (путь базы), `--output` (каталог Docx),
`--port` (по умолчанию 8000), `--test-mode` (без subprocess, ответ test.docx).
Тестовый режим не создаёт Docx. По умолчанию вычисления настоящие.
Сервер слушает только `127.0.0.1` и работает в одном процессе.

Пример ручного запроса:

```sh
curl -X PUT 'http://127.0.0.1:8000/private/api/v2/submit/actor/22?platform=macOS' \
  -H 'Accept: application/json' -H 'Content-Type: application/json'
```

Сгенерированные документы, базы и служебные файлы исключены из Git.
Проверки: `pytest` запускает все тесты, `pycodestyle` проверяет PEP8,
`radon cc src tests -s` показывает цикломатическую сложность.
В `reports` сохранены результаты запуска и отчёты покрытия API с ветвями.
Тесты API генерируются Hypothesis; MBT использует RuleBasedStateMachine.
Покрытие API измеряется отдельно от CLI, без примеси обычных тестов CLI.

## Инструкция для защиты

### Этап 1

```sh
./run.sh -m src.converter output/example.docx < examples/01-heading.md
./run.sh -m pytest tests/test_converter.py -v
```

Первая команда преобразует Markdown из stdin в Docx; вторая проверяет
все пять примеров.

### Этап 2

```sh
./run.sh -m src.server --database data/json.json
```

Сервер остаётся работать в этом терминале. В другом терминале:

```sh
./run.sh -m src.demo
./run.sh -m coverage run --branch --source=src -m pytest tests/test_api.py tests/test_report.py -q
.venv/bin/coverage report -m
./run.sh -m pytest tests/test_worker.py -v
```

Демонстрация вызывает все 10 маршрутов: создаёт участника, меняет его,
отправляет Markdown на преобразование, опрашивает результат, меняет задачу,
показывает отчёт, удаляет задачу и участника. Docx остаётся в `output`.
Тесты MBT сравнивают API с независимой моделью, coverage учитывает ветви.
Тест исполнителя отдельно проверяет настоящий subprocess и ошибки запуска.
Сервер останавливается сочетанием Ctrl+C.
