"""тестирование MBT: независимая модель в словарях сравнивается с HTTP API."""

from tempfile import TemporaryDirectory
from unittest.mock import patch

from fastapi.testclient import TestClient
from hypothesis import settings, strategies as st
from hypothesis.stateful import (
    RuleBasedStateMachine, initialize, invariant, rule,
)

from src.api import create_app
from src.client import ApiClient


NOW = 2_000_000_000
OK = 200
BAD_REQUEST = 400
UNSUPPORTED_MEDIA = 415
NOT_ACCEPTABLE = 406
METHOD_NOT_ALLOWED = 405
WINDOW_SECONDS = 6 * 60
UIDS = st.integers(min_value=1, max_value=5)
TEXT = st.text(alphabet='абв abc012#*_\n', max_size=30)
OFFSETS = st.sampled_from([0, 359, 360, 361, 900, -60])


def header_status(method, content, accept):
    """определяет ожидаемый статус по таблице заголовков задания."""
    if method in ('PUT', 'POST', 'PATCH') and content != 'application/json':
        return UNSUPPORTED_MEDIA
    if accept != 'application/json':
        return NOT_ACCEPTABLE
    return OK if method == 'GET' else METHOD_NOT_ALLOWED


class ApiMachine(RuleBasedStateMachine):
    """генерирует последовательности создания, изменения, поиска и удаления.

    ожидаемые данные не вычисляются функциями приложения: словари
    описывают состояние, которое должно наблюдаться через HTTP-клиент.
    """

    backend = 'json'

    def __init__(self):
        """создаёт отдельную базу и фиксирует время для границы отчёта."""
        super().__init__()
        self.directory = TemporaryDirectory()
        self.clock = patch('src.model.timestamp', return_value=NOW)
        self.clock.start()
        self.app = self.make_app()
        self.client = ApiClient(transport=TestClient(self.app))
        self.actors = {}
        self.instructions = {}
        self.responses = {}

    def make_app(self):
        """создаёт приложение с JSON-хранилищем второго этапа."""
        return create_app(f'{self.directory.name}/database.json', True,
                          backend=self.backend)

    def data(self, response):
        """проверяет успешный статус и JSON каждого штатного запроса."""
        assert response.status_code == OK, response.text
        assert response.headers['content-type'] == 'application/json'
        return response.json()

    @initialize(text=TEXT)
    def start(self, text):
        """гарантирует посещение всех десяти маршрутов в каждом сценарии."""
        self.actor_upsert(1, text)
        self.actor_upsert(1, text + 'x')
        self.instruction_upsert(1, 1, text, 360)
        self.instruction_upsert(1, 1, text + 'y', 361)
        self.observe()
        self.remove_instruction(1)
        self.remove_actor(1)
        self.headers('PUT', None, None)
        self.headers('GET', None, None)
        self.headers('GET', None, 'application/json')

    @rule(uid=UIDS, text=TEXT)
    def actor_upsert(self, uid, text):
        """создаёт участника или обновляет существующую запись."""
        if uid in self.actors:
            result = self.data(self.client.post_actor_revise(
                uid, platform=text,
            ))
            self.actors[uid]['platform'] = text
        else:
            fields = {'datetime': NOW, 'platform': text, 'user_agent': 'mbt'}
            result = self.data(self.client.put_actor_submit(uid, **fields))
            self.actors[uid] = fields | {'uid': uid}
        assert result == self.actors[uid]

    @rule(uid=UIDS, actor=UIDS, text=TEXT, offset=OFFSETS)
    def instruction_upsert(self, uid, actor, text, offset):
        """сравнивает поля задач, а после создания ожидает тестовый ответ."""
        if actor not in self.actors:
            self.actor_upsert(actor, text)
        fields = {'datetime': NOW - offset, 'actor': actor, 'input': text,
                  'description': text, 'tags': 'mbt', 'stage': 'queued'}
        if uid in self.instructions:
            fields['stage'] = 'done'
            result = self.data(self.client.post_instruction_revise(
                uid, **fields,
            ))
        else:
            result = self.data(self.client.put_instruction_submit(
                uid, **fields,
            ))
            response_uid = max(self.responses, default=0) + 1
            self.responses[response_uid] = {
                'uid': response_uid, 'datetime': NOW, 'output': 'test.docx',
                'stage': 'done', 'failure': '', 'instruction': uid,
            }
        assert result == fields | {'uid': uid}
        self.instructions[uid] = fields | {'uid': uid, 'stage': 'done'}

    @rule(uid=UIDS)
    def remove_instruction(self, uid):
        """удаляет задачу, включая её результаты в эталонной модели."""
        result = self.data(self.client.delete_instruction_pop(uid))
        assert result == {'deleted': uid in self.instructions}
        self.instructions.pop(uid, None)
        self.responses = {key: row for key, row in self.responses.items()
                          if row['instruction'] != uid}

    @rule(uid=UIDS)
    def remove_actor(self, uid):
        """проверяет каскадное удаление участника и его задач."""
        result = self.data(self.client.delete_actor_pop(uid))
        assert result == {'deleted': uid in self.actors}
        self.actors.pop(uid, None)
        self.instructions = {key: row for key, row in self.instructions.items()
                             if row['actor'] != uid}
        self.responses = {key: row for key, row in self.responses.items()
                          if row['instruction'] in self.instructions}

    @rule(uid=UIDS, text=TEXT)
    def filters(self, uid, text):
        """проверяет совпадающие и несовпадающие фильтры поиска."""
        result = self.data(self.client.get_actor_show(uid=uid))
        assert result == [row for row in self.actors.values()
                          if row['uid'] == uid]
        result = self.data(self.client.get_instruction_show(
            uid, description=text,
        ))
        assert result == [row for row in self.instructions.values()
                          if row['actor'] == uid
                          and row['description'] == text]
        result = self.data(self.client.get_response_show(uid, stage='failed'))
        assert result == []

    @rule(method=st.sampled_from(['GET', 'PUT', 'POST', 'PATCH', 'DELETE']),
          content=st.sampled_from([None, 'text/plain', 'application/json']),
          accept=st.sampled_from([None, '*/*', 'application/json']))
    def headers(self, method, content, accept):
        """проверяет приоритет 415 над 406, включая отсутствие обоих полей."""
        original = dict(self.client.http.headers)
        self.client.http.headers.clear()
        headers = {}
        if content is not None:
            headers['Content-Type'] = content
        if accept is not None:
            headers['Accept'] = accept
        response = self.client.request(method, '/show/actor', headers=headers)
        self.client.http.headers.update(original)
        assert response.status_code == header_status(method, content, accept)

    @rule(uid=UIDS)
    def invalid_changes(self, uid):
        """отсутствующая запись и неизвестное поле дают JSON с ошибкой."""
        response = self.client.post_actor_revise(uid, unknown='x')
        assert response.status_code == BAD_REQUEST
        assert 'error' in response.json()
        response = self.client.put_instruction_submit(
            999, actor=999, input='нет участника',
        )
        assert response.status_code == BAD_REQUEST

    @invariant()
    def observe(self):
        """после каждого действия сверяет все таблицы и отчёт через API."""
        actors = self.data(self.client.get_actor_show())
        assert sorted(actors, key=lambda row: row['uid']) == [
            self.actors[key] for key in sorted(self.actors)
        ]
        for uid in range(1, 6):
            instructions = self.data(self.client.get_instruction_show(uid))
            assert instructions == [row for row in self.instructions.values()
                                    if row['actor'] == uid]
            responses = self.data(self.client.get_response_show(uid))
            assert responses == [row for row in self.responses.values()
                                 if row['instruction'] == uid]
        expected = set()
        for response in self.responses.values():
            instruction = self.instructions[response['instruction']]
            if instruction['datetime'] >= NOW - WINDOW_SECONDS:
                expected.add((instruction['description'], response['output']))
        report = self.data(self.client.get_report_show())
        assert report == [{'description': description, 'output': output}
                          for description, output in sorted(expected)]

    def teardown(self):
        """закрывает транспорт и удаляет временные данные сценария."""
        self.client.close()
        self.app.state.model.storage.close()
        self.clock.stop()
        self.directory.cleanup()


TestJsonApi = ApiMachine.TestCase
TestJsonApi.settings = settings(max_examples=15, stateful_step_count=20,
                                deadline=None)
