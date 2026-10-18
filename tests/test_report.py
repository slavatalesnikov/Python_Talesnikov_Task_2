"""проверки LEFT JOIN и строгой границы пяти минут для Feedback."""

from tempfile import TemporaryDirectory
from unittest.mock import patch

from hypothesis import given, settings, strategies as st

from src.api import create_app
from src.client import ApiClient
from src.xml_format import loads


NOW = 2_000_000_000
WINDOW_SECONDS = 5 * 60
OK = 200


def seed_report(model, age, parameter):
    """создаёт старую задачу со свежим ответом, пустую и со старым ответом."""
    model.make_entity(1, {})
    for identifier, value in [(1, parameter), (2, 'empty'), (3, 'old')]:
        model.make_assignment(identifier, {
            'created': NOW - 1000, 'parameter': value, 'entity': 1,
        })
    tables = model.storage.load()
    for identifier, assignment, created in [
        (1, 1, NOW - age), (2, 1, NOW - age), (3, 3, NOW - WINDOW_SECONDS),
    ]:
        tables['feedback'].append({
            'identifier': identifier, 'assignment': assignment,
            'created': created, 'cache_hit': 0, 'output': 'a.docx',
            'stage': 'done', 'exception': '', 'duration': 0,
        })
    model.storage.save(tables)


@given(age=st.sampled_from([-10, 299, 300, 301]),
       parameter=st.text(alphabet='абв ab<&>', max_size=20))
@settings(max_examples=16, deadline=None)
def test_report_formula(age, parameter):
    """проверяет фильтрацию правого отношения до левого соединения."""
    with TemporaryDirectory() as directory:
        app = create_app(f'{directory}/db.json', True)
        seed_report(app.model, age, parameter)
        client = ApiClient(transport=app.test_client())
        with patch('src.model.timestamp', return_value=NOW):
            response = client.list_report()
        expected = {(parameter, None, None), ('empty', None, None),
                    ('old', None, None)}
        if age < WINDOW_SECONDS:
            expected.remove((parameter, None, None))
            expected.add((parameter, 0, 'a.docx'))
        assert response.status_code == OK
        assert loads(response.content) == [
            {'parameter': value, 'cache_hit': hit, 'output': output}
            for value, hit, output in sorted(expected, key=repr)
        ]
        client.close()
        app.worker.close()
        app.model.storage.close()
