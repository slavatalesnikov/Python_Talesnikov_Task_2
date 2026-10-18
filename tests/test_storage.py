"""сгенерированные проверки сохранения базы на диске."""

from tempfile import TemporaryDirectory

from hypothesis import given, settings, strategies as st

from src.model import Model
from src.storage import JsonStorage
from src.sql_storage import SqlStorage


@given(text=st.text(max_size=40), backend=st.sampled_from(['json', 'sqlite']))
@settings(max_examples=10, deadline=None)
def test_reopen_storage(text, backend):
    """после закрытия и открытия базы видны те же записи."""
    with TemporaryDirectory() as directory:
        path = f'{directory}/db'
        storage_class = {'json': JsonStorage, 'sqlite': SqlStorage}[backend]
        storage = storage_class(path)
        model = Model(storage)
        expected = model.make_entity(1, {'platform': text})
        storage.close()
        storage = storage_class(path)
        assert Model(storage).fetch_entity(1) == expected
        storage.close()
