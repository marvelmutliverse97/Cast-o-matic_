import os
import secrets
import string

from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit, join_room
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


def new_room_code():
    return "".join(secrets.choice(ROOM_CHARS) for _ in range(ROOM_LENGTH))


def clean_room(value):
    value = (value or "").strip().upper()
    if not value:
        return None
    if len(value) > MAX_ROOM_LENGTH or not all(c in ROOM_CHARS for c in value):
        return None
    return value


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/sender")
def sender():
    room = clean_room(request.args.get("room"))
    if not room:
        room = new_room_code()
    return render_template("sender.html", room=room)


@app.route("/receiver")
def receiver():
    room = clean_room(request.args.get("room"))
    if not room:
        return render_template("receiver.html", room=None, presentation=None)
    return render_template(
        "receiver.html",
        room=room,
        presentation=current_presentations.get(room),
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
        return jsonify(success=False, error="Please select a PDF file"), 400

    filename = secure_filename(file.filename)
    if not filename or not filename.lower().endswith(".pdf"):
        return jsonify(success=False, error="Only PDF files are supported"), 400

    # Prefix with room code to avoid filename collisions between rooms.
    stored_name = f"{room}_{filename}"
    filepath = os.path.join(UPLOAD_FOLDER, stored_name)

    try:
        file.save(filepath)
        with open(filepath, "rb") as pdf:
            if not pdf.read(5).startswith(b"%PDF-"):
                os.remove(filepath)
                return jsonify(success=False, error="Invalid PDF file"), 400

        current_presentations[room] = stored_name
        socketio.emit(
            "presentation_update",
            {"filename": stored_name},
            to=room,
        )
        return jsonify(success=True, filename=stored_name)

    except OSError as error:
        app.logger.exception("Upload failed")
        return jsonify(success=False, error=str(error)), 500


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename, as_attachment=False)


@app.route("/manifest.json")
def manifest():
    return send_from_directory(
        os.path.join(BASE_DIR, "static"), "manifest.json"
    )


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
        return

    join_room(room)
    print(f"{role.capitalize()} joined room: {room}")

    # Tell the other side that a peer is ready. The sender creates
    # the WebRTC offer only after a receiver is actually connected.
    if role == "receiver":
        emit("receiver_ready", {"room": room}, to=room, include_self=False)
    else:
        emit("sender_ready", {"room": room}, to=room, include_self=False)

        if current_presentations.get(room):
            emit(
                "presentation_update",
                {"filename": current_presentations[room]},
            )


@socketio.on("offer")
def handle_offer(data):
    data = data or {}
    room = clean_room(data.get("room"))
    if room and data.get("offer"):
        emit("offer", data["offer"], to=room, include_self=False)


@socketio.on("answer")
def handle_answer(data):
    data = data or {}
    room = clean_room(data.get("room"))
    if room and data.get("answer"):
        emit("answer", data["answer"], to=room, include_self=False)


@socketio.on("ice-candidate")
def handle_ice_candidate(data):
    data = data or {}
    room = clean_room(data.get("room"))
    candidate = data.get("candidate")

    if room and isinstance(candidate, dict) and candidate.get("candidate"):
        emit("ice-candidate", {"candidate": candidate}, to=room, include_self=False)


@socketio.on("leave")
def on_leave(data):
    room = clean_room((data or {}).get("room"))
    if room:
        emit("peer_left", to=room, include_self=False)


@app.errorhandler(413)
def file_too_large(error):
    return jsonify(success=False, error="File exceeds the 50 MB upload limit"), 413


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 5080)), debug=False)
