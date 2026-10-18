"""запуск Flask и корректное завершение фонового исполнителя."""

import argparse

from src.api import create_app


DEFAULT_PORT = 8000


def main():
    """читает параметры запуска, конфигурацию и открывает локальный сервер."""
    parser = argparse.ArgumentParser(description='Markdown -> Docx')
    parser.add_argument('--database', default='data/variant24.json')
    parser.add_argument('--config', default='config.ini')
    parser.add_argument('--output', default='output')
    parser.add_argument('--port', type=int, default=DEFAULT_PORT)
    parser.add_argument('--test-mode', action='store_true')
    args = parser.parse_args()
    app = create_app(args.database, args.test_mode, args.output, args.config)
    try:
        app.run(host='127.0.0.1', port=args.port, threaded=True)
    finally:
        app.worker.close()
        app.model.storage.close()


if __name__ == '__main__':
    main()
