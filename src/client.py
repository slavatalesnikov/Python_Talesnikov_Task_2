"""клиент HTTP с именами методов вида метод_таблица_действие."""

import httpx


PREFIX = '/private/api/v2'


class ApiClient:
    """работает с настоящим HTTP-сервером или тестовым транспортом."""

    def __init__(self, base_url='http://127.0.0.1:8000', transport=None):
        """переданный TestClient позволяет запускать те же методы в MBT."""
        self.http = transport if transport is not None else httpx.Client(
            base_url=base_url, timeout=30,
        )
        self.http.headers.update({'Accept': 'application/json',
                                  'Content-Type': 'application/json'})

    def request(self, method, path, **kwargs):
        """возвращает HTTP-ответ, позволяя проверять и статус, и JSON."""
        return self.http.request(method, PREFIX + path, **kwargs)

    def put_actor_submit(self, uid, **fields):
        """создаёт Actor, передавая его поля в строке запроса."""
        return self.request('PUT', f'/submit/actor/{uid}', params=fields)

    def delete_actor_pop(self, uid):
        """удаляет Actor по ключу из пути."""
        return self.request('DELETE', f'/pop/actor/{uid}')

    def get_actor_show(self, **filters):
        """ищет участников по точному совпадению полей."""
        return self.request('GET', '/show/actor', params=filters)

    def post_actor_revise(self, uid, **changes):
        """отправляет uid и изменяемые поля в JSON."""
        return self.request('POST', '/revise/actor',
                            json=changes | {'uid': uid})

    def put_instruction_submit(self, uid, **fields):
        """передаёт Markdown и параметры новой задачи в строке запроса."""
        return self.request('PUT', f'/submit/instruction/{uid}', params=fields)

    def delete_instruction_pop(self, uid):
        """удаляет Instruction по ключу из пути."""
        return self.request('DELETE', f'/pop/instruction/{uid}')

    def get_instruction_show(self, actor, **filters):
        """ищет задачи выбранного участника."""
        return self.request('GET', f'/show/instruction/{actor}',
                            params=filters)

    def post_instruction_revise(self, uid, **changes):
        """изменяет Instruction через JSON-тело."""
        return self.request('POST', '/revise/instruction',
                            json=changes | {'uid': uid})

    def get_response_show(self, instruction, **filters):
        """ищет результаты выбранной задачи."""
        return self.request('GET', f'/show/response/{instruction}',
                            params=filters)

    def get_report_show(self):
        """получает отчёт за последние шесть минут."""
        return self.request('GET', '/show/report')

    def close(self):
        """освобождает соединения HTTP-клиента."""
        self.http.close()
