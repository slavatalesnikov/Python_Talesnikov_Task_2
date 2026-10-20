"""тестирование MBT API варианта 24: независимая модель, XML и Basic Auth."""

from tempfile import TemporaryDirectory
from unittest.mock import patch

from hypothesis import settings, strategies as st
from hypothesis.stateful import (
    RuleBasedStateMachine, initialize, invariant, rule,
)

from src.api import create_app
from src.client import ApiClient
from src.xml_format import loads


NOW = 2_000_000_000
OK = 200
BAD_REQUEST = 400
UNAUTHORIZED = 401
NOT_FOUND = 404
IDENTIFIERS = st.integers(min_value=1, max_value=4)
TEXT = st.text(alphabet='абв abc012<&>', max_size=20)
ROUTES = [
    ('PUT', 'make-entity/1'), ('POST', 'discard-entity'),
    ('POST', 'list-entity'), ('GET', 'fetch-entity'),
    ('PUT', 'make-assignment/1'), ('POST', 'discard-assignment'),
    ('POST', 'list-assignment/1'), ('GET', 'fetch-assignment'),
    ('POST', 'list-feedback/1'), ('GET', 'fetch-feedback'),
    ('POST', 'list-report'),
]


class ApiMachine(RuleBasedStateMachine):
    """сравнивает данные через клиент с отдельными словарями Python."""

    backend = 'json'

    def __init__(self):
        """создаёт отдельную базу для каждого сгенерированного сценария."""
        super().__init__()
        self.directory = TemporaryDirectory()
        self.clock = patch('src.model.timestamp', return_value=NOW)
        self.clock.start()
        self.app = self.make_app()
        self.client = ApiClient(transport=self.app.test_client())
        self.entities = {}
        self.assignments = {}
        self.feedback = {}

    def make_app(self):
        """использует файловое JSON-хранилище второго этапа."""
        return create_app(f'{self.directory.name}/db', True,
                          backend=self.backend)

    def data(self, response):
        """требует 200 OK и XML для каждого штатного запроса."""
        assert response.status_code == OK, response.text
        assert response.headers['content-type'].startswith('application/xml')
        return loads(response.content)

    @initialize(text=TEXT)
    def start(self, text):
        """гарантирует выполнение всех одиннадцати обработчиков."""
        self.create_entity(1, text)
        self.create_assignment(1, 1, text)
        self.observe()
        self.filters(1, text)
        self.remove_assignment(1)
        self.remove_entity(1)
        self.unauthorized('')
        self.protocol_errors()

    @rule(identifier=IDENTIFIERS, text=TEXT)
    def create_entity(self, identifier, text):
        """создаёт Entity либо проверяет отказ при повторении ключа."""
        fields = {'created': NOW, 'ip': '127.0.0.1',
                  'locale': 'ru', 'platform': text}
        response = self.client.make_entity(identifier, fields)
        if identifier in self.entities:
            assert response.status_code == BAD_REQUEST
        else:
            self.entities[identifier] = fields | {'identifier': identifier}
            assert self.data(response) == self.entities[identifier]

    @rule(identifier=IDENTIFIERS, entity=IDENTIFIERS, text=TEXT)
    def create_assignment(self, identifier, entity, text):
        """проверяет создание задачи и автоматического тестового Feedback."""
        if entity not in self.entities:
            self.create_entity(entity, text)
        fields = {'created': NOW, 'entity': entity, 'parameter': text,
                  'tags': 'mbt', 'stage': 'queued', 'triggered': 0}
        response = self.client.make_assignment(identifier, fields)
        if identifier in self.assignments:
            assert response.status_code == BAD_REQUEST
            return
        assert self.data(response) == fields | {'identifier': identifier}
        self.assignments[identifier] = fields | {
            'identifier': identifier, 'stage': 'done', 'triggered': NOW,
        }
        key = max(self.feedback, default=0) + 1
        self.feedback[key] = {
            'identifier': key, 'created': NOW, 'output': 'test.docx',
            'stage': 'done', 'exception': '', 'assignment': identifier,
            'cache_hit': 0, 'duration': 0,
        }

    @rule(identifier=IDENTIFIERS)
    def remove_assignment(self, identifier):
        """сравнивает удаление задачи и каскада результатов."""
        response = self.client.discard_assignment({'identifier': identifier})
        assert self.data(response) == {
            'deleted': int(identifier in self.assignments),
        }
        self.assignments.pop(identifier, None)
        self.feedback = {key: row for key, row in self.feedback.items()
                         if row['assignment'] != identifier}

    @rule(identifier=IDENTIFIERS)
    def remove_entity(self, identifier):
        """сравнивает удаление Entity и её дочерних данных."""
        response = self.client.discard_entity({'identifier': identifier})
        assert self.data(response) == {
            'deleted': int(identifier in self.entities),
        }
        self.entities.pop(identifier, None)
        self.assignments = {key: row for key, row in self.assignments.items()
                            if row['entity'] != identifier}
        self.feedback = {key: row for key, row in self.feedback.items()
                         if row['assignment'] in self.assignments}

    def read_records(self, identifier):
        """проверяет чтение существующих и отсутствующих первичных ключей."""
        assert self.data(self.client.fetch_entity(identifier)) == (
            self.entities.get(identifier)
        )
        assert self.data(self.client.fetch_assignment(identifier)) == (
            self.assignments.get(identifier)
        )
        assert self.data(self.client.fetch_feedback(identifier)) == (
            self.feedback.get(identifier)
        )

    @rule(identifier=IDENTIFIERS, text=TEXT)
    def filters(self, identifier, text):
        """проверяет дополнительные фильтры поиска и чтение по ключам."""
        self.read_records(identifier)
        rows = self.data(self.client.list_entity({'platform': text}))
        expected = [row for row in self.entities.values()
                    if row['platform'] == text]
        assert rows == sorted(expected, key=lambda row: row['identifier'])
        rows = self.data(self.client.list_assignment(
            identifier, {'tags': text},
        ))
        expected = [row for row in self.assignments.values()
                    if row['entity'] == identifier and row['tags'] == text]
        assert rows == sorted(expected, key=lambda row: row['identifier'])
        assert self.data(self.client.list_feedback(
            identifier, {'stage': 'failed'},
        )) == []

    @rule(header=st.sampled_from(['', 'Basic !!!', 'Bearer abc',
                                 'Basic c3R1ZGVudDp3cm9uZw==']))
    def unauthorized(self, header):
        """проверяет 401 и WWW-Authenticate на каждом маршруте таблицы 24."""
        for method, path in ROUTES:
            response = self.client.request(
                method, path, headers={'Authorization': header},
            )
            assert response.status_code == UNAUTHORIZED
            assert 'Basic realm=' in response.headers['www-authenticate']
            assert 'error' in loads(response.content)

    @rule(identifier=IDENTIFIERS)
    def invalid_fields(self, identifier):
        """проверяет неизвестные поля и отсутствующую родительскую запись."""
        response = self.client.make_entity(identifier, {'unknown': 'x'})
        assert response.status_code == BAD_REQUEST
        response = self.client.make_assignment(
            999, {'entity': 999, 'parameter': 'x.md'},
        )
        assert response.status_code == BAD_REQUEST
        response = self.client.fetch_entity('invalid')
        assert response.status_code == BAD_REQUEST

    @rule()
    def protocol_errors(self):
        """проверяет ошибки XML, неизвестный маршрут и неверный метод."""
        response = self.client.request('GET', 'missing')
        assert response.status_code == NOT_FOUND
        assert 'error' in loads(response.content)
        response = self.client.request('POST', 'list-entity', {'x': {'y': 1}})
        assert response.status_code == BAD_REQUEST

    @invariant()
    def observe(self):
        """сверяет все записи и отчёт после каждого действия модели."""
        entities = self.data(self.client.list_entity({}))
        expected = [self.entities[key] for key in sorted(self.entities)]
        assert entities == expected
        for identifier in range(1, 5):
            rows = self.data(self.client.list_assignment(identifier, {}))
            expected = [row for row in self.assignments.values()
                        if row['entity'] == identifier]
            assert rows == sorted(expected, key=lambda row: row['identifier'])
            rows = self.data(self.client.list_feedback(identifier, {}))
            expected = [row for row in self.feedback.values()
                        if row['assignment'] == identifier]
            assert rows == sorted(expected, key=lambda row: row['identifier'])
        self.check_report()

    def check_report(self):
        """сравнивает независимую проекцию тестовых ответов с отчётом."""
        expected = {(row['parameter'], 0, 'test.docx')
                    for row in self.assignments.values()}
        assert self.data(self.client.list_report()) == [
            {'parameter': parameter, 'cache_hit': hit, 'output': output}
            for parameter, hit, output in sorted(expected, key=repr)
        ]

    def teardown(self):
        """освобождает транспорт, исполнитель, базу и временный каталог."""
        self.client.close()
        self.app.executor.shutdown(wait=True)
        self.app.model.storage.close()
        self.clock.stop()
        self.directory.cleanup()


TestJsonApi = ApiMachine.TestCase
TestJsonApi.settings = settings(max_examples=15, stateful_step_count=20,
                                deadline=None)
