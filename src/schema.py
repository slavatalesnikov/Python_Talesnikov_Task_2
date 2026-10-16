"""поля трёх таблиц из ER-диаграммы варианта 22."""

from time import time

from pydantic import BaseModel, ConfigDict, Field


REPORT_SECONDS = 6 * 60


def timestamp():
    """возвращает целое число секунд Unix, как требует поле datetime."""
    return int(time())


class ActorData(BaseModel):
    """поля участника без первичного ключа, передаваемого в пути."""

    model_config = ConfigDict(extra='forbid')
    datetime: int = Field(default_factory=timestamp)
    platform: str = ''
    user_agent: str = ''


class Actor(ActorData):
    """полная запись Actor с целочисленным первичным ключом."""

    uid: int


class InstructionData(BaseModel):
    """входные данные задачи; input содержит сам текст Markdown."""

    model_config = ConfigDict(extra='forbid')
    datetime: int = Field(default_factory=timestamp)
    input: str
    actor: int
    description: str = ''
    tags: str = ''
    stage: str = 'queued'


class Instruction(InstructionData):
    """полная запись Instruction, связанная с Actor через actor."""

    uid: int


class Response(BaseModel):
    """результат: output — путь к docx, failure — текст ошибки."""

    model_config = ConfigDict(extra='forbid')
    uid: int
    datetime: int
    output: str
    stage: str
    failure: str
    instruction: int


SCHEMAS = {'actor': Actor, 'instruction': Instruction, 'response': Response}
