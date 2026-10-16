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
- `JsonStorage` и `TinyStorage`: `load`, `save`, `close` — чтение,
  сохранение и закрытие JSON-файла или документной базы TinyDB.
- `Worker.execute` выполняет CLI; таймаут процесса — 60 секунд.
- `create_app` собирает приложение; `check_headers` проверяет заголовки;
  `bad_request` оформляет ошибки модели. Функции `routes` соответствуют
  строкам таблицы API и вызывают модель.
- `ApiClient` содержит десять методов вида `put_actor_submit`,
  `get_report_show` и т. д.; имена соответствуют методу, таблице и действию.
  `request` отправляет HTTP-запрос, `close` закрывает соединение.
- `demo.main` демонстрирует API; `show` печатает ответ;
  `wait_result` опрашивает результат до 10 секунд. Параметр `--url`
  у демонстрации задаёт адрес сервера (по умолчанию порт 8000).

`src.server` принимает `--backend` (`tinydb` по умолчанию или `json`),
`--database` (путь базы, по умолчанию `data/<backend>.json`), `--output` (каталог Docx),
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
./run.sh -m src.server --backend json --database data/json.json
```

Сервер остаётся работать в этом терминале. В другом терминале:

```sh
./run.sh -m src.demo
./run.sh -m coverage run --branch --source=src -m pytest tests/test_api.py tests/test_report.py -q
.venv/bin/coverage report -m --include='src/api.py,src/routes.py'
./run.sh -m pytest tests/test_worker.py -v
```

Демонстрация вызывает все 10 маршрутов: создаёт участника, меняет его,
отправляет Markdown на преобразование, опрашивает результат, меняет задачу,
показывает отчёт, удаляет задачу и участника. Docx остаётся в `output`.
Тесты MBT сравнивают API с независимой моделью, coverage учитывает ветви.
Тест исполнителя отдельно проверяет настоящий subprocess и ошибки запуска.
Сервер останавливается сочетанием Ctrl+C.

### Этап 3

```sh
./run.sh -m src.server --backend tinydb --database data/tinydb.json
```

После остановки сервера второго этапа запускаем приложение с TinyDB.
В другом терминале:

```sh
./run.sh -m src.demo
./run.sh -m coverage run --branch --source=src -m pytest tests/test_tiny_api.py tests/test_report.py -q
.venv/bin/coverage report -m --include='src/api.py,src/routes.py'
./run.sh -m pytest -q
.venv/bin/pycodestyle src tests
.venv/bin/radon cc src tests -s
```

Первый запуск показывает те же 10 операций с базой TinyDB. Затем MBT
повторяет проверки API с новым слоем доступа; coverage показывает покрытие
обработчиков и ветвей проверки заголовков. Последние команды запускают все
тесты (включая сохранность после открытия базы), PEP8 и проверку сложности.

Чтобы показать режим без настоящего преобразования, остановить сервер и
запустить `./run.sh -m src.server --test-mode`, затем `./run.sh -m src.demo`.
В ответе будет `test.docx`, настоящий файл в этом режиме не создаётся.
