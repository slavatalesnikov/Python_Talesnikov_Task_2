"""чтение учебных реквизитов Basic Auth из конфигурационного файла."""

from configparser import ConfigParser


DEFAULT_CONFIG = 'config.ini'


def load_auth(path=DEFAULT_CONFIG):
    """читает имя и пароль; это пример локальной учебной конфигурации."""
    parser = ConfigParser(interpolation=None)
    if not parser.read(path, encoding='utf-8'):
        raise ValueError('конфигурационный файл не найден')
    return parser['auth']['username'], parser['auth']['password']
