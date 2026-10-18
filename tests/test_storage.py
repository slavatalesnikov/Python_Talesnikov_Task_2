"""сгенерированные проверки сохранения базы на диске."""

from tempfile import TemporaryDirectory

from hypothesis import given, settings, strategies as st

from src.model import Model
from src.storage import JsonStorage


@given(text=st.text(max_size=40))
@settings(max_examples=10, deadline=None)
def test_reopen_storage(text):
    """после закрытия и открытия базы видны те же записи."""
    with TemporaryDirectory() as directory:
        path = f'{directory}/db.json'
        storage = JsonStorage(path)
        model = Model(storage)
        expected = model.make_entity(1, {'platform': text})
        storage.close()
        storage = JsonStorage(path)
        assert Model(storage).fetch_entity(1) == expected
        storage.close()
