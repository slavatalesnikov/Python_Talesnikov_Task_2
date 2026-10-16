"""проверка пяти примеров с настоящим запуском CLI."""

import subprocess
import sys
from pathlib import Path

import pytest
from docx import Document


@pytest.mark.parametrize('source', sorted(Path('examples').glob('*.md')))
def test_examples(source, tmp_path):
    """проверяет создание читаемого docx и непустых абзацев."""
    output = tmp_path / f'{source.stem}.docx'
    result = subprocess.run(
        [sys.executable, '-m', 'src.converter', str(output)],
        input=source.read_text(encoding='utf-8'), text=True,
        capture_output=True, check=True,
    )
    assert str(output) in result.stdout
    assert any(p.text for p in Document(output).paragraphs)
