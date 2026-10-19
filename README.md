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

## Инструкция для защиты по пунктам варианта 24

Ниже пункты идут в том же порядке, что в задании: 3 пункта первого этапа,
7 пунктов второго и 4 пункта третьего. Ссылки открывают код на GitHub;
в подписи указаны файл и строки, которые можно показать в VS Code.

Перед началом в терминале:

```sh
cd ~/Desktop/task2
mkdir -p output
```

### Этап 1. Преобразование данных

#### Пункт 1. Входной файл и результат в стандартный вывод

**Где в коде:**

- [src/converter.py:82–88](https://github.com/slavatalesnikov/Python_Talesnikov_Task_2/blob/main/src/converter.py#L82-L88) — аргумент с путём, чтение файла UTF-8 и передача результата в `sys.stdout.buffer`.
- [src/converter.py:58–79](https://github.com/slavatalesnikov/Python_Talesnikov_Task_2/blob/main/src/converter.py#L58-L79) — функция `convert`: разбирает Markdown и создаёт Docx.
- [src/converter.py:7–8](https://github.com/slavatalesnikov/Python_Talesnikov_Task_2/blob/main/src/converter.py#L7-L8) — библиотеки `markdown-it-py` и `python-docx`.

**Что сделали:** `MarkdownIt` разбирает оформление входного текста,
`Document` создаёт документ Word. Готовые байты направляются в stdout.
Символ `>` в терминале сохраняет этот поток в файл.

**Как запустить:**

```sh
./run.sh -m src.converter examples/01-heading.md > output/example.docx
```

**Что получится:** один файл `output/example.docx` из одного
`examples/01-heading.md`. Открыть его через Finder в Word или Pages.
Повтор той же команды перезапишет этот же документ.

**Что сказать:** «Утилита принимает путь к Markdown-файлу и выводит бинарный
Docx в стандартный вывод. Перенаправлением я сохраняю его в файл».

#### Пункт 2. Пять примеров входных данных

**Где в коде:**

- [examples](https://github.com/slavatalesnikov/Python_Talesnikov_Task_2/tree/main/examples) — пять исходных Markdown-файлов.
- [tests/test_converter.py:12–24](https://github.com/slavatalesnikov/Python_Talesnikov_Task_2/blob/main/tests/test_converter.py#L12-L24) — проверка каждого примера через настоящий запуск CLI.
- [src/converter.py:39–54](https://github.com/slavatalesnikov/Python_Talesnikov_Task_2/blob/main/src/converter.py#L39-L54) — оформление заголовков, абзацев, списков и кода.
- [src/converter.py:14–36](https://github.com/slavatalesnikov/Python_Talesnikov_Task_2/blob/main/src/converter.py#L14-L36) — выделение текста и ссылки.

**Что сделали:** подготовили примеры с разным оформлением и проверяем,
что каждый результат можно открыть как Docx.

**Как получить пять документов, которые останутся в output:**

```sh
./run.sh -m src.converter examples/01-heading.md > output/01-heading.docx
./run.sh -m src.converter examples/02-emphasis.md > output/02-emphasis.docx
./run.sh -m src.converter examples/03-list.md > output/03-list.docx
./run.sh -m src.converter examples/04-code.md > output/04-code.docx
./run.sh -m src.converter examples/05-mixed.md > output/05-mixed.docx
```

**Как отдельно проверить все пять примеров:**

```sh
./run.sh -m pytest tests/test_converter.py -v
```

Ожидается `5 passed`. pytest создаёт документы во временной папке для
проверки. Пять постоянных файлов в output создают именно команды выше.
`example.docx` из пункта 1 — дополнительный документ с другим именем.

**Что сказать:** «Я демонстрирую пять разных входных файлов и полученные
документы. Отдельно тесты автоматически проверяют читаемость результатов».

#### Пункт 3. Сохранение первого этапа коммитом

**Где смотреть:** [коммит a282955 — feat(part1)](https://github.com/slavatalesnikov/Python_Talesnikov_Task_2/commit/a282955).

**Что сделали:** сохранили первый этап варианта 24 отдельным коммитом
в формате Conventional Commits.

**Как показать в терминале:**

```sh
git show --stat a282955
```

**Что сказать:** «Результат первого этапа сохранён отдельным коммитом part1».

### Этап 2. HTTP API

Для демонстрации нужны два терминала VS Code, оба в папке task2.
Если в первом уже работает сервер на порту 8000, сначала остановить его
сочетанием Ctrl+C. Затем в первом терминале запустить:

```sh
./run.sh -m src.server --backend json --database data/variant24.json
```

Этот терминал оставить работающим. Команды клиента и тестов ниже выполнять
во втором терминале. `127.0.0.1:8000` — адрес сервера на этом компьютере.
Предупреждение Flask о development server ожидаемо для учебного запуска.

#### Пункт 1. Все обработчики таблицы 24 на Flask, ответы в XML

**Где в коде:**

- [src/api.py:49–63](https://github.com/slavatalesnikov/Python_Talesnikov_Task_2/blob/main/src/api.py#L49-L63) — создание приложения Flask и подключение маршрутов.
- [src/server.py:11–30](https://github.com/slavatalesnikov/Python_Talesnikov_Task_2/blob/main/src/server.py#L11-L30) — параметры команды и запуск сервера.
- [src/routes.py:16–19](https://github.com/slavatalesnikov/Python_Talesnikov_Task_2/blob/main/src/routes.py#L16-L19) — `answer`: помещает XML в тело HTTP-ответа.
- [src/xml_format.py:27–31](https://github.com/slavatalesnikov/Python_Talesnikov_Task_2/blob/main/src/xml_format.py#L27-L31) — сериализация XML через стандартный ElementTree.

**Все 11 обработчиков из таблицы:**

| Пункт таблицы | Метод и маршрут | Где показать |
| --- | --- | --- |
| 1.1 | PUT /api/make-entity/:identifier | [routes.py:22](https://github.com/slavatalesnikov/Python_Talesnikov_Task_2/blob/main/src/routes.py#L22) |
| 1.2 | POST /api/discard-entity | [routes.py:28](https://github.com/slavatalesnikov/Python_Talesnikov_Task_2/blob/main/src/routes.py#L28) |
| 1.3 | POST /api/list-entity | [routes.py:34](https://github.com/slavatalesnikov/Python_Talesnikov_Task_2/blob/main/src/routes.py#L34) |
| 1.4 | GET /api/fetch-entity | [routes.py:40](https://github.com/slavatalesnikov/Python_Talesnikov_Task_2/blob/main/src/routes.py#L40) |
| 2.1 | PUT /api/make-assignment/:identifier | [routes.py:46](https://github.com/slavatalesnikov/Python_Talesnikov_Task_2/blob/main/src/routes.py#L46) |
| 2.2 | POST /api/discard-assignment | [routes.py:54](https://github.com/slavatalesnikov/Python_Talesnikov_Task_2/blob/main/src/routes.py#L54) |
| 2.3 | POST /api/list-assignment/:entity | [routes.py:60](https://github.com/slavatalesnikov/Python_Talesnikov_Task_2/blob/main/src/routes.py#L60) |
| 2.4 | GET /api/fetch-assignment | [routes.py:66](https://github.com/slavatalesnikov/Python_Talesnikov_Task_2/blob/main/src/routes.py#L66) |
| 3.1 | POST /api/list-feedback/:assignment | [routes.py:74](https://github.com/slavatalesnikov/Python_Talesnikov_Task_2/blob/main/src/routes.py#L74) |
| 3.2 | GET /api/fetch-feedback | [routes.py:80](https://github.com/slavatalesnikov/Python_Talesnikov_Task_2/blob/main/src/routes.py#L80) |
| 4.1 | POST /api/list-report | [routes.py:86](https://github.com/slavatalesnikov/Python_Talesnikov_Task_2/blob/main/src/routes.py#L86) |

**Что сделали:** каждый HTTP-метод и маршрут связан с функцией Flask.
Она читает параметры, вызывает модель данных и возвращает XML через answer.
Отчёт файлового этапа реализован в
[src/report.py:6](https://github.com/slavatalesnikov/Python_Talesnikov_Task_2/blob/main/src/report.py#L6):
отбор Feedback за последние пять минут, LEFT JOIN с Assignment и проекция.

**Как продемонстрировать все операции через работающий сервер:**

```sh
./run.sh -m src.demo
```

Сценарий находится в
[src/demo.py:34–58](https://github.com/slavatalesnikov/Python_Talesnikov_Task_2/blob/main/src/demo.py#L34-L58).
Он создаёт Entity и Assignment, ждёт Feedback, читает записи и отчёт,
затем удаляет созданные записи. Docx остаётся в output. В терминале видны
статусы 200 и XML-ответы. Это HTTP-запросы к первому терминалу.

**Что сказать:** «Все 11 обработчиков реализованы на Flask в routes.py.
Результат каждого запроса возвращается в XML в теле ответа».

#### Пункт 2. Basic Auth по RFC 7617, реквизиты в конфигурации

**Где в коде:**

- [config.ini:1–3](https://github.com/slavatalesnikov/Python_Talesnikov_Task_2/blob/main/config.ini#L1-L3) — учебные имя и пароль student / student.
- [src/config.py:9–14](https://github.com/slavatalesnikov/Python_Talesnikov_Task_2/blob/main/src/config.py#L9-L14) — чтение реквизитов через ConfigParser.
- [src/api.py:20–36](https://github.com/slavatalesnikov/Python_Talesnikov_Task_2/blob/main/src/api.py#L20-L36) — проверка Basic Auth, ответ 401 и WWW-Authenticate при отказе.
- [src/api.py:58](https://github.com/slavatalesnikov/Python_Talesnikov_Task_2/blob/main/src/api.py#L58) — проверка подключена перед каждым запросом.
- [src/client.py:24–27](https://github.com/slavatalesnikov/Python_Talesnikov_Task_2/blob/main/src/client.py#L24-L27) — клиент кодирует пару имя:пароль в Base64 и передаёт Authorization: Basic.

**Что сделали:** сервер сравнивает реквизиты запроса с конфигурацией.
При ошибке возвращает 401 с XML. При верных реквизитах выполняется
обработчик; штатный результат возвращается с кодом 200 и XML.

**Как проверить во втором терминале:**

```sh
curl -i 'http://127.0.0.1:8000/api/fetch-entity?identifier=1'
curl -i -u student:wrong 'http://127.0.0.1:8000/api/fetch-entity?identifier=1'
curl -i -u student:student 'http://127.0.0.1:8000/api/fetch-entity?identifier=1'
```

Первые два запроса возвращают 401, третий — 200 и XML. Если записи 1 нет,
последний ответ содержит nil="true": авторизация успешна, запись не найдена.

**Что сказать:** «Basic Auth проверяется перед обработчиками. Имя и пароль
берутся из config.ini; неверные реквизиты дают 401, верные допускают запрос».

#### Пункт 3. Выполнение через subprocess и тестовый режим

**Где в коде:**

- [src/routes.py:46–51](https://github.com/slavatalesnikov/Python_Talesnikov_Task_2/blob/main/src/routes.py#L46-L51) — создание Assignment и передача Worker.
- [src/worker.py:18–30](https://github.com/slavatalesnikov/Python_Talesnikov_Task_2/blob/main/src/worker.py#L18-L30) — один фоновый поток и постановка задачи в очередь.
- [src/worker.py:32–51](https://github.com/slavatalesnikov/Python_Talesnikov_Task_2/blob/main/src/worker.py#L32-L51) — subprocess запускает src.converter с путём parameter; stdout сохраняется в Docx.
- [src/worker.py:53–65](https://github.com/slavatalesnikov/Python_Talesnikov_Task_2/blob/main/src/worker.py#L53-L65) — тестовый результат либо настоящее выполнение с замером времени.
- [src/model.py:125–144](https://github.com/slavatalesnikov/Python_Talesnikov_Task_2/blob/main/src/model.py#L125-L144) — сохранение Feedback и итогового stage.

**Что сделали:** при создании задачи API возвращает запись с queued.
Worker в фоне запускает утилиту первого этапа; результат получает done
или failed. Клиент опрашивает Feedback, пока результат не появится.
`parameter` — путь к Markdown-файлу на сервере; `output` — путь к Docx.

**Как показать настоящее выполнение:** при обычном JSON-сервере выполнить:

```sh
./run.sh -m src.demo
./run.sh -m pytest tests/test_worker.py -v
```

Демонстрация обращается к работающему серверу. Тесты отдельно создают своё
приложение, запускают настоящую утилиту и проверяют документ и ошибки.

**Как показать тестовый режим:** остановить первый сервер через Ctrl+C
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

**Что сказать:** «API передаёт задачу фоновому исполнителю, который запускает
CLI через subprocess. Тестовый режим подменяет вычисление готовым ответом».

#### Пункт 4. Класс API-клиента с именами методов как у модели

**Где в коде:**

- [src/client.py:11](https://github.com/slavatalesnikov/Python_Talesnikov_Task_2/blob/main/src/client.py#L11) — класс ApiClient.
- [src/client.py:41–86](https://github.com/slavatalesnikov/Python_Talesnikov_Task_2/blob/main/src/client.py#L41-L86) — 11 методов обращения к API.
- [src/model.py:69–112](https://github.com/slavatalesnikov/Python_Talesnikov_Task_2/blob/main/src/model.py#L69-L112) — соответствующие методы модели с такими же именами.
- [src/client.py:21–39](https://github.com/slavatalesnikov/Python_Talesnikov_Task_2/blob/main/src/client.py#L21-L39) — общая отправка HTTP через библиотеку httpx.

**Что сделали:** например, клиент make_entity отправляет HTTP-запрос,
а модель make_entity создаёт запись. Так же совпадают имена остальных
операций таблицы: discard_entity, list_entity, fetch_entity и другие.

**Как показать использование клиента:**

```sh
./run.sh -m src.demo
```

Показать вызовы client.make_entity, client.make_assignment и других методов
в [src/demo.py:40–56](https://github.com/slavatalesnikov/Python_Talesnikov_Task_2/blob/main/src/demo.py#L40-L56).

**Что сказать:** «Работа с HTTP оформлена классом ApiClient. Имена его
операций совпадают с именами соответствующих операций модели данных».

#### Пункт 5. MBT через API-клиент и RuleBasedStateMachine

**Где в коде:**

- [tests/test_api.py:33–48](https://github.com/slavatalesnikov/Python_Talesnikov_Task_2/blob/main/tests/test_api.py#L33-L48) — ApiMachine наследуется от RuleBasedStateMachine, создаёт клиент и независимые словари состояния.
- [tests/test_api.py:61–71](https://github.com/slavatalesnikov/Python_Talesnikov_Task_2/blob/main/tests/test_api.py#L61-L71) — начало каждого сценария, обеспечивающее вызов всех обработчиков.
- [tests/test_api.py:85–105](https://github.com/slavatalesnikov/Python_Talesnikov_Task_2/blob/main/tests/test_api.py#L85-L105) — правило создания задачи с данными Hypothesis.
- [tests/test_api.py:194–218](https://github.com/slavatalesnikov/Python_Talesnikov_Task_2/blob/main/tests/test_api.py#L194-L218) — сверка состояния и отчёта с независимой моделью.

**Что сделали:** Hypothesis генерирует данные и последовательности действий.
Тест хранит ожидаемые записи в собственных словарях и сравнивает их
с ответами через ApiClient. Проверяется поведение всей цепочки HTTP API.

**Как запустить:**

```sh
./run.sh -m pytest tests/test_api.py -v
```

Один тест класса содержит много сгенерированных сценариев и запросов.
Тесты запускают отдельное приложение с временной базой; к серверу в первом
терминале они не обращаются. Его данные не меняются.

**Что сказать:** «MBT сравнивает ответы API с независимой моделью.
Последовательности действий генерирует Hypothesis через RuleBasedStateMachine».

#### Пункт 6. Покрытие всех обработчиков, отчёт coverage с ветвями

**Где в коде:**

- [tests/test_api.py:61–71](https://github.com/slavatalesnikov/Python_Talesnikov_Task_2/blob/main/tests/test_api.py#L61-L71) — все 11 маршрутов вызываются в начале каждого MBT-сценария.
- [tests/test_report.py:39–64](https://github.com/slavatalesnikov/Python_Talesnikov_Task_2/blob/main/tests/test_report.py#L39-L64) — сгенерированные проверки LEFT JOIN и строгой границы пяти минут.
- [tests/test_protocol.py:19](https://github.com/slavatalesnikov/Python_Talesnikov_Task_2/blob/main/tests/test_protocol.py#L19) — проверки конфигурации авторизации через Hypothesis.
- [tests/test_protocol.py:42](https://github.com/slavatalesnikov/Python_Talesnikov_Task_2/blob/main/tests/test_protocol.py#L42) — сгенерированные проверки ошибочного XML.

**Что сделали:** измеряем покрытие API только тестами Hypothesis.
Обычные тесты пяти файлов CLI в эту команду не включены.

**Как сформировать и показать отчёт:**

```sh
./run.sh -m coverage run --branch --source=src -m pytest tests/test_api.py tests/test_report.py tests/test_protocol.py -q
.venv/bin/coverage report -m --include='src/api.py,src/routes.py'
```

`--branch` включает учёт ветвей условий. В сохранённом
[reports/part2-coverage.txt](reports/part2-coverage.txt) покрытие api.py
и routes.py — 100%. Это покрытие обработчиков API и авторизации,
а не заявление о 100% покрытия всех файлов проекта.

**Что сказать:** «Все обработчики выполнены тестами Hypothesis.
Coverage с параметром --branch подтверждает покрытие строк и ветвей API».

#### Пункт 7. Сохранение второго этапа коммитом

**Где смотреть:** [коммит 7631130 — feat(part2)](https://github.com/slavatalesnikov/Python_Talesnikov_Task_2/commit/7631130).

**Что сделали:** сохранили Flask API, XML, Basic Auth, subprocess,
API-клиент и тесты отдельным коммитом второго этапа варианта 24.

**Как показать:**

```sh
git show --stat 7631130
```

**Что сказать:** «Второй этап сохранён отдельным коммитом part2».

### Этап 3. SQLite через ORM SQLAlchemy

Остановить сервер второго этапа в первом терминале через Ctrl+C.
В первом терминале запустить сервер с SQLite:

```sh
./run.sh -m src.server --backend sqlite --database data/variant24.sqlite3
```

Первый терминал оставить работающим. Команды ниже выполнять во втором.

#### Пункт 1. Взаимодействие с SQLite через SQLAlchemy ORM

**Где в коде:**

- [src/orm.py:16–52](https://github.com/slavatalesnikov/Python_Talesnikov_Task_2/blob/main/src/orm.py#L16-L52) — ORM-классы Entity, Assignment, Feedback, столбцы и внешние ключи.
- [src/sql_storage.py:19–24](https://github.com/slavatalesnikov/Python_Talesnikov_Task_2/blob/main/src/sql_storage.py#L19-L24) — создание подключения к SQLite-файлу и таблиц.
- [src/sql_storage.py:26–44](https://github.com/slavatalesnikov/Python_Talesnikov_Task_2/blob/main/src/sql_storage.py#L26-L44) — чтение через Session/select и сохранение ORM-объектов в транзакции.
- [src/sql_storage.py:46–62](https://github.com/slavatalesnikov/Python_Talesnikov_Task_2/blob/main/src/sql_storage.py#L46-L62) — ORM-запрос отчёта с подзапросом, outerjoin и distinct.

**Что сделали:** классы Python отображают таблицы базы. SqlStorage работает
с ними через ORM, а SQLite хранит таблицы в одном файле .sqlite3.
Отдельный сервер базы устанавливать не нужно.

**Как показать операции с SQLite:**

```sh
./run.sh -m src.demo
```

Сценарий выполнит операции с новой базой, покажет XML и создаст настоящий
Docx. Показать файл data/variant24.sqlite3 в папке проекта.

**Что сказать:** «Для SQLite используется SQLAlchemy ORM: таблицы описаны
классами, чтение и сохранение выполняются через Session».

#### Пункт 2. Замена слоя данных и повторное MBT API

**Где в коде:**

- [src/api.py:55–57](https://github.com/slavatalesnikov/Python_Talesnikov_Task_2/blob/main/src/api.py#L55-L57) — выбор JsonStorage либо SqlStorage и подключение к модели.
- [src/server.py:15–25](https://github.com/slavatalesnikov/Python_Talesnikov_Task_2/blob/main/src/server.py#L15-L25) — параметр --backend и выбор файла базы.
- [tests/test_sql_api.py:8–16](https://github.com/slavatalesnikov/Python_Talesnikov_Task_2/blob/main/tests/test_sql_api.py#L8-L16) — те же MBT-сценарии с backend=sqlite.
- [tests/test_api.py:50–53](https://github.com/slavatalesnikov/Python_Talesnikov_Task_2/blob/main/tests/test_api.py#L50-L53) — создание тестового приложения с выбранным хранилищем.

**Что сделали:** заменили реализацию доступа к данным на SqlStorage.
Маршруты API и клиент используют прежние операции. Те же сценарии
проверяют, что поведение API сохранилось после замены хранилища.

**Как проверить:**

```sh
./run.sh -m pytest tests/test_sql_api.py -v
```

**Что сказать:** «Слой доступа заменён ORM-реализацией для SQLite.
После замены повторно выполнены те же модельные тесты через API-клиент».

#### Пункт 3. Покрытие API с SQLite тестами Hypothesis

**Где в коде:**

- [tests/test_sql_api.py:8](https://github.com/slavatalesnikov/Python_Talesnikov_Task_2/blob/main/tests/test_sql_api.py#L8) — модельные сценарии именно с SQLite.
- [tests/test_api.py:62–71](https://github.com/slavatalesnikov/Python_Talesnikov_Task_2/blob/main/tests/test_api.py#L62-L71) — все обработчики выполняются в каждом сценарии.
- [tests/test_report.py:39–64](https://github.com/slavatalesnikov/Python_Talesnikov_Task_2/blob/main/tests/test_report.py#L39-L64) — проверки формулы на JSON и SQLite, включая null и разные значения cache_hit/output.

**Что сделали:** повторили измерение покрытия с SQLite. Используются
только тесты Hypothesis; обычные CLI-тесты в измерение не включены.

**Как сформировать и показать отчёт:**

```sh
./run.sh -m coverage run --branch --source=src -m pytest tests/test_sql_api.py tests/test_report.py tests/test_protocol.py -q
.venv/bin/coverage report -m --include='src/api.py,src/routes.py'
```

Сохранённый результат —
[reports/part3-coverage.txt](reports/part3-coverage.txt): 100% обработчиков
API и ветвей авторизации. Подзапрос отчёта отбирает Feedback с
`created > now - 300`; LEFT JOIN сохраняет задачи без свежего результата.
Результат ровно пятиминутной давности не подходит. Время создания
самого Assignment на отбор Feedback не влияет.

**Что сказать:** «После перехода на SQLite все обработчики по-прежнему
покрыты сгенерированными тестами. Отчёт coverage учитывает ветви».

#### Пункт 4. Сохранение третьего этапа коммитом

**Где смотреть:** [коммит 32de20d — feat(part3)](https://github.com/slavatalesnikov/Python_Talesnikov_Task_2/commit/32de20d).

**Что сделали:** сохранили SQLite ORM, повторные MBT, отчёты покрытия
и результаты проверок отдельным коммитом третьего этапа варианта 24.

**Как показать:**

```sh
git show --stat 32de20d
```

**Что сказать:** «Третий этап сохранён отдельным коммитом part3».

### Общая проверка в конце защиты

```sh
./run.sh -m pytest -q
.venv/bin/pycodestyle src tests
.venv/bin/radon cc src tests -s
```

Первая команда запускает все проверки. В сохранённом
[reports/final-tests.txt](reports/final-tests.txt) — 13 passed.
Вторая проверяет PEP8: отсутствие сообщений означает отсутствие ошибок.
Третья показывает сложность функций. Результаты оформления и ограничений
по длине функций сохранены в [reports/quality.txt](reports/quality.txt).

В конце остановить сервер в первом терминале через Ctrl+C.
