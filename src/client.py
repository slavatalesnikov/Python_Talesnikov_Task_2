"""клиент XML API; имена методов совпадают с публичными методами модели."""

from base64 import b64encode

import requests

from src.config import DEFAULT_CONFIG, load_auth
from src.xml_format import dumps


class ApiClient:
    """использует настоящий HTTP либо тестовый транспорт Flask."""

    def __init__(self, base_url='http://127.0.0.1:8000', transport=None,
                 config_path=DEFAULT_CONFIG):
        """читает Basic Auth из того же конфигурационного файла."""
        self.username, self.password = load_auth(config_path)
        self.transport = transport
        self.base_url = base_url.rstrip('/')
        self.http = requests.Session()

    def request(self, method, path, fields=None, query=None, headers=None,
                raw=None):
        """отправляет XML с Basic Auth, возвращая обычный HTTP-ответ."""
        credentials = (self.username + ':' + self.password).encode('utf-8')
        token = b64encode(credentials).decode('ascii')
        values = {'Authorization': f'Basic {token}',
                  'Content-Type': 'application/xml'}
        values.update(headers or {})
        data = b'' if fields is None else dumps(fields, 'request')
        if raw is not None:
            data = raw
        path = '/api/' + path
        if self.transport is not None:
            result = self.transport.open(path, method=method, data=data,
                                         query_string=query, headers=values)
            response = requests.Response()
            response.status_code = result.status_code
            response._content = result.data
            response.headers.update(result.headers)
            response.encoding = 'utf-8'
            return response
        return self.http.request(method, self.base_url + path, data=data,
                                 params=query, headers=values, timeout=30)

    def make_entity(self, identifier, fields):
        """создаёт Entity по ключу в пути и XML-телу."""
        return self.request('PUT', f'make-entity/{identifier}', fields)

    def discard_entity(self, fields):
        """удаляет Entity по identifier из тела."""
        return self.request('POST', 'discard-entity', fields)

    def list_entity(self, fields):
        """ищет Entity по XML-фильтру."""
        return self.request('POST', 'list-entity', fields)

    def fetch_entity(self, identifier):
        """читает Entity по ключу в строке запроса."""
        return self.request('GET', 'fetch-entity',
                            query={'identifier': identifier})

    def make_assignment(self, identifier, fields):
        """создаёт задачу преобразования Markdown-файла."""
        return self.request('PUT', f'make-assignment/{identifier}', fields)

    def discard_assignment(self, fields):
        """удаляет Assignment по XML-телу."""
        return self.request('POST', 'discard-assignment', fields)

    def list_assignment(self, entity, fields):
        """ищет Assignment для участника, указанного в пути."""
        return self.request('POST', f'list-assignment/{entity}', fields)

    def fetch_assignment(self, identifier):
        """читает Assignment по первичному ключу."""
        return self.request('GET', 'fetch-assignment',
                            query={'identifier': identifier})

    def list_feedback(self, assignment, fields):
        """ищет Feedback задачи по XML-фильтру."""
        return self.request('POST', f'list-feedback/{assignment}', fields)

    def fetch_feedback(self, identifier):
        """читает Feedback по первичному ключу."""
        return self.request('GET', 'fetch-feedback',
                            query={'identifier': identifier})

    def list_report(self):
        """запрашивает отчёт без тела запроса."""
        return self.request('POST', 'list-report')

    def close(self):
        """закрывает сетевые соединения клиента."""
        self.http.close()
