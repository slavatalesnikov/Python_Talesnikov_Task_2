"""сгенерированные проверки конфигурации авторизации и ошибочного XML."""

from pathlib import Path
from tempfile import TemporaryDirectory

from hypothesis import given, settings, strategies as st

from src.api import create_app
from src.client import ApiClient
from src.xml_format import loads


OK = 200
BAD_REQUEST = 400
UNAUTHORIZED = 401
CREDENTIAL = st.text(alphabet='abc012абв', min_size=1, max_size=12)


@given(username=CREDENTIAL, password=CREDENTIAL)
@settings(max_examples=8, deadline=None)
def test_config_credentials(username, password):
    """проверяет чтение реквизитов из файла, включая символы UTF-8."""
    with TemporaryDirectory() as directory:
        config = Path(directory) / 'auth.ini'
        config.write_text(
            f'[auth]\nusername = {username}\npassword = {password}\n',
            encoding='utf-8',
        )
        app = create_app(f'{directory}/db.json', True, config_path=str(config))
        client = ApiClient(transport=app.test_client(),
                           config_path=str(config))
        response = client.fetch_entity(999)
        assert response.status_code == OK
        assert loads(response.content) is None
        client.password += 'wrong'
        assert client.fetch_entity(999).status_code == UNAUTHORIZED
        client.close()
        app.executor.shutdown(wait=True)
        app.model.storage.close()


@given(payload=st.sampled_from([
    b'<broken', b'<request><identifier type="int">x</identifier></request>',
    b'<request kind="list"><item>x</item></request>',
]))
@settings(max_examples=3, deadline=None)
def test_invalid_xml(payload):
    """сервер возвращает XML-ошибку, если входное тело нельзя разобрать."""
    with TemporaryDirectory() as directory:
        app = create_app(f'{directory}/db.json', True)
        client = ApiClient(transport=app.test_client())
        response = client.request('POST', 'list-entity', raw=payload)
        assert response.status_code == BAD_REQUEST
        assert 'error' in loads(response.content)
        client.close()
        app.executor.shutdown(wait=True)
        app.model.storage.close()
