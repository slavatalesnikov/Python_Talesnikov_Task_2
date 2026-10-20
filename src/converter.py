"""преобразование файла Markdown в бинарный Docx через Pandoc."""
import argparse
import subprocess

parser = argparse.ArgumentParser(description='Markdown -> Docx через Pandoc')
parser.add_argument('source')
args = parser.parse_args()
subprocess.run(['pandoc', args.source, '-f', 'markdown', '-t', 'docx',
                '-o', '-'], check=True)
