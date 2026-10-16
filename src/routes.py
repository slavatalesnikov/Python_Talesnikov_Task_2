"""десять обработчиков из таблицы 22 без изменения имён маршрутов."""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Query, Request

from src.schema import ActorData, InstructionData


router = APIRouter(prefix='/private/api/v2')


@router.put('/submit/actor/{uid}')
def put_actor_submit(uid: int, data: Annotated[ActorData, Query()],
                     request: Request):
    """создаёт Actor из ключа в пути и полей в строке запроса."""
    return request.app.state.model.submit('actor', data.model_dump() | {
        'uid': uid,
    })


@router.delete('/pop/actor/{uid}')
def delete_actor_pop(uid: int, request: Request):
    """удаляет участника и связанные данные."""
    return request.app.state.model.pop('actor', uid)


@router.get('/show/actor')
def get_actor_show(request: Request):
    """ищет Actor по полям строки запроса; пустой фильтр выбирает всех."""
    return request.app.state.model.find('actor', dict(request.query_params))


@router.post('/revise/actor')
def post_actor_revise(data: dict, request: Request):
    """изменяет Actor: uid и новые значения поступают в JSON."""
    return request.app.state.model.revise('actor', data)


@router.put('/submit/instruction/{uid}')
def put_instruction_submit(uid: int, request: Request,
                           tasks: BackgroundTasks,
                           data: Annotated[InstructionData, Query()]):
    """сохраняет задачу и передаёт её фоновому исполнителю."""
    record = request.app.state.model.submit(
        'instruction', data.model_dump() | {'uid': uid},
    )
    tasks.add_task(request.app.state.worker.execute, record)
    return record


@router.delete('/pop/instruction/{uid}')
def delete_instruction_pop(uid: int, request: Request):
    """удаляет задачу вместе с её результатами."""
    return request.app.state.model.pop('instruction', uid)


@router.get('/show/instruction/{actor}')
def get_instruction_show(actor: int, request: Request):
    """отбирает задачи участника и применяет дополнительные фильтры."""
    filters = dict(request.query_params) | {'actor': actor}
    return request.app.state.model.find('instruction', filters)


@router.post('/revise/instruction')
def post_instruction_revise(data: dict, request: Request):
    """обновляет поля задачи по uid из JSON-тела."""
    return request.app.state.model.revise('instruction', data)


@router.get('/show/response/{instruction}')
def get_response_show(instruction: int, request: Request):
    """возвращает результаты задачи с учётом фильтров строки запроса."""
    filters = dict(request.query_params) | {'instruction': instruction}
    return request.app.state.model.find('response', filters)


@router.get('/show/report')
def get_report_show(request: Request):
    """возвращает пары description и output по формуле 22."""
    return request.app.state.model.report()
