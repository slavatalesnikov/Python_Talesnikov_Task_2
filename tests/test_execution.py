"""сгенерированные проверки subprocess и настоящего Docx."""

from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from unittest.mock import patch

from docx import Document
from hypothesis import given, settings, strategies as st

from src.api import create_app
from src.client import ApiClient
from src.routes import execute_assignment
from src.xml_format import loads


OK = 200


def submit_document(app, path):
    """передаёт путь Markdown через XML API и ждёт фонового исполнителя."""
    client = ApiClient(transport=app.test_client())
    assert client.make_entity(1, {}).status_code == OK
    response = client.make_assignment(1, {'entity': 1, 'parameter': str(path)})
    assert response.status_code == OK
    app.executor.shutdown(wait=True)
    result = loads(client.list_feedback(1, {}).content)[0]
    client.close()
    return result


@given(text=st.text(alphabet='абв abc012', min_size=1, max_size=30)
       .filter(lambda text: bool(text.strip())))
@settings(max_examples=5, deadline=None)
def test_real_conversion(text):
    """читает созданный из бинарного stdout документ через python-docx."""
    with TemporaryDirectory() as directory:
        source = Path(directory) / 'input.md'
        source.write_text('# Заголовок\n\n' + text, encoding='utf-8')
        app = create_app(f'{directory}/db.json', False, f'{directory}/output')
        result = submit_document(app, source)
        assert result['stage'] == 'done'
        assert result['exception'] == ''
        assert result['cache_hit'] == 0
        assert result['duration'] >= 0
        paragraphs = Document(result['output']).paragraphs
        assert paragraphs[0].text == 'Заголовок'
        assert paragraphs[0].style.name == 'Heading 1'
        assert paragraphs[1].text == ' '.join(text.split())
        app.model.storage.close()


@given(identifier=st.integers(min_value=1, max_value=1000))
@settings(max_examples=5, deadline=None)
def test_deleted_assignment(identifier):
    """не запускает преобразование задачи, удалённой до её выполнения."""
    with TemporaryDirectory() as directory:
        app = create_app(f'{directory}/db.sqlite3', False,
                         f'{directory}/output')
        app.model.make_entity(1, {})
        fields = {'entity': 1, 'parameter': 'a.md'}
        record = app.model.make_assignment(identifier, fields)
        app.model.discard_assignment({'identifier': identifier})
        execute_assignment(app, record)
        assert app.model.list_feedback(identifier, {}) == []
        assert not Path(f'{directory}/output').exists()
        app.executor.shutdown(wait=True)
        app.model.storage.close()


@given(mode=st.sampled_from(['missing', 'timeout', 'oserror']))
@settings(max_examples=3, deadline=None)
def test_conversion_failure(mode):
    """проверяет отсутствующий файл, таймаут и ошибку запуска процесса."""
    with TemporaryDirectory() as directory:
        app = create_app(f'{directory}/db.json', False, f'{directory}/output')
        errors = {'timeout': subprocess.TimeoutExpired('converter', 60),
                  'oserror': OSError('процесс не запущен')}
        if mode == 'missing':
            result = submit_document(app, f'{directory}/missing.md')
        else:
            with patch('src.routes.subprocess.run', side_effect=errors[mode]):
                result = submit_document(app, 'example.md')
        assert result['stage'] == 'failed'
        assert result['output'] == ''
        assert result['exception']
        assert not list(Path(directory).rglob('*.docx'))
        app.model.storage.close()
