Практическая работа № 2, вариант 24

Тема: HTTP API для асинхронного преобразования Markdown в Docx.
CLI читает файл и выдаёт Docx в stdout. API реализовано на Flask,
возвращает XML и использует Basic Auth из конфигурационного файла.
На третьем этапе данные хранятся в SQLite через ORM SQLAlchemy.

Подготовка

```sh
cd ~/Desktop/task2
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
mkdir -p output
pandoc --version
```

Pandoc должен быть установлен отдельно и доступен командой pandoc.
Сборка не требуется. `run.sh` запускает Python из окружения проекта.
Пять файлов для демонстрации находятся в `examples`.

API и схема данных

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
затем выполнить LEFT JOIN Assignment с этим набором по
`Assignment.identifier = Feedback.assignment`, спроецировать `parameter`,
`cache_hit`, `output` и удалить одинаковые тройки. Задачи без свежего ответа
остаются с null в полях Feedback. Ответ ровно пятиминутной давности не подходит.
Время создания самого Assignment на включение в отчёт не влияет.

Функции и настройки

- `converter`: argparse получает путь к файлу, subprocess запускает Pandoc.
  Pandoc преобразует Markdown в Docx и выдаёт результат в stdout.
  python-docx используется в тестах для проверки готовых документов.
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
- `execute_assignment` запускает задачу; `convert_assignment` вызывает CLI.
  Обе функции находятся в routes.py. ThreadPoolExecutor выполняет их в фоне.
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

Инструкция для защиты по пунктам варианта 24

Ниже пункты идут в том же порядке, что в задании: 3 пункта первого этапа,
7 пунктов второго и 4 пункта третьего. Рядом с каждым пунктом
указаны файл и строки кода для показа в VS Code.

Перед началом в терминале:

```sh
cd ~/Desktop/task2
mkdir -p output
```

Этап 1. Преобразование данных

Пункт 1. Входной файл и результат в стандартный вывод

converter.py l4-6 — argparse получает путь к Markdown-файлу.
converter.py l7-8 — subprocess запускает Pandoc, результат идёт в stdout.

Что сделали: короткая программа передаёт файл Pandoc и выбирает формат Docx.
Параметр `-o -` направляет готовый документ в стандартный вывод.
Символ `>` в терминале сохраняет этот поток в файл.

Как запустить:

```sh
./run.sh -m src.converter examples/01-heading.md > output/example.docx
```

Что получится: один файл `output/example.docx` из одного
`examples/01-heading.md`. Открыть его через Finder в Word или Pages.
Повтор той же команды перезапишет этот же документ.

Утилита принимает путь к Markdown-файлу и выводит бинарный
Docx в стандартный вывод. Перенаправлением я сохраняю его в файл.

Пункт 2. Пять примеров входных данных

examples — пять исходных Markdown-файлов.
test_converter.py l12-24 — проверка каждого примера через настоящий запуск CLI.
converter.py l7-8 — Pandoc преобразует оформление Markdown в оформление Word.

Что сделали: подготовили примеры с разным оформлением и проверяем,
что каждый результат можно открыть как Docx.

Как получить пять документов, которые останутся в output:

```sh
./run.sh -m src.converter examples/01-heading.md > output/01-heading.docx
./run.sh -m src.converter examples/02-emphasis.md > output/02-emphasis.docx
./run.sh -m src.converter examples/03-list.md > output/03-list.docx
./run.sh -m src.converter examples/04-code.md > output/04-code.docx
./run.sh -m src.converter examples/05-mixed.md > output/05-mixed.docx
```

Как отдельно проверить все пять примеров:

```sh
./run.sh -m pytest tests/test_converter.py -v
```

Ожидается `5 passed`. pytest создаёт документы во временной папке для
проверки. Пять постоянных файлов в output создают именно команды выше.
`example.docx` из пункта 1 — дополнительный документ с другим именем.

Я демонстрирую пять разных входных файлов и полученные
документы. Отдельно тесты автоматически проверяют читаемость результатов.

Пункт 3. Сохранение первого этапа коммитом

Где смотреть: коммит f1bc402 — refactor(part1), короткий конвертер через Pandoc.

Что сделали: сохранили первый этап варианта 24 отдельным коммитом
в формате Conventional Commits.

Как показать в терминале:

```sh
git show --stat f1bc402
```

Результат первого этапа сохранён отдельным коммитом part1.

Этап 2. HTTP API

Для демонстрации нужны два терминала VS Code, оба в папке task2.
Если в первом уже работает сервер на порту 8000, сначала остановить его
сочетанием Ctrl+C. Затем в первом терминале запустить:

```sh
./run.sh -m src.server --backend json --database data/variant24.json
```

Этот терминал оставить работающим. Команды клиента и тестов ниже выполнять
во втором терминале. `127.0.0.1:8000` — адрес сервера на этом компьютере.
Предупреждение Flask о development server ожидаемо для учебного запуска.

Пункт 1. Все обработчики таблицы 24 на Flask, ответы в XML

api.py l49-64 — создание приложения Flask и подключение маршрутов.
server.py l11-30 — параметры команды и запуск сервера.
routes.py l24-27 — `answer`: помещает XML в тело HTTP-ответа.
xml_format.py l27-32 — сериализация XML через стандартный ElementTree.

Все 11 обработчиков из таблицы:

| Пункт таблицы | Метод и маршрут | Где показать |
| --- | --- | --- |
| 1.1 | PUT /api/make-entity/:identifier | routes.py l30 |
| 1.2 | POST /api/discard-entity | routes.py l36 |
| 1.3 | POST /api/list-entity | routes.py l42 |
| 1.4 | GET /api/fetch-entity | routes.py l48 |
| 2.1 | PUT /api/make-assignment/:identifier | routes.py l54 |
| 2.2 | POST /api/discard-assignment | routes.py l66 |
| 2.3 | POST /api/list-assignment/:entity | routes.py l72 |
| 2.4 | GET /api/fetch-assignment | routes.py l78 |
| 3.1 | POST /api/list-feedback/:assignment | routes.py l86 |
| 3.2 | GET /api/fetch-feedback | routes.py l92 |
| 4.1 | POST /api/list-report | routes.py l98 |

Что сделали: каждый HTTP-метод и маршрут связан с функцией Flask.
Она читает параметры, вызывает модель данных и возвращает XML через answer.
Отчёт файлового этапа реализован в
report.py l6:
отбор Feedback за последние пять минут, LEFT JOIN с Assignment и проекция.

Как продемонстрировать все операции через работающий сервер:

```sh
./run.sh -m src.demo
```

Сценарий находится в
demo.py l34-58.
Он создаёт Entity и Assignment, ждёт Feedback, читает записи и отчёт,
затем удаляет созданные записи. Docx остаётся в output. В терминале видны
статусы 200 и XML-ответы. Это HTTP-запросы к первому терминалу.

Все 11 обработчиков реализованы на Flask в routes.py.
Результат каждого запроса возвращается в XML в теле ответа.

Пункт 2. Basic Auth по RFC 7617, реквизиты в конфигурации

config.ini l1-3 — учебные имя и пароль student / student.
config.py l9-14 — чтение реквизитов через ConfigParser.
api.py l20-36 — проверка Basic Auth, ответ 401 и WWW-Authenticate при отказе.
api.py l59 — проверка подключена перед каждым запросом.
client.py l25-28 — клиент кодирует пару имя:пароль в Base64 и передаёт Authorization: Basic.

Что сделали: сервер сравнивает реквизиты запроса с конфигурацией.
При ошибке возвращает 401 с XML. При верных реквизитах выполняется
обработчик; штатный результат возвращается с кодом 200 и XML.

Как проверить во втором терминале:

```sh
curl -i 'http://127.0.0.1:8000/api/fetch-entity?identifier=1'
curl -i -u student:wrong 'http://127.0.0.1:8000/api/fetch-entity?identifier=1'
curl -i -u student:student 'http://127.0.0.1:8000/api/fetch-entity?identifier=1'
```

Первые два запроса возвращают 401, третий — 200 и XML. Если записи 1 нет,
последний ответ содержит nil="true": авторизация успешна, запись не найдена.

Basic Auth проверяется перед обработчиками. Имя и пароль
берутся из config.ini; неверные реквизиты дают 401, верные допускают запрос.

Пункт 3. Выполнение через subprocess и тестовый режим

routes.py l54-63 — создание Assignment и отправка на выполнение.
api.py l58 — ThreadPoolExecutor создаёт один фоновый поток.
routes.py l104-123 — subprocess вызывает CLI; stdout сохраняется в Docx.
routes.py l126-138 — тестовый ответ либо выполнение с замером времени.
model.py l125-144 — сохранение Feedback и итогового stage.

Что сделали: API создаёт задачу и возвращает ответ, пока преобразование
выполняется в фоне. Pandoc создаёт Docx; результат получает done или failed.
Клиент через requests опрашивает Feedback до появления результата.
`parameter` — путь к Markdown на сервере; `output` — путь к Docx.

Как показать настоящее выполнение: при обычном JSON-сервере выполнить:

```sh
./run.sh -m src.demo
./run.sh -m pytest tests/test_execution.py -v
```

Демонстрация обращается к работающему серверу. Тесты отдельно создают своё
приложение, запускают настоящую утилиту и проверяют документ и ошибки.

Как показать тестовый режим: остановить первый сервер через Ctrl+C
и в первом терминале запустить:

```sh
./run.sh -m src.server --backend json --database data/variant24.json --test-mode
```

Во втором терминале:

```sh
./run.sh -m src.demo
```

В Feedback будет test.docx. subprocess не запускается, Docx не создаётся.
После показа остановить сервер через Ctrl+C и вернуть обычный JSON-сервер:

```sh
./run.sh -m src.server --backend json --database data/variant24.json
```

API передаёт задачу фоновому исполнителю, который запускает
CLI через subprocess. Тестовый режим подменяет вычисление готовым ответом.

Пункт 4. Класс API-клиента с именами методов как у модели

client.py l11 — класс ApiClient.
client.py l46-91 — 11 методов обращения к API.
model.py l69-112 — соответствующие методы модели с такими же именами.
client.py l22-44 — общая отправка HTTP через библиотеку requests.

Что сделали: например, клиент make_entity отправляет HTTP-запрос,
а модель make_entity создаёт запись. Так же совпадают имена остальных
операций таблицы: discard_entity, list_entity, fetch_entity и другие.

Как показать использование клиента:

```sh
./run.sh -m src.demo
```

Показать вызовы client.make_entity, client.make_assignment и других методов
в demo.py l40-56.

Работа с HTTP оформлена классом ApiClient. Имена его
операций совпадают с именами соответствующих операций модели данных.

Пункт 5. MBT через API-клиент и RuleBasedStateMachine

test_api.py l33-48 — ApiMachine наследуется от RuleBasedStateMachine, создаёт клиент и независимые словари состояния.
test_api.py l61-71 — начало каждого сценария, обеспечивающее вызов всех обработчиков.
test_api.py l85-105 — правило создания задачи с данными Hypothesis.
test_api.py l194-218 — сверка состояния и отчёта с независимой моделью.

Что сделали: Hypothesis генерирует данные и последовательности действий.
Тест хранит ожидаемые записи в собственных словарях и сравнивает их
с ответами через ApiClient. Проверяется поведение всей цепочки HTTP API.

Как запустить:

```sh
./run.sh -m pytest tests/test_api.py -v
```

Один тест класса содержит много сгенерированных сценариев и запросов.
Тесты запускают отдельное приложение с временной базой; к серверу в первом
терминале они не обращаются. Его данные не меняются.

MBT сравнивает ответы API с независимой моделью.
Последовательности действий генерирует Hypothesis через RuleBasedStateMachine.

Пункт 6. Покрытие всех обработчиков, отчёт coverage с ветвями

test_api.py l61-71 — все 11 маршрутов вызываются в начале каждого MBT-сценария.
test_report.py l39-64 — сгенерированные проверки LEFT JOIN и строгой границы пяти минут.
test_protocol.py l19 — проверки конфигурации авторизации через Hypothesis.
test_protocol.py l42 — сгенерированные проверки ошибочного XML.

Что сделали: измеряем покрытие API только тестами Hypothesis.
test_execution.py дополнительно проверяет настоящий запуск Pandoc и ошибки.
Обычные тесты пяти файлов CLI в эту команду не включены.

Как сформировать и показать отчёт:

```sh
./run.sh -m coverage run --branch --source=src -m pytest tests/test_api.py tests/test_report.py tests/test_protocol.py tests/test_execution.py -q
.venv/bin/coverage report -m --include='src/api.py,src/routes.py'
```

`--branch` включает учёт ветвей условий. В сохранённом
reports/part2-coverage.txt покрытие api.py
и routes.py — 100%. Это покрытие обработчиков API и авторизации,
а не заявление о 100% покрытия всех файлов проекта.

Все обработчики выполнены тестами Hypothesis.
Coverage с параметром --branch подтверждает покрытие строк и ветвей API.

Пункт 7. Сохранение второго этапа коммитом

Где смотреть: коммит 7631130 — feat(part2).

Что сделали: сохранили Flask API, XML, Basic Auth, subprocess,
API-клиент и тесты отдельным коммитом второго этапа варианта 24.

Как показать:

```sh
git show --stat 7631130
```

Второй этап сохранён отдельным коммитом part2.

Этап 3. SQLite через ORM SQLAlchemy

Остановить сервер второго этапа в первом терминале через Ctrl+C.
В первом терминале запустить сервер с SQLite:

```sh
./run.sh -m src.server --backend sqlite --database data/variant24.sqlite3
```

Первый терминал оставить работающим. Команды ниже выполнять во втором.

Пункт 1. Взаимодействие с SQLite через SQLAlchemy ORM

orm.py l16-52 — ORM-классы Entity, Assignment, Feedback, столбцы и внешние ключи.
sql_storage.py l19-24 — создание подключения к SQLite-файлу и таблиц.
sql_storage.py l26-44 — чтение через Session/select и сохранение ORM-объектов в транзакции.
sql_storage.py l46-62 — ORM-запрос отчёта с подзапросом, outerjoin и distinct.

Что сделали: классы Python отображают таблицы базы. SqlStorage работает
с ними через ORM, а SQLite хранит таблицы в одном файле .sqlite3.
Отдельный сервер базы устанавливать не нужно.

Как показать операции с SQLite:

```sh
./run.sh -m src.demo
```

Сценарий выполнит операции с новой базой, покажет XML и создаст настоящий
Docx. Показать файл data/variant24.sqlite3 в папке проекта.

Для SQLite используется SQLAlchemy ORM: таблицы описаны
классами, чтение и сохранение выполняются через Session.

Пункт 2. Замена слоя данных и повторное MBT API

api.py l55-56 — выбор JsonStorage либо SqlStorage и подключение к модели.
server.py l15-25 — параметр --backend и выбор файла базы.
test_sql_api.py l8-16 — те же MBT-сценарии с backend=sqlite.
test_api.py l50-53 — создание тестового приложения с выбранным хранилищем.

Что сделали: заменили реализацию доступа к данным на SqlStorage.
Маршруты API и клиент используют прежние операции. Те же сценарии
проверяют, что поведение API сохранилось после замены хранилища.

Как проверить:

```sh
./run.sh -m pytest tests/test_sql_api.py -v
```

Слой доступа заменён ORM-реализацией для SQLite.
После замены повторно выполнены те же модельные тесты через API-клиент.

Пункт 3. Покрытие API с SQLite тестами Hypothesis

test_sql_api.py l8 — модельные сценарии именно с SQLite.
test_api.py l62-71 — все обработчики выполняются в каждом сценарии.
test_report.py l39-64 — проверки формулы на JSON и SQLite, включая null и разные значения cache_hit/output.

Что сделали: повторили измерение покрытия с SQLite. Используются
только тесты Hypothesis; обычные CLI-тесты в измерение не включены.

Как сформировать и показать отчёт:

```sh
./run.sh -m coverage run --branch --source=src -m pytest tests/test_sql_api.py tests/test_report.py tests/test_protocol.py tests/test_execution.py -q
.venv/bin/coverage report -m --include='src/api.py,src/routes.py'
```

Сохранённый результат —
reports/part3-coverage.txt: 100% обработчиков
API и ветвей авторизации. Подзапрос отчёта отбирает Feedback с
`created > now - 300`; LEFT JOIN сохраняет задачи без свежего результата.
Результат ровно пятиминутной давности не подходит. Время создания
самого Assignment на отбор Feedback не влияет.

После перехода на SQLite все обработчики по-прежнему
покрыты сгенерированными тестами. Отчёт coverage учитывает ветви.

Пункт 4. Сохранение третьего этапа коммитом

Где смотреть: коммит 32de20d — feat(part3).

Что сделали: сохранили SQLite ORM, повторные MBT, отчёты покрытия
и результаты проверок отдельным коммитом третьего этапа варианта 24.

Как показать:

```sh
git show --stat 32de20d
```

Третий этап сохранён отдельным коммитом part3.

Общая проверка в конце защиты

```sh
./run.sh -m pytest -q
.venv/bin/pycodestyle src tests
.venv/bin/radon cc src tests -s
```

Первая команда запускает все проверки. В сохранённом
reports/final-tests.txt — 14 passed.
Вторая проверяет PEP8: отсутствие сообщений означает отсутствие ошибок.
Третья показывает сложность функций. Результаты оформления и ограничений
по длине функций сохранены в reports/quality.txt.

В конце остановить сервер в первом терминале через Ctrl+C.
