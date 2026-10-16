"""проверки реального преобразования и сохранения ошибок исполнителя."""

import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from docx import Document
from fastapi.testclient import TestClient
from hypothesis import given, settings, strategies as st

from src.api import create_app
from src.client import ApiClient


OK = 200


def submit_document(app, text):
    """создаёт участника и задачу через тот же HTTP-клиент."""
    with TestClient(app) as transport:
        client = ApiClient(transport=transport)
        assert client.put_actor_submit(1).status_code == OK
        response = client.put_instruction_submit(1, actor=1, input=text)
        assert response.status_code == OK
        return client.get_response_show(1).json()[0]


@given(text=st.text(alphabet='абв abc012', min_size=1, max_size=30))
@settings(max_examples=5, deadline=None)
def test_real_conversion(text):
    """действительно запускает CLI и открывает полученный docx."""
    with TemporaryDirectory() as directory:
        app = create_app(f'{directory}/db.json', False, f'{directory}/output')
        result = submit_document(app, '# Заголовок\n\n' + text)
        assert result['stage'] == 'done'
        assert result['failure'] == ''
        output = Path(result['output'])
        assert output.is_file()
        paragraphs = Document(output).paragraphs
        assert paragraphs[0].text == 'Заголовок'
        assert paragraphs[0].style.name == 'Heading 1'
        assert paragraphs[1].text == text.strip()


@given(mode=st.sampled_from(['exit', 'timeout', 'oserror']))
@settings(max_examples=3, deadline=None)
def test_conversion_failure(mode):
    """проверяет ненулевой код процесса, таймаут и ошибку запуска."""
    with TemporaryDirectory() as directory:
        app = create_app(f'{directory}/db.json')
        error = {'exit': None,
                 'timeout': subprocess.TimeoutExpired('converter', 60),
                 'oserror': OSError('процесс не запущен')}[mode]
        result = subprocess.CompletedProcess([], 1, '', 'ошибка CLI')
        with patch('src.worker.subprocess.run', return_value=result,
                   side_effect=error):
            response = submit_document(app, '# Пример')
        assert response['stage'] == 'failed'
        assert response['output'] == ''
        assert response['failure']
