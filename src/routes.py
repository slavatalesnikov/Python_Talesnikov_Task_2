"""одиннадцать маршрутов таблицы 24; данные тела передаются в XML."""

from flask import Blueprint, Response, current_app, request

from src.xml_format import dumps, fields


router = Blueprint('api', __name__, url_prefix='/api')


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
    record = current_app.model.make_assignment(identifier, body())
    current_app.worker.submit(record)
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
