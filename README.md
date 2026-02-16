# Algorand Fintech Boilerplate

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Node.js 18+](https://img.shields.io/badge/node-18+-green.svg)](https://nodejs.org/)
[![Algorand](https://img.shields.io/badge/Algorand-TestNet-00D1B2.svg)](https://developer.algorand.org/)

> **Swap-ready smart contract infrastructure for Algorand dApps.**  
> Deploy any PyTeal contract, connect via Pera Wallet, and send transactions — all with a clean, modular codebase.

**Perfect for:** Campus payment systems, ticketing platforms, loan repayment dApps, or any fintech use case on Algorand.

---

## ✨ Features

- **Pera Wallet integration** — connect, sign, and submit transactions
- **Smart contract deployment** — deploy PyTeal contracts to TestNet in one click
- **Atomic group transactions** — payment + app call executed atomically
- **Swappable contracts** — replace `frontend/js/contract.js` and `backend/contracts/<name>/` for any fintech use case
- **Modular architecture** — clean separation of wallet, transaction, contract, and UI layers

---

## Project Structure

```
algorand_walletconnect/
├── README.md                  ← You are here
├── .env.example               ← Environment template
├── .gitignore
│
├── backend/
│   ├── main.py                ← FastAPI app factory (~65 lines)
│   ├── config.py              ← Settings from .env
│   ├── algorand_client.py     ← Algod singleton
│   ├── exceptions.py          ← Custom exceptions
│   ├── requirements.txt
│   │
│   ├── routes/
│   │   ├── health.py          ← GET /health
│   │   ├── params.py          ← GET /params (cached)
│   │   ├── transactions.py    ← POST /submit, /submit-group
│   │   └── contracts.py       ← POST /contract/deploy, /fund
│   │
│   ├── services/
│   │   ├── transaction_service.py  ← Base64, submission, error classification
│   │   └── contract_service.py     ← TEAL loading, deploy/fund txn creation
│   │
│   └── contracts/
│       ├── compile.py               ← Compiler (run: python -m contracts.compile)
│       └── payment_proxy/           ← Example contract
│           ├── contract.py          ← PyTeal source
│           └── compiled/            ← Generated TEAL + metadata
│
└── frontend/
    ├── index.html             ← Single page
    ├── styles.css             ← Dark theme UI
    ├── package.json           ← npm dependencies
    │
    ├── js/
    │   ├── app.js             ← Main orchestrator (ES module)
    │   ├── config.js          ← Frontend config
    │   ├── wallet.js          ← Pera Wallet lifecycle
    │   ├── transaction.js     ← Txn building & submission
    │   ├── contract.js        ← ★ SWAP POINT — contract-specific logic
    │   └── ui.js              ← DOM manipulation
    │
    ├── src/
    │   └── bundle-entry.js    ← esbuild entry (SDKs only)
    └── libs/
        └── bundle.js          ← Built SDK bundle
```

---

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- [Pera Wallet](https://perawallet.app/) mobile app (set to TestNet)

### 1. Clone and configure

```bash
git clone https://github.com/AdityaWagh19/algorand-fintech-boilerplate.git
cd algorand-fintech-boilerplate
cp .env.example backend/.env
```

### 2. Backend setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate     # Windows
# source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
```

### 3. Compile the smart contract

```bash
python -m contracts.compile
# Or compile a specific contract:
# python -m contracts.compile payment_proxy
```

### 4. Start the backend

```bash
python main.py
# → API running at http://localhost:8000
```

### 5. Frontend setup

```bash
cd ../frontend
npm install
npm run build    # Bundle algosdk + PeraWalletConnect
```

### 6. Start the frontend

```bash
npm start        # → http://localhost:8080
```

### 7. Use the dApp

1. Open `http://localhost:8080` in your browser
2. **Connect** your Pera Wallet (must be on TestNet)
3. **Deploy** the Payment Proxy contract
4. **Fund** the contract with 0.2 ALGO
5. **Send** ALGO through the smart contract to any TestNet address

---

## How to Swap Contracts

This is the core value of the boilerplate. To use a different smart contract:

### Backend (new contract)

1. Create `backend/contracts/your_contract/contract.py`:

```python
from pyteal import *

# Metadata (read by compiler)
CONTRACT_NAME = "Your Contract"
CONTRACT_DESCRIPTION = "What it does"
CONTRACT_VERSION = "1.0.0"
GLOBAL_UINTS = 2
GLOBAL_BYTES = 1
LOCAL_UINTS = 0
LOCAL_BYTES = 0
CONTRACT_METHODS = ["your_method"]

def approval_program():
    # Your PyTeal logic here
    return Approve()

def clear_program():
    return Approve()
```

2. Compile it:

```bash
python -m contracts.compile your_contract
```

3. Update frontend config to use it:

```javascript
// frontend/js/config.js
DEFAULT_CONTRACT: 'your_contract',
```

### Frontend (contract-specific logic)

4. Modify `frontend/js/contract.js` to match your contract's methods:

```javascript
// The transfer() function builds the atomic group specific to your contract.
// Change the appArgs, accounts, and transaction structure as needed.
export async function transfer(receiver, amount, onStatus) {
    // Build transactions matching YOUR contract's ABI
    const appCallTxn = algosdk.makeApplicationCallTxnFromObject({
        appArgs: [
            new Uint8Array(Buffer.from('your_method')),  // ← Your method
            // ... your args
        ],
        // ...
    });
}
```

> **Everything else stays unchanged**: wallet connection, transaction submission, UI, backend routes.

---

## API Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check + Algorand node status |
| `/params` | GET | Suggested transaction params (60s cache) |
| `/submit` | POST | Submit a single signed transaction |
| `/submit-group` | POST | Submit an atomic group of signed transactions |
| `/contract/info?name=` | GET | Contract compilation status |
| `/contract/list` | GET | List all available contracts |
| `/contract/deploy` | POST | Create unsigned deploy transaction |
| `/contract/fund` | POST | Create unsigned fund transaction |

---

## Architecture

```
┌─────────────────────────┐         ┌──────────────────────────┐
│      Frontend (JS)      │         │     Backend (FastAPI)     │
│                         │         │                          │
│  wallet.js ─────────────┤─ sign ──┤  routes/                 │
│  contract.js ★ ─────────┤─ fetch ─┤  services/               │
│  transaction.js ────────┤─ submit─┤  contracts/               │
│  ui.js ─────────────────┤         │    └─ payment_proxy/ ★    │
│  config.js              │         │                          │
└─────────────────────────┘         └──────────────────────────┘
                                              │
                                    ┌─────────▼──────────┐
                                    │  Algorand TestNet   │
                                    │  (via AlgoNode)     │
                                    └────────────────────┘
```

★ = swap points

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.10+, FastAPI, py-algorand-sdk, PyTeal |
| Frontend | Vanilla JS (ES modules), algosdk v3, Pera WalletConnect |
| Blockchain | Algorand TestNet (via AlgoNode) |
| Wallet | Pera Wallet (mobile) |

---

## License

MIT
