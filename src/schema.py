"""поля ER-диаграммы варианта 24 и проверка их типов."""

from time import time


REPORT_SECONDS = 5 * 60
FIELDS = {
    'entity': {'identifier': int, 'created': int, 'ip': str,
               'locale': str, 'platform': str},
    'assignment': {'identifier': int, 'created': int, 'parameter': str,
                   'entity': int, 'tags': str, 'stage': str, 'triggered': int},
    'feedback': {'identifier': int, 'created': int, 'output': str,
                 'stage': str, 'exception': str, 'assignment': int,
                 'cache_hit': int, 'duration': int},
}
DEFAULTS = {
    'entity': {'ip': '', 'locale': '', 'platform': ''},
    'assignment': {'tags': '', 'stage': 'queued', 'triggered': 0},
    'feedback': {'output': '', 'exception': '', 'cache_hit': 0, 'duration': 0},
}


def timestamp():
    """возвращает целое число секунд Unix для полей времени."""
    return int(time())


def normalize(table, fields, complete=False):
    """проверяет имена и преобразует строки XML в типы полей таблицы."""
    if fields.keys() - FIELDS[table].keys():
        raise ValueError('неизвестное поле')
    if complete and fields.keys() != FIELDS[table].keys():
        raise ValueError('не хватает обязательных полей')
    try:
        return {key: FIELDS[table][key](value)
                for key, value in fields.items()}
    except (TypeError, ValueError) as error:
        raise ValueError('неверный тип поля') from error
