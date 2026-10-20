"""одиннадцать маршрутов таблицы 24; данные тела передаются в XML."""

from pathlib import Path
import subprocess
import sys
from time import monotonic
from uuid import uuid4

from flask import Blueprint, Response, current_app, request

from src.xml_format import dumps, fields


router = Blueprint('api', __name__, url_prefix='/api')
PROCESS_TIMEOUT = 60
MILLISECONDS = 1000


def body():
    """читает простой XML-словарь из тела запроса."""
    return fields(request.get_data())


def answer(value, status=200):
    """оформляет записи и ошибки в XML с явной кодировкой UTF-8."""
    return Response(dumps(value), status=status,
                    content_type='application/xml; charset=utf-8')


@router.put('/make-entity/<int:identifier>')
def make_entity(identifier):
    """создаёт Entity: ключ в пути, остальные поля в XML."""
    return answer(current_app.model.make_entity(identifier, body()))


@router.post('/discard-entity')
def discard_entity():
    """удаляет Entity по identifier из XML-тела."""
    return answer(current_app.model.discard_entity(body()))


@router.post('/list-entity')
def list_entity():
    """ищет Entity по XML-фильтру."""
    return answer(current_app.model.list_entity(body()))


@router.get('/fetch-entity')
def fetch_entity():
    """читает Entity по identifier из строки запроса."""
    return answer(current_app.model.fetch_entity(request.args['identifier']))


@router.put('/make-assignment/<int:identifier>')
def make_assignment(identifier):
    """создаёт задачу и ставит её в очередь фонового исполнителя."""
    app = current_app._get_current_object()
    record = app.model.make_assignment(identifier, body())
    if app.config['TEST_MODE']:
        execute_assignment(app, record)
    else:
        app.executor.submit(execute_assignment, app, record)
    return answer(record)


@router.post('/discard-assignment')
def discard_assignment():
    """удаляет Assignment по XML-телу и связанные Feedback."""
    return answer(current_app.model.discard_assignment(body()))


@router.post('/list-assignment/<int:entity>')
def list_assignment(entity):
    """ищет задачи Entity с дополнительным XML-фильтром."""
    return answer(current_app.model.list_assignment(entity, body()))


@router.get('/fetch-assignment')
def fetch_assignment():
    """читает Assignment по ключу из строки запроса."""
    return answer(current_app.model.fetch_assignment(
        request.args['identifier'],
    ))


@router.post('/list-feedback/<int:assignment>')
def list_feedback(assignment):
    """ищет результаты Assignment с дополнительным XML-фильтром."""
    return answer(current_app.model.list_feedback(assignment, body()))


@router.get('/fetch-feedback')
def fetch_feedback():
    """читает Feedback по ключу из строки запроса."""
    return answer(current_app.model.fetch_feedback(request.args['identifier']))


@router.post('/list-report')
def list_report():
    """строит отчёт по формуле 24; тело запроса не требуется."""
    return answer(current_app.model.list_report())


def convert_assignment(app, assignment):
    """запускает CLI первого этапа и сохраняет его stdout в Docx."""
    filename = f'{assignment["identifier"]}-{uuid4().hex}.docx'
    output = Path(app.config['OUTPUT_DIR']).resolve() / filename
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open('wb') as stream:
            subprocess.run(
                [sys.executable, '-m', 'src.converter',
                 assignment['parameter']], stdout=stream,
                stderr=subprocess.PIPE, check=True, timeout=PROCESS_TIMEOUT,
                cwd=Path(__file__).resolve().parents[1],
            )
        return {'output': str(output), 'exception': ''}
    except (OSError, subprocess.SubprocessError) as error:
        output.unlink(missing_ok=True)
        message = str(error)
        if isinstance(error, subprocess.CalledProcessError):
            message = error.stderr.decode('utf-8', errors='replace').strip()
        return {'output': '', 'exception': message}


def execute_assignment(app, assignment):
    """выполняет задачу в фоне или сохраняет условный тестовый результат."""
    identifier = assignment['identifier']
    if not app.model.start(identifier):
        return
    if app.config['TEST_MODE']:
        app.model.complete(identifier, {'output': 'test.docx',
                                        'exception': ''}, 0)
        return
    started = monotonic()
    result = convert_assignment(app, assignment)
    duration = int((monotonic() - started) * MILLISECONDS)
    app.model.complete(identifier, result, duration)
