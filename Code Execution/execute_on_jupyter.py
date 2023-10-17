import datetime
import json
import uuid

import requests
from websocket import create_connection

# The token is written on stdout when you start the notebook
base = "http://13.215.50.249:8888"
headers = {"Authorization": "Token 4fb90e6cdc4dbf40e73f60b4df56cf8ed7ddcd3a791e0ec9"}

url = base + "/api/kernels"
response = requests.post(url, headers=headers, timeout=10)
kernel = json.loads(response.text)

# Load the notebook and get the code of each cell
code = ["print('Hello World')", "print('Hello World 2')"]

# Execution request/reply is done on websockets channels
ws = create_connection(
    "ws://13.215.50.249:8888/api/kernels/" + kernel["id"] + "/channels", header=headers
)


def send_execute_request(code):
    msg_type = "execute_request"
    content = {"code": code, "silent": False}
    hdr = {
        "msg_id": uuid.uuid4().hex,
        "session": "test",
        "data": datetime.datetime.now().isoformat(),
        "msg_type": msg_type,
        "version": "5.0",
    }
    msg = {"header": hdr, "parent_header": hdr, "metadata": {}, "content": content}

    return msg


for c in code:
    ws.send(json.dumps(send_execute_request(c)))

# We ignore all the other messages, we just get the code execution output
# (this needs to be improved for production to take into account errors, large cell output, images, etc.)

msg_type = ""
for i in code:
    while msg_type != "stream":
        rsp = json.loads(ws.recv())
        msg_type = rsp["msg_type"]
    print(rsp["content"]["text"])

ws.close()
