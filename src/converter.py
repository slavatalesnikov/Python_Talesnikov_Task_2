import argparse
import subprocess

parser = argparse.ArgumentParser(description='mmarkdown -> docx')
parser.add_argument('source')
args = parser.parse_args()
subprocess.run(['pandoc', args.source, '-f', 'markdown', '-t', 'docx',
                '-o', '-'], check=True)
