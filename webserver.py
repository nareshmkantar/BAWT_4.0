"""
BAWT - Simple HTTP Server
Run this file to start a local development server.

Usage:
    python webserver.py

Then open http://localhost:8000 in your browser.
"""

import http.server
import socketserver
import os
import webbrowser
from functools import partial

PORT = 8000
DIRECTORY = os.path.dirname(os.path.abspath(__file__))


class BAWTHandler(http.server.SimpleHTTPRequestHandler):
    """Custom HTTP handler for BAWT application."""
    
    def __init__(self, *args, directory=None, **kwargs):
        super().__init__(*args, directory=directory, **kwargs)
    
    def end_headers(self):
        # Add CORS headers for local development
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        super().end_headers()
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()
    
    def log_message(self, format, *args):
        # Custom log format with color
        print(f"[BAWT Server] {args[0]}")


def run_server():
    """Start the development server."""
    handler = partial(BAWTHandler, directory=DIRECTORY)
    
    # Try ports 8000-8010
    start_port = 8000
    max_retries = 10
    httpd = None
    port = start_port
    
    for i in range(max_retries):
        port = start_port + i
        try:
            httpd = socketserver.TCPServer(("", port), handler)
            break
        except OSError:
            print(f"Port {port} is in use, trying next...")
            continue
            
    if httpd is None:
        print(f"Could not bind to any port between {start_port} and {start_port + max_retries - 1}")
        return

    with httpd:
        url = f"http://localhost:{port}"
        print("=" * 50)
        print("  BAWT - Budget Allocation Workflow Tool")
        print("=" * 50)
        print(f"\n  Server running at: {url}")
        print(f"  Login page: {url}/login.html")
        print(f"  Main app: {url}/index.html")
        print("\n  Press Ctrl+C to stop the server")
        print("=" * 50)
        
        # Open browser automatically
        try:
            webbrowser.open(url)
        except Exception:
            pass
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n  Server stopped.")


if __name__ == "__main__":
    run_server()
