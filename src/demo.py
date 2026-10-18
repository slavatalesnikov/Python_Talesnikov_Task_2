"""демонстрация всех одиннадцати маршрутов варианта 24."""

import argparse
from time import monotonic, sleep

from src.client import ApiClient
from src.xml_format import loads


WAIT_SECONDS = 10
POLL_SECONDS = 0.1
DEMO_ENTITY = 24001
DEMO_ASSIGNMENT = 24002


def show(response):
    """показывает настоящий XML-ответ и проверяет успешность запроса."""
    response.raise_for_status()
    print(response.status_code, response.text)
    return loads(response.content)


def wait_result(client):
    """опрашивает Feedback, пока асинхронное преобразование не завершено."""
    deadline = monotonic() + WAIT_SECONDS
    while monotonic() < deadline:
        rows = show(client.list_feedback(DEMO_ASSIGNMENT, {}))
        if rows:
            return rows[0]
        sleep(POLL_SECONDS)
    raise TimeoutError('результат не появился за 10 секунд')


def main():
    """создаёт данные, читает результат и отчёт, затем удаляет записи."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:8000')
    parser.add_argument('--config', default='config.ini')
    args = parser.parse_args()
    client = ApiClient(args.url, config_path=args.config)
    try:
        show(client.make_entity(DEMO_ENTITY, {
            'ip': '127.0.0.1', 'locale': 'ru', 'platform': 'mac',
        }))
        show(client.list_entity({'identifier': DEMO_ENTITY}))
        show(client.fetch_entity(DEMO_ENTITY))
        show(client.make_assignment(DEMO_ASSIGNMENT, {
            'entity': DEMO_ENTITY, 'parameter': 'examples/05-mixed.md',
        }))
        feedback = wait_result(client)
        show(client.list_assignment(DEMO_ENTITY, {}))
        show(client.fetch_assignment(DEMO_ASSIGNMENT))
        show(client.fetch_feedback(feedback['identifier']))
        show(client.list_report())
        show(client.discard_assignment({'identifier': DEMO_ASSIGNMENT}))
        show(client.discard_entity({'identifier': DEMO_ENTITY}))
    finally:
        client.close()


if __name__ == '__main__':
    main()
