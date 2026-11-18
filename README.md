# Cast-O-Matic

## Wireless Presentation and Multi-Device Display System

Cast-O-Matic is a browser-based presentation system built with Flask, Flask-SocketIO and WebRTC. A presenter creates a private room and can cast files or share a live screen with phones, tablets, laptops and compatible smart-TV or network-display browsers.

The application is designed for classroom and demonstration use. It does not require projector-specific IP commands, Epson control APIs or PJLink.

## Core capabilities

- Online presentation mode
- Offline LAN mode over the same Wi-Fi network
- Automatic room-code generation
- QR code session joining
- Built-in QR scanner on the home page
- Recent-session reconnect
- File casting up to 50 MB
- PDF preview
- Office document support through the public Office viewer when Internet access is available
- Images, video, audio and text preview
- Download/open fallback for unsupported file types
- Live screen casting with WebRTC
- Multiple receivers in the same room
- Responsive receiver for phones, tablets and large displays
- Receiver full-screen mode
- Automatic receiver connection handling
- PWA manifest and service worker
- Docker, Jenkins and Kubernetes configuration
- Render-compatible production startup

## Technology stack

- Python 3.11+
- Flask 3.0.2
- Flask-SocketIO 5.3.6
- Socket.IO JavaScript 4.7.2
- HTML5, CSS3 and JavaScript
- WebRTC
- Progressive Web App
- Docker
- Jenkins
- Kubernetes
- Render

## Local setup

```bash
python -m pip install -r requirements.txt
python app.py
```

The application listens on port `5080`.

Open the home page:

```text
http://127.0.0.1:5080/
```

For LAN/offline classroom use, start the server on the presenter laptop and connect the laptop and receiver devices to the same Wi-Fi network. The presenter page shows the detected LAN receiver URL.

Example:

```text
http://192.168.1.105:5080/receiver?room=A7K29B
```

The receiver devices do not need Internet access to communicate with the local Flask server and WebRTC peer. However, browser-hosted third-party CDN assets and the public Office viewer can require Internet access on a first load or when their services are used.

## Online demo flow

1. Open the deployed Cast-O-Matic website.
2. Select **Create Online Session**.
3. A room code and receiver QR code are generated.
4. Open the receiver by scanning the QR code, entering the room code, or opening the receiver link.
5. Upload a supported file, or select **Start Live Cast**.
6. For live casting, choose the desktop, browser tab or application window in the browser permission dialog.
7. The receiver displays the content.
8. Use **Full Screen** on the receiver for a TV or large display.
9. Stop the cast when the presentation is finished.

## Offline LAN flow

1. Install the requirements on the presenter laptop.
2. Start `python app.py`.
3. Select **Create Offline Session**.
4. Connect all receiver devices to the same Wi-Fi network.
5. Use the LAN receiver URL or room code shown by the presenter.
6. Use file casting or live screen casting.
7. No Internet connection to the application server is required.

## QR joining

The presenter displays one QR code for the current room.

The receiver can:

- Scan the QR code using the built-in scanner.
- Enter the room code manually.
- Reconnect to the most recently used room.

The QR code opens the receiver URL for that specific room.

## File casting

The backend accepts files up to 50 MB.

The receiver handles:

- PDF
- Word
- PowerPoint
- Excel
- Images
- Video
- Audio
- Text
- Other files through an open/download fallback

Office preview uses Microsoft's public Office viewer, so that preview path requires Internet access. For an offline classroom, use live screen casting for Office content.

## Live screen casting

Live Screen Cast uses:

```text
navigator.mediaDevices.getDisplayMedia()
```

The captured stream is sent through WebRTC. Socket.IO is used only for signaling.

A Google STUN server is configured:

```text
stun:stun.l.google.com:19302
```

Some restrictive networks may require a TURN server for reliable WebRTC connectivity across difficult NAT/firewall conditions.

## Multiple receivers

One presenter can have multiple receiver browsers in the same room. Each receiver gets its own WebRTC peer connection, so one receiver disconnecting does not terminate the other receiver connections.

## Smart TVs and projectors

A smart TV or network display can be used when it provides a compatible modern browser. Open the receiver URL and use full-screen mode.

A Wi-Fi projector can be used when its browser/display environment can open the receiver page.

This project does **not** implement Miracast, AirPlay, Chromecast, Epson control commands or PJLink. Those are separate device-specific protocols.

## Production deployment

The application is compatible with Render and can also be containerized.

Docker:

```bash
docker build -t cast-o-matic:latest .
docker run -p 5080:5080 cast-o-matic:latest
```

Kubernetes:

```bash
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
kubectl get pods
kubectl get services
```

## Testing

Run:

```bash
python -m unittest discover -s tests -v
```

The automated tests cover:

- Home, sender and receiver routes
- Offline mode route
- Network information endpoint
- Room validation
- File upload
- File retrieval
- Presentation update signaling
- Multiple receiver signaling
- Filename sanitization

Browser testing should additionally cover:

- QR scanner camera permission
- Receiver on Android/iOS
- Receiver on laptop
- Smart-TV browser where available
- Live screen sharing
- File display
- Full-screen receiver
- Same-Wi-Fi LAN mode
- Public HTTPS deployment

## Project structure

```text
cast-o-matic/
├── app.py
├── guard.py
├── requirements.txt
├── Dockerfile
├── Jenkinsfile
├── deployment.yaml
├── service.yaml
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
    ├── test_guard.py
    └── test_app.py
```

## Important production notes

- The upload directory is local storage. Files are not a permanent database.
- A 50 MB upload limit is enforced.
- WebRTC connectivity depends on the network and browser.
- HTTPS is recommended for public deployment and browser media permissions.
- Do not expose sensitive classroom files publicly without authentication.
- For a high-reliability production system, add authentication, persistent storage, TURN, rate limiting and monitoring.
