"""доступ к реляционной базе SQLite через ORM SQLAlchemy."""

from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, aliased

from src.orm import Assignment, Base, Feedback, TABLES
from src.schema import REPORT_SECONDS


class SqlStorage:
    """заменяет файловое хранилище второго этапа ORM-реализацией.

    сеанс создаётся отдельно на операцию, поэтому основной поток сервера
    и фоновый исполнитель не используют один Session одновременно.
    """

    def __init__(self, path):
        """создаёт SQLite-файл и таблицы по декларативным ORM-классам."""
        path = Path(path).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(f'sqlite:///{path}')
        Base.metadata.create_all(self.engine)

    def load(self):
        """читает все три таблицы ORM-запросами без ручных строк SQL."""
        with Session(self.engine) as session:
            return {name: [row.as_dict() for row in session.scalars(
                select(record).order_by(record.identifier),
            )] for name, record in TABLES.items()}

    def save(self, tables):
        """сохраняет маленький учебный набор в одной транзакции.

        дочерние записи удаляются раньше родительских; новые родители
        сохраняются раньше детей. при ошибке транзакция откатывается.
        """
        with Session(self.engine) as session, session.begin():
            for record in reversed(list(TABLES.values())):
                session.query(record).delete(synchronize_session=False)
            for name, record in TABLES.items():
                session.add_all(record(**row) for row in tables[name])
                session.flush()

    def report(self, now):
        """вычисляет формулу 24 в SQLite с помощью ORM select и outerjoin.

        подзапрос сначала отбирает только свежие Feedback. LEFT JOIN
        сохраняет Assignment даже при отсутствии строк в подзапросе.
        """
        recent = aliased(Feedback, select(Feedback).where(
            Feedback.created > now - REPORT_SECONDS,
        ).subquery())
        query = select(Assignment.parameter, recent.cache_hit, recent.output)
        query = query.outerjoin(
            recent, Assignment.identifier == recent.assignment,
        ).distinct()
        with Session(self.engine) as session:
            rows = session.execute(query).all()
            return [dict(row._mapping)
                    for row in sorted(rows, key=lambda row: repr(tuple(row)))]

    def close(self):
        """освобождает пул подключений к SQLite."""
        self.engine.dispose()
