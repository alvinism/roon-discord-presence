"""Roon's MOO/1 message framing (as used by node-roon-api over WebSocket).

    MOO/1 <VERB> <name>
    Request-Id: <n>
    Content-Length: <bytes>          (only with a body)
    Content-Type: application/json   (only with a body)

    <json body>

VERB is REQUEST (name = "service/method"), CONTINUE or COMPLETE (name = e.g. "Success").
"""

import json
from typing import Any, NamedTuple


class MooError(ValueError):
    pass


class Message(NamedTuple):
    verb: str
    name: str
    request_id: int
    body: Any = None


def encode(verb: str, name: str, request_id: int, body: Any = None) -> bytes:
    head = f"MOO/1 {verb} {name}\nRequest-Id: {request_id}\n"
    if body is None:
        return (head + "\n").encode()
    payload = json.dumps(body, ensure_ascii=False).encode()
    head += f"Content-Length: {len(payload)}\nContent-Type: application/json\n\n"
    return head.encode() + payload


def decode(data: bytes | str) -> Message:
    if isinstance(data, str):
        data = data.encode()
    head, sep, payload = data.partition(b"\n\n")
    lines = head.decode().split("\n")
    first = lines[0].split(" ", 2)
    if len(first) != 3 or first[0] != "MOO/1":
        raise MooError(f"bad first line: {lines[0]!r}")
    headers = {}
    for line in lines[1:]:
        key, _, value = line.partition(":")
        headers[key.strip().lower()] = value.strip()
    if "request-id" not in headers:
        raise MooError("missing Request-Id")
    body = None
    if sep and payload:
        if "application/json" not in headers.get("content-type", "application/json"):
            raise MooError(f"unsupported content type: {headers['content-type']}")
        body = json.loads(payload)
    return Message(first[1], first[2], int(headers["request-id"]), body)
