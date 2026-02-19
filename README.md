# FanForge — Algorand NFT Tipping & Creator Economy Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Algorand](https://img.shields.io/badge/Algorand-TestNet-00D1B2.svg)](https://developer.algorand.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-4.0-009688.svg)](https://fastapi.tiangolo.com/)
[![Security Hardened](https://img.shields.io/badge/Security-Hardened-brightgreen.svg)](#security)
[![Pera Wallet](https://img.shields.io/badge/Wallet-Pera-6C5CE7.svg)](https://perawallet.app/)

> **A full-stack Web3 tipping platform on Algorand.**
> Fans tip creators through per-creator smart contracts and automatically earn NFT sticker rewards — soulbound collectibles and tradable golden stickers — all powered by on-chain events and IPFS metadata.

---

## Table of Contents

- [What This Project Does](#what-this-project-does)
- [Features](#features)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Frontend](#frontend)
- [Security](#security)
- [TipProxy Smart Contract](#tipproxy-smart-contract)
- [Minting Pipeline](#minting-pipeline-listener)
- [API Reference](#api-reference-30-endpoints)
- [Architecture](#architecture)
- [Database Schema](#database-schema)
- [Environment Variables](#environment-variables)
- [Tech Stack](#tech-stack)
- [Development History](#development-history)
- [Production Roadmap](#production-roadmap)
- [License](#license)

---

## What This Project Does

When a fan sends ALGO to a creator, the platform:

1. **Routes the tip** through a per-creator **TipProxy smart contract** (atomic group transaction: payment + app call)
2. **The smart contract validates** the tip (minimum amount, contract not paused) and **forwards ALGO** to the creator via an inner transaction
3. **The backend listener** polls the Algorand Indexer, detects the tip event from the on-chain log
4. **Automatically mints** the correct NFT sticker based on the tip amount (threshold-based template matching)
5. **Transfers the NFT** to the fan's wallet (auto opt-in + clawback transfer in demo mode)

All of this happens **end-to-end, in one fluent flow** — no manual steps required.

### Sticker System (Fully Creator-Customizable)

Creators configure their own sticker tiers via the API — custom names, images, thresholds, and types:

| Setting | Range / Options | Description |
|---------|----------------|-------------|
| **Name** | Any (up to 200 chars) | Display name for the sticker |
| **Image** | Any image (up to 5 MB) | Custom artwork uploaded to IPFS |
| **Threshold** | 0.1 – 10,000 ALGO | Minimum tip amount to earn this sticker |
| **Type** | `soulbound` or `golden` | Non-transferable vs tradable |
| **Min Tip** | 0.1 – 1,000 ALGO | Smart contract minimum (set at registration) |

**Example configuration** (from the demo):

| Threshold | Sticker | Type |
|-----------|---------|------|
| ≥ 1 ALGO | Butki | 🔒 Soulbound |
| ≥ 2 ALGO | Bauni | 🔒 Soulbound |
| ≥ 5 ALGO | Shawty | ⭐ Golden (tradable) |

Creators can have up to **20 sticker templates**. Each threshold + type combination must be unique per creator.

---

## Features

### Core Platform
- **Per-creator TipProxy smart contracts** — each creator gets a unique on-chain tip jar (PyTeal → TEAL)
- **Atomic group transactions** — payment + app call executed atomically (both succeed or both fail)
- **Creator-configurable min tip** — each creator sets their own minimum tip amount (0.1–1000 ALGO) during registration, enforced on-chain

### NFT Sticker Engine
- **Fully customizable sticker tiers** — creators define their own names, images, thresholds (0.1–10k ALGO), and types (up to 20 templates per creator)
- **Dual NFT economy** — soulbound stickers (`default_frozen=True`, non-transferable) + golden collectibles (`default_frozen=False`, tradable)
- **Custom sticker images** — creators upload their own artwork via the API; stored on IPFS with ARC-3 metadata
- **IPFS storage** — sticker images and metadata stored on Pinata IPFS

### Backend Services
- **Transaction listener** — background service polls Indexer for on-chain tip events, triggers minting pipeline
- **Security hardened** — wallet authentication, rate limiting, address validation, error sanitization (12 fixes from security audit)
- **Demo mode** — automatic opt-in + transfer using stored fan keys (production uses Pera Wallet)
- **Membership tiers** — Bronze (30 days) / Silver (90 days) / Gold (365 days)
- **Leaderboards** — per-creator fan rankings and global top creators
- **Fiat on-ramp** — simulated ALGO funding (Transak integration ready for production)
- **Alembic migrations** — database versioned with Alembic for safe schema evolution

### Frontend (9 Screens)
- **Landing Page** — hero section, live metrics, feature cards, sticker breakdown
- **Creator Setup Wizard** — 4-step onboarding: Connect → Deploy → Upload Stickers → Share Link
- **Fan Tip Page** — sticker gallery, tip form, golden odds preview, transaction progress
- **Creator Dashboard** — analytics, sticker management, top fans, contract controls, system status
- **Fan Dashboard** — tipping stats, recent tips, creators supported, golden odds, balance
- **Sticker Inventory** — NFT gallery grid, filter tabs, detail modal, golden transfer
- **Add Balance** — simulation faucet, quick-pick amounts, success card, session history
- **Leaderboard** — top creators table, per-creator fan ranking, search & filter
- **About & 404** — how it works, FAQ accordion, clean 404 page

---

## Project Structure

```
algorand_creator_project/
├── README.md                           ← This file
├── CONTRIBUTING.md                     ← Contribution guidelines
├── SECURITY.md                         ← Security policy & reporting
├── LICENSE                             ← MIT License
├── .gitignore
│
├── docs/
│   ├── FRONTEND_PLAN.md                ← Complete frontend specification (10 pages)
│   ├── BACKEND_INTEGRATION_PLAN.md     ← Screen-by-screen backend wiring plan
│   ├── BACKEND_SECURITY_AUDIT.md       ← 23-finding security audit + fix status
│   ├── PRODUCTION_ROADMAP.md           ← Known gaps & production migration guide
│   └── transak_onramp_flow.md          ← Fiat-to-crypto onramp documentation
│
└── backend/
    ├── main.py                         ← FastAPI app + listener lifespan
    ├── config.py                       ← Settings from .env + production validation
    ├── algorand_client.py              ← Algod singleton client
    ├── database.py                     ← SQLAlchemy async engine + session
    ├── db_models.py                    ← 7 ORM tables (User → ListenerState)
    ├── models.py                       ← Pydantic request/response models
    ├── exceptions.py                   ← Custom exception classes
    ├── requirements.txt                ← Python dependencies
    ├── .env.example                    ← Template for .env (secrets placeholders)
    ├── alembic.ini                     ← Alembic migration config
    │
    ├── alembic/                         ← Database migrations
    │   ├── env.py
    │   ├── script.py.mako
    │   └── versions/                   ← Migration scripts
    │
    ├── middleware/                       ← Security middleware
    │   ├── auth.py                     ← Wallet authentication (X-Wallet-Address)
    │   └── rate_limit.py               ← In-memory sliding-window rate limiting
    │
    ├── utils/                           ← Shared utilities
    │   └── validators.py               ← Algorand address validation (58-char, checksum)
    │
    ├── routes/                          ← API route handlers (8 modules, 30+ endpoints)
    │   ├── health.py                   ← GET /health
    │   ├── params.py                   ← GET /params (60s cache)
    │   ├── transactions.py             ← POST /submit, /submit-group
    │   ├── contracts.py                ← Contract info + listing
    │   ├── creator.py                  ← Registration, templates, dashboard, contract mgmt
    │   ├── nft.py                      ← NFT minting, transfer, opt-in, inventory
    │   ├── fan.py                      ← Fan stats, inventory, leaderboards
    │   └── onramp.py                   ← On-ramp: simulation faucet + Transak webhook
    │
    ├── services/                        ← Business logic layer (8 services)
    │   ├── listener_service.py         ← Indexer polling + threshold-based minting pipeline
    │   ├── nft_service.py              ← Mint soulbound/golden, transfer, opt-in
    │   ├── contract_service.py         ← TEAL loading, deploy, fund
    │   ├── ipfs_service.py             ← Pinata image + ARC-3 metadata upload
    │   ├── transak_service.py          ← Transak webhook + ALGO delivery routing
    │   ├── probability_service.py      ← Golden sticker chance engine
    │   ├── membership_service.py       ← Bronze/Silver/Gold tier definitions
    │   └── transaction_service.py      ← Transaction submission + error classification
    │
    ├── contracts/                       ← PyTeal smart contracts
    │   ├── compile.py                  ← Compiler (python -m contracts.compile)
    │   └── tip_proxy/                  ← V4 TipProxy smart contract
    │       └── contract.py             ← PyTeal source (4 methods: tip, update_min_tip, pause, unpause)
    │
    ├── sticker_scripts/                 ← Low-level NFT operations (used by nft_service)
    │   ├── utils.py                    ← Mnemonic → account derivation
    │   ├── mint_soulbound.py           ← Soulbound NFT (default_frozen=True)
    │   ├── mint_golden.py              ← Golden NFT (default_frozen=False, tradable)
    │   ├── optin_asset.py              ← ASA opt-in helper
    │   └── transfer_nft.py             ← NFT transfer helper
    │
    └── scripts/                         ← Development & testing utilities
        ├── generate_accounts.py        ← Generate demo creator + fan accounts
        ├── run_demo.py                 ← Full demo: register, deploy, fund, tip, mint
        ├── test_security_fixes.py      ← 23 security verification tests
        ├── test_all_endpoints.py       ← 28 endpoint smoke tests
        └── migrate_add_delivery_status.py ← DB migration helper
```

---

## Quick Start

### Prerequisites

- Python 3.10+
- [Pera Wallet](https://perawallet.app/) mobile app (set to **TestNet**)
- Pinata account (free tier — for IPFS image/metadata storage)

### 1. Clone and configure

```bash
git clone https://github.com/AdityaWagh19/algorand-fintech-boilerplate.git
cd algorand-fintech-boilerplate
cp backend/.env.example backend/.env
# Edit backend/.env with your platform wallet mnemonic, Pinata keys, etc.
```

### 2. Backend setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate       # Windows
# source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
```

### 3. Compile the TipProxy smart contract

```bash
python -m contracts.compile tip_proxy
# → Creates backend/contracts/tip_proxy/compiled/ (approval.teal + clear.teal)
```

### 4. Start the backend

```bash
python main.py
# → API at http://localhost:8000
# → Swagger UI at http://localhost:8000/docs
# → Database auto-created at data/sticker_platform.db
# → Transaction listener starts automatically
```

### 5. Run the demo (optional)

```bash
cd backend

# Generate demo accounts (creator + 2 fans)
python scripts/generate_accounts.py

# Run the full end-to-end demo
python scripts/run_demo.py
```

### 6. Run tests

```bash
# Start the server first, then in a separate terminal:
cd backend

# Security fix verification (23 tests)
python scripts/test_security_fixes.py

# Endpoint smoke tests (28 tests)
python scripts/test_all_endpoints.py
```

---

## Frontend

The frontend consists of **9 static HTML screens** designed via [Google Stitch](https://stitch.withgoogle.com/) with corresponding JavaScript modules for backend integration.

### Architecture

- **HTML screens** — Stitch-generated, styled with Tailwind CSS
- **JavaScript modules** — ES Module files that inject dynamic behavior via DOM `id` attributes
- **Shared infrastructure** — `shared.js` provides API client, Pera Wallet integration, state management, toast notifications, and utility functions
- **Zero build step** — serve directly with any HTTP server (no bundler required)

### Screen Overview

| # | Screen | HTML File | JS Module | Key Features |
|---|--------|-----------|-----------|-------------|
| 1 | Landing Page | `01-landing-page.html` | `01-landing.js` | Hero section, metrics, CTA buttons, wallet connect |
| 2 | Creator Setup | `02-creator-setup-wizard.html` | `02-setup-wizard.js` | 4-step wizard: Connect → Deploy → Stickers → Share |
| 3 | Fan Tip Page | `03-fan-tip-page.html` | `03-fan-tip.js` | Sticker gallery, tip flow, atomic group signing, polling |
| 4 | Creator Dashboard | `04-creator-dashboard.html` | `04-creator-dashboard.js` | Analytics, sticker CRUD, contract pause/resume, fans |
| 5 | Fan Dashboard | `05-fan-dashboard.html` | `05-fan-dashboard.js` | Stats, recent tips, golden odds, balance |
| 6 | Sticker Inventory | `06-sticker-inventory.html` | `06-inventory.js` | NFT grid, filter tabs, detail modal, transfer |
| 7 | Add Balance | `07-add-balance.html` | `07-add-balance.js` | Simulation faucet, quick-pick, success card |
| 8 | Leaderboard | `08-leaderboard.html` | `08-leaderboard.js` | Creator/fan tables, search, tab switching |
| 9 | About & 404 | `09-about-and-404.html` | `09-about.js` | FAQ accordion, nav, Go Home/Back |

### Running the Frontend

```bash
# Serve the frontend (from docs/stitch-screens/)
python -m http.server 3000
# → Open http://localhost:3000/01-landing-page.html
```

> **Note:** The backend must be running on `http://localhost:8000` for API calls to work. Without the backend, pages still render their static UI correctly — API-dependent features will show fallback states.

### Frontend Documentation

| Document | Description |
|----------|-------------|
| [`docs/FRONTEND_PLAN.md`](docs/FRONTEND_PLAN.md) | Complete frontend specification — all 10 pages, component design system, UX flows |
| [`docs/BACKEND_INTEGRATION_PLAN.md`](docs/BACKEND_INTEGRATION_PLAN.md) | Screen-by-screen wiring plan — DOM mappings, API endpoints, data flows, testing checklists |

---

## Security

The backend has been hardened with **12 security fixes** from a comprehensive audit ([full report](docs/BACKEND_SECURITY_AUDIT.md)).

### Implemented Security Measures

| Category | Fix | Description |
|----------|-----|-------------|
| **Authentication** | C1 | `X-Wallet-Address` header required on state-changing endpoints |
| **Secrets** | C2 | Demo account mnemonics replaced with placeholders |
| **Webhook** | C3 | Transak webhook signature verification fails closed |
| **Validation** | H1 | All wallet address parameters validated (58-char, checksum) |
| **Rate Limiting** | H2 | Sensitive endpoints rate-limited (creator registration, funding) |
| **Environment Guard** | H3 | Simulation endpoint double-guarded (disabled in production) |
| **Key Caching** | H4 | Platform private key cached instead of re-derived per request |
| **Error Handling** | H5 | Error messages sanitized — no tracebacks leaked to clients |
| **CORS** | M2 | Wildcard CORS rejected in production |
| **Financial Math** | M6 | Decimal arithmetic for fiat-to-crypto calculations |
| **Pagination** | L4 | NFT and fan inventory endpoints paginated |
| **Documentation** | I1, I3 | Singleton Algorand client, env vars documented |

### Authentication

State-changing endpoints require the `X-Wallet-Address` header matching the wallet in the URL path:

```bash
# Pause a creator's contract (requires auth)
curl -X POST http://localhost:8000/creator/{wallet}/pause-contract \
  -H "X-Wallet-Address: {wallet}"
```

Read-only endpoints (GET) are publicly accessible.

---

## TipProxy Smart Contract

The core of the platform — a per-creator tip validation and forwarding contract written in PyTeal.

### Methods

| Method | Description | Caller |
|--------|-------------|--------|
| `tip(memo)` | Validate payment, forward ALGO to creator via inner txn, emit log | Fan |
| `update_min_tip(amount)` | Update minimum tip threshold | Creator |
| `pause()` | Pause tip acceptance | Creator |
| `unpause()` | Resume tip acceptance | Creator |

### On-Chain Log Format

```
[32 bytes: fan_address][8 bytes: amount (big-endian uint64)][N bytes: memo (UTF-8)]
```

The listener parses this log to extract tip details and trigger the minting pipeline.

### Global State

| Key | Type | Description |
|-----|------|-------------|
| `creator` | Bytes (32) | Creator wallet address |
| `min_tip` | Uint64 | Minimum tip in microAlgos |
| `paused` | Uint64 | 0 = active, 1 = paused |
| `total_tips` | Uint64 | Lifetime tip count |
| `total_amount` | Uint64 | Lifetime microAlgos received |

---

## Minting Pipeline (Listener)

```
Indexer poll → parse TipProxy log → deduplicate →
  ├── MEMBERSHIP:* memo → membership sticker (soulbound + expiry)
  └── Regular tip → threshold match → best template (soulbound or golden)
       ├── 1 ALGO → Butki (soulbound)
       ├── 2 ALGO → Bauni (soulbound)
       └── 5 ALGO → Shawty (golden, tradable)
```

The listener uses **round-based tracking** (persisted via `ListenerState` table) to ensure no tips are skipped, even when minting takes several seconds.

### Demo Mode vs Production

| Feature | Demo Mode (`DEMO_MODE=True`) | Production |
|---------|------------------------------|------------|
| Fan opt-in | Automatic (uses stored keys) | Frontend prompts via Pera Wallet |
| NFT transfer | Immediate clawback transfer | After fan signs opt-in |
| Fan keys | Stored in `demo_accounts.json` | Never stored server-side |

---

## API Reference (30+ endpoints)

Full interactive documentation available at `http://localhost:8000/docs` (Swagger UI).

### Core

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/health` | GET | — | Health check + Algorand node status |
| `/params` | GET | — | Suggested transaction params (60s cache) |
| `/submit` | POST | — | Submit a single signed transaction |
| `/submit-group` | POST | — | Submit an atomic group of transactions |
| `/listener/status` | GET | — | Transaction listener status + last round |

### Contract

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/contract/info?name=` | GET | — | Contract compilation status |
| `/contract/list` | GET | — | List all available contracts |

### Creator

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/creator/register` | POST | Rate limited | Register wallet + deploy TipProxy |
| `/creator/{wallet}/contract` | GET | — | Active app_id + app_address |
| `/creator/{wallet}/contract/stats` | GET | — | On-chain global state |
| `/creator/{wallet}/upgrade-contract` | POST | ✅ Wallet | Deploy new TipProxy version |
| `/creator/{wallet}/pause-contract` | POST | ✅ Wallet | Pause active TipProxy |
| `/creator/{wallet}/unpause-contract` | POST | ✅ Wallet | Unpause TipProxy |
| `/creator/{wallet}/sticker-template` | POST | ✅ Wallet | Upload image to IPFS + save template |
| `/creator/{wallet}/templates` | GET | — | List all sticker templates |
| `/creator/{wallet}/template/{id}` | DELETE | ✅ Wallet | Delete template (0 mints only) |
| `/creator/{wallet}/dashboard` | GET | — | Combined on-chain + DB analytics |

### NFT

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/nft/mint/soulbound` | POST | — | Mint non-transferable sticker NFT |
| `/nft/mint/golden` | POST | — | Mint tradable sticker NFT |
| `/nft/transfer` | POST | — | Transfer golden NFT to new owner |
| `/nft/optin` | POST | — | Create unsigned opt-in transaction |
| `/nft/inventory/{wallet}` | GET | — | All NFTs owned (paginated: `?skip=0&limit=20`) |
| `/nft/{asset_id}` | GET | — | Single NFT details with template info |

### Fan & Leaderboards

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/fan/{wallet}/inventory` | GET | — | NFTs + template details (paginated) |
| `/fan/{wallet}/stats` | GET | — | Tip count, ALGO spent, creator breakdown |
| `/fan/{wallet}/pending` | GET | — | NFTs awaiting claim (opt-in) |
| `/fan/{wallet}/golden-odds` | GET | — | Golden sticker probability calculator |
| `/leaderboard/{creator_wallet}` | GET | — | Top fans ranked by ALGO tipped |
| `/leaderboard/global/top-creators` | GET | — | Global top creators |

### On-Ramp

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/onramp/config` | GET | — | Simulation/production mode + exchange rates |
| `/simulate/fund-wallet` | POST | Rate limited | Fund wallet with TestNet ALGO (3/min) |
| `/onramp/create-order` | POST | — | Create Transak on-ramp order |
| `/onramp/order/{id}` | GET | — | Get order status |
| `/onramp/fan/{wallet}/orders` | GET | — | Fan's order history |
| `/onramp/webhook` | POST | Signature | Transak delivery webhook |

---

## Architecture

```
┌───────────────────────────────────┐         ┌────────────────────────────────────┐
│   Frontend (9 HTML Screens)       │         │      Backend (FastAPI)              │
│                                   │         │                                    │
│  Pera Wallet SDK ─────────────────┤─ sign ──┤  middleware/                       │
│  shared.js API Client ────────────┤─ fetch ─┤    auth.py (wallet verification)  │
│  ES Module JS (per screen) ───────┤         │    rate_limit.py (abuse prevention)│
│                                   │         │                                    │
│  Pages:                           │         │  routes/ (8 modules)               │
│   01-landing, 02-setup-wizard     │         │    health, params, transactions    │
│   03-fan-tip, 04-creator-dash     │         │    contracts, creator, nft, fan    │
│   05-fan-dash, 06-inventory       │         │    onramp                          │
│   07-add-balance, 08-leaderboard  │         │                                    │
│   09-about-404                    │         │  services/ (8 services)            │
└───────────────────────────────────┘         │    contract, ipfs, nft, transak    │
                                              │    membership, listener, txn       │
                                              │    probability                     │
                                              │                                    │
                                              │  contracts/tip_proxy/              │
                                              │  db_models → SQLite + Alembic      │
                                              └─────────────┬──────────────────────┘
                                                            │
                               ┌─────────────────────────────┼─────────────────────┐
                               │                             │                     │
                     ┌─────────▼──────┐           ┌──────────▼────────┐   ┌───────▼───────┐
                     │ Algorand       │           │ Algorand Indexer   │   │ Pinata IPFS   │
                     │ TestNet Node   │           │ (polls for tips)   │   │ (images +     │
                     │ (via AlgoNode) │           │                    │   │  ARC-3 JSON)  │
                     └────────────────┘           └────────────────────┘   └───────────────┘
```

---

## Database Schema

| Table | Columns | Purpose |
|-------|---------|---------|
| `users` | wallet_address, role, username | Wallet addresses (creator / fan roles) |
| `contracts` | app_id, app_address, version, active | Per-creator TipProxy deployments |
| `sticker_templates` | name, ipfs_hash, sticker_type, tip_threshold | Creator sticker designs with IPFS hashes |
| `nfts` | asset_id, owner_wallet, sticker_type, delivery_status | Minted NFT instances (ASA IDs) |
| `transactions` | tx_id, fan_wallet, creator_wallet, amount_micro | Tip events from TipProxy on-chain logs |
| `transak_orders` | order_id, fiat_amount, crypto_amount, status | Fiat on-ramp order tracking |
| `listener_state` | last_processed_round | Persisted listener round for crash recovery |

---

## Environment Variables

See [`backend/.env.example`](backend/.env.example) for the complete template.

| Variable | Description |
|----------|-------------|
| `PLATFORM_WALLET` | Platform wallet address (deploys contracts, mints NFTs) |
| `PLATFORM_MNEMONIC` | 25-word mnemonic for the platform wallet |
| `PINATA_API_KEY` | Pinata IPFS API key |
| `PINATA_SECRET` | Pinata IPFS secret key |
| `PINATA_GATEWAY` | Pinata gateway URL (default: `https://gateway.pinata.cloud/ipfs`) |
| `DATABASE_URL` | Database connection (default: `sqlite:///./data/sticker_platform.db`) |
| `SIMULATION_MODE` | `True` for TestNet wallet funding, `False` for production |
| `DEMO_MODE` | `True` for auto opt-in/transfer, `False` for production |
| `TRANSAK_API_KEY` | Transak API key (production on-ramp) |
| `TRANSAK_SECRET` | Webhook signature verification secret |
| `CORS_ORIGINS` | Allowed CORS origins (must be explicit in production) |
| `ENVIRONMENT` | `development` or `production` |
| `GOLDEN_THRESHOLD` | Base probability for rare stickers (default: `0.10`) |
| `GOLDEN_TRIGGER_INTERVAL` | Guaranteed rare every N tips (default: `10`) |
| `LISTENER_POLL_SECONDS` | Indexer polling interval (default: `10`) |
| `CONTRACT_FUND_AMOUNT` | MicroAlgos to fund new contracts (default: `100000`) |
| `PLATFORM_FEE_PERCENT` | Fee percentage on Transak on-ramp orders (default: `2.0`) |

---

## Tech Stack

| Layer | Technology |
|-------|-----------:|
| Backend | Python 3.10+, FastAPI, SQLAlchemy (async), Pydantic, Alembic |
| Smart Contracts | PyTeal → TEAL v4, deployed on Algorand TestNet |
| Blockchain SDK | py-algorand-sdk (`algosdk`), algokit-utils |
| NFT Standard | Algorand ASA with ARC-3 metadata |
| IPFS | Pinata (image + JSON metadata hosting) |
| Database | SQLite (async via `aiosqlite`) — swap to PostgreSQL for production |
| Wallet | Pera Wallet Connect SDK (frontend), mnemonic (backend platform key) |
| Frontend | Vanilla HTML + Tailwind CSS + ES Module JavaScript |
| Image Processing | Pillow (sticker image validation) |
| HTTP Client | httpx (async, for Transak/IPFS calls) |

---

## Development History

### Phase 1–3: Core Platform
- Designed and implemented the **TipProxy V4 smart contract** in PyTeal with 4 methods (tip, update_min_tip, pause, unpause)
- Built the **FastAPI backend** with 30+ REST endpoints across 8 route modules
- Implemented **IPFS integration** with Pinata for image + ARC-3 metadata upload
- Created the **NFT minting pipeline** supporting soulbound (frozen) and golden (tradable) stickers

### Phase 4: Transaction Listener & Automation
- Built the **transaction listener** that polls the Algorand Indexer for on-chain tip events
- Implemented **membership tiers**, **leaderboards**, and **fan statistics**
- Added **Transak on-ramp integration** with webhook processing and order tracking

### Phase 5: End-to-End Testing & Hardening
- Deployed TipProxy contract to Algorand TestNet
- Created demo accounts (creator + 2 fans) and tested the full tip-to-NFT flow
- **Fixed atomic NFT transfers** — implemented demo mode with auto opt-in + clawback transfer
- **Fixed golden sticker minting** — added `strict_empty_address_check=False` for truly tradable NFTs
- **Changed golden sticker logic** from probability-based to **threshold-based** — 5 ALGO tip always earns the golden sticker
- **Fixed listener round tracking** — switched from indexer health round to max-round-of-processed-transactions

### Phase 6: Security Audit & Hardening
- Conducted comprehensive **23-finding security audit** across all backend code
- Implemented **12 security fixes** covering authentication, input validation, rate limiting, error sanitization, CORS validation, and financial math accuracy
- Created **wallet authentication middleware** (`X-Wallet-Address` header verification)
- Added **Algorand address validation** utility (58-char, checksum verification)
- Created **automated test suites** — 23 security tests + 28 endpoint tests
- **Removed demo secrets** from source files (replaced with placeholders)

### Phase 7: Frontend Design & Integration
- Generated **9 production-quality screens** via Google Stitch from a comprehensive frontend specification
- Created **10 JavaScript modules** (1 shared + 9 per-screen) for backend integration
- Implemented **Pera Wallet Connect** flow across all screens
- Wired all screens to backend API endpoints with proper error handling, loading states, and fallbacks
- Built complete **FAQ accordion**, **leaderboard search**, **sticker filtering**, and **simulation faucet** features

---

## Production Roadmap

See [`docs/PRODUCTION_ROADMAP.md`](docs/PRODUCTION_ROADMAP.md) for the full list of known gaps. Key items:

| Priority | Item | Effort |
|----------|------|--------|
| **P0** | Ed25519 wallet signature auth (replace header check) | ~2 days |
| **P0** | PostgreSQL (replace SQLite) | ~30 min |
| **P1** | HSM / KMS key management | ~1 week |
| **P1** | Task queue for minting pipeline (Celery/ARQ) | ~3 days |
| **P2** | Redis-backed rate limiting | ~2 hours |
| **P2** | Listener liveness monitoring | ~2 hours |
| **P3** | Automated test suite (pytest + CI/CD) | Ongoing |

---

## License

MIT — see [LICENSE](LICENSE) for details.
