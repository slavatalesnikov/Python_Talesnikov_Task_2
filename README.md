# Практическая работа № 2, вариант 24

Тема: HTTP API для асинхронного преобразования Markdown в Docx.
CLI читает файл и выдаёт Docx в stdout. API реализовано на Flask,
возвращает XML и использует Basic Auth из конфигурационного файла.
На третьем этапе данные хранятся в SQLite через ORM SQLAlchemy.

## Подготовка

```sh
cd ~/Desktop/task2
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
mkdir -p output
```

Сборка не требуется. `run.sh` запускает Python из окружения проекта.
Пять файлов для демонстрации находятся в `examples`.

## API и схема данных

| Метод | Маршрут | Параметры |
| --- | --- | --- |
| PUT | `/api/make-entity/{identifier}` | путь, XML |
| POST | `/api/discard-entity` | XML |
| POST | `/api/list-entity` | XML |
| GET | `/api/fetch-entity` | query |
| PUT | `/api/make-assignment/{identifier}` | путь, XML |
| POST | `/api/discard-assignment` | XML |
| POST | `/api/list-assignment/{entity}` | путь, XML |
| GET | `/api/fetch-assignment` | query |
| POST | `/api/list-feedback/{assignment}` | путь, XML |
| GET | `/api/fetch-feedback` | query |
| POST | `/api/list-report` | нет |

Поля соответствуют рисунку 24:

- Entity: `identifier`, `created`, `ip`, `locale`, `platform`.
- Assignment: `identifier`, `created`, `parameter`, `entity`, `tags`,
  `stage`, `triggered`.
- Feedback: `identifier`, `created`, `output`, `stage`, `exception`,
  `assignment`, `cache_hit`, `duration`.

Ключи, created, triggered, cache_hit и duration — целые числа.
Остальные поля — строки. Время created и triggered — секунды Unix;
duration — длительность выполнения в миллисекундах. cache_hit равен 0:
кэширование в этом задании не реализуется.

`parameter` содержит путь к Markdown-файлу, доступному серверу;
`output` — путь к созданному Docx. Относительные пути считаются от папки
проекта. Создать Entity нужно до её Assignment. Удаление Entity каскадно
удаляет её Assignment и Feedback; удаление Assignment удаляет её Feedback.

Для чтения передаётся `?identifier=1`; для удаления — identifier в XML.
Поиск сравнивает все переданные поля на равенство. Пустое тело фильтра —
`<request/>`. Если запись не найдена, чтение возвращает XML с `nil="true"`,
поиск — пустой список. Повторное удаление возвращает deleted=0.

Ответы: 200 для штатного запроса; 401 без верной авторизации;
400 при ошибке входных полей или XML. Все ответы оформляются в XML.
Списки имеют `kind="list"`, словари — `kind="object"`, числа — `type="int"`.
Отсутствующее значение передаётся атрибутом `nil="true"`.

Пример XML-запроса с учебными реквизитами:

```sh
curl -u student:student -X PUT http://127.0.0.1:8000/api/make-entity/1 \
  -H 'Content-Type: application/xml' \
  --data '<request><ip>127.0.0.1</ip><locale>ru</locale><platform>mac</platform></request>'
curl -u student:student 'http://127.0.0.1:8000/api/fetch-entity?identifier=1'
```

Задача создаётся со stage=queued. Один фоновый поток вызывает CLI через
subprocess, передаёт путь Markdown аргументом и сохраняет бинарный stdout
в Docx. HTTP-запрос не ждёт преобразования. Во время исполнения stage=running;
итог — done или failed. Feedback содержит результат либо текст exception.
Таймаут CLI — 60 секунд. В тестовом режиме subprocess не запускается,
возвращается test.docx; настоящий файл в этом режиме не создаётся.

Отчёт по формуле 24: сначала выбрать Feedback с `created > now - 5 * 60`,
затем выполнить **LEFT JOIN** Assignment с этим набором по
`Assignment.identifier = Feedback.assignment`, спроецировать `parameter`,
`cache_hit`, `output` и удалить одинаковые тройки. Задачи без свежего ответа
остаются с null в полях Feedback. Ответ ровно пятиминутной давности не подходит.
Время создания самого Assignment на включение в отчёт не влияет.

## Функции и настройки

- `converter`: main читает UTF-8 файл; convert создаёт Docx; add_block
  оформляет блоки; add_inline переносит текст и выделение. Поддерживаются
  заголовки, абзацы, списки, выделение, ссылки и блоки кода; цитаты — абзацы.
- `Model` и `ApiClient` имеют одинаковые 11 публичных методов: make_entity,
  discard_entity, list_entity, fetch_entity, make_assignment,
  discard_assignment, list_assignment, fetch_assignment, list_feedback,
  fetch_feedback, list_report. Их назначение соответствует таблице API.
- Внутренние `_make`, `_list`, `_fetch`, `_discard` обслуживают таблицы;
  start отмечает запуск; complete сохраняет Feedback и итоговый stage.
- `JsonStorage.load/save/report/close` читает, сохраняет, строит отчёт
  и закрывает файловое хранилище.
- `SqlStorage` имеет тот же интерфейс и выполняет операции через ORM.
  Классы Entity, Assignment, Feedback в orm.py отображают таблицы SQLite.
  Сохранение выполняется транзакцией; report использует ORM-подзапрос
  с фильтром времени, outerjoin и distinct.
- `build_report` вычисляет формулу; normalize проверяет поля и типы.
- `Worker.submit/execute/convert_file/close` ставит задачу в очередь,
  выполняет её, запускает CLI и дожидается завершения.
- `create_app` собирает Flask; authorize проверяет Basic Auth;
  bad_request и http_error оформляют ошибки; функции routes вызывают модель.
- `xml_format` кодирует и разбирает XML: fill/dumps, read/loads, fields.
- `load_auth` читает файл; `ApiClient.request/close` отправляет запросы
  и закрывает соединения; `demo.main/show/wait_result` демонстрирует API.

`config.ini` содержит секцию `[auth]`, поля username и password.
В репозитории указаны учебные реквизиты `student` / `student`.
Сервер принимает `--backend` (`sqlite` по умолчанию или `json`),
`--config`, `--database`, `--output`, `--port` (8000)
и `--test-mode`. Клиент демонстрации — `--config` и `--url`.
Сервер слушает 127.0.0.1. Базы, Docx и служебные файлы исключены из Git.

MBT использует RuleBasedStateMachine и независимую модель в словарях.
Отчёты покрытия с ветвями формируются только тестами Hypothesis.
Отдельные тесты проверяют LEFT JOIN, границу времени, Basic Auth,
сохранность базы, реальный subprocess и ошибки преобразования.

## Инструкция для защиты

### Этап 1: файл → стандартный вывод

```sh
./run.sh -m src.converter examples/01-heading.md > output/example.docx
./run.sh -m pytest tests/test_converter.py -v
```

Первый запуск читает Markdown-файл; `>` сохраняет бинарный stdout в Docx.
Второй проверяет пять примеров. В stdout нет служебного текста.

### Этап 2: Flask, XML и Basic Auth

```sh
./run.sh -m src.server --backend json --database data/variant24.json
```

В другом терминале, также из папки task2:

```sh
./run.sh -m src.demo
./run.sh -m coverage run --branch --source=src -m pytest tests/test_api.py tests/test_report.py tests/test_protocol.py -q
.venv/bin/coverage report -m --include='src/api.py,src/routes.py'
./run.sh -m pytest tests/test_worker.py -v
```

Демонстрация вызывает все 11 маршрутов, ждёт Feedback и показывает XML-отчёт.
Затем удаляет свои записи; созданный Docx остаётся в output.
MBT проверяет API и авторизацию, coverage показывает покрытие ветвей.
Тесты исполнителя проверяют настоящее преобразование и ошибки процесса.
Для остановки сервера нажать Ctrl+C.

### Этап 3: SQLite через ORM SQLAlchemy

Остановить сервер второго этапа и запустить:

```sh
./run.sh -m src.server --backend sqlite --database data/variant24.sqlite3
```

В другом терминале:

```sh
./run.sh -m src.demo
./run.sh -m coverage run --branch --source=src -m pytest tests/test_sql_api.py tests/test_report.py tests/test_protocol.py -q
.venv/bin/coverage report -m --include='src/api.py,src/routes.py'
./run.sh -m pytest -q
.venv/bin/pycodestyle src tests
.venv/bin/radon cc src tests -s
```

Демонстрация повторяет 11 операций с SQLite. MBT проверяет тот же контракт
с новым слоем доступа; отчёт вычисляется ORM-запросом с LEFT JOIN.
Последние команды проверяют весь проект, оформление PEP8 и сложность.
Результаты проверок сохранены в reports. По умолчанию база —
`data/variant24.sqlite3`; для JSON — `data/variant24.json`.

Чтобы показать режим без subprocess: остановить сервер, запустить
`./run.sh -m src.server --test-mode`, затем в другом терминале
`./run.sh -m src.demo`. В Feedback будет test.docx без создания файла.
