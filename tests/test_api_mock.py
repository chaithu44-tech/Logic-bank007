#!/usr/bin/env python3
"""
In-process Mock Tests for ClubCredits HTTP Request Handlers.
Runs without opening TCP sockets to remain 100% compatible with sandboxed execution.
"""

import unittest
import os
import sys
import tempfile
import json
import io

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import server
from server import ClubCreditsHandler, LedgerStore, default_database


class MockRequest:
    def makefile(self, *args, **kwargs):
        return io.BytesIO(b"")


class TestClubCreditsHandlers(unittest.TestCase):
    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        self.temp_file.close()

        # Isolate database
        server.DATA_FILE = self.temp_file.name
        server.ledger = LedgerStore(self.temp_file.name)

    def tearDown(self):
        if os.path.exists(self.temp_file.name):
            os.remove(self.temp_file.name)

    def create_handler(self, method="GET", path="/", body=None, headers=None):
        if headers is None:
            headers = {}
        body_bytes = json.dumps(body).encode("utf-8") if body is not None else b""
        headers["Content-Length"] = str(len(body_bytes))

        # Build raw HTTP request buffer
        header_lines = [f"{method} {path} HTTP/1.1"]
        for k, v in headers.items():
            header_lines.append(f"{k}: {v}")
        header_lines.append("")
        header_lines.append("")
        raw_request = "\r\n".join(header_lines).encode("utf-8") + body_bytes

        handler = ClubCreditsHandler.__new__(ClubCreditsHandler)
        handler.rfile = io.BytesIO(raw_request)
        handler.wfile = io.BytesIO()
        handler.client_address = ("127.0.0.1", 12345)
        handler.headers = headers
        handler.path = path
        handler.command = method
        handler.requestline = f"{method} {path} HTTP/1.1"

        # Mock send_response, send_header, end_headers
        handler.response_status = None
        handler.response_headers = {}

        def mock_send_response(code, message=None):
            handler.response_status = code

        def mock_send_header(keyword, value):
            handler.response_headers[keyword] = value

        def mock_end_headers():
            pass

        handler.send_response = mock_send_response
        handler.send_header = mock_send_header
        handler.end_headers = mock_end_headers

        return handler

    def get_json_response(self, handler):
        raw = handler.wfile.getvalue().decode("utf-8")
        return json.loads(raw) if raw else {}

    def test_member_login_success(self):
        handler = self.create_handler("POST", "/api/auth/member-login", {
            "member_id": "MEMBER-01",
            "passcode": "1234"
        })
        handler.handle_member_login({"member_id": "MEMBER-01", "passcode": "1234"})
        self.assertEqual(handler.response_status, 200)
        data = self.get_json_response(handler)
        self.assertIn("token", data)
        self.assertEqual(data["user"]["name"], "Alex Rivera")
        self.assertEqual(data["user"]["id"], "MEMBER-01")

    def test_member_login_invalid_credentials(self):
        handler = self.create_handler("POST", "/api/auth/member-login")
        handler.handle_member_login({"member_id": "MEMBER-01", "passcode": "wrong"})
        self.assertEqual(handler.response_status, 401)
        data = self.get_json_response(handler)
        self.assertIn("error", data)

    def test_transfer_execution_and_reasoning(self):
        # 1. Login to get token
        login_h = self.create_handler("POST", "/api/auth/member-login")
        login_h.handle_member_login({"member_id": "MEMBER-01", "passcode": "1234"})
        token = self.get_json_response(login_h)["token"]

        # 2. Approved transfer (Alex sends 20 credits to Jordan)
        transfer_h = self.create_handler("POST", "/api/transfer", headers={"Authorization": f"Bearer {token}"})
        transfer_h.handle_transfer({"recipient_id": "MEMBER-02", "amount": 20})
        self.assertEqual(transfer_h.response_status, 200)
        res = self.get_json_response(transfer_h)
        self.assertEqual(res["decision"], "approved")
        self.assertEqual(res["checks"]["A"], True)
        self.assertEqual(res["checks"]["B"], True)
        self.assertEqual(res["checks"]["L"], True)
        self.assertEqual(res["checks"]["D"], True)
        self.assertEqual(res["checks"]["T"], True)
        self.assertEqual(res["sender_balance"], 130)  # 150 - 20

        # Verify Jordan Chen balance increased
        self.assertEqual(server.ledger.data["members"]["MEMBER-02"]["balance"], 100)  # 80 + 20

    def test_transfer_declined_exceeds_max_limit(self):
        login_h = self.create_handler("POST", "/api/auth/member-login")
        login_h.handle_member_login({"member_id": "MEMBER-01", "passcode": "1234"})
        token = self.get_json_response(login_h)["token"]

        transfer_h = self.create_handler("POST", "/api/transfer", headers={"Authorization": f"Bearer {token}"})
        # max_transfer limit is 50, trying to send 55
        transfer_h.handle_transfer({"recipient_id": "MEMBER-02", "amount": 55})
        self.assertEqual(transfer_h.response_status, 200)
        res = self.get_json_response(transfer_h)
        self.assertEqual(res["decision"], "declined")
        self.assertEqual(res["checks"]["A"], True)
        self.assertEqual(res["checks"]["B"], True)
        self.assertEqual(res["checks"]["L"], False)  # Failed L!
        self.assertEqual(res["checks"]["T"], False)

        # Confirm balances unchanged
        self.assertEqual(server.ledger.data["members"]["MEMBER-01"]["balance"], 150)
        self.assertEqual(server.ledger.data["members"]["MEMBER-02"]["balance"], 80)

    def test_transfer_unauthenticated(self):
        transfer_h = self.create_handler("POST", "/api/transfer")
        transfer_h.handle_transfer({"recipient_id": "MEMBER-02", "amount": 10})
        self.assertEqual(transfer_h.response_status, 401)
        res = self.get_json_response(transfer_h)
        self.assertEqual(res["decision"], "declined")
        self.assertEqual(res["checks"]["A"], False)
        self.assertEqual(res["checks"]["T"], False)

    def test_admin_set_limits_and_add_member(self):
        # Admin login
        admin_login_h = self.create_handler("POST", "/api/auth/admin-login")
        admin_login_h.handle_admin_login({"passcode": "adminpass"})
        self.assertEqual(admin_login_h.response_status, 200)
        admin_token = self.get_json_response(admin_login_h)["token"]

        # Set limits
        limits_h = self.create_handler("POST", "/api/admin/set-limits", headers={"Authorization": f"Bearer {admin_token}"})
        limits_h.handle_admin_set_limits({"max_transfer": 40, "daily_limit": 80})
        self.assertEqual(limits_h.response_status, 200)
        res_limits = self.get_json_response(limits_h)
        self.assertEqual(res_limits["limits"]["max_transfer"], 40)
        self.assertEqual(res_limits["limits"]["daily_limit"], 80)

        # Add member
        add_h = self.create_handler("POST", "/api/admin/add-member", headers={"Authorization": f"Bearer {admin_token}"})
        add_h.handle_admin_add_member({
            "member_id": "MEMBER-999",
            "name": "Rowan Vance",
            "role": "Robotics Programmer",
            "passcode": "7777",
            "balance": 120
        })
        self.assertEqual(add_h.response_status, 200)
        res_add = self.get_json_response(add_h)
        self.assertEqual(res_add["member"]["id"], "MEMBER-999")
        self.assertIn("MEMBER-999", server.ledger.data["members"])


if __name__ == "__main__":
    unittest.main()
