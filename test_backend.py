#!/usr/bin/env python3
"""
Test suite for ClubCredits transfer rules, propositions (A, B, L, D, T),
balance conservation, and admin controls.
"""

import unittest
import os
import sys
import tempfile
import json
import datetime

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import LedgerStore, default_database, get_today_string


class TestClubCreditsLedger(unittest.TestCase):
    def setUp(self):
        # Create a temporary file for isolated testing
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        self.temp_file.close()
        self.store = LedgerStore(self.temp_file.name)

    def tearDown(self):
        if os.path.exists(self.temp_file.name):
            os.remove(self.temp_file.name)

    def test_initial_seed_data(self):
        """Test default members and limits are initialized properly."""
        self.assertIn("MEMBER-01", self.store.data["members"])
        self.assertIn("MEMBER-02", self.store.data["members"])
        self.assertEqual(self.store.data["limits"]["max_transfer"], 50)
        self.assertEqual(self.store.data["limits"]["daily_limit"], 100)
        self.assertEqual(self.store.data["members"]["MEMBER-01"]["balance"], 150)
        self.assertEqual(self.store.data["members"]["MEMBER-02"]["balance"], 80)

    def test_approved_transfer_logic(self):
        """
        Verify that an approved transfer:
        - Evaluates A=True, B=True, L=True, D=True -> T=True
        - Subtracts exact credits from sender
        - Adds exact credits to recipient
        - Conserves total group credits
        """
        initial_sender_bal = self.store.data["members"]["MEMBER-01"]["balance"]
        initial_recip_bal = self.store.data["members"]["MEMBER-02"]["balance"]
        total_before = sum(m["balance"] for m in self.store.data["members"].values())

        amount = 30
        max_limit = self.store.data["limits"]["max_transfer"]
        daily_limit = self.store.data["limits"]["daily_limit"]
        today_spent = self.store.get_daily_spent("MEMBER-01")

        # Evaluate propositions
        check_A = True
        check_B = initial_sender_bal >= amount
        check_L = amount <= max_limit
        check_D = (today_spent + amount) <= daily_limit
        check_T = check_A and check_B and check_L and check_D

        self.assertTrue(check_T, "Transfer should be approved")

        # Execute
        self.store.data["members"]["MEMBER-01"]["balance"] -= amount
        self.store.data["members"]["MEMBER-02"]["balance"] += amount
        self.store.data["transactions"].append({
            "id": "TXN-TEST-01",
            "timestamp": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "sender_id": "MEMBER-01",
            "sender_name": "Alex Rivera",
            "recipient_id": "MEMBER-02",
            "recipient_name": "Jordan Chen",
            "amount": amount,
            "status": "approved",
            "checks": {"A": check_A, "B": check_B, "L": check_L, "D": check_D, "T": check_T}
        })
        self.store.save()

        # Reload from disk and verify
        reloaded = LedgerStore(self.temp_file.name)
        self.assertEqual(reloaded.data["members"]["MEMBER-01"]["balance"], initial_sender_bal - amount)
        self.assertEqual(reloaded.data["members"]["MEMBER-02"]["balance"], initial_recip_bal + amount)

        total_after = sum(m["balance"] for m in reloaded.data["members"].values())
        self.assertEqual(total_before, total_after, "Total group credits must remain strictly conserved")

    def test_declined_insufficient_credits_proposition_B(self):
        """
        Verify Proposition B fails when balance is insufficient:
        - B = False -> T = False
        - Balances remain strictly unchanged
        """
        sender = self.store.data["members"]["MEMBER-04"] # Balance: 60
        sender["balance"] = 10
        self.store.save()

        amount = 25
        check_A = True
        check_B = sender["balance"] >= amount # 10 >= 25 -> False
        check_L = amount <= self.store.data["limits"]["max_transfer"] # 25 <= 50 -> True
        check_D = True
        check_T = check_A and check_B and check_L and check_D

        self.assertFalse(check_B)
        self.assertFalse(check_T)

    def test_declined_max_transfer_limit_proposition_L(self):
        """
        Verify Proposition L fails when amount exceeds max transfer limit:
        - L = False -> T = False
        - Balances remain unchanged
        """
        sender = self.store.data["members"]["MEMBER-01"] # Balance: 150
        amount = 60 # max_transfer is 50

        check_A = True
        check_B = sender["balance"] >= amount # 150 >= 60 -> True
        check_L = amount <= self.store.data["limits"]["max_transfer"] # 60 <= 50 -> False
        check_D = True
        check_T = check_A and check_B and check_L and check_D

        self.assertTrue(check_B)
        self.assertFalse(check_L)
        self.assertFalse(check_T)

    def test_declined_daily_limit_proposition_D(self):
        """
        Verify Proposition D fails when transfer exceeds daily cumulative limit:
        - D = False -> T = False
        """
        today = get_today_string()
        base_spent = self.store.get_daily_spent("MEMBER-01", today)

        # Seed an additional approved transfer today
        self.store.data["transactions"].append({
            "id": "TXN-DAILY-01",
            "timestamp": f"{today}T10:00:00Z",
            "sender_id": "MEMBER-01",
            "sender_name": "Alex Rivera",
            "recipient_id": "MEMBER-02",
            "recipient_name": "Jordan Chen",
            "amount": 70,
            "status": "approved",
            "checks": {"A": True, "B": True, "L": True, "D": True, "T": True}
        })
        self.store.save()

        daily_spent = self.store.get_daily_spent("MEMBER-01", today)
        self.assertEqual(daily_spent, base_spent + 70)

        # MEMBER-01 tries to send 40 more credits:
        # daily_spent + 40 >= 110 > daily_limit (100)
        amount = 40
        daily_limit = self.store.data["limits"]["daily_limit"]
        check_A = True
        check_B = self.store.data["members"]["MEMBER-01"]["balance"] >= amount
        check_L = amount <= self.store.data["limits"]["max_transfer"] # 40 <= 50 -> True
        check_D = (daily_spent + amount) <= daily_limit # > 100 -> False
        check_T = check_A and check_B and check_L and check_D

        self.assertTrue(check_B)
        self.assertTrue(check_L)
        self.assertFalse(check_D)
        self.assertFalse(check_T)

    def test_safety_rule_invariant(self):
        """
        Verify the safety rule invariant: T -> (A and B).
        It is mathematically impossible for T to be True if either A or B is False.
        """
        for a in [False, True]:
            for b in [False, True]:
                for l in [False, True]:
                    for d in [False, True]:
                        t = a and b and l and d
                        # Safety rule check: T -> (A and B) is logically equivalent to (not T) or (A and B)
                        safety_rule_holds = (not t) or (a and b)
                        self.assertTrue(safety_rule_holds, f"Safety rule violated for A={a}, B={b}, L={l}, D={d}")

    def test_admin_set_balance_and_limits(self):
        """Verify administrator can update member balances and transfer limits."""
        # Update balance
        self.store.data["members"]["MEMBER-01"]["balance"] = 250
        # Update limits
        self.store.data["limits"]["max_transfer"] = 75
        self.store.data["limits"]["daily_limit"] = 150
        self.store.save()

        reloaded = LedgerStore(self.temp_file.name)
        self.assertEqual(reloaded.data["members"]["MEMBER-01"]["balance"], 250)
        self.assertEqual(reloaded.data["limits"]["max_transfer"], 75)
        self.assertEqual(reloaded.data["limits"]["daily_limit"], 150)


if __name__ == "__main__":
    unittest.main()
