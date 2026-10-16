"""настройка FastAPI, хранения и обязательных заголовков варианта 22."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.model import Model
from src.routes import router
from src.storage import JsonStorage
from src.tiny_storage import TinyStorage
from src.worker import Worker


JSON_TYPE = 'application/json'
BODY_METHODS = {'POST', 'PUT', 'PATCH'}
UNSUPPORTED_MEDIA = 415
NOT_ACCEPTABLE = 406
BAD_REQUEST = 400


async def check_headers(request: Request, call_next):
    """проверяет заголовки в порядке таблицы: Content-Type, затем Accept.

    значения также проверяются. для Content-Type допускается charset,
    для Accept — список типов, содержащий application/json.
    """
    content_type = request.headers.get('content-type', '').split(';')[0]
    if request.method in BODY_METHODS and content_type.lower() != JSON_TYPE:
        return JSONResponse({'error': 'нужен Content-Type: application/json'},
                            status_code=UNSUPPORTED_MEDIA)
    accepts = request.headers.get('accept', '').lower().split(',')
    if JSON_TYPE not in [value.strip() for value in accepts]:
        return JSONResponse({'error': 'нужен Accept: application/json'},
                            status_code=NOT_ACCEPTABLE)
    return await call_next(request)


async def bad_request(request: Request, error: Exception):
    """возвращает ошибки модели в JSON вместо внутренней ошибки сервера."""
    return JSONResponse({'error': str(error)}, status_code=BAD_REQUEST)


def create_app(path='data/database.json', test_mode=False,
               output_dir='output', backend='tinydb'):
    """создаёт приложение; по умолчанию используется TinyDB третьего этапа."""
    @asynccontextmanager
    async def lifespan(app):
        """закрывает хранилище после остановки сервера."""
        yield
        app.state.model.storage.close()

    app = FastAPI(title='Markdown -> Docx, вариант 22', lifespan=lifespan)
    storage_class = {'json': JsonStorage, 'tinydb': TinyStorage}[backend]
    app.state.model = Model(storage_class(path))
    app.state.worker = Worker(app.state.model, output_dir, test_mode)
    app.middleware('http')(check_headers)
    app.add_exception_handler(ValueError, bad_request)
    app.add_exception_handler(KeyError, bad_request)
    app.include_router(router)
    return app
