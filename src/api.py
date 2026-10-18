"""приложение Flask с XML и Basic Auth по RFC 7617 для варианта 24."""

from hmac import compare_digest

from flask import Flask, current_app, request
from werkzeug.exceptions import HTTPException

from src.config import DEFAULT_CONFIG, load_auth
from src.model import Model
from src.routes import answer as xml_response, router
from src.storage import JsonStorage
from src.worker import Worker


UNAUTHORIZED = 401
BAD_REQUEST = 400


def authorize():
    """проверяет Basic Auth до чтения тела и вызова любого обработчика."""
    auth = request.authorization
    username, password = current_app.config['API_AUTH']
    valid = auth is not None and auth.type == 'basic'
    if valid:
        valid = (compare_digest((auth.username or '').encode(),
                                username.encode())
                 and compare_digest((auth.password or '').encode(),
                                    password.encode()))
    if not valid:
        response = xml_response({'error': 'нужна авторизация'}, UNAUTHORIZED)
        response.headers['WWW-Authenticate'] = (
            'Basic realm="task2", charset="UTF-8"'
        )
        return response
    return None


def bad_request(error):
    """возвращает ошибки полей, ключей и XML в теле ответа."""
    return xml_response({'error': str(error)}, BAD_REQUEST)


def http_error(error):
    """сохраняет XML также для неизвестного маршрута или метода."""
    return xml_response({'error': error.description}, error.code)


def create_app(path='data/variant24.json', test_mode=False,
               output_dir='output', config_path=DEFAULT_CONFIG):
    """собирает приложение с файловым хранилищем второго этапа."""
    app = Flask(__name__)
    app.config['API_AUTH'] = load_auth(config_path)
    app.model = Model(JsonStorage(path))
    app.worker = Worker(app.model, output_dir, test_mode)
    app.before_request(authorize)
    app.register_error_handler(ValueError, bad_request)
    app.register_error_handler(KeyError, bad_request)
    app.register_error_handler(HTTPException, http_error)
    app.register_blueprint(router)
    return app
