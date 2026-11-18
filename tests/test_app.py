import io
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import app as app_module


class TestCastOMaticApp(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

        self.old_upload = app_module.UPLOAD_FOLDER

        app_module.UPLOAD_FOLDER = self.tmp.name
        app_module.app.config["UPLOAD_FOLDER"] = self.tmp.name

        app_module.current_presentations.clear()
        app_module.rooms.clear()
        app_module.sid_info.clear()

        self.client = app_module.app.test_client()

    def tearDown(self):
        app_module.current_presentations.clear()
        app_module.rooms.clear()
        app_module.sid_info.clear()

        app_module.UPLOAD_FOLDER = self.old_upload
        app_module.app.config["UPLOAD_FOLDER"] = self.old_upload

        try:
            for name in os.listdir(self.tmp.name):
                path = os.path.join(self.tmp.name, name)

                if os.path.isfile(path):
                    try:
                        os.remove(path)
                    except PermissionError:
                        pass
        finally:
            self.tmp.cleanup()

    def test_pages_and_network_info(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        self.assertEqual(self.client.get("/sender").status_code, 200)
        self.assertEqual(
            self.client.get("/sender?mode=offline").status_code,
            200,
        )
        self.assertEqual(
            self.client.get("/receiver?room=ABC123").status_code,
            200,
        )
        self.assertEqual(
            self.client.get("/network-info").status_code,
            200,
        )

    def test_room_validation(self):
        response = self.client.post(
            "/upload",
            data={"room": "../../"},
        )

        self.assertEqual(response.status_code, 400)

    def test_upload_and_receiver_gets_presentation(self):
        room = "ABC123"

        sender = app_module.socketio.test_client(app_module.app)
        receiver = app_module.socketio.test_client(app_module.app)

        sender.emit(
            "join",
            {
                "room": room,
                "role": "sender",
            },
        )

        receiver.emit(
            "join",
            {
                "room": room,
                "role": "receiver",
            },
        )

        sender.get_received()
        receiver.get_received()

        response = self.client.post(
            "/upload",
            data={
                "room": room,
                "file": (
                    io.BytesIO(b"%PDF-test"),
                    "demo.pdf",
                ),
            },
            content_type="multipart/form-data",
        )

        self.assertEqual(response.status_code, 200)

        payload = response.get_json()

        self.assertTrue(payload["success"])
        self.assertEqual(payload["kind"], "pdf")

        events = receiver.get_received()

        self.assertTrue(
            any(
                event["name"] == "presentation_update"
                for event in events
            )
        )

        file_response = self.client.get(
            "/uploads/" + payload["filename"],
            buffered=True,
        )

        self.assertEqual(file_response.status_code, 200)
        self.assertEqual(file_response.data, b"%PDF-test")

        file_response.close()

        sender.disconnect()
        receiver.disconnect()

    def test_multiple_receivers_receive_targeted_signaling(self):
        room = "ZXCV12"

        sender = app_module.socketio.test_client(app_module.app)
        receiver_a = app_module.socketio.test_client(app_module.app)
        receiver_b = app_module.socketio.test_client(app_module.app)

        sender.emit(
            "join",
            {
                "room": room,
                "role": "sender",
            },
        )

        receiver_a.emit(
            "join",
            {
                "room": room,
                "role": "receiver",
            },
        )

        receiver_b.emit(
            "join",
            {
                "room": room,
                "role": "receiver",
            },
        )

        sender_events = sender.get_received()

        ready = [
            event
            for event in sender_events
            if event["name"] == "receiver_ready"
        ]

        self.assertEqual(len(ready), 2)

        receiver_ids = {
            event["args"][0]["receiver_id"]
            for event in ready
        }

        self.assertEqual(len(receiver_ids), 2)

        offer = {
            "type": "offer",
            "sdp": "demo-sdp",
        }

        target = next(iter(receiver_ids))

        sender.emit(
            "offer",
            {
                "room": room,
                "target": target,
                "offer": offer,
            },
        )

        a_events = receiver_a.get_received()
        b_events = receiver_b.get_received()

        delivered = [
            event
            for event in a_events + b_events
            if event["name"] == "offer"
        ]

        self.assertEqual(len(delivered), 1)

        self.assertEqual(
            delivered[0]["args"][0]["offer"],
            offer,
        )

        sender.disconnect()
        receiver_a.disconnect()
        receiver_b.disconnect()


if __name__ == "__main__":
    unittest.main()