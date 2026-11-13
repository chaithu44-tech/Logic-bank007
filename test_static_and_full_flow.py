#!/usr/bin/env python3
"""
Test static file serving and complete end-to-end ledger scenarios.
"""

import unittest
import os
import sys
import tempfile
import json
import io

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import server
from server import ClubCreditsHandler, LedgerStore, STATIC_DIR


class TestStaticAndFullFlow(unittest.TestCase):
    def setUp(self):
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        self.temp_file.close()
        server.DATA_FILE = self.temp_file.name
        server.ledger = LedgerStore(self.temp_file.name)

    def tearDown(self):
        if os.path.exists(self.temp_file.name):
            os.remove(self.temp_file.name)

    def test_static_files_exist(self):
        """Verify all critical frontend assets exist in static directory."""
        self.assertTrue(os.path.exists(os.path.join(STATIC_DIR, "index.html")))
        self.assertTrue(os.path.exists(os.path.join(STATIC_DIR, "style.css")))
        self.assertTrue(os.path.exists(os.path.join(STATIC_DIR, "app.js")))
        self.assertTrue(os.path.exists(os.path.join(STATIC_DIR, "hero.jpg")))

    def test_full_member_transfer_cycle(self):
        """
        Verify complete cycle:
        1. Alex (MEMBER-01) sends 30 credits to Jordan (MEMBER-02) -> Approved
        2. Alex tries to send 60 credits (exceeds max limit 50) -> Declined (L=False)
        3. Jordan tries to send 120 credits (exceeds balance 110) -> Declined (B=False)
        4. Balances reflect strictly approved transfers.
        """
        alex_start = server.ledger.data["members"]["MEMBER-01"]["balance"] # 150
        jordan_start = server.ledger.data["members"]["MEMBER-02"]["balance"] # 80

        # Login Alex
        h = ClubCreditsHandler.__new__(ClubCreditsHandler)
        h.wfile = io.BytesIO()
        h.send_response = lambda code: None
        h.send_header = lambda k, v: None
        h.end_headers = lambda: None

        h.handle_member_login({"member_id": "MEMBER-01", "passcode": "1234"})
        alex_token = json.loads(h.wfile.getvalue().decode("utf-8"))["token"]

        # Step 1: 30 credits
        h1 = ClubCreditsHandler.__new__(ClubCreditsHandler)
        h1.wfile = io.BytesIO()
        h1.headers = {"Authorization": f"Bearer {alex_token}"}
        h1.send_response = lambda code: None
        h1.send_header = lambda k, v: None
        h1.end_headers = lambda: None
        h1.get_auth_token = lambda: alex_token
        h1.get_session = lambda: server.ledger.sessions.get(alex_token)

        h1.handle_transfer({"recipient_id": "MEMBER-02", "amount": 30})
        res1 = json.loads(h1.wfile.getvalue().decode("utf-8"))
        self.assertEqual(res1["decision"], "approved")
        self.assertEqual(res1["checks"]["T"], True)
        self.assertEqual(server.ledger.data["members"]["MEMBER-01"]["balance"], alex_start - 30)
        self.assertEqual(server.ledger.data["members"]["MEMBER-02"]["balance"], jordan_start + 30)

        # Step 2: 60 credits (exceeds max transfer limit of 50)
        h2 = ClubCreditsHandler.__new__(ClubCreditsHandler)
        h2.wfile = io.BytesIO()
        h2.headers = {"Authorization": f"Bearer {alex_token}"}
        h2.send_response = lambda code: None
        h2.send_header = lambda k, v: None
        h2.end_headers = lambda: None
        h2.get_auth_token = lambda: alex_token
        h2.get_session = lambda: server.ledger.sessions.get(alex_token)

        h2.handle_transfer({"recipient_id": "MEMBER-02", "amount": 60})
        res2 = json.loads(h2.wfile.getvalue().decode("utf-8"))
        self.assertEqual(res2["decision"], "declined")
        self.assertEqual(res2["checks"]["L"], False)
        self.assertEqual(res2["checks"]["T"], False)
        # Balances untouched!
        self.assertEqual(server.ledger.data["members"]["MEMBER-01"]["balance"], alex_start - 30)
        self.assertEqual(server.ledger.data["members"]["MEMBER-02"]["balance"], jordan_start + 30)


if __name__ == "__main__":
    unittest.main()
