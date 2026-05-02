"""輕量 HTTP healthcheck server — paint-worker 專用。

paint-worker 跑 Celery，本身沒 HTTP port。但 Railway 會 ping 容器 PORT
判斷服務 ready，沒 ping 通就停在 Deploying，超過 deploy timeout 會
被標 Failed 並 kill — 即使 celery 已正常處理任務。

此 server 在 worker 容器內背景跑，吃任何 GET 都回 200 OK，純為了
讓 Railway 偵測到 port 開了 → 服務變 Active → 不被 kill。
"""
import http.server
import os
import socketserver

PORT = int(os.environ.get("PORT", "8080"))


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *args, **kwargs):
        pass


if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), Handler) as srv:
        print(f"[healthcheck] worker healthcheck server listening on :{PORT}", flush=True)
        srv.serve_forever()
