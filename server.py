#!/usr/bin/env python3
"""
ClubCredits - Live Group Credit Website
A private group-credit ledger for fictional club credits with visible transfer reasoning.

This is NOT a bank. Credits have no cash value and cannot be deposited,
withdrawn, redeemed, or exchanged for real money.
"""

import sys
import os
import json
import uuid
import time
import datetime
import threading
import queue
from http import HTTPStatus
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import urllib.parse

# Configuration
PORT = int(os.environ.get("PORT", 8080))
HOST = os.environ.get("HOST", "127.0.0.1")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DATA_FILE = os.path.join(DATA_DIR, "clubcredits.json")
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Thread safety lock for ledger operations
ledger_lock = threading.Lock()

# SSE clients tracking
sse_subscribers = []
sse_lock = threading.Lock()


def get_today_string():
    """Return current date in YYYY-MM-DD UTC for deterministic daily limits."""
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")


def generate_default_members():
    first_names = [
        'Alex', 'Jordan', 'Taylor', 'Morgan', 'Casey', 'Riley', 'Samira', 'Liam', 'Maya', 'Marcus',
        'Chloe', 'Lucas', 'Sofia', 'Ethan', 'Zoe', 'Noah', 'Priya', 'Julian', 'Aria', 'Leo',
        'Amara', 'Devon', 'Elena', 'Gabriel', 'Hannah', 'Isaac', 'Jasmine', 'Kai', 'Leila', 'Miles',
        'Nadia', 'Oliver', 'Penelope', 'Quinn', 'Rafael', 'Sienna', 'Tristan', 'Uma', 'Victor', 'Willow',
        'Xavier', 'Yasmine', 'Zachary', 'Ava', 'Benjamin', 'Camila', 'Daniel', 'Fatima', 'George', 'Hailey'
    ]
    last_names = [
        'Rivera', 'Chen', 'Kim', 'Smith', 'Patel', 'O\'Connor', 'Lin', 'Vance', 'Bennett', 'Tanaka',
        'Rodriguez', 'Walker', 'Martinez', 'Washington', 'Sharma', 'Brooks', 'Dubois', 'Sterling', 'Zhao', 'Alvarez',
        'Johansson', 'Nakamura', 'Gupta', 'Morales', 'Sinclair', 'Kowalski', 'Haddad', 'Novak', 'Thornton', 'Mercer',
        'Castillo', 'Abebe', 'Fischer', 'Fontaine', 'Okafor', 'Santos', 'Reyes', 'Lindqvist', 'Popov', 'Moreau'
    ]
    roles = [
        'Robotics Club Lead', 'Event Coordinator', 'Design Lead', 'Science Olympiad Captain',
        'Debate Team Captain', 'Chess Club President', 'Eco Club Organizer', 'Theater Tech Director',
        'Coding Club Mentor', 'Quiz Bowl Specialist', 'Photography Lead', 'Campus Radio DJ',
        'Math Olympiad Competitor', 'Science Fair Coordinator', 'Astronomy Club Scout', 'Hackathon Lead',
        'Journalism Editor', 'Art Studio Host', 'Model UN Delegate', 'Peer Tutoring Liaison',
        'Maker Space Safety Lead', 'Cybersecurity Analyst', 'Esports Captain', 'Music Ensemble Lead',
        'Community Outreach Officer', 'Volunteer Coordinator', 'Rocketry Engineer', 'AI Club Researcher'
    ]

    members = {
        "MEMBER-01": {
            "id": "MEMBER-01",
            "name": "Alex Rivera",
            "role": "Robotics Club Lead",
            "passcode": "1234",
            "balance": 150,
            "created_at": "2026-11-01T10:00:00Z"
        },
        "MEMBER-02": {
            "id": "MEMBER-02",
            "name": "Jordan Chen",
            "role": "Event Coordinator",
            "passcode": "2468",
            "balance": 80,
            "created_at": "2026-11-01T10:15:00Z"
        },
        "MEMBER-03": {
            "id": "MEMBER-03",
            "name": "Taylor Kim",
            "role": "Design Lead",
            "passcode": "1357",
            "balance": 95,
            "created_at": "2026-11-02T09:30:00Z"
        },
        "MEMBER-04": {
            "id": "MEMBER-04",
            "name": "Morgan Smith",
            "role": "Science Olympiad Captain",
            "passcode": "9876",
            "balance": 60,
            "created_at": "2026-11-03T14:20:00Z"
        }
    }

    count = 4
    for fn in first_names:
        for ln in last_names:
            if count >= 120:
                break
            full_name = f"{fn} {ln}"
            if any(m["name"] == full_name for m in members.values()):
                continue
            count += 1
            m_id = f"MEMBER-{count:02d}" if count < 100 else f"MEMBER-{count}"
            role = roles[count % len(roles)]
            passcode = f"{1000 + count}"
            balance = 30 + ((count * 17) % 180)
            members[m_id] = {
                "id": m_id,
                "name": full_name,
                "role": role,
                "passcode": passcode,
                "balance": balance,
                "created_at": f"2026-11-0{min(9, 1 + count % 8)}T12:00:00Z"
            }
        if count >= 120:
            break
    return members


def generate_default_transactions(members, limits, today):
    member_ids = sorted(list(members.keys()))
    balances = {m_id: members[m_id]["balance"] for m_id in members}
    daily_spent = {m_id: 0 for m_id in members}

    reasons_approved = [
        "Peer recognition for leading the club workshop.",
        "Transfer approved under active group policy.",
        "Shared tokens for 3D printing supplies and filament.",
        "Thank you for designing the club showcase banners!",
        "Shared token reward for Science Fair booth setup.",
        "Code review assistance and hackathon mentoring recognition.",
        "Reimbursement for campus club fair stickers and badges.",
        "Chess tournament participation reward tokens.",
        "Eco club campus clean-up volunteer tokens.",
        "Debate tournament prep peer coaching tokens.",
        "Math study session organizing recognition.",
        "Theater soundboard equipment setup assistance.",
        "Campus radio podcast editing token reward.",
        "Astronomy club stargazing night logistics tokens.",
        "Model UN draft resolution peer collaboration."
    ]

    txns = []
    txn_id_counter = 1

    # Canonical historical transfer: MEMBER-01 -> MEMBER-02 (25 credits)
    amt1 = 25
    balances["MEMBER-01"] -= amt1
    balances["MEMBER-02"] += amt1
    daily_spent["MEMBER-01"] += amt1
    txns.append({
        "id": "TXN-0001",
        "timestamp": f"{today}T09:15:22Z",
        "sender_id": "MEMBER-01",
        "sender_name": members["MEMBER-01"]["name"],
        "recipient_id": "MEMBER-02",
        "recipient_name": members["MEMBER-02"]["name"],
        "amount": amt1,
        "status": "approved",
        "reason": "Transfer approved under active group policy.",
        "checks": {"A": True, "B": True, "L": True, "D": True, "T": True}
    })
    txn_id_counter += 1

    # Canonical declined transfer: MEMBER-02 -> MEMBER-03 (75 credits > 50)
    txns.append({
        "id": "TXN-0002",
        "timestamp": f"{today}T10:45:00Z",
        "sender_id": "MEMBER-02",
        "sender_name": members["MEMBER-02"]["name"],
        "recipient_id": "MEMBER-03",
        "recipient_name": members["MEMBER-03"]["name"],
        "amount": 75,
        "status": "declined",
        "reason": f"The transfer amount (75 credits) exceeds the single transfer limit ({limits['max_transfer']} credits).",
        "checks": {"A": True, "B": True, "L": False, "D": True, "T": False}
    })
    txn_id_counter += 1

    # Balance neutrality for MEMBER-01 & MEMBER-02 (maintains 150 & 80 baseline)
    balances["MEMBER-02"] -= 25
    balances["MEMBER-01"] += 25
    txns.append({
        "id": "TXN-0003",
        "timestamp": "2026-11-12T16:30:00Z",
        "sender_id": "MEMBER-02",
        "sender_name": members["MEMBER-02"]["name"],
        "recipient_id": "MEMBER-01",
        "recipient_name": members["MEMBER-01"]["name"],
        "amount": 25,
        "status": "approved",
        "reason": "Robotics workshop parts kit shared return.",
        "checks": {"A": True, "B": True, "L": True, "D": True, "T": True}
    })
    txn_id_counter += 1

    # Systematic circular transfers across all members (MEMBER-03 through MEMBER-120)
    for i in range(2, len(member_ids)):
        sender_id = member_ids[i]
        recip_id = member_ids[(i + 1) % len(member_ids)]
        if recip_id in ("MEMBER-01", "MEMBER-02"):
            recip_id = "MEMBER-03"

        amount = 8 + (i % 14)
        if balances[sender_id] > amount + 20 and (daily_spent[sender_id] + amount) <= limits["daily_limit"]:
            balances[sender_id] -= amount
            balances[recip_id] += amount
            daily_spent[sender_id] += amount
            status = "approved"
            reason = reasons_approved[i % len(reasons_approved)]
            checks = {"A": True, "B": True, "L": True, "D": True, "T": True}
        else:
            status = "declined"
            reason = f"Insufficient credits: transfer requires {amount} credits."
            checks = {"A": True, "B": False, "L": True, "D": True, "T": False}

        h = 8 + (i % 10)
        m = (i * 7) % 60
        s = (i * 13) % 60
        day_str = "2026-11-12" if i < 60 else today
        txns.append({
            "id": f"TXN-{txn_id_counter:04d}",
            "timestamp": f"{day_str}T{h:02d}:{m:02d}:{s:02d}Z",
            "sender_id": sender_id,
            "sender_name": members[sender_id]["name"],
            "recipient_id": recip_id,
            "recipient_name": members[recip_id]["name"],
            "amount": amount,
            "status": status,
            "reason": reason,
            "checks": checks
        })
        txn_id_counter += 1

    # Diverse secondary transfers and realistic policy edge cases
    for j in range(60):
        sender_idx = (j * 7 + 2) % len(member_ids)
        recip_idx = (j * 11 + 5) % len(member_ids)
        sender_id = member_ids[sender_idx]
        recip_id = member_ids[recip_idx]
        if sender_id == recip_id:
            recip_id = member_ids[(recip_idx + 1) % len(member_ids)]

        if sender_id in ("MEMBER-01", "MEMBER-02") or recip_id in ("MEMBER-01", "MEMBER-02"):
            continue

        if j % 6 == 0:
            amount = 60 + (j % 15)
            status = "declined"
            reason = f"The transfer amount ({amount} credits) exceeds the single transfer limit ({limits['max_transfer']} credits)."
            checks = {"A": True, "B": balances[sender_id] >= amount, "L": False, "D": True, "T": False}
        elif j % 6 == 1:
            amount = 35
            status = "declined"
            reason = f"The daily credit limit would be exceeded: sending {amount} credits would exceed the daily limit of {limits['daily_limit']} credits."
            checks = {"A": True, "B": True, "L": True, "D": False, "T": False}
        else:
            amount = 6 + (j % 16)
            if balances[sender_id] > amount + 15 and (daily_spent[sender_id] + amount) <= limits["daily_limit"]:
                balances[sender_id] -= amount
                balances[recip_id] += amount
                daily_spent[sender_id] += amount
                status = "approved"
                reason = reasons_approved[(j + 3) % len(reasons_approved)]
                checks = {"A": True, "B": True, "L": True, "D": True, "T": True}
            else:
                status = "declined"
                reason = f"Insufficient credits: transfer requires {amount} credits."
                checks = {"A": True, "B": False, "L": True, "D": True, "T": False}

        h = 11 + (j % 6)
        m = (j * 9) % 60
        s = (j * 19) % 60
        txns.append({
            "id": f"TXN-{txn_id_counter:04d}",
            "timestamp": f"{today}T{h:02d}:{m:02d}:{s:02d}Z",
            "sender_id": sender_id,
            "sender_name": members[sender_id]["name"],
            "recipient_id": recip_id,
            "recipient_name": members[recip_id]["name"],
            "amount": amount,
            "status": status,
            "reason": reason,
            "checks": checks
        })
        txn_id_counter += 1

    # Update member balances
    for m_id, b in balances.items():
        members[m_id]["balance"] = b

    return txns


def default_database():
    """Create initial seed data for local demo."""
    today = get_today_string()
    limits = {
        "max_transfer": 50,    # L: Maximum credits per single transfer
        "daily_limit": 100     # D: Daily credit transfer limit per member
    }
    members = generate_default_members()
    transactions = generate_default_transactions(members, limits, today)
    return {
        "admin": {
            "passcode": os.environ.get("CLUBCREDITS_ADMIN_PASS", "adminpass")
        },
        "limits": limits,
        "members": members,
        "transactions": transactions
    }


class LedgerStore:
    def __init__(self, filepath):
        self.filepath = filepath
        self.data = {}
        self.sessions = {}  # token -> session dict
        self.load()

    def load(self):
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        if not os.path.exists(self.filepath) or os.path.getsize(self.filepath) == 0:
            self.data = default_database()
            self.save()
        else:
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception as e:
                print(f"[LedgerStore] Error loading {self.filepath}: {e}, using defaults.")
                self.data = default_database()
                self.save()

    def save(self):
        try:
            tmp_file = self.filepath + ".tmp"
            with open(tmp_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
            os.replace(tmp_file, self.filepath)
        except Exception as e:
            print(f"[LedgerStore] Error saving {self.filepath}: {e}")

    def get_daily_spent(self, member_id, date_str=None):
        """Calculate total approved credits spent by member today."""
        if not date_str:
            date_str = get_today_string()
        total = 0
        for txn in self.data.get("transactions", []):
            if (txn.get("sender_id") == member_id and
                txn.get("status") == "approved" and
                txn.get("timestamp", "").startswith(date_str)):
                total += txn.get("amount", 0)
        return total

    def sanitize_member(self, member, include_private=False, current_member_id=None):
        """Sanitize member info for client representation."""
        today_spent = self.get_daily_spent(member["id"])
        base = {
            "id": member["id"],
            "name": member["name"],
            "role": member.get("role", "Club Member"),
            "balance": member["balance"],
            "today_spent": today_spent,
        }
        if include_private or member["id"] == current_member_id:
            base["created_at"] = member.get("created_at")
        return base

    def get_members_list(self, current_member_id=None):
        result = []
        for m in sorted(self.data.get("members", {}).values(), key=lambda x: x["id"]):
            result.append(self.sanitize_member(m, current_member_id=current_member_id))
        return result

    def get_public_state(self, current_session=None):
        limits = self.data.get("limits", {"max_transfer": 50, "daily_limit": 100})
        current_user = None
        if current_session:
            if current_session.get("type") == "member":
                m_id = current_session.get("member_id")
                if m_id in self.data["members"]:
                    current_user = self.sanitize_member(self.data["members"][m_id], include_private=True)
            elif current_session.get("type") == "admin":
                current_user = {
                    "type": "admin",
                    "name": "Group Administrator (Treasurer)"
                }

        return {
            "limits": limits,
            "members": self.get_members_list(current_user["id"] if current_user and "id" in current_user else None),
            "current_user": current_user,
            "recent_transactions": list(reversed(self.data.get("transactions", [])[-300:])),
            "stats": {
                "total_members": len(self.data.get("members", {})),
                "total_credits_in_circulation": sum(m["balance"] for m in self.data.get("members", {}).values()),
                "total_transactions": len(self.data.get("transactions", [])),
                "approved_transfers": sum(1 for t in self.data.get("transactions", []) if t.get("status") == "approved"),
                "declined_transfers": sum(1 for t in self.data.get("transactions", []) if t.get("status") == "declined"),
            }
        }


# Global store instance
ledger = LedgerStore(DATA_FILE)


def broadcast_event(event_type, payload):
    """Broadcast an SSE update to all connected clients."""
    with sse_lock:
        data_str = f"event: {event_type}\ndata: {json.dumps(payload)}\n\n"
        dead_clients = []
        for q in sse_subscribers:
            try:
                q.put_nowait(data_str)
            except Exception:
                dead_clients.append(q)
        for dead in dead_clients:
            if dead in sse_subscribers:
                sse_subscribers.remove(dead)


class ClubCreditsHandler(SimpleHTTPRequestHandler):
    """HTTP request handler for REST API and SSE stream."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def log_message(self, format, *args):
        # Override to keep terminal output clean and readable
        if "/api/events" not in args[0]:
            sys.stdout.write("%s - - [%s] %s\n" %
                             (self.client_address[0],
                              self.log_date_time_string(),
                              format % args))

    def get_auth_token(self):
        auth_header = self.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:].strip()
        # Fallback to query param
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)
        if "token" in qs:
            return qs["token"][0]
        return None

    def get_session(self):
        token = self.get_auth_token()
        if not token:
            return None
        with ledger_lock:
            session = ledger.sessions.get(token)
            if session:
                # Refresh touch timestamp
                session["last_seen"] = time.time()
            return session

    def send_json(self, data, status_code=HTTPStatus.OK):
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, message, status_code=HTTPStatus.BAD_REQUEST, extra=None):
        payload = {"error": message, "status": status_code}
        if extra:
            payload.update(extra)
        self.send_json(payload, status_code=status_code)

    def do_OPTIONS(self):
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/api/events":
            self.handle_sse()
            return

        if path == "/api/state":
            session = self.get_session()
            with ledger_lock:
                state = ledger.get_public_state(session)
            self.send_json(state)
            return

        if path == "/api/auth/me":
            session = self.get_session()
            if not session:
                self.send_error_json("Not authenticated", HTTPStatus.UNAUTHORIZED)
                return
            with ledger_lock:
                if session.get("type") == "member":
                    m_id = session.get("member_id")
                    if m_id not in ledger.data["members"]:
                        self.send_error_json("Member no longer exists", HTTPStatus.UNAUTHORIZED)
                        return
                    member = ledger.sanitize_member(ledger.data["members"][m_id], include_private=True)
                    self.send_json({"type": "member", "user": member})
                else:
                    self.send_json({
                        "type": "admin",
                        "user": {"name": "Group Administrator (Treasurer)", "role": "admin"}
                    })
            return

        if path == "/api/members":
            session = self.get_session()
            curr_id = session.get("member_id") if session and session.get("type") == "member" else None
            with ledger_lock:
                members = ledger.get_members_list(curr_id)
            self.send_json({"members": members})
            return

        if path == "/api/limits":
            with ledger_lock:
                limits = ledger.data.get("limits", {})
            self.send_json({"limits": limits})
            return

        if path == "/api/activity":
            with ledger_lock:
                txns = list(reversed(ledger.data.get("transactions", [])[-300:]))
            self.send_json({"transactions": txns})
            return

        if path == "/api/demo-accounts":
            with ledger_lock:
                accounts = []
                for m in sorted(ledger.data.get("members", {}).values(), key=lambda x: x["id"]):
                    accounts.append({
                        "id": m["id"],
                        "name": m["name"],
                        "role": m.get("role", "Club Member"),
                        "passcode": m["passcode"],
                        "balance": m["balance"],
                    })
            self.send_json({"accounts": accounts, "total": len(accounts)})
            return

        if path in ("/download", "/api/download", "/download.zip", "/api/download.zip"):
            import zipfile
            import io
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                for root, dirs, files in os.walk(BASE_DIR):
                    dirs[:] = [d for d in dirs if d not in ("__pycache__", ".git", ".system_generated")]
                    for f in files:
                        if f.endswith((".pyc", ".swp")) or f in (".DS_Store",):
                            continue
                        fp = os.path.join(root, f)
                        zf.write(fp, arcname=os.path.relpath(fp, BASE_DIR))
            zip_data = zip_buffer.getvalue()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/zip")
            self.send_header("Content-Disposition", 'attachment; filename="clubcredits-logic-bank.zip"')
            self.send_header("Content-Length", str(len(zip_data)))
            self.end_headers()
            self.wfile.write(zip_data)
            return

        # Serve static index.html or assets
        if path == "/" or path == "/index.html":
            self.path = "/index.html"
            return super().do_GET()

        return super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # Read JSON body
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length) if content_length > 0 else b"{}"
        try:
            body = json.loads(post_data.decode("utf-8")) if post_data else {}
        except Exception:
            self.send_error_json("Malformed JSON payload", HTTPStatus.BAD_REQUEST)
            return

        if path == "/api/auth/member-login":
            self.handle_member_login(body)
            return
        elif path == "/api/auth/admin-login":
            self.handle_admin_login(body)
            return
        elif path == "/api/auth/logout":
            self.handle_logout()
            return
        elif path == "/api/transfer":
            self.handle_transfer(body)
            return
        elif path == "/api/admin/set-limits":
            self.handle_admin_set_limits(body)
            return
        elif path == "/api/admin/set-balance":
            self.handle_admin_set_balance(body)
            return
        elif path == "/api/admin/add-member":
            self.handle_admin_add_member(body)
            return
        elif path == "/api/admin/change-passcode":
            self.handle_admin_change_passcode(body)
            return
        elif path == "/api/admin/reset-demo":
            self.handle_admin_reset_demo()
            return
        else:
            self.send_error_json(f"Endpoint not found: {path}", HTTPStatus.NOT_FOUND)

    def handle_member_login(self, body):
        member_id = (body.get("member_id") or "").strip().upper()
        passcode = (body.get("passcode") or "").strip()

        if not member_id or not passcode:
            self.send_error_json("Member ID and passcode are required.")
            return

        with ledger_lock:
            member = ledger.data.get("members", {}).get(member_id)
            if not member or member.get("passcode") != passcode:
                self.send_error_json("Invalid Member ID or passcode.", HTTPStatus.UNAUTHORIZED)
                return

            token = f"mem_{uuid.uuid4().hex}"
            session = {
                "token": token,
                "type": "member",
                "member_id": member_id,
                "created_at": time.time(),
                "last_seen": time.time()
            }
            ledger.sessions[token] = session
            sanitized = ledger.sanitize_member(member, include_private=True)

        self.send_json({
            "token": token,
            "type": "member",
            "user": sanitized,
            "message": f"Welcome back, {sanitized['name']}!"
        })

    def handle_admin_login(self, body):
        passcode = (body.get("passcode") or "").strip()
        if not passcode:
            self.send_error_json("Admin passcode is required.")
            return

        with ledger_lock:
            admin_pass = ledger.data.get("admin", {}).get("passcode", "adminpass")
            if passcode != admin_pass:
                self.send_error_json("Incorrect administrator passcode.", HTTPStatus.UNAUTHORIZED)
                return

            token = f"adm_{uuid.uuid4().hex}"
            session = {
                "token": token,
                "type": "admin",
                "created_at": time.time(),
                "last_seen": time.time()
            }
            ledger.sessions[token] = session

        self.send_json({
            "token": token,
            "type": "admin",
            "user": {"name": "Group Administrator", "role": "admin"},
            "message": "Administrator session verified."
        })

    def handle_logout(self):
        token = self.get_auth_token()
        if token:
            with ledger_lock:
                ledger.sessions.pop(token, None)
        self.send_json({"message": "Successfully signed out."})

    def handle_transfer(self, body):
        """
        Process a transfer request following strict logical propositions:
        A: the sending member is authenticated.
        B: the member has enough credits.
        L: the transfer is within the maximum transfer limit.
        D: the transfer stays within the daily limit.
        T: the transfer is approved.
        Decision policy: T <=> (A and B and L and D)
        Safety rule: T -> (A and B)
        """
        session = self.get_session()

        recipient_id = (body.get("recipient_id") or "").strip().upper()
        raw_amount = body.get("amount")

        # Step 1: Check A (sender authenticated)
        check_A = bool(session and session.get("type") == "member")
        sender_id = session.get("member_id") if check_A else None

        # Check for non-member trying to transfer
        if not check_A:
            # Transfer declined: A is False
            txn_record = {
                "id": f"TXN-{uuid.uuid4().hex[:8].upper()}",
                "timestamp": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "sender_id": "ANONYMOUS",
                "sender_name": "Unauthenticated User",
                "recipient_id": recipient_id or "UNKNOWN",
                "recipient_name": "Unknown",
                "amount": 0,
                "status": "declined",
                "reason": "Authentication required. You must sign in to send credits.",
                "checks": {
                    "A": False,
                    "B": False,
                    "L": False,
                    "D": False,
                    "T": False
                }
            }
            self.send_json({
                "decision": "declined",
                "reason": txn_record["reason"],
                "transaction": txn_record,
                "checks": txn_record["checks"]
            }, status_code=HTTPStatus.UNAUTHORIZED)
            return

        # Validate amount input: must be positive integer
        try:
            amount = int(raw_amount)
            if amount <= 0:
                raise ValueError("Amount must be greater than zero.")
        except (ValueError, TypeError):
            self.send_error_json("Transfer amount must be a positive whole number of credits.")
            return

        with ledger_lock:
            # Confirm sender exists
            sender = ledger.data.get("members", {}).get(sender_id)
            if not sender:
                self.send_error_json("Sender account not found.", HTTPStatus.UNAUTHORIZED)
                return

            # Confirm recipient exists and is not self
            recipient = ledger.data.get("members", {}).get(recipient_id)
            if not recipient:
                self.send_error_json(f"Recipient '{recipient_id}' not found in group directory.")
                return

            if recipient_id == sender_id:
                self.send_error_json("Cannot transfer credits to yourself.")
                return

            # Read latest balances, daily usage, and admin limits
            limits = ledger.data.get("limits", {"max_transfer": 50, "daily_limit": 100})
            max_transfer_limit = limits.get("max_transfer", 50)
            daily_limit = limits.get("daily_limit", 100)

            today_spent = ledger.get_daily_spent(sender_id)

            # Evaluate propositions:
            # A: Sender authenticated (True here)
            check_A = True
            # B: Sender has enough credits
            check_B = bool(sender["balance"] >= amount)
            # L: Within maximum transfer limit
            check_L = bool(amount <= max_transfer_limit)
            # D: Within daily limit
            check_D = bool((today_spent + amount) <= daily_limit)

            # Decision policy: T <=> (A and B and L and D)
            check_T = bool(check_A and check_B and check_L and check_D)

            # Compose human-readable reason
            reasons = []
            if not check_B:
                reasons.append(f"Insufficient credits: transfer requires {amount} credits, but current balance is {sender['balance']}.")
            if not check_L:
                reasons.append(f"Transfer limit exceeded: transfer amount ({amount} credits) exceeds maximum per transfer ({max_transfer_limit} credits).")
            if not check_D:
                reasons.append(f"Daily credit limit would be exceeded: sending {amount} credits would bring today's total to {today_spent + amount} credits (daily limit is {daily_limit} credits).")

            if check_T:
                status = "approved"
                reason_text = "All transfer policy checks passed successfully."
                # Execute balance updates atomically
                sender["balance"] -= amount
                recipient["balance"] += amount
            else:
                status = "declined"
                reason_text = " ".join(reasons)

            # Record transaction
            txn_id = f"TXN-{len(ledger.data.get('transactions', [])) + 1:04d}"
            txn_record = {
                "id": txn_id,
                "timestamp": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "sender_id": sender["id"],
                "sender_name": sender["name"],
                "recipient_id": recipient["id"],
                "recipient_name": recipient["name"],
                "amount": amount,
                "status": status,
                "reason": reason_text,
                "checks": {
                    "A": check_A,
                    "B": check_B,
                    "L": check_L,
                    "D": check_D,
                    "T": check_T
                }
            }
            ledger.data.setdefault("transactions", []).append(txn_record)
            ledger.save()

            sender_sanitized = ledger.sanitize_member(sender, include_private=True)
            recipient_sanitized = ledger.sanitize_member(recipient)

        # Broadcast live update
        broadcast_event("transfer_completed", {
            "transaction": txn_record,
            "sender": sender_sanitized,
            "recipient": recipient_sanitized
        })

        self.send_json({
            "decision": status,
            "reason": reason_text,
            "checks": txn_record["checks"],
            "transaction": txn_record,
            "sender_balance": sender_sanitized["balance"],
            "sender_today_spent": sender_sanitized["today_spent"]
        })

    def handle_admin_set_limits(self, body):
        session = self.get_session()
        if not session or session.get("type") != "admin":
            self.send_error_json("Administrator privileges required.", HTTPStatus.FORBIDDEN)
            return

        raw_max = body.get("max_transfer")
        raw_daily = body.get("daily_limit")

        try:
            max_transfer = int(raw_max)
            daily_limit = int(raw_daily)
            if max_transfer <= 0 or daily_limit <= 0:
                raise ValueError("Limits must be greater than zero.")
        except (ValueError, TypeError):
            self.send_error_json("Limits must be positive integers.")
            return

        with ledger_lock:
            ledger.data["limits"] = {
                "max_transfer": max_transfer,
                "daily_limit": daily_limit
            }
            ledger.save()
            updated_limits = ledger.data["limits"]

        broadcast_event("limits_updated", {"limits": updated_limits})
        self.send_json({
            "message": "Transfer limits updated successfully.",
            "limits": updated_limits
        })

    def handle_admin_set_balance(self, body):
        session = self.get_session()
        if not session or session.get("type") != "admin":
            self.send_error_json("Administrator privileges required.", HTTPStatus.FORBIDDEN)
            return

        member_id = (body.get("member_id") or "").strip().upper()
        raw_balance = body.get("balance")

        try:
            balance = int(raw_balance)
            if balance < 0:
                raise ValueError("Balance cannot be negative.")
        except (ValueError, TypeError):
            self.send_error_json("Balance must be a non-negative whole integer.")
            return

        with ledger_lock:
            member = ledger.data.get("members", {}).get(member_id)
            if not member:
                self.send_error_json(f"Member '{member_id}' not found.")
                return

            old_balance = member["balance"]
            member["balance"] = balance
            ledger.save()
            sanitized = ledger.sanitize_member(member)

        broadcast_event("member_updated", {"member": sanitized, "old_balance": old_balance})
        self.send_json({
            "message": f"Updated balance for {sanitized['name']} ({member_id}) to {balance} credits.",
            "member": sanitized
        })

    def handle_admin_add_member(self, body):
        session = self.get_session()
        if not session or session.get("type") != "admin":
            self.send_error_json("Administrator privileges required.", HTTPStatus.FORBIDDEN)
            return

        member_id = (body.get("member_id") or "").strip().upper()
        name = (body.get("name") or "").strip()
        role = (body.get("role") or "").strip() or "Club Member"
        passcode = (body.get("passcode") or "").strip()
        raw_balance = body.get("balance", 0)

        if not member_id or not name or not passcode:
            self.send_error_json("Member ID, display name, and passcode are all required.")
            return

        try:
            balance = int(raw_balance)
            if balance < 0:
                raise ValueError("Balance cannot be negative.")
        except (ValueError, TypeError):
            self.send_error_json("Starting balance must be a non-negative integer.")
            return

        with ledger_lock:
            if member_id in ledger.data.get("members", {}):
                self.send_error_json(f"Member with ID '{member_id}' already exists.")
                return

            new_member = {
                "id": member_id,
                "name": name,
                "role": role,
                "passcode": passcode,
                "balance": balance,
                "created_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            }
            ledger.data.setdefault("members", {})[member_id] = new_member
            ledger.save()
            sanitized = ledger.sanitize_member(new_member)

        broadcast_event("member_added", {"member": sanitized})
        self.send_json({
            "message": f"Member {name} ({member_id}) added successfully.",
            "member": sanitized
        })

    def handle_admin_change_passcode(self, body):
        session = self.get_session()
        if not session or session.get("type") != "admin":
            self.send_error_json("Administrator privileges required.", HTTPStatus.FORBIDDEN)
            return

        new_passcode = (body.get("new_passcode") or "").strip()
        if not new_passcode or len(new_passcode) < 4:
            self.send_error_json("New administrator passcode must be at least 4 characters long.")
            return

        with ledger_lock:
            ledger.data.setdefault("admin", {})["passcode"] = new_passcode
            ledger.save()

        self.send_json({"message": "Administrator passcode changed successfully."})

    def handle_admin_reset_demo(self):
        session = self.get_session()
        if not session or session.get("type") != "admin":
            self.send_error_json("Administrator privileges required.", HTTPStatus.FORBIDDEN)
            return

        with ledger_lock:
            ledger.data = default_database()
            ledger.save()

        broadcast_event("demo_reset", {})
        self.send_json({"message": "Demo data reset to initial default state."})

    def handle_sse(self):
        """Serve Server-Sent Events stream for real-time frontend reactivity."""
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache, no-transform")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        client_queue = queue.Queue(maxsize=100)
        with sse_lock:
            sse_subscribers.append(client_queue)

        # Initial handshake event
        try:
            self.wfile.write(b": connected\n\n")
            self.wfile.flush()
        except Exception:
            with sse_lock:
                if client_queue in sse_subscribers:
                    sse_subscribers.remove(client_queue)
            return

        try:
            while True:
                try:
                    # Wait for up to 15 seconds for a message or send keep-alive ping
                    message = client_queue.get(timeout=15.0)
                    self.wfile.write(message.encode("utf-8"))
                    self.wfile.flush()
                except queue.Empty:
                    # Keep-alive comment
                    self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, Exception):
            pass
        finally:
            with sse_lock:
                if client_queue in sse_subscribers:
                    sse_subscribers.remove(client_queue)


def run_server():
    global PORT
    ThreadingHTTPServer.allow_reuse_address = True
    start_port = PORT
    httpd = None

    for port_offset in range(10):
        current_port = start_port + port_offset
        try:
            server_address = (HOST, current_port)
            httpd = ThreadingHTTPServer(server_address, ClubCreditsHandler)
            PORT = current_port
            break
        except OSError as e:
            if e.errno == 48:  # Address already in use
                continue
            raise

    if httpd is None:
        print(f"Error: Could not bind to any port in range {start_port}-{start_port+9}")
        sys.exit(1)

    print(f"===============================================================")
    print(f" ClubCredits Server Running at http://{HOST}:{PORT}/")
    print(f" Demo Member Logins:")
    print(f"   MEMBER-01 (Alex Rivera)   - Passcode: 1234")
    print(f"   MEMBER-02 (Jordan Chen)   - Passcode: 2468")
    print(f"   MEMBER-03 (Taylor Kim)    - Passcode: 1357")
    print(f"   MEMBER-04 (Morgan Smith)  - Passcode: 9876")
    print(f" Administrator Login:")
    print(f"   Admin Passcode: {ledger.data.get('admin', {}).get('passcode', 'adminpass')}")
    print(f"===============================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down ClubCredits server.")
        httpd.server_close()


if __name__ == "__main__":
    run_server()
