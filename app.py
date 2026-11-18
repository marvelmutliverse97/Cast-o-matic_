import os
import secrets
import string
import mimetypes
import socket

from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit, join_room, leave_room
from werkzeug.utils import secure_filename

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "cast-o-matic-secret")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

ROOM_CHARS = string.ascii_uppercase + string.digits
ROOM_LENGTH = 6
MAX_ROOM_LENGTH = 20
current_presentations = {}
rooms = {}
sid_info = {}


def file_kind(filename, mime_type):
    ext = os.path.splitext(filename.lower())[1]
    if ext == ".pdf":
        return "pdf"
    if ext in {".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx"}:
        return "office"
    if mime_type.startswith("image/"):
        return "image"
    if mime_type.startswith("video/"):
        return "video"
    if mime_type.startswith("audio/"):
        return "audio"
    if mime_type.startswith("text/"):
        return "text"
    return "download"


def new_room_code():
    return "".join(secrets.choice(ROOM_CHARS) for _ in range(ROOM_LENGTH))


def clean_room(value):
    value = (value or "").strip().upper()
    if not value:
        return None
    if len(value) > MAX_ROOM_LENGTH or not all(c in ROOM_CHARS for c in value):
        return None
    return value


def get_local_ip():
    """Return the LAN address used by the machine when available."""
    try:
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        probe.settimeout(0.2)
        probe.connect(("192.0.2.1", 80))
        ip = probe.getsockname()[0]
        probe.close()
        if ip and not ip.startswith("127."):
            return ip
    except OSError:
        pass
    return "127.0.0.1"


def room_state(room):
    return rooms.setdefault(room, {"sender": None, "receivers": set()})


def remove_socket(sid):
    info = sid_info.pop(sid, None)
    if not info:
        return

    room, role = info
    state = rooms.get(room)
    if not state:
        return

    if role == "sender" and state["sender"] == sid:
        state["sender"] = None
        for receiver_sid in list(state["receivers"]):
            socketio.emit("peer_left", {"peer_id": sid}, to=receiver_sid)
        state["receivers"].clear()
    elif role == "receiver":
        state["receivers"].discard(sid)
        if state["sender"]:
            socketio.emit("peer_left", {"peer_id": sid}, to=state["sender"])

    if state["sender"] is None and not state["receivers"]:
        rooms.pop(room, None)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/sender")
def sender():
    room = clean_room(request.args.get("room"))
    if not room:
        room = new_room_code()
    mode = request.args.get("mode", "online").lower()
    if mode not in ("online", "offline"):
        mode = "online"
    return render_template("sender.html", room=room, mode=mode)


@app.route("/receiver")
def receiver():
    room = clean_room(request.args.get("room"))
    return render_template(
        "receiver.html",
        room=room,
        presentation=current_presentations.get(room) if room else None,
    )


@app.route("/network-info")
def network_info():
    return jsonify(
        local_ip=get_local_ip(),
        port=int(os.environ.get("PORT", 5080)),
        host=request.host,
        secure=request.is_secure,
    )


@app.route("/upload", methods=["POST"])
def upload_file():
    room = clean_room(request.form.get("room"))
    if not room:
        return jsonify(success=False, error="Invalid or missing room code"), 400

    if "file" not in request.files:
        return jsonify(success=False, error="No file was selected"), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify(success=False, error="Please select a file"), 400

    filename = secure_filename(file.filename)
    if not filename:
        return jsonify(success=False, error="Invalid filename"), 400

    stored_name = f"{room}_{filename}"
    filepath = os.path.join(UPLOAD_FOLDER, stored_name)
    mime_type = (
        file.mimetype
        or mimetypes.guess_type(filename)[0]
        or "application/octet-stream"
    )

    try:
        file.save(filepath)
        kind = file_kind(filename, mime_type)
        presentation = {
            "filename": stored_name,
            "original_name": filename,
            "mime": mime_type,
            "kind": kind,
        }
        current_presentations[room] = presentation
        socketio.emit("presentation_update", presentation, to=room)
        return jsonify(success=True, **presentation)
    except OSError:
        app.logger.exception("Upload failed")
        return jsonify(success=False, error="The server could not save the file"), 500


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=False)


@app.route("/manifest.json")
def manifest():
    return send_from_directory(os.path.join(BASE_DIR, "static"), "manifest.json")


@app.route("/sw.js")
def service_worker():
    response = send_from_directory(os.path.join(BASE_DIR, "static"), "sw.js")
    response.headers["Service-Worker-Allowed"] = "/"
    return response


@app.route("/favicon.ico")
def favicon():
    return "", 204


@socketio.on("join")
def on_join(data):
    data = data or {}
    room = clean_room(data.get("room"))
    role = data.get("role")

    if not room or role not in ("sender", "receiver"):
        emit("join_error", {"message": "Invalid room or role"})
        return

    state = room_state(room)

    # Only one presenter controls a room. A second presenter is rejected.
    if role == "sender" and state["sender"] and state["sender"] != request.sid:
        emit("join_error", {"message": "This room already has a presenter"})
        return

    join_room(room)
    sid_info[request.sid] = (room, role)

    if role == "sender":
        state["sender"] = request.sid
        emit("sender_joined", {"room": room, "receiver_count": len(state["receivers"])})
        for receiver_sid in list(state["receivers"]):
            emit("receiver_ready", {"room": room, "receiver_id": receiver_sid}, to=request.sid)
            emit("sender_ready", {"room": room}, to=receiver_sid)
    else:
        state["receivers"].add(request.sid)
        if state["sender"]:
            emit("receiver_ready", {"room": room, "receiver_id": request.sid}, to=state["sender"])
            emit("sender_ready", {"room": room}, to=request.sid)
        if current_presentations.get(room):
            emit("presentation_update", current_presentations[room], to=request.sid)


@socketio.on("offer")
def handle_offer(data):
    data = data or {}
    room = clean_room(data.get("room"))
    target = data.get("target")
    offer = data.get("offer")
    state = rooms.get(room or "")
    if not room or not target or not offer or not state or state.get("sender") != request.sid:
        return
    if target not in state["receivers"]:
        return
    emit("offer", {"offer": offer, "sender_id": request.sid}, to=target)


@socketio.on("answer")
def handle_answer(data):
    data = data or {}
    room = clean_room(data.get("room"))
    target = data.get("target")
    answer = data.get("answer")
    state = rooms.get(room or "")
    if not room or not target or not answer or not state or request.sid not in state["receivers"]:
        return
    if state.get("sender") != target:
        return
    emit("answer", {"answer": answer, "receiver_id": request.sid}, to=target)


@socketio.on("ice-candidate")
def handle_ice_candidate(data):
    data = data or {}
    room = clean_room(data.get("room"))
    target = data.get("target")
    candidate = data.get("candidate")
    state = rooms.get(room or "")
    if not room or not target or not isinstance(candidate, dict) or not candidate.get("candidate") or not state:
        return

    role = sid_info.get(request.sid, (None, None))[1]
    if role == "sender":
        if state.get("sender") != request.sid or target not in state["receivers"]:
            return
    elif role == "receiver":
        if request.sid not in state["receivers"] or state.get("sender") != target:
            return
    else:
        return

    emit(
        "ice-candidate",
        {"candidate": candidate, "peer_id": request.sid},
        to=target,
    )


@socketio.on("leave")
def on_leave(data):
    room = clean_room((data or {}).get("room"))
    if room and sid_info.get(request.sid, (None, None))[0] == room:
        remove_socket(request.sid)


@socketio.on("disconnect")
def on_disconnect():
    remove_socket(request.sid)


@app.errorhandler(413)
def file_too_large(error):
    return jsonify(success=False, error="File exceeds the 50 MB upload limit"), 413


if __name__ == "__main__":
    socketio.run(
        app,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5080)),
        debug=False,
        allow_unsafe_werkzeug=True,
    )
