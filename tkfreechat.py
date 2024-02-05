import argparse
import base64
import hashlib
import http.server
import json
import os.path
import shutil
import time
import threading
from typing import Any

# Constants
data_dir = "tfc_data"
messages_index_path = f"{data_dir}/index.json"
messages_path = f"{data_dir}/messages.json"
ext2type = {"js": "text/javascript", "html": "text/html", "css": "text/css"}
timeout_ms = 4 * 60 * 1000

def check_args(handler: http.server.BaseHTTPRequestHandler, args: tuple, target: dict) -> bool:
    err_info = "Missing parameter\nParameter: %s\nType: %s"

    for key, key_type in args:
        if (key not in target) or (not isinstance(target[key], key_type)):
            handler.send_response(500)
            handler.end_headers()
            handler.wfile.write(json.dumps({"err": err_info % (key, str(key_type))}).encode())
            return False
    return True


class TkFreeTalkRequestHandler(http.server.BaseHTTPRequestHandler):
    def __init__(self, a, b, c):
        super().__init__(a, b, c)

    def do_GET(self):
        if self.path == "/":
            filepath = "root/index.html"
        else:
            filepath = "root/{}".format(self.path.replace("..", ""))

        if self.path.startswith("/get_message_content"):
            # Get message content hash
            content_hash = self.path.split("/")[-1]

            # Get messages index
            with open(messages_index_path, mode="r", encoding="utf-8") as f:
                messages_index = json.load(f)

            # If not exists
            if content_hash not in messages_index:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"{\"err\": \"Message Not Found: %s\"}" % content_hash.encode())
                return

            # If not closed
            if messages_index[content_hash].get("uploading", False):
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"{\"err\": \"Message is uploading.\"}")
                return

            # Read message content
            msg = messages_index[content_hash]

            with open(f"{data_dir}/{content_hash}", mode="rb") as f:
                msg_content = f.read()

            # Send response
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Disposition",
                             "attachment; filename=\"{}\"".format(msg["filename"]).encode().decode("latin-1"))
            self.send_header("Content-Length", str(len(msg_content)))
            self.end_headers()
            self.wfile.write(msg_content)
        else:
            # Get static resource
            # Find file
            if os.path.exists(filepath) and os.path.isfile(filepath):
                with open(filepath, mode="rb") as f:
                    self.send_response(200)
                    # Get type
                    if filepath.find(".") != -1 and ((file_ext := filepath.split(".")[-1]) in ext2type):
                        self.send_header("Content-Type", ext2type[file_ext])
                    self.end_headers()
                    self.wfile.write(f.read())
            else:
                self.send_error(404)

    def do_POST(self):
        try:
            request_json = json.loads(
                self.rfile.read(
                    int(self.headers["Content-Length"])
                ).decode(errors="ignore")
            )
        except (KeyError, ValueError, json.decoder.JSONDecodeError):
            self.send_error(500)
            return

        if self.path == "/send_message":
            # Check arguments
            if not check_args(self, (("author", str), ("type", str), ("filename", str), ("hash", str)),
                              request_json):
                return

            # Setting message's index
            message_index = {
                "author": request_json["author"], "type": request_json["type"],
                "filename": request_json["filename"], "hash": request_json["hash"],
                "timestamp": int(time.time() * 1000), "uploading": True
            }

            # Read messages
            with open(messages_index_path, mode="r", encoding="utf-8") as f:
                messages: dict[str, Any] = json.load(f)

            # Append message to index
            with open(messages_index_path, mode="w", encoding="utf-8") as f:
                messages[message_index["hash"]] = message_index
                json.dump(messages, f)

            # Append message to messages.json
            with open(messages_path, mode="r+", encoding="utf-8") as f:
                m = json.load(f)
                m.append(message_index["hash"])
                f.seek(0)
                json.dump(m, f)

            # Send response
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"{}")

        elif self.path == "/get_messages":
            # Check arguments
            if not check_args(self, (("count", int),), request_json):
                return

            # Read messages index
            with open(messages_index_path, mode="r", encoding="utf-8") as f:
                msg_index = json.load(f)

            with open(messages_path, mode="r", encoding="utf-8") as f:
                messages = json.load(f)

            # Ready for response
            response_messages = [msg for msg in messages[-request_json["count"]:]
                                 if (msg_index[msg]["timestamp"] > request_json["after"])
                                 and (not msg_index[msg].get("uploading", False))]
            response_list = [
                {"hash": k, "type": msg_index[k]["type"],
                 "author": msg_index[k]["author"], "filename": msg_index[k]["filename"],
                 "timestamp": msg_index[k]["timestamp"]}
                for k in response_messages
            ]

            # Send response
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps(response_list).encode())

        elif self.path == "/push_content":
            # Check arguments
            if not check_args(self, (("hash", str), ("content", str), ("eof", bool)), request_json):
                return
        
            # Read messages index
            with open(messages_index_path, mode="r", encoding="utf-8") as f:
                msg_index = json.load(f)
        
            # Check if the message is in index
            if request_json["hash"] not in msg_index:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"{\"err\": \"Message is not in index.\"}")
                return
        
            # Check if the message is EOF
            if "uploading" not in msg_index[request_json["hash"]]:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"{\"err\": \"Message is closed.\"}")
                return
        
            with open(f"{data_dir}/{request_json['hash']}", mode="ab") as f:
                # Append to content
                f.write(base64.b64decode(request_json["content"]))

            # If EOF
            if request_json["eof"]:
                # Verify hash
                with open(f"{data_dir}/{request_json['hash']}", mode="rb") as f:
                    file_hash = hashlib.sha256(f.read()).hexdigest()
    
                if file_hash != request_json["hash"]:
                    # Clean
                    del msg_index[request_json["hash"]]
                    os.remove(f"{data_dir}/{request_json['hash']}")
    
                    # Send response
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b"{\"err\": \"The hash provided does not match the actual hash.\"}")
                    return
                else:
                    del msg_index[request_json["hash"]]["uploading"]
    
                # Write to msg index
                with open(messages_index_path, mode="w", encoding="utf-8") as f:
                    json.dump(msg_index, f)
    
            # Send response
            self.send_response(201)
            self.end_headers()
            self.wfile.write(b"{}")



def check_messages(interval: int):
    while True:
        # Wait for the specified interval
        time.sleep(interval)

        # Read messages from the file system
        with open(messages_index_path, mode="r", encoding="utf-8") as f:
            msg_index = json.load(f)
        with open(messages_path, mode="r", encoding="utf-8") as f:
            messages = json.load(f)
    
        # Filter messages that have timed out
        msg_index = [msg for msg in msg_index if (time.time() - msg["timestamp"]) < timeout_ms]
        messages = [msg for msg in messages if messages in msg_index]
    
        # Write the filtered messages back to the file system
        with open(messages_index_path, mode="w", encoding="utf-8") as f:
            json.dump(msg_index, f)
        with open(messages_path, mode="w", encoding="utf-8") as f:
            json.load(messages, f)


def main():
    # Define command line arguments
    parser = argparse.ArgumentParser(
        prog="tkfreechat",
        description="Chat with others.",
        epilog="This program is licensed under the AGPLv3 or later."
    )
    parser.add_argument(
        "-p", "--port", type=int, default=11451, dest="port",
        help="The port of the server."
    )
    parser.add_argument(
        "-s", "--share", action="store_true", default=False, dest="share",
        help="To enable this option, bind the server to the address 0.0.0.0."
    )
    parser.add_argument(
        "-c", "--continue-chat", action="store_true", default=False, dest="using_old",
        help="Use the old data (if exists)."
    )
    parser.add_argument(
        "-i", "--check-interval", default=60*1000, type=int, dest="check_interval",
        help="Check the interval for message timeout."
    )

    # Parse command line arguments
    args = parser.parse_args()

    # Define server address
    host, port = "0.0.0.0" if args.share else "127.0.0.1", args.port

    # Clean and create directory
    if not args.using_old:
        if os.path.exists(data_dir):
            shutil.rmtree(data_dir)

    if not os.path.exists(data_dir):
        os.mkdir(data_dir)

        # Create files
        with open(messages_path, mode="w", encoding="utf-8") as f:
            f.write("[]")

        with open(messages_index_path, mode="w", encoding="utf-8") as f:
            f.write("{}")

    # Run server
    server = http.server.HTTPServer((host, port), TkFreeTalkRequestHandler)
    print(f"TkFreeChat runs on port {port}.")

    # Check
    threading.Thread(target=check_messages, name="Check Thread", args=(args.check_interval,), daemon=True).start()

    # Run server forever
    server.serve_forever()
    print("Stopping server...")


if __name__ == "__main__":
    main()
