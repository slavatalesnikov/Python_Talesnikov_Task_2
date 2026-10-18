"""отображение ORM для SQLite для трёх таблиц рисунка 24."""

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """общая база отображения таблиц SQLAlchemy."""

    def as_dict(self):
        """возвращает поля записи без служебных атрибутов ORM."""
        return {column.name: getattr(self, column.name)
                for column in self.__table__.columns}


class Entity(Base):
    """отображает Entity с первичным ключом identifier."""

    __tablename__ = 'entity'
    identifier = Column(Integer, primary_key=True)
    created = Column(Integer, nullable=False)
    ip = Column(String, nullable=False)
    locale = Column(String, nullable=False)
    platform = Column(String, nullable=False)


class Assignment(Base):
    """отображает Assignment со ссылкой на Entity."""

    __tablename__ = 'assignment'
    identifier = Column(Integer, primary_key=True)
    created = Column(Integer, nullable=False)
    parameter = Column(String, nullable=False)
    entity = Column(Integer, ForeignKey('entity.identifier'), nullable=False)
    tags = Column(String, nullable=False)
    stage = Column(String, nullable=False)
    triggered = Column(Integer, nullable=False)


class Feedback(Base):
    """отображает Feedback со ссылкой на Assignment."""

    __tablename__ = 'feedback'
    identifier = Column(Integer, primary_key=True)
    created = Column(Integer, nullable=False)
    output = Column(String, nullable=False)
    stage = Column(String, nullable=False)
    exception = Column(String, nullable=False)
    assignment = Column(Integer, ForeignKey('assignment.identifier'),
                        nullable=False)
    cache_hit = Column(Integer, nullable=False)
    duration = Column(Integer, nullable=False)


TABLES = {'entity': Entity, 'assignment': Assignment, 'feedback': Feedback}
