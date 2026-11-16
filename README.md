# Cast-O-Matic

## Cross-device presentation casting web app

Cast-O-Matic is a responsive Progressive Web App (PWA) for presenting content from a laptop to a phone, tablet, another laptop, or a modern smart-TV browser.

It uses **Flask + Flask-SocketIO + WebRTC**. A presenter creates a room, shares the receiver link/code, uploads a PDF or starts live screen sharing, and the receiver displays the presentation.

### Why this version is different

- No projector-specific IP, Epson commands, or PJLink hardware is required.
- Each presentation uses its own room code.
- The receiver URL is generated automatically.
- The receiver works in a normal browser and is responsive for mobile and large displays.
- The web app can be installed as a PWA on supported browsers.
- WebRTC is used for live screen casting; Socket.IO handles signaling.
- PDF presentations are delivered to the selected room.

## Technology stack

- Python 3.11+
- Flask
- Flask-SocketIO
- HTML/CSS/JavaScript
- WebRTC
- Progressive Web App (PWA)
- Docker
- Kubernetes
- Jenkins

## Run locally

```bash
python -m pip install -r requirements.txt
python app.py
```

The server listens on port `5080`.

Open:

- Home: `http://localhost:5080/`
- Presenter: `http://localhost:5080/sender`
- Receiver: `http://localhost:5080/receiver`

### Demo flow

1. Open `/sender` on the presentation laptop.
2. A room code is created automatically.
3. Copy the generated receiver link or share the room code.
4. Open that receiver link on a phone, tablet, another laptop, or smart-TV browser.
5. Upload a PDF from the presenter page **or** click **Start Live Cast**.
6. Choose the browser window/screen to share.
7. The receiver displays the live presentation.
8. Click **Stop** when finished.

For a real deployment, publish the application behind a domain using HTTPS. PWA installation and some browser capabilities require a secure context. `localhost` is also treated as secure for local development.

## Docker

```bash
docker build -t cast-o-matic:latest .
docker run -p 5080:5080 cast-o-matic:latest
```

## Kubernetes

```bash
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
kubectl get pods
kubectl get services
```

The included service exposes port `30080` on the Kubernetes node.

## Project structure

```text
cast-o-matic/
├── app.py
├── requirements.txt
├── Dockerfile
├── Jenkinsfile
├── deployment.yaml
├── service.yaml
├── guard.py
├── templates/
│   ├── index.html
│   ├── sender.html
│   └── receiver.html
├── static/
│   ├── manifest.json
│   ├── sw.js
│   ├── icon-192.png
│   └── icon-512.png
├── uploads/
└── tests/
    └── test_guard.py
```

## Presentation explanation

**Problem:** Traditional classrooms may depend on a physical projector and proprietary projector control protocols.

**Solution:** Cast-O-Matic provides a browser-based presentation receiver. A presenter creates a room and sends a PDF or live screen stream using WebRTC. Any compatible mobile, tablet, laptop, or smart-TV browser can act as the display.

**Key advantage:** Users interact with a normal web app instead of configuring projector hardware.

## Important deployment note

For a classroom demo on the same network, the server must be reachable by the receiver device. For many independent users, deploy the app to a reachable server/domain and use HTTPS. Users then open the website and use room links/codes instead of manually entering a machine's IP address.


## Universal casting

Cast-O-Matic supports two modes:

- **File Cast:** upload PDF, Word, PowerPoint, Excel, images, video, audio, text and other files up to 50 MB. Browser-supported formats are displayed directly; Office documents use the public Microsoft Office viewer; other formats can be downloaded on the receiver.
- **Live Screen Cast:** use WebRTC `getDisplayMedia()` to cast any visible desktop window, browser tab, presentation, document, video, website or application. This is the universal fallback for formats that a receiver browser cannot render directly.

The receiver is a normal HTTPS web page, so users do not need to enter a local IP address. They only need the public receiver link or room code.
