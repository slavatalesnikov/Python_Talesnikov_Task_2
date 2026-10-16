"""документное хранилище третьего этапа через библиотеку tinydb."""

from pathlib import Path

from tinydb import TinyDB


TABLE_NAMES = ('actor', 'instruction', 'response')


class TinyStorage:
    """сохраняет записи в именованных таблицах TinyDB.

    интерфейс load/save совпадает с файловым хранилищем второго этапа,
    поэтому HTTP-обработчики и правила работы с данными не меняются.
    """

    def __init__(self, path):
        """открывает документную базу по указанному пути."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.database = TinyDB(path, ensure_ascii=False, indent=2)

    def load(self):
        """читает документы трёх таблиц, не раскрывая служебные doc_id."""
        return {name: [dict(row) for row in self.database.table(name).all()]
                for name in TABLE_NAMES}

    def save(self, tables):
        """заменяет содержимое таблиц документами обновлённой модели.

        модель держит общую блокировку на время чтения и сохранения.
        для маленького учебного набора достаточно перезаписи таблиц.
        """
        for name in TABLE_NAMES:
            table = self.database.table(name)
            table.truncate()
            table.insert_multiple(tables[name])

    def close(self):
        """закрывает файл базы при остановке приложения."""
        self.database.close()
