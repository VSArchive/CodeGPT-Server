import json
import os
import re
import secrets

import openai
import requests
from dotenv import load_dotenv
from flask import Flask, request
from flask_cors import CORS

# Load environment variables from .env
load_dotenv()

app = Flask(__name__)
CORS(app)

# Set your OpenAI API key here
openai.api_key = os.getenv("OPENAI_API_KEY")

CODE_EXECUTION_SERVER = os.getenv("CODE_EXECUTION_SERVER")
SYSTEM_PROMPT = "You are a code generator and modifier that generates and modifies code based on a prompt in python, you are only allowed to generate, modify and produce a output that is valid python code with no syntax errors, the generated content must not contain anything except for valid python code, don't prompt the user for input."


def cleanup_message(message) -> list:
    """
    Removes fields other than role and content from the message
    """
    new_message = []

    for item in message:
        new_message.append(
            {
                "role": item["role"],
                "content": item["content"],
            }
        )

    return new_message


@app.route("/api/threads", methods=["GET"])
def get_threads():
    """
    Returns all threads
    """
    with open("thread_cache.json", encoding="utf-8") as f:
        thread_cache = json.load(f)

    return thread_cache


@app.route("/api/threads/<thread_id>", methods=["GET"])
def get_thread(thread_id):
    """
    Returns a thread by id
    """
    with open("thread_cache.json", encoding="utf-8") as f:
        thread_cache = json.load(f)

    return thread_cache.get(thread_id, {})


@app.route("/api/generate_code", methods=["POST"])
def generate_code():
    """
    Generates code based on a prompt and returns the generated code and output of the code
    """
    data = request.json

    with open("cache.json", encoding="utf-8") as f:
        cache = json.load(f)

    with open("thread_cache.json", encoding="utf-8") as f:
        thread_cache = json.load(f)

    prompt = data["prompt"]

    thread_id = data["threadId"]

    if thread_id == "":
        message = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]
        if prompt in cache:
            code = cache[prompt]["content"]
            message.append(cache[prompt])
        else:
            completion = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=message,
            )

            cache[prompt] = completion.choices[0].message

            message.append(completion.choices[0].message)

            with open("cache.json", "w", encoding="utf-8") as f:
                json.dump(cache, f)

            code = completion.choices[0].message["content"]

        thread_id = secrets.token_hex(16)

        thread = {
            "thread_id": thread_id,
            "content": message,
        }

        thread_cache[thread_id] = thread

    else:
        message = thread_cache.get(thread_id, {}).get("content", [])

        message.append({"role": "user", "content": prompt})

        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=cleanup_message(message),
        )

        message.append(completion.choices[0].message)
        code = completion.choices[0].message["content"]

    if "```python" in code:
        code = re.findall(r"```python\n(.*)\n```", code, re.DOTALL)[0]

    response = requests.post(
        f"{CODE_EXECUTION_SERVER}/run",
        json={
            "code": code,
            "language": "python",
        },
        timeout=30,
    )

    print(response.json())

    message[len(message) - 1]["code"] = code
    message[len(message) - 1]["output"] = response.json()["output"]
    message[len(message) - 1]["run_id"] = response.json()["runId"]

    print(message)

    thread_cache[thread_id]["content"] = message

    with open("thread_cache.json", "w", encoding="utf-8") as f:
        json.dump(thread_cache, f)

    return {
        "code": code,
        "output": response.json()["output"],
        "runId": response.json()["runId"],
        "threadId": thread_id,
        "thread": thread_cache.get(thread_id, {}),
    }


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=os.environ.get("PORT", 3001), debug=True)
