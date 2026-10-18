"""повторяет сгенерированные MBT-сценарии с SQLite через SQLAlchemy."""

from hypothesis import settings

from tests.test_api import ApiMachine


class SqlApiMachine(ApiMachine):
    """меняет хранилище, сохраняя клиент и независимую эталонную модель."""

    backend = 'sqlite'


TestSqlApi = SqlApiMachine.TestCase
TestSqlApi.settings = settings(max_examples=15, stateful_step_count=20,
                               deadline=None)
