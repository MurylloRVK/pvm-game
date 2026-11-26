"""
PvM Admin API
- Senha armazenada apenas no ambiente do serviço Render (PVM_ADMIN_PASSWORD).
- Sessões curtas e revogáveis; a senha nunca é enviada a clientes exceto durante o POST HTTPS de login.
- Relay de avisos, eventos e invocação do TAF para jogadores atualmente conectados.
- Estado de eventos/presença mantido em memória: é intencionalmente temporário e reinicia junto com o serviço.
"""
from __future__ import annotations

import hmac
import os
import secrets
import threading
import time
from collections import defaultdict, deque
from functools import wraps
from typing import Any

from flask import Flask, jsonify, make_response, request

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024

ALLOWED_ORIGINS = {
    "https://pvm-game.onrender.com",
    "https://pvm-game-2.onrender.com",
    "http://127.0.0.1:5500",
    "http://localhost:5500",
}
SESSION_TTL_SECONDS = 6 * 60 * 60
PRESENCE_TTL_SECONDS = 35
EVENT_LOG_LIMIT = 500
ALLOWED_EVENT_TYPES = {
    "taco", "shock", "leprechaun", "eclipse", "chorume", "frost",
    "flame", "armored", "phantom", "spore", "cosmic", "tafAura",
}

_lock = threading.RLock()
_sessions: dict[str, float] = {}
_login_attempts: dict[str, deque[float]] = defaultdict(deque)
_presence: dict[str, float] = {}
_event_log: deque[dict[str, Any]] = deque(maxlen=EVENT_LOG_LIMIT)
_active_world_events: dict[str, dict[str, Any]] = {}
_next_event_id = 1


@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        return make_response("", 204)
    return None


@app.after_request
def add_cors_headers(response):
    origin = request.headers.get("Origin")
    if origin in ALLOWED_ORIGINS:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response.headers["Access-Control-Max-Age"] = "600"
        response.headers["Vary"] = "Origin"
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


def _prune_locked(now: float) -> None:
    expired = [token for token, expiry in _sessions.items() if expiry <= now]
    for token in expired:
        _sessions.pop(token, None)

    stale_clients = [
        client_id for client_id, seen in _presence.items()
        if now - seen > PRESENCE_TTL_SECONDS
    ]
    for client_id in stale_clients:
        _presence.pop(client_id, None)

    now_ms = int(now * 1000)
    expired_events = [
        event_id for event_id, event in _active_world_events.items()
        if int(event.get("endsAt", 0)) <= now_ms
    ]
    for event_id in expired_events:
        _active_world_events.pop(event_id, None)


def _admin_token_is_valid() -> bool:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return False
    token = auth[7:].strip()
    if not token:
        return False
    now = time.time()
    with _lock:
        _prune_locked(now)
        expiry = _sessions.get(token)
        return bool(expiry and expiry > now)


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not _admin_token_is_valid():
            return jsonify({"error": "Sessão de administrador ausente ou expirada."}), 401
        return fn(*args, **kwargs)
    return wrapper


def _online_count_locked(now: float) -> int:
    _prune_locked(now)
    return len(_presence)


def _append_event_locked(kind: str, payload: dict[str, Any]) -> int:
    global _next_event_id
    event_id = _next_event_id
    _next_event_id += 1
    _event_log.append({
        "id": event_id,
        "type": kind,
        "payload": payload,
        "createdAt": int(time.time() * 1000),
    })
    return event_id


@app.get("/health")
def health():
    # Não revela a senha nem o token; só informa se o servidor foi configurado.
    return jsonify({
        "ok": True,
        "service": "pvm-admin-api",
        "adminAuthConfigured": bool(os.environ.get("PVM_ADMIN_PASSWORD")),
    })


@app.post("/api/admin/login")
def admin_login():
    expected = os.environ.get("PVM_ADMIN_PASSWORD", "")
    if not expected:
        return jsonify({
            "error": "A senha ainda não foi configurada no ambiente privado do Render."
        }), 503

    body = request.get_json(silent=True) or {}
    supplied = body.get("password")
    if not isinstance(supplied, str) or not supplied or len(supplied) > 256:
        return jsonify({"error": "Digite a senha de administrador."}), 400

    ip = request.headers.get("X-Forwarded-For", request.remote_addr or "unknown").split(",")[0].strip()
    now = time.time()
    with _lock:
        attempts = _login_attempts[ip]
        while attempts and now - attempts[0] > 600:
            attempts.popleft()
        if len(attempts) >= 8:
            return jsonify({"error": "Muitas tentativas. Aguarde alguns minutos e tente novamente."}), 429

        if not hmac.compare_digest(supplied.encode("utf-8"), expected.encode("utf-8")):
            attempts.append(now)
            return jsonify({"error": "Senha incorreta."}), 401

        attempts.clear()
        token = secrets.token_urlsafe(36)
        expires_at = now + SESSION_TTL_SECONDS
        _sessions[token] = expires_at

    return jsonify({
        "ok": True,
        "token": token,
        "expiresAt": int(expires_at * 1000),
        "sessionSeconds": SESSION_TTL_SECONDS,
    })


@app.get("/api/poll")
def poll_players():
    client_id = request.args.get("client_id", "")
    if not isinstance(client_id, str) or not (8 <= len(client_id) <= 96):
        return jsonify({"error": "Identificador de sessão inválido."}), 400

    after_raw = request.args.get("after")
    try:
        after_id = max(0, int(after_raw)) if after_raw is not None else None
    except (TypeError, ValueError):
        return jsonify({"error": "Cursor de eventos inválido."}), 400

    now = time.time()
    with _lock:
        _presence[client_id] = now
        _prune_locked(now)
        latest_id = _next_event_id - 1

        # Em uma aba nova, não repetimos avisos antigos; devolvemos os eventos de mundo que ainda estão ativos.
        if after_id is None:
            events: list[dict[str, Any]] = []
        else:
            events = [event for event in _event_log if event["id"] > after_id]

        active_events = list(_active_world_events.values())
        online_players = _online_count_locked(now)

    return jsonify({
        "events": events,
        "activeEvents": active_events,
        "latestId": latest_id,
        "onlinePlayers": online_players,
        "serverTime": int(now * 1000),
    })


@app.get("/api/admin/status")
@admin_required
def admin_status():
    now = time.time()
    with _lock:
        count = _online_count_locked(now)
        active_events = list(_active_world_events.values())
        latest_id = _next_event_id - 1
    return jsonify({
        "ok": True,
        "onlinePlayers": count,
        "activeEvents": active_events,
        "latestId": latest_id,
    })


@app.post("/api/admin/broadcast")
@admin_required
def admin_broadcast():
    body = request.get_json(silent=True) or {}
    kind = body.get("type")
    now_ms = int(time.time() * 1000)

    if kind == "event":
        raw = body.get("event") or {}
        event_type = raw.get("type")
        if event_type not in ALLOWED_EVENT_TYPES:
            return jsonify({"error": "Tipo de evento não permitido."}), 400
        try:
            ends_at = int(raw.get("endsAt", 0))
        except (TypeError, ValueError):
            ends_at = 0
        if ends_at <= now_ms or ends_at > now_ms + 7 * 24 * 60 * 60 * 1000:
            return jsonify({"error": "A duração do evento precisa estar entre agora e sete dias."}), 400

        label = str(raw.get("label") or event_type)[:80]
        event = {
            "id": f"admin-{secrets.token_hex(8)}",
            "type": event_type,
            "label": label,
            "source": "admin-hub",
            "startsAt": now_ms,
            "endsAt": ends_at,
        }
        with _lock:
            _active_world_events[event["id"]] = event
            event_id = _append_event_locked("event", event)
            online_players = _online_count_locked(time.time())
        return jsonify({"ok": True, "eventId": event_id, "deliveredTo": online_players})

    if kind == "clear":
        with _lock:
            _active_world_events.clear()
            event_id = _append_event_locked("clear", {})
            online_players = _online_count_locked(time.time())
        return jsonify({"ok": True, "eventId": event_id, "deliveredTo": online_players})

    if kind == "taf":
        try:
            hp = int(float((body.get("options") or {}).get("hp", 24000)))
        except (TypeError, ValueError):
            hp = 24000
        payload = {"hp": max(12000, min(250000, hp))}
        with _lock:
            event_id = _append_event_locked("taf", payload)
            online_players = _online_count_locked(time.time())
        return jsonify({"ok": True, "eventId": event_id, "deliveredTo": online_players})

    if kind == "notice":
        title = str(body.get("title") or "").strip()[:90]
        message = str(body.get("body") or "").strip()[:260]
        if not title or not message:
            return jsonify({"error": "Preencha o título e o comunicado."}), 400
        with _lock:
            event_id = _append_event_locked("notice", {"title": title, "body": message})
            online_players = _online_count_locked(time.time())
        return jsonify({"ok": True, "eventId": event_id, "deliveredTo": online_players})

    return jsonify({"error": "Ação administrativa desconhecida."}), 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "10000")))
