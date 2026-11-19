"""统一响应结构：成功 {"ok": true, "data": ...}，失败 {"ok": false, "error": {...}}。"""

from typing import Any


def ok(data: Any) -> dict:
    return {'ok': True, 'data': data}


def fail(code: str, message: str) -> dict:
    return {'ok': False, 'error': {'code': code, 'message': message}}
