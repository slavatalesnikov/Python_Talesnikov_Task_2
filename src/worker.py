"""фоновое выполнение CLI через subprocess без блокировки HTTP-ответа."""

import subprocess
import sys
from pathlib import Path
from uuid import uuid4


PROCESS_TIMEOUT = 60


class Worker:
    """связывает модель данных с утилитой первого этапа."""

    def __init__(self, model, output_dir, test_mode=False):
        """в тестовом режиме результат имитируется без запуска CLI."""
        self.model = model
        self.output_dir = Path(output_dir).resolve()
        self.test_mode = test_mode

    def execute(self, instruction):
        """запускается FastAPI после отправки ответа о принятой задаче.

        Markdown передаётся через stdin без shell. имя результата задаётся
        сервером, чтобы разные задачи не перезаписывали один документ.
        """
        uid = instruction['uid']
        output = self.output_dir / f'{uid}-{uuid4().hex}.docx'
        failure = ''
        if self.test_mode:
            self.model.complete(uid, 'test.docx', failure)
            return
        try:
            result = subprocess.run(
                [sys.executable, '-m', 'src.converter', str(output)],
                input=instruction['input'], text=True, encoding='utf-8',
                capture_output=True, timeout=PROCESS_TIMEOUT,
                cwd=Path(__file__).resolve().parents[1],
            )
            if result.returncode:
                failure = result.stderr.strip() or 'ошибка преобразования'
        except (OSError, subprocess.TimeoutExpired) as error:
            failure = str(error)
        self.model.complete(uid, '' if failure else str(output), failure)
