"""операции с записями и отчёт; модель не зависит от HTTP."""

from threading import RLock

from src.schema import REPORT_SECONDS, SCHEMAS, timestamp


class Model:
    """проверяет поля, ключи и связи перед сохранением данных.

    одна блокировка защищает чтение и изменение таблиц от одновременных
    HTTP-запросов и фонового обработчика. сервер запускается в один процесс.
    """

    def __init__(self, storage):
        """получает реализацию хранения через аргумент."""
        self.storage = storage
        self.lock = RLock()

    def find(self, table, filters):
        """возвращает записи с точным совпадением всех заданных полей."""
        with self.lock:
            rows = self.storage.load()[table]
            return [row for row in rows if all(
                str(row.get(key)) == str(value)
                for key, value in filters.items()
            )]

    def validate(self, table, record, tables):
        """проверяет типы полей и наличие родительской записи."""
        record = SCHEMAS[table].model_validate(record).model_dump()
        relations = {'instruction': ('actor', 'actor'),
                     'response': ('instruction', 'instruction')}
        if table in relations:
            parent, field = relations[table]
            if not any(row['uid'] == record[field] for row in tables[parent]):
                raise ValueError(f'нет связанной записи {parent}')
        return record

    def submit(self, table, record):
        """добавляет запись, запрещая повторение первичного ключа."""
        with self.lock:
            tables = self.storage.load()
            record = self.validate(table, record, tables)
            if any(row['uid'] == record['uid'] for row in tables[table]):
                raise ValueError('uid уже существует')
            tables[table].append(record)
            self.storage.save(tables)
            return record

    def revise(self, table, changes):
        """меняет только переданные поля записи с указанным uid."""
        with self.lock:
            tables = self.storage.load()
            for index, row in enumerate(tables[table]):
                if row['uid'] == changes['uid']:
                    record = self.validate(table, row | changes, tables)
                    tables[table][index] = record
                    self.storage.save(tables)
                    return record
            raise ValueError('запись не найдена')

    def pop(self, table, uid):
        """удаляет запись и её дочерние задачи и результаты.

        каскад не оставляет ссылок на удалённых участников или инструкции.
        повторное удаление допустимо и возвращает deleted: false.
        """
        with self.lock:
            tables = self.storage.load()
            rows = tables[table]
            remaining = [row for row in rows if row['uid'] != uid]
            deleted = len(remaining) != len(rows)
            tables[table] = remaining
            if table == 'actor':
                tables['instruction'] = [
                    row for row in tables['instruction'] if row['actor'] != uid
                ]
            instructions = {row['uid'] for row in tables['instruction']}
            tables['response'] = [row for row in tables['response']
                                  if row['instruction'] in instructions]
            self.storage.save(tables)
            return {'deleted': deleted}

    def complete(self, uid, output, failure):
        """сохраняет результат, если задачу ещё не удалили через API."""
        with self.lock:
            if not self.find('instruction', {'uid': uid}):
                return
            stage = 'failed' if failure else 'done'
            tables = self.storage.load()
            response_uid = max((row['uid'] for row in tables['response']),
                               default=0) + 1
            self.submit('response', {
                'uid': response_uid, 'datetime': timestamp(),
                'output': output, 'stage': stage, 'failure': failure,
                'instruction': uid,
            })
            self.revise('instruction', {'uid': uid, 'stage': stage})

    def report(self, now=None):
        """реализует формулу 22: фильтр времени, inner join, проекция.

        граница включается: datetime >= now - 360. пара без результата
        не попадает в отчёт. одинаковые пары убираются, как в отношении.
        """
        with self.lock:
            tables = self.storage.load()
            boundary = (timestamp() if now is None else now) - REPORT_SECONDS
            descriptions = {
                row['uid']: row['description']
                for row in tables['instruction'] if row['datetime'] >= boundary
            }
            pairs = {(descriptions[row['instruction']], row['output'])
                     for row in tables['response']
                     if row['instruction'] in descriptions}
            return [{'description': description, 'output': output}
                    for description, output in sorted(pairs)]
