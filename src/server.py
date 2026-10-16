"""запуск HTTP-сервера и выбор тестового режима."""

import argparse

import uvicorn

from src.api import create_app


DEFAULT_PORT = 8000


def main():
    """читает параметры запуска и запускает один процесс сервера."""
    parser = argparse.ArgumentParser(description='Markdown -> Docx HTTP API')
    parser.add_argument('--database')
    parser.add_argument('--backend', choices=['json', 'tinydb'],
                        default='tinydb')
    parser.add_argument('--output', default='output')
    parser.add_argument('--port', type=int, default=DEFAULT_PORT)
    parser.add_argument('--test-mode', action='store_true')
    args = parser.parse_args()
    database = args.database or f'data/{args.backend}.json'
    app = create_app(database, args.test_mode, args.output, args.backend)
    uvicorn.run(app, host='127.0.0.1', port=args.port)


if __name__ == '__main__':
    main()
