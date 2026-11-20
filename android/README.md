# Cast-O-Matic Native Android

This is the native Android companion for the existing Cast-O-Matic Flask/WebRTC application.

## What this build adds

- Native Android application shell
- Bluetooth Low Energy nearby-device discovery
- Cast-O-Matic service UUID filtering
- Android Nearby Devices permission handling
- Local WebView access to the existing Cast-O-Matic web application
- One-tap Receiver / Projector mode
- Same web/WebRTC presentation flow preserved
- Architecture ready for Wi-Fi Direct and native peer-to-peer transfer

## Important architecture

Bluetooth is used for discovery and pairing signals, not for high-bandwidth presentation video.

High-bandwidth transport should use:
- Wi-Fi Direct / local Wi-Fi
- WebRTC
- native socket transfer where appropriate

This avoids pretending Bluetooth can efficiently carry live screen video.

## Build

Open this folder in Android Studio.

Let Gradle sync.

Run on an Android phone with Bluetooth enabled.

For a local college demo, set the web URL in `app/build.gradle.kts` to the laptop LAN address:

http://YOUR-LAPTOP-IP:5080

The phone and laptop must be on the same Wi-Fi network for the existing web receiver/signaling path.

## Native roadmap

The project is intentionally split into layers:

1. BLE discovery
2. Wi-Fi Direct connection
3. Secure device consent
4. Native P2P file transfer
5. WebRTC screen/media transport
6. Projector/display receiver mode
7. Presentation remote
8. Optional native receiver device

The existing Flask/WebRTC application remains the compatibility layer and fallback.

## Claims for demonstration

Say:

"Cast-O-Matic combines browser compatibility with native nearby-device discovery. Bluetooth is used for discovery and Wi-Fi/WebRTC is used for high-speed presentation and transfer."

Do not claim:
- native Google Quick Share protocol
- universal Bluetooth video streaming
- universal control of every Epson/BenQ/ViewSonic/Optoma model
- Miracast/AirPlay/Chromecast support unless a specific implementation is actually added.
