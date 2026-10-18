"""асинхронный запуск CLI: файл на входе, Docx из stdout на диск."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess
import sys
from time import monotonic
from uuid import uuid4


PROCESS_TIMEOUT = 60
MILLISECONDS = 1000


class Worker:
    """выполняет задачи в одном фоновом потоке, не задерживая HTTP-ответ."""

    def __init__(self, model, output_dir, test_mode=False):
        """в тестовом режиме subprocess заменяется тестовым результатом."""
        self.model = model
        self.output_dir = Path(output_dir).resolve()
        self.test_mode = test_mode
        self.executor = ThreadPoolExecutor(max_workers=1)

    def submit(self, assignment):
        """ставит реальную задачу в очередь, тестовую выполняет сразу."""
        if self.test_mode:
            self.execute(assignment)
        else:
            self.executor.submit(self.execute, assignment)

    def convert_file(self, assignment):
        """передаёт путь parameter и перехватывает бинарный stdout."""
        filename = f'{assignment["identifier"]}-{uuid4().hex}.docx'
        output = self.output_dir / filename
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            with output.open('wb') as stream:
                process = subprocess.run(
                    [sys.executable, '-m', 'src.converter',
                     assignment['parameter']], stdout=stream,
                    stderr=subprocess.PIPE, timeout=PROCESS_TIMEOUT,
                    cwd=Path(__file__).resolve().parents[1],
                )
            if process.returncode:
                message = process.stderr.decode('utf-8', errors='replace')
                raise ValueError(message.strip() or 'ошибка преобразования')
            return {'output': str(output), 'exception': ''}
        except (OSError, ValueError, subprocess.TimeoutExpired) as error:
            output.unlink(missing_ok=True)
            return {'output': '', 'exception': str(error)}

    def execute(self, assignment):
        """сохраняет время запуска, результат, длительность и текст ошибки."""
        identifier = assignment['identifier']
        if not self.model.start(identifier):
            return
        if self.test_mode:
            self.model.complete(identifier, {'output': 'test.docx',
                                             'exception': ''}, 0)
            return
        started = monotonic()
        result = self.convert_file(assignment)
        duration = int((monotonic() - started) * MILLISECONDS)
        self.model.complete(identifier, result, duration)

    def close(self):
        """дожидается фоновых задач перед закрытием базы."""
        self.executor.shutdown(wait=True)
