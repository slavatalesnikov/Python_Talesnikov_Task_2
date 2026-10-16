"""сгенерированные проверки inner join, проекции и границы времени."""

from tempfile import TemporaryDirectory
from unittest.mock import patch

from fastapi.testclient import TestClient
from hypothesis import given, settings, strategies as st

from src.api import create_app
from src.client import ApiClient


NOW = 2_000_000_000
WINDOW_SECONDS = 6 * 60
OK = 200


def seed_report(model, age, description):
    """задаёт две инструкции: у второй намеренно нет результата.

    две одинаковые строки результата проверяют устранение дубликатов
    проекции. лишний результат без пары проверяет именно inner join.
    """
    model.storage.save({
        'actor': [],
        'instruction': [
            {'uid': 1, 'datetime': NOW - age, 'description': description},
            {'uid': 2, 'datetime': NOW, 'description': 'без результата'},
        ],
        'response': [
            {'uid': 1, 'instruction': 1, 'output': 'a.docx'},
            {'uid': 2, 'instruction': 1, 'output': 'a.docx'},
            {'uid': 3, 'instruction': 999, 'output': 'без инструкции'},
        ],
    })


@given(age=st.sampled_from([359, 360, 361]), description=st.text(max_size=30))
@settings(max_examples=12, deadline=None)
def test_report_formula(age, description):
    """запрашивает отчёт через API с заранее подготовленными таблицами."""
    with TemporaryDirectory() as directory:
        app = create_app(f'{directory}/db.json', True)
        seed_report(app.state.model, age, description)
        with patch('src.model.timestamp', return_value=NOW):
            with TestClient(app) as transport:
                client = ApiClient(transport=transport)
                response = client.get_report_show()
        expected = []
        if age <= WINDOW_SECONDS:
            expected = [{'description': description, 'output': 'a.docx'}]
        assert response.status_code == OK
        assert response.json() == expected
