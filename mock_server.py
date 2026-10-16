import http.server
import json

class MockGeminiHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        response_data = {
            "candidates": [{
                "content": {
                    "parts": [{"text": "```json\n{\"command\": \"uname -a\"}\n```"}]
                }
            }]
        }
        self.wfile.write(json.dumps(response_data).encode("utf-8"))
    
    def log_message(self, format, *args):
        return

if __name__ == "__main__":
    server = http.server.HTTPServer(("127.0.0.1", 8080), MockGeminiHandler)
    print("[+] Mock Gemini API server active on http://127.0.0.1:8080")
    server.serve_forever()
