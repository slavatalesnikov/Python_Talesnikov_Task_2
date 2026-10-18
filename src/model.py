"""слой данных; публичные имена методов совпадают с HTTP-клиентом."""

from threading import RLock

from src.report import build_report
from src.schema import DEFAULTS, normalize, timestamp


class Model:
    """защищает чтение и изменение базы общей блокировкой.

    JSON-хранилище можно заменить другим без изменения HTTP-обработчиков.
    дополнительные функции с подчёркиванием обслуживают операции таблиц.
    """

    def __init__(self, storage):
        """получает реализацию доступа к данным."""
        self.storage = storage
        self.lock = RLock()

    def _make(self, table, identifier, fields):
        """добавляет запись, проверяя первичный ключ и родительскую связь."""
        record = {'created': timestamp()} | DEFAULTS[table] | fields
        record = normalize(table, record | {'identifier': identifier}, True)
        with self.lock:
            tables = self.storage.load()
            if any(row['identifier'] == identifier for row in tables[table]):
                raise ValueError('identifier уже существует')
            if table == 'assignment':
                if not any(row['identifier'] == record['entity']
                           for row in tables['entity']):
                    raise ValueError('entity не найдена')
            tables[table].append(record)
            self.storage.save(tables)
        return record

    def _list(self, table, fields):
        """ищет записи по точному совпадению переданных полей."""
        filters = normalize(table, fields)
        with self.lock:
            rows = self.storage.load()[table]
            result = [row for row in rows if all(
                row[key] == value for key, value in filters.items()
            )]
        return sorted(result, key=lambda row: row['identifier'])

    def _fetch(self, table, identifier):
        """возвращает одну запись по ключу или null, если записи нет."""
        rows = self._list(table, {'identifier': identifier})
        return rows[0] if rows else None

    def _discard(self, table, fields):
        """удаляет запись по identifier и каскадно удаляет дочерние данные."""
        identifier = int(fields['identifier'])
        with self.lock:
            tables = self.storage.load()
            old = tables[table]
            tables[table] = [row for row in old
                             if row['identifier'] != identifier]
            deleted = int(len(old) != len(tables[table]))
            if table == 'entity':
                tables['assignment'] = [row for row in tables['assignment']
                                        if row['entity'] != identifier]
            keys = {row['identifier'] for row in tables['assignment']}
            tables['feedback'] = [row for row in tables['feedback']
                                  if row['assignment'] in keys]
            self.storage.save(tables)
        return {'deleted': deleted}

    def make_entity(self, identifier, fields):
        """создаёт Entity с полями created, ip, locale и platform."""
        return self._make('entity', identifier, fields)

    def discard_entity(self, fields):
        """удаляет Entity по ключу из XML-тела."""
        return self._discard('entity', fields)

    def list_entity(self, fields):
        """ищет Entity по XML-фильтру."""
        return self._list('entity', fields)

    def fetch_entity(self, identifier):
        """читает Entity по identifier из строки запроса."""
        return self._fetch('entity', identifier)

    def make_assignment(self, identifier, fields):
        """создаёт Assignment; parameter содержит путь к Markdown-файлу."""
        return self._make('assignment', identifier, fields)

    def discard_assignment(self, fields):
        """удаляет Assignment и связанные Feedback."""
        return self._discard('assignment', fields)

    def list_assignment(self, entity, fields):
        """ищет задачи участника, переданного в пути запроса."""
        return self._list('assignment', fields | {'entity': entity})

    def fetch_assignment(self, identifier):
        """читает Assignment по первичному ключу."""
        return self._fetch('assignment', identifier)

    def list_feedback(self, assignment, fields):
        """ищет результаты выбранной задачи по XML-фильтру."""
        return self._list('feedback', fields | {'assignment': assignment})

    def fetch_feedback(self, identifier):
        """читает один Feedback по первичному ключу."""
        return self._fetch('feedback', identifier)

    def list_report(self):
        """строит отчёт с LEFT JOIN по формуле 24."""
        with self.lock:
            return build_report(self.storage.load(), timestamp())

    def start(self, identifier):
        """ставит время запуска и running, если задача ещё существует."""
        with self.lock:
            tables = self.storage.load()
            for row in tables['assignment']:
                if row['identifier'] == identifier:
                    row.update(stage='running', triggered=timestamp())
                    self.storage.save(tables)
                    return True
        return False

    def complete(self, identifier, result, duration):
        """сохраняет Feedback и итоговую стадию ещё существующей задачи."""
        with self.lock:
            tables = self.storage.load()
            for row in tables['assignment']:
                if row['identifier'] == identifier:
                    stage = 'failed' if result['exception'] else 'done'
                    row['stage'] = stage
                    key = max((item['identifier']
                               for item in tables['feedback']), default=0) + 1
                    feedback = result | {
                        'identifier': key, 'created': timestamp(),
                        'assignment': identifier, 'stage': stage,
                        'cache_hit': 0, 'duration': duration,
                    }
                    tables['feedback'].append(normalize(
                        'feedback', feedback, True,
                    ))
                    self.storage.save(tables)
                    return
