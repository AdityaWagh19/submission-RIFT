# FanForge — Creator Economy Platform on Algorand

> **Fans tip creators with ALGO. Creators reward fans with collectible NFT stickers.**
> Full-stack Web3 platform with per-creator smart contracts, three NFT types, a merch store with token-gated discounts, and a fiat on-ramp.

[![Built on Algorand](https://img.shields.io/badge/Built_on-Algorand-black?style=flat-square&logo=algorand)](https://algorand.co)
[![Python 3.13+](https://img.shields.io/badge/Python-3.13+-blue?style=flat-square&logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=flat-square&logo=react)](https://react.dev)
[![Vite](https://img.shields.io/badge/Vite-7-646CFF?style=flat-square&logo=vite)](https://vite.dev)
[![License: MIT](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

---

## What is FanForge?

FanForge is a non-custodial creator economy platform where:

- **Fans** tip creators with ALGO and earn collectible NFT stickers
- **Creators** deploy smart contracts (TipProxy) and design custom sticker rewards
- **Everything** runs on Algorand TestNet — transparent, instant, trustless

### The 3-NFT System

| NFT Type | Name | How to Earn | Properties |
|----------|------|-------------|------------|
| 🏆 **Butki** | Loyalty Badge | Tip 5 times → earn 1 badge | Soulbound, non-transferable |
| 🎫 **Bauni** | Membership | Purchase for 1 ALGO | Soulbound, 30-day expiry |
| 🌟 **Shawty** | Collectible | Purchase for 2 ALGO | Golden, fully transferable |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Frontend (React + Vite)           http://localhost:5173        │
│  ├── Pera Wallet Connect (wallet signing)                      │
│  ├── 6 Pages: Landing, Creator Hub, Fan Hub, Store, Explore, Tip│
│  └── JWT Auth + 8 API service modules (62 endpoints mapped)    │
├─────────────────────────────────────────────────────────────────┤
│  Backend (FastAPI + Python 3.13)   http://localhost:8000        │
│  ├── 30+ REST endpoints with JWT authentication                │
│  ├── On-chain listener (polls Algorand every 10s)              │
│  ├── NFT minting pipeline (Pinata IPFS → ARC-3 mint)          │
│  └── SQLite + SQLAlchemy async ORM                             │
├─────────────────────────────────────────────────────────────────┤
│  Algorand TestNet                  AlgoNode Cloud              │
│  ├── TipProxy smart contracts (per-creator)                    │
│  ├── ASA NFTs (ARC-3 metadata)                                 │
│  └── Atomic transaction groups (app call + payment)            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
algorand_creator_project_onramp/
│
├── frontend/                        # React + Vite SPA
│   ├── package.json
│   ├── vite.config.js               # Node polyfills for algosdk
│   └── src/
│       ├── main.jsx                 # Entry point
│       ├── App.jsx                  # 6 routes + context providers
│       ├── index.css                # Full design system (dark mode, glassmorphism)
│       │
│       ├── api/                     # Backend API service layer
│       │   ├── client.js            # Base fetch wrapper with JWT
│       │   ├── auth.js              # Challenge/verify flow
│       │   ├── creator.js           # 17 creator endpoints
│       │   ├── fan.js               # 5 fan endpoints
│       │   ├── nft.js               # 6 NFT endpoints
│       │   ├── loyalty.js           # Butki(3) + Bauni(3) + Shawty(6)
│       │   ├── merch.js             # Store catalog, quote, order
│       │   ├── leaderboard.js       # 2 leaderboard endpoints
│       │   └── system.js            # Health, params, onramp, submit
│       │
│       ├── context/                 # React context providers
│       │   ├── AuthContext.jsx      # JWT + wallet + role management
│       │   ├── WalletContext.jsx    # Pera Wallet SDK wrapper
│       │   └── ToastContext.jsx     # Toast notification system
│       │
│       ├── components/              # Shared UI components
│       │   ├── Navbar.jsx           # Wallet badge, role pill, nav links
│       │   ├── TabPanel.jsx         # Reusable tabbed interface
│       │   └── Modal.jsx            # Generic modal dialog
│       │
│       ├── pages/                   # 6 core pages
│       │   ├── Landing.jsx          # Hero, NFT showcase, connect, fund
│       │   ├── CreatorHub.jsx       # Dashboard, templates, products, contract
│       │   ├── FanHub.jsx           # NFTs, loyalty, Shawty, stats
│       │   ├── Store.jsx            # Catalog, cart, checkout, orders
│       │   ├── Explore.jsx          # Global leaderboard, creator detail
│       │   └── Tip.jsx              # Tip form with real algosdk txns
│       │
│       └── utils/
│           └── helpers.js           # Wallet truncation, date formatting
│
├── backend/                         # FastAPI Python backend
│   ├── main.py                      # App entry point + lifespan
│   ├── config.py                    # pydantic-settings (.env loader)
│   ├── database.py                  # SQLAlchemy async engine
│   ├── db_models.py                 # 10 ORM models
│   ├── models.py                    # 31 Pydantic request/response schemas
│   ├── algorand_client.py           # Singleton algod client
│   ├── requirements.txt
│   │
│   ├── contracts/                   # PyTeal smart contracts
│   │   ├── compile.py
│   │   ├── tip_proxy/               # Per-creator tip jar contract
│   │   └── nft_controller/          # NFT management contract
│   │
│   ├── routes/                      # API endpoints (30+)
│   │   ├── auth.py                  # JWT wallet authentication
│   │   ├── health.py                # GET /health
│   │   ├── creator.py               # Creator registration + management
│   │   ├── fan.py                   # Fan inventory + stats
│   │   ├── nft.py                   # NFT minting + transfer
│   │   ├── merch.py                 # Store + orders + discounts
│   │   ├── butki.py                 # Loyalty badges
│   │   ├── bauni.py                 # Membership gating
│   │   ├── shawty.py                # Collectible tokens
│   │   ├── onramp.py                # Fiat on-ramp + simulation
│   │   ├── transactions.py          # Signed txn submission
│   │   ├── contracts.py             # Contract deploy + fund
│   │   └── params.py                # Suggested txn params
│   │
│   ├── services/                    # Business logic (12 services)
│   ├── middleware/                   # JWT auth + rate limiting
│   ├── sticker_scripts/             # Low-level ASA operations
│   ├── assets/stickers/             # Default sticker images
│   ├── scripts/                     # Demo + test scripts
│   └── data/                        # SQLite database
│
├── frontend1.md                     # Frontend build plan (reference)
└── README.md                        # This file
```

---

## Quick Start

### Prerequisites

- **Python 3.13+** (backend)
- **Node.js 18+** (frontend)
- **Pera Wallet** mobile app (set to TestNet)

### 1. Clone & Install Backend

```bash
git clone https://github.com/your-repo/fanforge.git
cd fanforge/backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
```

### 2. Configure Environment

Create `backend/.env` (a working `.env` is already included for hackathon demo):

```env
# Algorand TestNet
ALGORAND_ALGOD_ADDRESS=https://testnet-api.algonode.cloud
ALGORAND_ALGOD_TOKEN=
ALGORAND_INDEXER_URL=https://testnet-idx.algonode.cloud

# Platform wallet (deploys contracts, mints NFTs)
PLATFORM_WALLET=your_platform_address_here
PLATFORM_MNEMONIC=your twenty five word mnemonic here

# Fan wallet (for testing)
FAN_WALLET=your_fan_address_here
FAN_MNEMONIC=your fan twenty five word mnemonic here

# IPFS (Pinata)
PINATA_API_KEY=your_pinata_api_key
PINATA_SECRET=your_pinata_secret

# Database
DATABASE_URL=sqlite:///./data/sticker_platform.db

# Auth (JWT)
JWT_SECRET=your_random_secret_key_here

# Mode
ENVIRONMENT=development
SIMULATION_MODE=True
DEMO_MODE=True
CORS_ORIGINS=http://localhost:3000,http://localhost:5500,http://localhost:8080,http://localhost:5173,http://127.0.0.1:5173
```

### 3. Start the Backend

```bash
cd backend
venv\Scripts\activate
python main.py
```

Backend runs at **http://localhost:8000**. Swagger docs at **http://localhost:8000/docs**.

### 4. Install & Start the Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at **http://localhost:5173**.

### 5. Open & Test

1. Open **http://localhost:5173** in your browser
2. Click **"Connect Pera Wallet"** → scan QR with Pera Wallet app (TestNet mode)
3. Sign the authentication challenge
4. Register as a **Creator** → deploys your TipProxy smart contract
5. Create **sticker templates** → upload images for Butki/Bauni/Shawty
6. **Fund your wallet** (simulation mode) on the Landing page
7. Navigate to **`/tip/{your-wallet}`** and send a tip → signs via Pera
8. Check **Fan Hub** (`/fan`) to see your minted NFTs!

---

## Frontend Pages

| # | Page | Route | Key Features |
|---|------|-------|-------------|
| 1 | **Landing** | `/` | Hero section, NFT showcase (Butki/Bauni/Shawty), Pera wallet connect, wallet funding (simulation), health badge |
| 2 | **Creator Hub** | `/creator` | 4 tabs: Dashboard (stats + recent tips), Templates (CRUD + image upload), Products & Discounts, Contract (pause/unpause/upgrade + on-chain stats) |
| 3 | **Fan Hub** | `/fan` | 4 tabs: My NFTs (inventory + pending claims), Loyalty & Membership (Butki + Bauni), Shawty Tokens (burn/lock/transfer), Stats |
| 4 | **Store** | `/store/:creatorWallet` | Product catalog, Members-only tab, Cart + Quote + Checkout, Order history |
| 5 | **Explore** | `/explore` | Global creator leaderboard, expandable creator detail with fan/Butki sub-leaderboards, links to Store/Tip |
| 6 | **Tip** | `/tip/:creatorWallet` | Real algosdk transaction building (AppCall + Payment atomic group), Pera signing, loyalty/membership/golden odds preview |

### Navigation Flow

```
Landing  ──→  Creator Hub  ──→  Store (own)
   │              │                │
   ├──→  Explore  ├──→  Leaderboard│
   │       │      │                │
   │       ├──→  Store (any) ←─────┘
   │       │        │
   ├──→  Fan Hub ←──┘
   │       │
   │       ├──→  Tip (any creator)
   │       │
   └──→  Explore
```

---

## API Overview

| Category | Endpoint | Description |
|----------|----------|-------------|
| **Health** | `GET /health` | Node status + round number |
| **Auth** | `POST /auth/challenge` | Request nonce for wallet signing |
| | `POST /auth/verify` | Verify Ed25519 signature → JWT token |
| **Creator** | `POST /creator/register` | Register + deploy TipProxy |
| | `GET /creator/{wallet}/dashboard` | Stats, contract, templates, transactions |
| | `GET /creator/{wallet}/contract` | Contract info |
| | `GET /creator/{wallet}/contract/stats` | On-chain contract state |
| | `POST /creator/{wallet}/pause-contract` | Pause contract |
| | `POST /creator/{wallet}/unpause-contract` | Unpause contract |
| | `POST /creator/{wallet}/upgrade-contract` | Deploy new contract version |
| | `GET /creator/{wallet}/templates` | List sticker templates |
| | `POST /creator/{wallet}/sticker-template` | Create template (multipart) |
| | `DELETE /creator/{wallet}/template/{id}` | Delete unminted template |
| | `GET /creator/{wallet}/products` | List merch products |
| | `POST /creator/{wallet}/products` | Create product |
| | `PATCH /creator/{wallet}/products/{id}` | Update product |
| | `DELETE /creator/{wallet}/products/{id}` | Delete product |
| | `GET /creator/{wallet}/discounts` | List discount rules |
| | `POST /creator/{wallet}/discounts` | Create discount rule |
| **Fan** | `GET /fan/{wallet}/inventory` | Fan's NFT collection |
| | `GET /fan/{wallet}/pending` | NFTs awaiting claim |
| | `POST /fan/{wallet}/claim/{nftId}` | Claim pending NFT |
| | `GET /fan/{wallet}/stats` | Tipping statistics |
| | `GET /fan/{wallet}/golden-odds` | Golden sticker probability |
| | `GET /fan/{wallet}/orders` | Fan's merch orders |
| **Store** | `GET /creator/{wallet}/store` | Public store catalog |
| | `GET /creator/{wallet}/store/members-only` | Bauni-gated catalog |
| | `POST /creator/{wallet}/store/quote` | Build order quote |
| | `POST /creator/{wallet}/store/order` | Place order |
| **NFT** | `GET /nft/inventory/{wallet}` | NFT inventory |
| | `GET /nft/{assetId}` | NFT details |
| | `POST /nft/optin` | Create opt-in transaction |
| | `POST /nft/transfer` | Transfer golden NFT |
| | `POST /nft/mint/soulbound` | Mint soulbound NFT (listener) |
| | `POST /nft/mint/golden` | Mint golden NFT (listener) |
| **Butki** | `GET /butki/{wallet}/loyalty` | Fan loyalty (all creators) |
| | `GET /butki/{wallet}/loyalty/{creator}` | Fan loyalty (specific creator) |
| | `GET /butki/leaderboard/{creator}` | Creator's fan leaderboard |
| **Bauni** | `GET /bauni/{wallet}/membership/{creator}` | Membership status |
| | `GET /bauni/{wallet}/memberships` | All memberships |
| | `POST /bauni/verify` | Verify membership |
| **Shawty** | `GET /shawty/{wallet}/tokens` | Collectible tokens |
| | `POST /shawty/burn` | Burn for merch |
| | `POST /shawty/lock` | Lock for discount |
| | `POST /shawty/transfer` | Transfer token |
| | `GET /shawty/{wallet}/validate/{assetId}` | Validate ownership |
| | `GET /shawty/{wallet}/redemptions` | Redemption history |
| **Leaderboard** | `GET /leaderboard/global/top-creators` | Top creators by ALGO |
| | `GET /leaderboard/{creator}` | Creator's top fans |
| **On-Ramp** | `GET /onramp/config` | On-ramp configuration |
| | `POST /onramp/create-order` | Create on-ramp order |
| | `GET /onramp/order/{id}` | Order status |
| | `GET /onramp/fan/{wallet}/orders` | Fan's on-ramp orders |
| | `POST /simulate/fund-wallet` | Fund wallet (TestNet only) |
| **Txn** | `GET /params` | Suggested transaction params |
| | `POST /submit` | Submit signed transaction |
| | `POST /submit-group` | Submit atomic group |
| **Contract** | `GET /contract/info` | Contract TEAL info |
| | `GET /contract/list` | Available contracts |
| | `POST /contract/deploy` | Deploy contract |
| | `POST /contract/fund` | Fund contract |

Full interactive API docs: **http://localhost:8000/docs**

---

## Security

- **Non-custodial**: Users sign all transactions with Pera Wallet. No private keys in the frontend.
- **Platform key**: Only `PLATFORM_MNEMONIC` is stored server-side (for minting NFTs).
- **Auth**: JWT-based wallet authentication with Ed25519 signature challenge/verify flow.
- **Rate limiting**: Creator registration (5/hour), wallet funding (3/min), auth endpoints (20-30/min).
- **Production guards**: Validates CORS origins, disables simulation/demo mode, requires JWT_SECRET at startup.
- **Input validation**: All wallet addresses validated via `algosdk.encoding`.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Blockchain** | Algorand TestNet (AVM 8) |
| **Smart Contracts** | PyTeal → TEAL |
| **Backend** | FastAPI + Python 3.13 |
| **Frontend** | React 19 + Vite 7 |
| **Wallet** | Pera Wallet Connect |
| **Styling** | Vanilla CSS (dark mode, glassmorphism) |
| **Database** | SQLite + SQLAlchemy (async) |
| **IPFS** | Pinata |
| **NFT Standard** | ARC-3 (metadata) |
| **Node Polyfills** | vite-plugin-node-polyfills (Buffer, crypto) |

---

## Demo Flow

```
1. Connect Pera Wallet → Auth challenge → JWT token
2. Register as Creator → TipProxy contract deployed on TestNet
3. Create sticker templates (Butki, Bauni, Shawty) with images
4. Add merch products + discount rules
5. Fund test wallet (simulation mode)
6. Send tips via /tip/:creatorWallet → atomic AppCall + Payment
7. Listener detects tips → mints NFT stickers → delivers to fan
8. Fan views collection in Fan Hub → claims pending NFTs
9. Fan burns Shawty tokens for merch discounts
10. Global leaderboard updates in real-time
```

---

## License

MIT — see [LICENSE](LICENSE)
