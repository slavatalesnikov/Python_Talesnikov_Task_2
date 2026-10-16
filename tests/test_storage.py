"""сгенерированные проверки сохранения данных после повторного открытия."""

from tempfile import TemporaryDirectory

from hypothesis import given, settings, strategies as st

from src.storage import JsonStorage
from src.tiny_storage import TinyStorage


@given(text=st.text(max_size=40), backend=st.sampled_from(['json', 'tinydb']))
@settings(max_examples=10, deadline=None)
def test_reopen_storage(text, backend):
    """закрывает базу и проверяет те же документы после нового открытия."""
    storage_class = {'json': JsonStorage, 'tinydb': TinyStorage}[backend]
    with TemporaryDirectory() as directory:
        path = f'{directory}/db.json'
        storage = storage_class(path)
        tables = {'actor': [{'uid': 1, 'datetime': 1,
                             'platform': text, 'user_agent': 'test'}],
                  'instruction': [], 'response': []}
        storage.save(tables)
        storage.close()
        storage = storage_class(path)
        assert storage.load() == tables
        storage.close()
