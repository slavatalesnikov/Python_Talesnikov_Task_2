"""запуск HTTP-сервера и выбор тестового режима."""

import argparse

import uvicorn

from src.api import create_app


DEFAULT_PORT = 8000


def main():
    """читает параметры запуска и запускает один процесс сервера."""
    parser = argparse.ArgumentParser(description='Markdown -> Docx HTTP API')
    parser.add_argument('--database', default='data/database.json')
    parser.add_argument('--output', default='output')
    parser.add_argument('--port', type=int, default=DEFAULT_PORT)
    parser.add_argument('--test-mode', action='store_true')
    args = parser.parse_args()
    app = create_app(args.database, args.test_mode, args.output)
    uvicorn.run(app, host='127.0.0.1', port=args.port)


if __name__ == '__main__':
    main()
