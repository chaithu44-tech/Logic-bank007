# ClubCredits 🪙

A private group credit system and live peer token ledger for clubs, classes, and workshop events. Members can send **fictional credits** to celebrate collaboration, share supplies, or reward workshop milestones with real-time updates and visible transfer reasoning.

> [!IMPORTANT]
> **Fictional credits only · No cash value.**
> This is **not a bank**. Credits have zero monetary value and cannot be deposited, withdrawn, redeemed, or exchanged for real money. The system connects to no financial institutions or payment processors.

---

## Features

- **Visible Transfer Reasoning**: Every transfer is evaluated on the backend using explicit logical propositions, and a compact explanation is displayed alongside the transaction outcome.
- **Strict Transfer Safety Invariants**: Overdrafts and unauthenticated transfers are structurally prohibited ($T \rightarrow (A \land B)$).
- **Live Reactive Dashboard**: Real-time balance updates, progress bars, and activity logs via Server-Sent Events (SSE) without reloading the page.
- **Member Portal**: Sign in, view credit balances and daily limits, select peers, and send credits with instant logic evaluation.
- **Administrator Dashboard**: Club treasurers and organizers can manage members, adjust credit balances, set transfer caps, and monitor the group activity log.
- **Zero External Dependencies**: Pure Python standard library backend with responsive vanilla HTML/CSS/JavaScript.

---

## Transfer Rules & Visible Reasoning

Each transfer is evaluated against the following propositions:

| Proposition | Description | Evaluated On Server |
| :---: | :--- | :--- |
| **A** | The sending member is authenticated | Verified via valid session token |
| **B** | The member has enough credits | `sender.balance >= amount` |
| **L** | The transfer is within the single-transfer limit | `amount <= max_transfer_limit` |
| **D** | The transfer stays within the daily limit | `(today_spent + amount) <= daily_limit` |
| **T** | The transfer is approved | All checks must pass |

### Safety Invariant
$$T \rightarrow (A \land B)$$
The system **always** requires member authentication and sufficient credits. While the administrator can configure the transfer cap ($L$) and daily limit ($D$), the safety invariant ($A \land B$) is an immutable code-level rule that cannot be disabled.

### Decision Policy
$$T \leftrightarrow (A \land B \land L \land D)$$

When a transfer is submitted, a compact explanation is rendered next to the transaction result:
```text
A: Signed in ✓
B: Enough credits ✓
L: Within transfer limit ✓
D: Within daily limit ✗

Decision: Declined
Reason: The daily credit limit would be exceeded.
```

---

## Architecture Overview

```text
Member or Administrator in the Browser (HTML / CSS / Vanilla JS)
        │
        ▼  REST API (POST /api/transfer, GET /api/state)
Backend (Python ThreadingHTTPServer)
        │
        ├─ 1. Authenticate session & validate input types
        ├─ 2. Evaluate propositions A, B, L, D under server lock
        ├─ 3. Approve (T=True: update both balances equally)
        │     OR Decline (T=False: balances untouched, explain failed checks)
        ├─ 4. Append transaction to local ledger store
        │
        ├─► Local Data Store (data/clubcredits.json)
        │
        ▼  Server-Sent Events (SSE /api/events)
Live broadcast instantly refreshes member balances, progress bars, and activity feed
```

---

## Local Run Instructions

### 1. Requirements
- Python 3.8+ (zero `pip` dependencies needed)
- Modern web browser (Chrome, Firefox, Safari, Edge)

### 2. Start the Server
From the project directory:

```bash
cd /Users/bunnyroyal/.gemini/antigravity/scratch/clubcredits
python3 server.py
```

By default, the server binds to `http://127.0.0.1:8080/`.

You can also specify a custom port or host via environment variables:
```bash
PORT=9000 HOST=127.0.0.1 python3 server.py
```

### 3. Open in Browser
Visit [http://127.0.0.1:8080](http://127.0.0.1:8080) in your web browser.

---

## Sample Credentials (Local Demo: 120 Accounts)

The application includes **120 pre-seeded sample member accounts** across diverse club roles, along with an administrator account.

### Quick Spotlight Accounts
| Member ID | Passcode | Display Name | Role | Starting Balance |
| :--- | :---: | :--- | :--- | :---: |
| `MEMBER-01` | `1234` | Alex Rivera | Robotics Club Lead | 150 credits |
| `MEMBER-02` | `2468` | Jordan Chen | Event Coordinator | 80 credits |
| `MEMBER-03` | `1357` | Taylor Kim | Design Lead | 95 credits |
| `MEMBER-04` | `9876` | Morgan Smith | Science Olympiad Captain | 60 credits |

### Extended Directory (`MEMBER-05` through `MEMBER-120`)
- **Passcode Pattern:** For accounts `MEMBER-05` to `MEMBER-120`, the passcode is `1000 + N` (e.g. `MEMBER-05` is `1005`, `MEMBER-42` is `1042`, `MEMBER-120` is `1120`).
- **Interactive Directory:** Click **"Browse All 120+ Demo Members"** on the member sign-in panel to open a searchable modal with live category filtering (Leads, STEM, Arts, High Balance). Clicking any account signs in instantly.
- **Random Demo Member:** Click **"🎲 Sign In as Random Member"** to immediately sign in as a random club member.

### Pre-Seeded Club Activity History (179 Transactions)
Every single one of the 120 members has pre-recorded transfer activity in the ledger (155+ approved peer tokens and 24 transparently declined limit/balance edge-cases). When any member signs in, their **My Recent Activity** table displays their authentic incoming and outgoing club transfers!

### Administrator Account
- **Passcode:** `adminpass`
- **Role:** Group Administrator / Club Treasurer

---

## How to Change the Administrator Passcode

You can change the administrator passcode in two ways:

### Option A: Via the Admin Portal (UI)
1. Sign in to the **Admin Portal** using the current passcode (`adminpass`).
2. Scroll to the **Administrator Passcode Settings** card at the bottom.
3. Enter your new passcode (at least 4 characters) and click **Update Passcode**.
4. The change is saved immediately to `data/clubcredits.json`.

### Option B: Via Environment Variable
Set `CLUBCREDITS_ADMIN_PASS` prior to starting the server:
```bash
CLUBCREDITS_ADMIN_PASS="mySecretPass2026" python3 server.py
```

---

## Running the Automated Test Suite

A comprehensive test suite is included in `tests/`:

```bash
cd /Users/bunnyroyal/.gemini/antigravity/scratch/clubcredits
python3 -m unittest discover -s tests -v
```

Tests verify:
- Proposition **A**: Unauthenticated transfer rejection ($A=\text{False} \rightarrow T=\text{False}$).
- Proposition **B**: Overdraft prevention ($B=\text{False} \rightarrow T=\text{False}$).
- Proposition **L**: Single-transfer maximum enforcement ($L=\text{False} \rightarrow T=\text{False}$).
- Proposition **D**: Cumulative daily limit enforcement ($D=\text{False} \rightarrow T=\text{False}$).
- Invariant: Balance conservation across approved transfers ($\sum \Delta \text{balance} = 0$).
- Security: Privilege isolation ensuring ordinary members cannot access administrator endpoints.

---

## File Structure

```text
clubcredits/
├── server.py              # Lightweight HTTP server, REST endpoints, and SSE broadcast
├── data/
│   └── clubcredits.json   # Local JSON persistence store
├── static/
│   ├── index.html         # Responsive, accessible single-page layout
│   ├── style.css          # Cream/mint palette, deep teal text, rounded cards
│   ├── app.js             # Vanilla JS client with SSE reactivity and logic display
│   └── hero.jpg           # Club community illustration artwork
├── tests/
│   ├── test_backend.py    # Unit tests for propositions and ledger operations
│   ├── test_api_mock.py   # Sandboxed HTTP handler integration tests
│   └── test_static_and_full_flow.py # End-to-end flow tests
└── README.md              # Project documentation and quickstart
```
