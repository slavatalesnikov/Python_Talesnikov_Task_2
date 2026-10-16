"""короткая демонстрация всех десяти маршрутов для защиты."""

from time import monotonic, sleep

from src.client import ApiClient


WAIT_SECONDS = 10
POLL_SECONDS = 0.1
DEMO_ACTOR = 22001
DEMO_INSTRUCTION = 22002


def show(response):
    """показывает ответ и останавливает демонстрацию при ошибке HTTP."""
    print(response.request.method, response.request.url.path,
          response.status_code, response.json())
    response.raise_for_status()
    return response.json()


def wait_result(client):
    """опрашивает результат, пока фоновый процесс создаёт документ."""
    deadline = monotonic() + WAIT_SECONDS
    while monotonic() < deadline:
        rows = show(client.get_response_show(DEMO_INSTRUCTION))
        if rows:
            return rows
        sleep(POLL_SECONDS)
    raise TimeoutError('результат не появился за 10 секунд')


def main():
    """создаёт данные, получает docx и отчёт, затем удаляет записи."""
    client = ApiClient()
    try:
        show(client.put_actor_submit(DEMO_ACTOR, platform='macOS',
                                     user_agent='defence'))
        show(client.get_actor_show(uid=DEMO_ACTOR))
        show(client.post_actor_revise(DEMO_ACTOR, platform='Python'))
        show(client.put_instruction_submit(
            DEMO_INSTRUCTION, actor=DEMO_ACTOR,
            input='# Защита\n\n**Markdown** преобразуется в Docx.',
            description='пример для защиты', tags='demo',
        ))
        wait_result(client)
        show(client.get_instruction_show(DEMO_ACTOR))
        show(client.post_instruction_revise(DEMO_INSTRUCTION, tags='checked'))
        show(client.get_report_show())
        show(client.delete_instruction_pop(DEMO_INSTRUCTION))
        show(client.delete_actor_pop(DEMO_ACTOR))
    finally:
        client.close()


if __name__ == '__main__':
    main()
