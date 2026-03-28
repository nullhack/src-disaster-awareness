#!/usr/bin/env python3
"""Simple HTTP server for dashboard development."""

import http.server
import socketserver
import argparse
import os
import webbrowser
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="Serve the Disaster Awareness Dashboard"
    )
    parser.add_argument("--port", type=int, default=8000, help="Port to serve on")
    parser.add_argument(
        "--open", action="store_true", help="Open browser automatically"
    )
    parser.add_argument("--directory", default=None, help="Directory to serve from")
    args = parser.parse_args()

    # Use static directory if not specified
    if args.directory:
        serve_dir = Path(args.directory)
    else:
        serve_dir = Path(__file__).parent / "static"

    os.chdir(serve_dir)

    # Allow port reuse
    socketserver.TCPServer.allow_reuse_address = True

    class Handler(http.server.SimpleHTTPRequestHandler):
        def end_headers(self):
            # Add CORS headers for development
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-cache")
            super().end_headers()

        def log_message(self, format, *args):
            print(f"[Dashboard] {args[0]}")

    with socketserver.TCPServer(("", args.port), Handler) as httpd:
        url = f"http://localhost:{args.port}"
        print(f"\n{'=' * 60}")
        print(f"  Disaster Awareness Dashboard")
        print(f"{'=' * 60}")
        print(f"  Serving at: {url}")
        print(f"  Directory:  {serve_dir}")
        print(f"{'=' * 60}\n")

        if args.open:
            webbrowser.open(url)

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\nShutting down...")


if __name__ == "__main__":
    main()
