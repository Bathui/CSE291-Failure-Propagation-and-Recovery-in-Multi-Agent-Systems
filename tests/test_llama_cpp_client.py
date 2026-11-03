"""HTTP transport checks against an isolated local test server."""
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from agent_system.clients.llama_cpp import LlamaCppClient
from agent_system.protocol import AgentError
from tests.helpers import tool_response


class TransportTests(unittest.TestCase):
    def test_http_payload_uses_local_server_compatible_options(self):
        captured = []
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_GET(self):
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'{"data":[{"id":"test-model"}]}')
            def do_POST(self):
                captured.append((self.path, json.loads(self.rfile.read(int(self.headers["Content-Length"])))))
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps(tool_response("lookup_product", {"sku": "alpha"})).encode())
        server = HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            client = LlamaCppClient("http://127.0.0.1:%d/v1" % server.server_port, "test-model")
            client.preflight()
            client.chat([{"role": "user", "content": "test"}], [], 42)
            self.assertEqual(captured[0][0], "/v1/chat/completions")
            self.assertEqual(captured[0][1]["tool_choice"], "auto")
            self.assertFalse(captured[0][1]["parallel_tool_calls"])
            self.assertFalse(captured[0][1]["chat_template_kwargs"]["enable_thinking"])
            with self.assertRaises(AgentError):
                LlamaCppClient(client.base_url, "unavailable").preflight()
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
