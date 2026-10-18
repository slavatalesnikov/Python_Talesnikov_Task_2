"""файловая реализация слоя хранения для второго этапа."""

import json
from pathlib import Path

from src.report import build_report


class JsonStorage:
    """хранит три таблицы в одном JSON-файле; запись заменяет файл целиком.

    доступ сериализуется блокировкой модели. временный файл и replace
    не оставляют наполовину записанный JSON при обычном обновлении.
    """

    def __init__(self, path):
        """создаёт каталог и пустую базу, если файл ещё не существует."""
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            names = ('entity', 'assignment', 'feedback')
            self.save({name: [] for name in names})

    def load(self):
        """читает актуальные таблицы с диска."""
        return json.loads(self.path.read_text(encoding='utf-8'))

    def save(self, tables):
        """сохраняет данные в читаемом виде с русскими символами."""
        temporary = self.path.with_suffix('.tmp')
        temporary.write_text(
            json.dumps(tables, ensure_ascii=False, indent=2),
            encoding='utf-8',
        )
        temporary.replace(self.path)

    def report(self, now):
        """строит файловую версию отчёта по формуле 24."""
        return build_report(self.load(), now)

    def close(self):
        """у JSON-хранилища нет постоянно открытых файлов."""
