"""所持チェック画面をローカルだけで表示する簡易サーバー。"""

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PORT = 8765
DIRECTORY = Path(__file__).parent


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIRECTORY), **kwargs)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"ブラウザで http://127.0.0.1:{PORT} を開いてください。終了は Ctrl+C です。")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("終了しました。")
    finally:
        server.server_close()
