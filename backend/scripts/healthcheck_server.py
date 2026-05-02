"""輕量 HTTP healthcheck server — paint-worker 專用。

paint-worker 跑 Celery，本身沒 HTTP port。但 Railway 會 ping 容器 PORT
判斷服務 ready，沒 ping 通就停在 Deploying，超過 deploy timeout 會
被標 Failed 並 kill — 即使 celery 已正常處理任務。

此 server 在 worker 容器內背景跑，吃任何 GET 都回 200 OK，純為了
讓 Railway 偵測到 port 開了 → 服務變 Active → 不被 kill。

Dual-stack（IPv6 + IPv4）：Railway 內網是 IPv6（fd12:...），但容器內 process
若只 bind IPv4 (0.0.0.0)，Railway 從 IPv6 來的 health probe 會 ping 不通。
本 server 用 AF_INET6 + IPV6_V6ONLY=0 同時接受 IPv6 與 v4-mapped-v6 連線。
"""
import http.server
import os
import socket
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


class DualStackTCPServer(socketserver.TCPServer):
    """Bind IPv6 socket with IPV6_V6ONLY=0 → 同時接 IPv6 與 IPv4 連線。"""
    address_family = socket.AF_INET6

    def server_bind(self):
        self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        super().server_bind()


if __name__ == "__main__":
    with DualStackTCPServer(("::", PORT), Handler) as srv:
        print(
            f"[healthcheck] worker healthcheck server listening on [::]:{PORT} (dual-stack)",
            flush=True,
        )
        srv.serve_forever()
