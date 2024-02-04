import argparse
import base64
import datetime
import hashlib
import http.server
import json
import os.path
import shutil
from typing import Any

# Constants
cache_dir = "tfc_data"
messages_index_path = f"{cache_dir}/index.json"
messages_bin_path = f"{cache_dir}/messages.bin"
messages_path = f"{cache_dir}/messages.json"

ext2type = {"js": "text/javascript", "html": "text/html", "css": "text/css"}


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

            # Read message content
            msg = messages_index[content_hash]

            with open(messages_bin_path, mode="rb") as f:
                f.seek(msg["seek"])
                msg_content = f.read(msg["size"])

            # Send response
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Disposition",
                             "attachment; filename=\"{}\"".format(msg["filename"]).encode().decode("latin-1"))
            self.send_header("Content-Length", msg["size"])
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
            msg_json = json.loads(
                self.rfile.read(
                    int(self.headers["Content-Length"])
                ).decode(errors="ignore")
            )
        except KeyError | ValueError | json.decoder.JSONDecodeError:
            self.send_error(500)
            return

        if self.path == "/send_message":
            # Check arguments
            if not check_args(self, (("author", str), ("type", str), ("content", str), ("filename", str)), msg_json):
                return

            # Base64 Decode
            msg_json["content"] = base64.b64decode(msg_json["content"])

            # Setting message's index
            message_index = {"author": msg_json["author"], "type": msg_json["type"], "filename": msg_json["filename"],
                             "time": datetime.datetime.now(datetime.UTC).strftime("%Z %Y/%m/%d %H:%M:%S")}

            # Read messages
            with open(messages_index_path, mode="r", encoding="utf-8") as f:
                messages: dict[str, Any] = json.load(f)

            # Get SHA256
            content_hash = hashlib.sha256(msg_json["content"]).hexdigest()

            # Write to messages.bin
            if content_hash not in messages:
                with open(messages_bin_path, mode="ab") as f:
                    message_index["seek"] = f.tell()
                    message_index["size"] = len(msg_json["content"])

                    f.write(msg_json["content"])
            else:
                message_index["seek"] = messages[content_hash]["seek"]
                message_index["size"] = messages[content_hash]["size"]

            # Append message to index
            with open(messages_index_path, mode="w", encoding="utf-8") as f:
                messages[content_hash] = message_index
                json.dump(messages, f)

            # Append message to messages.json
            with open(messages_path, mode="r", encoding="utf-8") as f:
                m = json.load(f)

            m.append(content_hash)
            with open(messages_path, mode="w", encoding="utf-8") as f:
                json.dump(m, f)

            # Send response
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"{}")

        elif self.path == "/get_messages":
            # Check arguments
            if not check_args(self, (("count", int),), msg_json):
                return

            # Read messages index
            with open(messages_index_path, mode="r", encoding="utf-8") as f:
                msg_index = json.load(f)

            with open(messages_path, mode="r", encoding="utf-8") as f:
                messages = json.load(f)

            # Ready for response
            response_messages = messages[-msg_json["count"]:]
            response_list = [
                {"hash": k, "type": msg_index[k]["type"],
                 "author": msg_index[k]["author"], "filename": msg_index[k]["filename"],
                 "time": msg_index[k]["time"]}
                for k in response_messages
            ]

            # Send response
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps(response_list).encode())


def main():
    parser = argparse.ArgumentParser(
        prog="tkfreechat",
        description="Chat with others.",
        epilog="This program is licensed under the AGPLv3 or later."
    )
    parser.add_argument(
        "-p", "--port",
        type=int, default=11451, dest="port",
        help="The port of the server."
    )
    parser.add_argument(
        "-s", "--share",
        action="store_true", default=False, dest="share",
        help="To enable this option, bind the server to the address 0.0.0.0."
    )
    parser.add_argument(
        "-c", "--continue-talk", action="store_true", default=False, dest="using_old",
        help="Use the old data(if exists)."
    )
    args = parser.parse_args()

    # Define server address
    host, port = "0.0.0.0" if args.share else "127.0.0.1", args.port

    # Ready
    # Clean && Make dir
    if not args.using_old:
        if os.path.exists(cache_dir):
            shutil.rmtree(cache_dir)

    if not os.path.exists(cache_dir):
        os.mkdir(cache_dir)

        # Files
        with open(messages_path, mode="w", encoding="utf-8") as f:
            f.write("[]")

        with open(messages_index_path, mode="w", encoding="utf-8") as f:
            f.write("{}")

        with open(messages_bin_path, mode="wb") as f:
            f.write(b"")

    # Run server
    server = http.server.HTTPServer((host, port), TkFreeTalkRequestHandler)
    print("TkFreeChat runs on port {}.".format(port))

    # Run Forever
    server.serve_forever()
    print("Stopping server...")


if __name__ == "__main__":
    main()
