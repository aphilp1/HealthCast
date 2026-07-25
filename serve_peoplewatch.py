"""PeopleWatch local server — same as python -m http.server, but tells the browser
NEVER to cache the app. Chrome was serving stale (and sometimes broken) copies of
census.html, which looked like "the app shows nothing".

Run:  python serve_peoplewatch.py      (serves this folder on :8020)
"""
import functools
import http.server
import socketserver

PORT = 8020


class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def log_message(self, fmt, *args):   # keep the console quiet
        pass


if __name__ == "__main__":
    handler = functools.partial(NoCacheHandler, directory=r"C:\Users\aphil\Documents\Census")
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        print(f"PeopleWatch serving on http://localhost:{PORT}/census.html (no-cache)")
        httpd.serve_forever()
