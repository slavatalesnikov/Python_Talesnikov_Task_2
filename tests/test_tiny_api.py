"""те же сгенерированные MBT-сценарии для слоя доступа на основе TinyDB."""

from hypothesis import settings

from tests.test_api import ApiMachine


class TinyApiMachine(ApiMachine):
    """меняет только хранилище, оставляя независимую модель и HTTP-клиент."""

    backend = 'tinydb'


TestTinyApi = TinyApiMachine.TestCase
TestTinyApi.settings = settings(max_examples=15, stateful_step_count=20,
                                deadline=None)
