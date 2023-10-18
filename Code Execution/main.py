import datetime
import json
import os
import uuid

# import docker
import requests
from flask import Flask, Response, request
from flask_cors import CORS
from websocket import create_connection

# client = docker.from_env()

app = Flask(__name__)
CORS(app)

# The token is written on stdout when you start the notebook
base = "http://13.215.50.249:8888"
headers = {"Authorization": "Token 4fb90e6cdc4dbf40e73f60b4df56cf8ed7ddcd3a791e0ec9"}

url = base + "/api/kernels"
response = requests.post(url, headers=headers, timeout=10)
kernel = json.loads(response.text)

print(kernel)


opensearch_url = (
    "https://search-test-anqyvyqn2pxbklmlzfo27ikk4i.ap-southeast-1.es.amazonaws.com"
)


# @app.route("/api/run", methods=["POST"])
# def run_code():
#     if not os.path.exists("runs"):
#         os.mkdir("runs")

#     run_id = uuid.uuid4().hex
#     data = request.json

#     with open(f"runs/{run_id}.py", "w", encoding="utf-8") as f:
#         f.write(data["code"])

#     container = client.containers.run(
#         image="code-execution",
#         command=f"bash -c 'python3 /runs/{run_id}.py'",
#         detach=True,
#         auto_remove=True,
#         stdout=True,
#         stderr=True,
#         network_mode="host",
#         environment={"PYTHONUNBUFFERED": "1"},
#         volumes={os.path.join(os.getcwd(), "runs"): {"bind": "/runs", "mode": "rw"}},
#     )

#     def logs():
#         for line in container.logs(stream=True):
#             print(line)
#             yield line

#     return Response(logs())


@app.route("/api/execute", methods=["POST"])
def execute_code():
    data = request.json
    print(data)

    # Load the notebook and get the code of each cell
    code = data["code"]
    lang = data["language"]

    if lang == "python":
        # Execution request/reply is done on websockets channels
        ws = create_connection(
            "ws://13.215.50.249:8888/api/kernels/" + kernel["id"] + "/channels",
            header=headers,
        )

        def send_execute_request(code):
            msg_type = "execute_request"
            content = {"code": code, "silent": False}
            hdr = {
                "msg_id": uuid.uuid4().hex,
                "session": "test",
                "data": datetime.datetime.now().isoformat(),
                "msg_type": msg_type,
            }
            msg = {
                "header": hdr,
                "parent_header": hdr,
                "metadata": {},
                "content": content,
            }

            return msg

        ws.send(json.dumps(send_execute_request(code)))

        # output = []
        def logs():
            msg_type = ""
            rsp = {
                "content": {"execution_state": ""},
            }
            while msg_type != "stream":
                rsp = json.loads(ws.recv())
                msg_type = rsp["msg_type"]

                print(json.dumps(rsp, indent=4))

                if msg_type == "stream":
                    yield rsp["content"]["text"]
                elif msg_type == "display_data":
                    yield rsp["content"]["data"]["image/png"]
                elif msg_type == "error":
                    for t in rsp["content"]["traceback"]:
                        yield t
                elif msg_type == "status":
                    yield rsp["content"]["execution_state"]
                else:
                    yield "Unknown message type: " + msg_type

            ws.close()

    elif lang == "sql":
        res = requests.post(
            opensearch_url + "/_plugins/_sql",
            json={"query": code},
            headers={
                "Content-Type": "application/json",
                "Authorization": "Basic dGVzdDpUZXN0QDEyMw==",
            },
            timeout=10,
        )

        def logs():
            yield res.json()

    # return output
    return Response(logs())


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=os.environ.get("PORT", 3000), debug=True)
