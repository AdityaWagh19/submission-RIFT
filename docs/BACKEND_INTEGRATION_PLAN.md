# FanForge — Backend Integration Plan (v2)

> **Goal:** Wire 9 static Stitch HTML screens to the FastAPI backend WITHOUT changing the UI.
> **Approach:** Convert each static screen into a dynamic page by injecting JavaScript that fetches real data from the backend API and wires up interactive elements (buttons, forms, modals).
> **Backend Base URL:** `http://localhost:8000` (configurable via `CONFIG.API_BASE` in `shared.js`)
> **Wallet:** Pera Wallet SDK (connect, sign, disconnect — NO private keys EVER)
> **Last Updated:** 2026-02-19 (ALL PHASES COMPLETE — 9/9 screens wired)

---

## Table of Contents

1.  [Architecture Overview](#1-architecture-overview)
2.  [File Inventory & Progress](#2-file-inventory--progress)
3.  [Shared Infrastructure (DONE)](#3-shared-infrastructure-done)
4.  [Screen 01 — Landing Page (DONE)](#4-screen-01--landing-page-done)
5.  [Screen 02 — Creator Setup Wizard (DONE)](#5-screen-02--creator-setup-wizard-done)
6.  [Screen 03 — Fan Tip Page (DONE)](#6-screen-03--fan-tip-page-done)
7.  [Screen 04 — Creator Dashboard (DONE)](#7-screen-04--creator-dashboard-done)
8.  [Screen 05 — Fan Dashboard (DONE)](#8-screen-05--fan-dashboard-done)
9.  [Screen 06 — Sticker Inventory (DONE)](#9-screen-06--sticker-inventory-done)
10. [Screen 07 — Add Balance (DONE)](#10-screen-07--add-balance-done)
11. [Screen 08 — Leaderboard (DONE)](#11-screen-08--leaderboard-done)
12. [Screen 09 — About & 404 (DONE)](#12-screen-09--about--404-done)
13. [Backend Route Summary](#13-backend-route-summary)
14. [Integration Phases](#14-integration-phases)
15. [Error Handling Matrix](#15-error-handling-matrix)
16. [Testing Checklist](#16-testing-checklist)

---

## 1. Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────┐
│                    STITCH HTML SCREENS (FROZEN UI)                    │
│  01-landing  02-wizard  03-tip  04-dash  05-fan  06-inv  07-bal     │
│  08-board  09-about  — ALL Tailwind CSS, DO NOT MODIFY MARKUP       │
├──────────────────────────────────────────────────────────────────────┤
│                  INTEGRATION LAYER (JavaScript Modules)              │
│  shared.js → API client, Pera wallet, state, utils, toast           │
│  NN-xxx.js → per-screen logic (imports from shared.js)              │
├─────────────────────────┬────────────────────────────────────────────┤
│    Pera Wallet SDK      │    FastAPI Backend (localhost:8000)        │
│    (CDN, WalletConnect) │    /creator  /fan  /nft  /submit          │
│                         │    /onramp  /simulate  /leaderboard       │
│                         │    /params  /health  /listener/status     │
│    algosdk (CDN)        │    /contract                              │
└─────────────────────────┴────────────────────────────────────────────┘
```

### Key Principles

1. **UI is frozen** — Do not change any HTML structure, CSS classes, or Tailwind config. Integration is purely additive JS + ID injection.
2. **Progressive enhancement** — Each screen works visually without JS. JS adds live data + interactivity.
3. **IDs & data attributes** — Add `id` and `data-*` attributes to existing elements as hooks for JS. This is the ONLY HTML modification allowed.
4. **Single API client** — All backend calls go through `shared.js` → `apiRequest()`.
5. **ES Modules** — All JS files use `import` / `export`. HTML loads them with `<script type="module">`.

---

## 2. File Inventory & Progress

### HTML Screens (All 9 ✅)

| # | File | Bytes | IDs Injected | Script Tag Added |
|---|------|-------|:---:|:---:|
| 1 | `01-landing-page.html` | 36,668 | ✅ | ✅ `01-landing.js` |
| 2 | `02-creator-setup-wizard.html` | 22,235 | ✅ | ✅ `02-setup-wizard.js` |
| 3 | `03-fan-tip-page.html` | 19,009 | ✅ | ✅ `03-fan-tip.js` |
| 4 | `04-creator-dashboard.html` | 19,728 | ✅ | ✅ `04-creator-dashboard.js` |
| 5 | `05-fan-dashboard.html` | 19,489 | ✅ | ✅ `05-fan-dashboard.js` |
| 6 | `06-sticker-inventory.html` | 24,013 | ✅ | ✅ `06-inventory.js` |
| 7 | `07-add-balance.html` | 15,582 | ✅ | ✅ `07-add-balance.js` |
| 8 | `08-leaderboard.html` | 21,537 | ✅ | ✅ `08-leaderboard.js` |
| 9 | `09-about-and-404.html` | 18,387 | ✅ | ✅ `09-about.js` |

### JavaScript Files

| File | Bytes | Status | Description |
|------|-------|--------|-------------|
| `js/shared.js` | 13,581 | ✅ Done | API client, Pera wallet, state, utils, toast |
| `js/01-landing.js` | 1,537 | ✅ Done | Nav wiring, CTA buttons, wallet connect |
| `js/02-setup-wizard.js` | 11,989 | ✅ Done | 4-step wizard: connect → deploy → stickers → share |
| `js/03-fan-tip.js` | 14,243 | ✅ Done | Tip flow: sticker gallery → sign → submit → poll → claim |
| `js/04-creator-dashboard.js` | 10,800+ | ✅ Done | Stats, sticker grid, transactions, fans, contract pause/resume, system status |
| `js/05-fan-dashboard.js` | 9,500+ | ✅ Done | Fan stats, recent tips, golden odds, creators supported, balance display |
| `js/06-inventory.js` | 8,500+ | ✅ Done | Grid gallery, filter tabs, detail modal, golden transfer, pagination |
| `js/07-add-balance.js` | 7,500+ | ✅ Done | Quick-pick amounts, simulation faucet, success card, session history |
| `js/08-leaderboard.js` | 8,000+ | ✅ Done | Top creators table, fan leaderboard per creator, search, stats |
| `js/09-about.js` | 5,500+ | ✅ Done | FAQ accordion, wallet connect, Go Home/Back, nav wiring |

---

## 3. Shared Infrastructure (DONE)

`docs/stitch-screens/js/shared.js` — loaded by every screen as `<script type="module">`.

### 3A. Configuration

```javascript
const CONFIG = {
  API_BASE: 'http://localhost:8000',
  EXPLORER_BASE: 'https://lora.algokit.io/testnet',
  IPFS_GATEWAY: 'https://gateway.pinata.cloud/ipfs',
  NETWORK: 'testnet',
  POLL_INTERVAL_MS: 4000,
  TOAST_DURATION_MS: 5000,
  MAX_STICKER_TEMPLATES: 20,
  MIN_TIP_ALGO: 0.1,
  MAX_TIP_ALGO: 1000,
  MAX_TIP_THRESHOLD: 10000,
  MAX_FUND_ALGO: 10,
};
```

### 3B. Exported API Functions

All go through `apiRequest(method, path, body, options)` which handles:
- `Content-Type: application/json` (auto-set, except multipart)
- `X-Wallet-Address` header (when `options.authenticated`)
- Error handling: `401→toast`, `403→toast`, `409→toast`, `429→toast+RetryAfter`, `5xx→toast`
- `ApiError` class with `.status`, `.details`

```javascript
// Creator
api.registerCreator(wallet, username, minTipAlgo)
api.getCreatorContract(wallet)
api.getCreatorContractStats(wallet)
api.getCreatorDashboard(wallet)
api.getCreatorTemplates(wallet)
api.createStickerTemplate(wallet, formData)        // AUTH + multipart
api.deleteStickerTemplate(wallet, templateId)
api.pauseContract(wallet)                           // AUTH
api.unpauseContract(wallet)

// Fan
api.getFanInventory(wallet, skip, limit)
api.getFanPending(wallet)
api.claimPendingNFT(wallet, nftId)
api.getFanStats(wallet)
api.getGoldenOdds(wallet, amountAlgo)
api.getCreatorLeaderboard(wallet, limit)
api.getGlobalTopCreators(limit)

// NFT
api.getNFTDetails(assetId)
api.createOptIn(assetId, fanWallet)
api.transferNFT(assetId, receiverWallet)
api.getNFTInventory(wallet, skip, limit)

// Transactions
api.getTransactionParams()
api.submitTransaction(signedTxn)                    // { signed_txn: "base64" }
api.submitGroup(signedTxns)                         // { signed_txns: ["b64",...] }

// On-ramp / Simulation
api.getOnrampConfig()
api.simulateFundWallet(walletAddress, amountAlgo)
api.getOnrampOrderStatus(partnerOrderId)
api.getFanOnrampOrders(wallet)

// System
api.getListenerStatus()
api.healthCheck()
```

### 3C. Wallet Manager (Pera)

```javascript
// Exported: connectWallet, disconnectWallet, signTransactions
// State: state.walletAddress, state.connected
// UI: updateWalletUI() — toggles "Sign In" / truncated address display
```

### 3D. Utilities (Exported)

```javascript
truncateAddress(addr)      // "Axf3…7Kq"
formatAlgo(amount)         // "12.35"
formatDate(isoString)      // "Feb 18, 2026"
relativeTime(isoString)    // "2h ago"
explorerUrl(type, id)      // full Lora explorer URL
showToast(message, type)   // info|success|error|warning
```

---

## 4. Screen 01 — Landing Page (DONE)

**File:** `01-landing-page.html` → `js/01-landing.js`
**Status:** ✅ Wired

### What's Done
- Navigation buttons wired (Get Started, Sign In, Start as Creator, Start as Fan)
- Wallet connect + role-based redirect (creator vs fan)
- CTA buttons navigate to appropriate pages

### Backend Calls
- `GET /health` — optional node status indicator
- Wallet detection: `GET /creator/{wallet}/contract` to check if user is a registered creator

---

## 5. Screen 02 — Creator Setup Wizard (DONE)

**File:** `02-creator-setup-wizard.html` → `js/02-setup-wizard.js`
**Status:** ✅ Wired

### What's Done
- 4-step wizard flow fully implemented
- Step 1: Wallet connect via Pera
- Step 2: Deploy tip jar `POST /creator/register`
- Step 3: Upload stickers `POST /creator/{wallet}/sticker-template` (multipart, AUTH)
- Step 3: List stickers `GET /creator/{wallet}/templates`
- Step 4: Generate and copy share link

### Error Handling
- `409` on duplicate registration
- `400` on max 20 templates
- `409` on duplicate threshold/type combination
- Rate limiting toast on `429`

---

## 6. Screen 03 — Fan Tip Page (DONE)

**File:** `03-fan-tip-page.html` → `js/03-fan-tip.js`
**Status:** ✅ Wired

### What's Done
- Creator wallet read from URL `?creator=ADDR`
- Creator data fetched: `getCreatorDashboard`, `getCreatorContract`, `getCreatorTemplates`
- Sticker gallery rendered dynamically
- Amount selection (quick-pick + custom) with live preview
- Golden odds fetched: `getGoldenOdds`
- Full transaction flow: construct → sign → submit → poll → opt-in → claim
- Transaction stepper UI with 4 states

### Dependencies
- `algosdk` loaded via CDN `<script>` tag
- `signTransactions` exported from `shared.js`

---

## 7. Screen 04 — Creator Dashboard (DONE)

**File:** `04-creator-dashboard.html`
**JS:** `js/04-creator-dashboard.js` (✅ created)

### Prerequisites
1. Add IDs to HTML elements (see DOM mapping below)
2. Add `<script type="module" src="js/04-creator-dashboard.js"></script>` before `</body>`
3. Add `<script src="https://cdn.jsdelivr.net/npm/algosdk@2.7.0/dist/browser/algosdk.min.js"></script>` in `<head>`

### Backend Endpoints Used

| Section | Endpoint | Method | Auth | Response Key Fields |
|---------|----------|--------|:---:|-----|
| Stat cards | `GET /creator/{wallet}/dashboard` | GET | No | `totalFans`, `totalStickersMinted`, `username` |
| Stat cards | `GET /creator/{wallet}/contract/stats` | GET | No | `totalTips`, `totalAmountAlgo`, `minTipAlgo`, `paused`, `contractVersion` |
| Sticker grid | `GET /creator/{wallet}/templates` | GET | No | `templates[]`, `total` |
| Add sticker | `POST /creator/{wallet}/sticker-template` | POST | ✅ | `id`, `name`, `imageUrl`, `metadataUrl`, `stickerType`, `tipThreshold` |
| Delete sticker | `DELETE /creator/{wallet}/template/{id}` | DELETE | No¹ | `{ message }` |
| Top fans | `GET /leaderboard/{wallet}?limit=5` | GET | No | `leaderboard[]` → `{ rank, fanWallet, tipCount, totalAlgo, nftCount }` |
| Contract info | `GET /creator/{wallet}/contract` | GET | No | `appId`, `appAddress`, `version`, `active`, `deployedAt` |
| Pause | `POST /creator/{wallet}/pause-contract` | POST | ✅ | Unsigned `ApplicationCallTxn` → Pera signs → `/submit` |
| Unpause | `POST /creator/{wallet}/unpause-contract` | POST | No¹ | Unsigned `ApplicationCallTxn` → Pera signs → `/submit` |
| Upgrade | `POST /creator/{wallet}/upgrade-contract` | POST | ✅ | New contract deployed |
| Recent tips | `GET /creator/{wallet}/dashboard` | GET | No | `recentTransactions[]` → `{ txId, fanWallet, amountAlgo, memo, processed, detectedAt }` |
| System | `GET /listener/status` | GET | No | `running`, `lastProcessedRound`, `errorsCount`, `retryEnabled`, `maxRetryAttempts` |

¹ Known auth gap — endpoint validates wallet via URL path only.

### DOM Mapping (IDs to inject)

```
STAT CARDS (inject IDs into existing stat card elements):
  id="stat-total-tips"       ← stats.totalTips (from contract/stats)
  id="stat-algo-earned"      ← stats.totalAmountAlgo (from contract/stats)
  id="stat-unique-fans"      ← dashboard.totalFans
  id="stat-nfts-minted"      ← dashboard.totalStickersMinted

STICKER MANAGEMENT:
  id="sticker-grid"          ← templates[] rendered here
  id="slot-counter"          ← "${total}/20 slots used"
  id="btn-add-sticker"       ← opens add sticker modal/form

TOP FANS TABLE:
  id="fan-table-body"        ← leaderboard[] rows

CONTRACT INFO:
  id="contract-app-id"       ← contract.appId
  id="contract-version"      ← contract.version
  id="contract-status"       ← "Active" / "Paused"
  id="contract-min-tip"      ← stats.minTipAlgo
  id="btn-pause"             ← pause-contract flow
  id="btn-unpause"           ← unpause-contract flow (hidden when active)
  id="btn-upgrade"           ← upgrade-contract flow
  id="link-explorer"         ← explorerUrl('app', appId)

SYSTEM STATUS:
  id="listener-status"       ← running ? "● Running" : "○ Stopped"
  id="listener-round"        ← lastProcessedRound
  id="listener-errors"       ← errorsCount
  id="listener-retry"        ← retryEnabled ? "Enabled (max N)" : "Disabled"

RECENT TRANSACTIONS:
  id="recent-tx-body"        ← recentTransactions[] table rows

SHARE LINK:
  id="btn-share-link"        ← Copy tip page URL to clipboard
```

### Contract Actions (Pera Signing Flow)

```javascript
// Pause
async function pauseContract() {
  const result = await api.pauseContract(state.walletAddress);
  // result = { unsignedTxn: "base64..." } (base64-encoded msgpack)
  const signed = await signTransactions([result.unsignedTxn]);
  await api.submitTransaction(toBase64(signed[0]));
  showToast('Contract paused', 'success');
  refreshDashboard();
}

// Unpause — same pattern with api.unpauseContract
// Upgrade — api.upgradeContract, no signing needed (platform deploys)
```

### Auto-Refresh
```javascript
setInterval(refreshDashboard, 30000); // Poll every 30s
```

### Sticker CRUD in Dashboard
```javascript
// Add sticker (reuse same FormData logic from 02-setup-wizard.js)
async function addSticker(formData) {
  const result = await api.createStickerTemplate(state.walletAddress, formData);
  showToast(`${result.name} created!`, 'success');
  refreshStickers(); // Re-fetch and re-render grid
}

// Delete sticker (only if mint_count === 0)
async function deleteSticker(templateId) {
  await api.deleteStickerTemplate(state.walletAddress, templateId);
  showToast('Sticker deleted', 'success');
  refreshStickers();
}
// DELETE on 409 → "Cannot delete — NFTs have been minted from this template"
```

---

## 8. Screen 05 — Fan Dashboard (DONE)

**File:** `05-fan-dashboard.html`
**JS:** `js/05-fan-dashboard.js` (✅ created)

### Prerequisites
1. Add IDs to HTML elements
2. Add `<script type="module" src="js/05-fan-dashboard.js"></script>`

### Backend Endpoints Used

| Section | Endpoint | Method | Response Key Fields |
|---------|----------|--------|-----|
| Stat cards | `GET /fan/{wallet}/stats` | GET | `totalTips`, `totalAlgoSpent`, `uniqueCreators`, `totalNfts`, `totalSoulbound`, `totalGolden` |
| Recent tips | `GET /fan/{wallet}/stats` | GET | `recentTips[]` → `{ txId, creatorWallet, amountAlgo, memo, detectedAt }` (last 10) |
| Creators | `GET /fan/{wallet}/stats` | GET | `creatorBreakdown[]` → `{ creatorWallet, tipCount, totalAlgo }` (top 10) |
| Golden odds | `GET /fan/{wallet}/golden-odds?amount_algo=5` | GET | `baseProbability`, `bonus`, `totalProbability`, `triggerInterval`, `description` |
| Balance | Pera SDK / `algod.accountInformation(wallet)` | — | ALGO balance |

### DOM Mapping (IDs to inject)

```
STAT CARDS:
  id="stat-total-tips"         ← stats.totalTips
  id="stat-algo-spent"         ← formatAlgo(stats.totalAlgoSpent)
  id="stat-creators"           ← stats.uniqueCreators
  id="stat-total-stickers"     ← stats.totalNfts

RECENT TIPS TABLE:
  id="recent-tips-body"        ← recentTips[] rows
  Each row: "${amountAlgo} ALGO → ${truncateAddress(creatorWallet)} · ${memo} · ${relativeTime(detectedAt)}"

CREATORS I SUPPORT:
  id="creator-cards"           ← creatorBreakdown[] cards
  Each card: avatar (first 2 chars), name/wallet, totalAlgo tipped, tipCount, [Tip Again] link

GOLDEN ODDS:
  id="odds-current"            ← `${(totalProbability * 100).toFixed(1)}%`
  id="odds-base"               ← baseProbability description
  id="odds-calculator"         ← Input to preview odds at different amounts

BALANCE:
  id="wallet-balance"          ← ALGO balance from algod
  id="btn-add-balance"         ← Navigate to 07-add-balance.html

VIEW STICKERS:
  id="btn-view-stickers"       ← Navigate to 06-sticker-inventory.html
```

### Response Shape Reference

```javascript
// GET /fan/{wallet}/stats
{
  wallet: "ADDR...",
  totalTips: 15,
  totalAlgoSpent: 8.5,      // already float, NOT microAlgos
  averageTipAlgo: 0.567,
  uniqueCreators: 3,
  totalSoulbound: 8,
  totalGolden: 4,
  totalNfts: 12,
  creatorBreakdown: [
    { creatorWallet: "ADDR", tipCount: 5, totalAlgo: 6.5 }
  ],
  recentTips: [
    { txId: "TX...", creatorWallet: "ADDR", amountAlgo: 5.0, memo: "great!", detectedAt: "2026-02-18T..." }
  ]
}

// GET /fan/{wallet}/golden-odds?amount_algo=5
{
  wallet: "ADDR", tipAmount: 5.0,
  baseProbability: 0.1,
  bonus: 0.02,
  totalProbability: 0.12,
  triggerInterval: 10,
  description: "12% chance on next tip"
}
```

---

## 9. Screen 06 — Sticker Inventory (DONE)

**File:** `06-sticker-inventory.html`
**JS:** `js/06-inventory.js` ✅ created

### Prerequisites
1. Add IDs to HTML elements
2. Add `<script type="module" src="js/06-inventory.js"></script>`
3. Add algosdk CDN in `<head>` (needed for opt-in transactions)

### Backend Endpoints Used

| Action | Endpoint | Method | Notes |
|--------|----------|--------|-------|
| Load inventory | `GET /nft/inventory/{wallet}?skip=0&limit=20` | GET | Paginated |
| Load pending | `GET /fan/{wallet}/pending` | GET | NFTs awaiting claim |
| NFT details | `GET /nft/{asset_id}` | GET | Full metadata |
| Transfer golden | `POST /nft/transfer` | POST | `{ assetId, receiverWallet }` |
| Opt-in (claim) | Build `AssetTransferTxn` (self-transfer, amt=0) → Pera sign → `/submit` | — | Client-side + Pera |
| Claim delivery | `POST /fan/{wallet}/claim/{nft_id}` | POST | After opt-in, backend transfers NFT |

### DOM Mapping (IDs to inject)

```
HEADER:
  id="inventory-title"         ← "My Stickers (${totalCount})"
  id="btn-sort"                ← Sort dropdown control

FILTER TABS:
  id="tab-all"                 ← "All (totalCount)"
  id="tab-soulbound"           ← "Soulbound 🔒 (totalSoulbound)"
  id="tab-golden"              ← "Golden ⭐ (totalGolden)"

GRID:
  id="sticker-grid"            ← NFT cards rendered here
  id="btn-load-more"           ← "Load More" (hidden when !hasMore)
  id="showing-count"           ← "Showing X of Y stickers"

PENDING BANNER:
  id="pending-banner"          ← Hidden by default, shown when pending[] exists
  id="pending-count"           ← Number of claimable stickers
  id="btn-claim-all"           ← Opt-in + claim flow

DETAIL MODAL (overlay, hidden by default):
  id="nft-modal"               ← Modal container
  id="modal-image"             ← Large NFT image (IPFS gateway URL)
  id="modal-name"              ← Template name
  id="modal-type"              ← Soulbound/Golden badge
  id="modal-creator"           ← truncateAddress(creatorWallet)
  id="modal-date"              ← formatDate(mintedAt)
  id="modal-asa-id"            ← assetId + copy button
  id="modal-explorer"          ← explorerUrl('asset', assetId)
  id="transfer-section"        ← Visible only for golden type
  id="input-receiver"          ← Recipient wallet address
  id="btn-transfer"            ← Execute transfer
  id="btn-close-modal"         ← Close modal
```

### Inventory Response Shape

```javascript
// GET /nft/inventory/{wallet}?skip=0&limit=20
{
  wallet: "ADDR...",
  nfts: [{
    id: 1, assetId: 12345, templateId: 3, ownerWallet: "ADDR",
    stickerType: "golden",           // "soulbound" | "golden"
    txId: "TXID...", mintedAt: "2026-02-18T...", expiresAt: null,
    templateName: "Shawty", imageUrl: "https://gateway.pinata.cloud/ipfs/Qm...",
    metadataUrl: "https://gateway.pinata.cloud/ipfs/Qm...", category: "premium"
  }],
  total: 20,           // items in THIS page
  totalCount: 87,      // total across ALL pages
  skip: 0, limit: 20,
  hasMore: true,        // (skip + limit) < totalCount
  totalSoulbound: 12,
  totalGolden: 8
}
```

### Pagination Logic

```javascript
let currentSkip = 0;
const LIMIT = 20;
let activeFilter = 'all'; // 'all' | 'soulbound' | 'golden'

async function loadMore() {
  currentSkip += LIMIT;
  const data = await api.getNFTInventory(state.walletAddress, currentSkip, LIMIT);
  appendToGrid(filterByType(data.nfts, activeFilter));
  if (!data.hasMore) hide('btn-load-more');
}
```

### Transfer Flow (Golden Only)

```javascript
async function transferSticker(assetId, receiverWallet) {
  // Backend handles the actual ASA transfer
  await api.transferNFT(assetId, receiverWallet);
  showToast('Sticker transferred!', 'success');
  closeModal();
  refreshInventory();
}
```

### Claim Flow (Pending NFTs)

```javascript
async function claimPending(nft) {
  // 1. Build opt-in txn (self-transfer, 0 amount)
  const params = await api.getTransactionParams();
  const optInTxn = algosdk.makeAssetTransferTxnWithSuggestedParamsFromObject({
    from: state.walletAddress,
    to: state.walletAddress,
    assetIndex: nft.assetId,
    amount: 0,
    suggestedParams: params
  });

  // 2. Sign with Pera
  const signedOptIn = await signTransactions([optInTxn.toByte()]);
  await api.submitTransaction(toBase64(signedOptIn[0]));

  // 3. Tell backend to deliver
  await api.claimPendingNFT(state.walletAddress, nft.id);
  showToast(`${nft.templateName} claimed!`, 'success');
  refreshInventory();
}
```

---

## 10. Screen 07 — Add Balance (DONE)

**File:** `07-add-balance.html`
**JS:** `js/07-add-balance.js` ✅ created

### Prerequisites
1. Add IDs to HTML elements
2. Add `<script type="module" src="js/07-add-balance.js"></script>`

### Backend Endpoints Used

| Action | Endpoint | Method | Body | Rate Limit |
|--------|----------|--------|------|:---:|
| Get config | `GET /onramp/config` | GET | — | No |
| Fund (sim) | `POST /simulate/fund-wallet` | POST | `{ walletAddress, amountAlgo }` | **3/min** |
| Order history | `GET /onramp/fan/{wallet}/orders` | GET | — | No |

### DOM Mapping (IDs to inject)

```
SIM BANNER:
  id="sim-banner"              ← "⚠ Simulation Mode" (check config.simulationMode)

FAUCET SECTION:
  id="btn-fund-1"              ← Quick-pick 1 ALGO
  id="btn-fund-2"              ← Quick-pick 2 ALGO
  id="btn-fund-5"              ← Quick-pick 5 ALGO (default selected)
  id="input-custom-fund"       ← Custom amount input (max 10 ALGO)
  id="btn-fund"                ← "Fund My Wallet" primary button

SUCCESS CARD:
  id="fund-success"            ← Hidden by default, shows after successful fund
  id="fund-tx-link"            ← Explorer link for the transaction
  id="fund-new-balance"        ← Updated balance

TOP-UP HISTORY:
  id="topup-list"              ← On-ramp order history items

TRANSAK (PRODUCTION):
  id="transak-section"         ← Greyed out when simulationMode
  id="transak-widget"          ← Widget embed area (future)
```

### Fund Flow

```javascript
async function fundWallet() {
  const amount = getSelectedAmount(); // from buttons or custom input
  if (amount > CONFIG.MAX_FUND_ALGO) {
    return showToast('Maximum 10 ALGO per transaction', 'warning');
  }

  setLoading(true);
  try {
    const result = await api.simulateFundWallet(state.walletAddress, amount);
    // Response: { status, txId, amountAlgo, wallet, message, explorerUrl }
    showSuccessCard({
      txId: result.txId,
      amount: result.amountAlgo,
      explorerUrl: result.explorerUrl,
    });
    refreshBalance();
    refreshTopUpHistory();
  } catch (err) {
    // 429 → "Rate limited: 3 requests per minute"
  } finally {
    setLoading(false);
  }
}
```

### On-Page Load

```javascript
// Check simulation mode
const config = await api.getOnrampConfig();
if (config.simulationMode) {
  show('sim-banner');
  disable('transak-section');
}
// Load order history
const orders = await api.getFanOnrampOrders(state.walletAddress);
renderTopUpHistory(orders);
```

---

## 11. Screen 08 — Leaderboard (DONE)

**File:** `08-leaderboard.html`
**JS:** `js/08-leaderboard.js` ✅ created

### Prerequisites
1. Add IDs to HTML elements
2. Add `<script type="module" src="js/08-leaderboard.js"></script>`

### Backend Endpoints Used

| Tab | Endpoint | Method | Response Shape |
|-----|----------|--------|----------------|
| Top Creators | `GET /leaderboard/global/top-creators?limit=20` | GET | `{ topCreators: [{ rank, creatorWallet, username, appId, totalAlgoReceived, uniqueFans }] }` |
| Top Fans | `GET /leaderboard/{creatorWallet}?limit=20` | GET | `{ creatorWallet, creatorUsername, totalFans, totalAlgoReceived, leaderboard: [{ rank, fanWallet, tipCount, totalAlgo, nftCount }] }` |

### DOM Mapping (IDs to inject)

```
HEADER STATS:
  id="stat-total-creators"     ← Total registered creators
  id="stat-total-algo"         ← Total ALGO tipped platform-wide
  id="stat-total-fans"         ← Total active fans

SEARCH:
  id="input-search"            ← Filter table by creator name/wallet

TAB NAVIGATION:
  id="tab-creators"            ← "Top Creators" tab button
  id="tab-fans"                ← "Top Fans" tab button

CREATOR TABLE:
  id="creator-table"           ← Table container (shown on Top Creators tab)
  id="creator-table-body"      ← Table body for rows

FAN TABLE:
  id="fan-table"               ← Table container (shown on Top Fans tab)
  id="fan-table-body"          ← Table body for rows
  id="select-creator"          ← Dropdown to pick which creator to show fans for
```

### Row Click Navigation

```javascript
// When a creator row is clicked, navigate to their tip page
row.onclick = () => window.location.href = `03-fan-tip-page.html?creator=${creatorWallet}`;
```

### Creator Table Rendering

```javascript
async function loadCreatorLeaderboard() {
  const data = await api.getGlobalTopCreators(20);
  const tbody = document.getElementById('creator-table-body');
  tbody.innerHTML = data.topCreators.map(c => `
    <tr class="hover:bg-slate-50 cursor-pointer"
        onclick="window.location='03-fan-tip-page.html?creator=${c.creatorWallet}'">
      <td class="py-4 px-6 text-center font-bold">${c.rank}</td>
      <td class="py-4 px-6">
        <div class="font-semibold">${c.username || truncateAddress(c.creatorWallet)}</div>
        <div class="text-xs text-slate-500 font-mono">${truncateAddress(c.creatorWallet)}</div>
      </td>
      <td class="py-4 px-6 text-right font-mono font-medium">${formatAlgo(c.totalAlgoReceived)}</td>
      <td class="py-4 px-6 text-right">${c.uniqueFans || '—'}</td>
      <td class="py-4 px-6 text-right font-mono text-xs">APP-${c.appId}</td>
    </tr>
  `).join('');
}
```

---

## 12. Screen 09 — About & 404 (DONE)

**File:** `09-about-and-404.html`
**JS:** `js/09-about.js` ✅ created

### Prerequisites
1. Add IDs to FAQ accordion elements
2. Add `<script type="module" src="js/09-about.js"></script>`

### Backend Calls: NONE (Static Content)

### Integration Points

| Element | Action |
|---------|--------|
| FAQ accordion buttons | Toggle `.hidden` on answer panels (pure JS, no API) |
| Nav "Connect Wallet" | `connectWallet()` from shared.js |
| "Go Home" link (404 section) | Navigate to `01-landing-page.html` |
| "Start Tipping" CTA | Navigate to `08-leaderboard.html` or `03-fan-tip-page.html` |

### FAQ Toggle Logic

```javascript
document.querySelectorAll('[data-faq-toggle]').forEach(btn => {
  btn.onclick = () => {
    const answer = btn.nextElementSibling;
    const icon = btn.querySelector('.material-symbols-outlined');
    answer.classList.toggle('hidden');
    icon.style.transform = answer.classList.contains('hidden') ? '' : 'rotate(180deg)';
  };
});
```

---

## 13. Backend Route Summary

Complete listing of all backend routes, verified against `backend/main.py` and route files:

### Core Routes (Always Available)

| Route | Method | File | Purpose |
|-------|--------|------|---------|
| `/health` | GET | `health.py` | Algorand node status |
| `/params` | GET | `params.py` | Suggested transaction params (cached 60s) |
| `/submit` | POST | `transactions.py` | Submit single signed txn |
| `/submit-group` | POST | `transactions.py` | Submit atomic txn group |
| `/contract/info` | GET | `contracts.py` | Contract compilation info |
| `/contract/list` | GET | `contracts.py` | List available contracts |
| `/contract/deploy` | POST | `contracts.py` | Create unsigned deploy txn |
| `/contract/fund` | POST | `contracts.py` | Create unsigned fund txn |

### Creator Routes (`/creator` prefix)

| Route | Method | Auth | Purpose |
|-------|--------|:---:|---------|
| `/creator/register` | POST | No¹ | Register + deploy TipProxy |
| `/creator/{wallet}/contract` | GET | No | Get active contract |
| `/creator/{wallet}/contract/stats` | GET | No | On-chain global state |
| `/creator/{wallet}/dashboard` | GET | No | Combined analytics |
| `/creator/{wallet}/upgrade-contract` | POST | ✅ | Deploy new version |
| `/creator/{wallet}/pause-contract` | POST | ✅ | Unsigned pause txn |
| `/creator/{wallet}/unpause-contract` | POST | No² | Unsigned unpause txn |
| `/creator/{wallet}/sticker-template` | POST | ✅ | Create template (multipart) |
| `/creator/{wallet}/templates` | GET | No | List templates |
| `/creator/{wallet}/template/{id}` | DELETE | No² | Delete template |

¹ Rate limited: 5/hour per IP
² Known auth gap

### Fan Routes (`/fan` prefix)

| Route | Method | Purpose |
|-------|--------|---------|
| `/fan/{wallet}/inventory` | GET | Paginated NFT inventory |
| `/fan/{wallet}/pending` | GET | Undelivered NFTs |
| `/fan/{wallet}/claim/{nft_id}` | POST | Deliver after opt-in |
| `/fan/{wallet}/stats` | GET | Tipping statistics |
| `/fan/{wallet}/golden-odds` | GET | Golden probability |

### Leaderboard Routes (`/leaderboard` prefix)

| Route | Method | Purpose |
|-------|--------|---------|
| `/leaderboard/{wallet}` | GET | Top fans for a creator |
| `/leaderboard/global/top-creators` | GET | Global creator rankings |

### NFT Routes (`/nft` prefix)

| Route | Method | Purpose |
|-------|--------|---------|
| `/nft/mint/soulbound` | POST | Mint soulbound (backend only) |
| `/nft/mint/golden` | POST | Mint golden (backend only) |
| `/nft/transfer` | POST | Transfer golden NFT |
| `/nft/optin` | POST | Create unsigned opt-in txn |
| `/nft/inventory/{wallet}` | GET | Paginated NFT list |
| `/nft/{asset_id}` | GET | Single NFT details |

### On-Ramp Routes (`/onramp` + `/simulate`)

| Route | Method | Limit | Purpose |
|-------|--------|:---:|---------|
| `/onramp/config` | GET | — | Simulation mode flag |
| `/onramp/create-order` | POST | — | Create on-ramp order |
| `/onramp/webhook` | POST | — | Transak callback (production) |
| `/onramp/order/{id}` | GET | — | Order status |
| `/onramp/fan/{wallet}/orders` | GET | — | Fan's order history |
| `/simulate/fund-wallet` | POST | **3/min** | TestNet faucet |

### System Routes

| Route | Method | Purpose |
|-------|--------|---------|
| `/listener/status` | GET | Transaction listener state |

---

## 14. Integration Phases

### Phase 1 — Foundation ✅ DONE
- [x] Create `js/shared.js` with API client, wallet manager, state, utils, toast
- [x] Add `<script type="module">` tags to screens 01-03
- [x] Add `id` attributes to interactive elements on screens 01-03
- [x] Verified: `healthCheck()` returns, wallet connects via Pera

### Phase 2 — Landing + Setup ✅ DONE
- [x] Wire `01-landing-page.html` navigation buttons + wallet connect
- [x] Wire `02-creator-setup-wizard.html` full 4-step flow
- [x] Tested: Creator connect → register → upload stickers → share link

### Phase 3 — Tip Flow ✅ DONE
- [x] Wire `03-fan-tip-page.html` complete tip-to-sticker flow
- [x] Transaction construction with algosdk
- [x] Pera signing → submit → poll → opt-in → claim
- [x] Transaction stepper UI

### Phase 4 — Dashboards ⏳ NEXT
- [ ] Inject IDs into `04-creator-dashboard.html`
- [ ] Create `js/04-creator-dashboard.js`
  - [ ] 4 stat cards from dashboard + contract/stats
  - [ ] Sticker grid with add/delete (reuse FormData pattern)
  - [ ] Top fans table from leaderboard
  - [ ] Contract actions: pause/unpause/upgrade (Pera signing)
  - [ ] Listener status section
  - [ ] Recent transactions table
  - [ ] Auto-refresh every 30s
- [ ] Inject IDs into `05-fan-dashboard.html`
- [ ] Create `js/05-fan-dashboard.js`
  - [ ] 4 stat cards from fan/stats
  - [ ] Recent tips list
  - [ ] Creator breakdown cards with "Tip Again" links
  - [ ] Golden odds section with amount calculator
  - [ ] Balance display + "Add Balance" link

### Phase 5 — Inventory + Balance ⏳
- [ ] Inject IDs into `06-sticker-inventory.html`
- [ ] Create `js/06-inventory.js`
  - [ ] Load NFT grid from `/nft/inventory/{wallet}` (paginated)
  - [ ] Filter tabs (All / Soulbound / Golden) using response counts
  - [ ] Click card → detail modal
  - [ ] Transfer golden stickers (recipient input → `api.transferNFT`)
  - [ ] Pending stickers banner + claim flow (opt-in via Pera → claim)
  - [ ] "Load More" pagination
- [ ] Inject IDs into `07-add-balance.html`
- [ ] Create `js/07-add-balance.js`
  - [ ] Check `onramp/config` → show/hide sim banner
  - [ ] Quick-pick amount buttons + custom input
  - [ ] Fund via `simulate/fund-wallet` (handle 429 rate limit)
  - [ ] Success card with TX link
  - [ ] Top-up history from `onramp/fan/{w}/orders`

### Phase 6 — Secondary + Polish ⏳
- [ ] Inject IDs into `08-leaderboard.html`
- [ ] Create `js/08-leaderboard.js`
  - [ ] Top creators table from `/leaderboard/global/top-creators`
  - [ ] Fan leaderboard tab from `/leaderboard/{wallet}`
  - [ ] Tab switching logic
  - [ ] Creator selector dropdown
  - [ ] Click row → navigate to tip page
  - [ ] Search/filter
- [ ] Inject IDs into `09-about-and-404.html`
- [ ] Create `js/09-about.js`
  - [ ] FAQ accordion toggle
  - [ ] Nav wallet connect + redirect
- [ ] All screens: loading states / skeleton shimmer
- [ ] All screens: empty states for zero-data scenarios
- [ ] All screens: error recovery (retry buttons)
- [ ] End-to-end test: full creator + fan flow on TestNet

---

## 15. Error Handling Matrix

| HTTP Code | Meaning | User-Facing Message | Action |
|-----------|---------|---------------------|--------|
| `400` | Validation error | Show `response.detail` directly | Highlight invalid field |
| `401` | No wallet header | "Please connect your wallet" | Trigger wallet connect |
| `403` | Wallet mismatch | "Permission denied. Wrong wallet?" | Show disconnect option |
| `404` | Resource not found | "Not found" | Navigate away or show empty state |
| `409` | Conflict | Show `response.detail` (duplicate, has NFTs) | Prevent duplicate action |
| `429` | Rate limited | "Too many requests. Try again in Xs" | Disable button, show countdown |
| `500` | Server error | "Something went wrong. Please try again." | Log to console |
| Network | Fetch failed | "Cannot reach server. Check connection." | Show retry button |

### Error Response Formats

```javascript
// HTTPException (most endpoints):
{ "detail": "Human-readable error message" }

// Global catch-all (unhandled errors):
{ "error": "Internal server error" }

// API client checks BOTH:
const message = err.detail || err.error || 'Unknown error';
```

### Screen-Specific Error Handling

| Screen | Error | Response |
|--------|-------|----------|
| Creator Setup | Already registered | `409` → "You're already registered" toast |
| Creator Setup | Max stickers | `400` → "20/20 slots used" toast |
| Creator Setup | Duplicate template | `409` → "Template at this threshold exists" toast |
| Creator Dashboard | Delete with mints | `409` → "Cannot delete — NFTs minted" toast |
| Fan Tip Page | Low balance | Pre-submit check → "Need X ALGO" warning |
| Fan Tip Page | Contract paused | Pre-submit check → "Creator paused" banner |
| Add Balance | Rate limited | `429` → "3 requests per minute" toast |
| Inventory | Transfer failed | `400` → Show error detail |

---

## 16. Testing Checklist

### Per-Screen Tests

#### ✅ Landing Page (Done)
- [x] Nav buttons navigate correctly
- [x] Wallet connect shows address in nav
- [x] "Sign In" detects creator vs fan role

#### ✅ Creator Setup Wizard (Done)
- [x] Step 1: Pera wallet connects, shows address
- [x] Step 2: Register with valid username + min tip deploys contract
- [x] Step 3: Upload sticker with image, name, threshold
- [x] Step 4: Copy link works, dashboard button navigates

#### ✅ Fan Tip Page (Done)
- [x] Creator header loads real data
- [x] Sticker gallery shows actual templates
- [x] Quick-pick buttons update amount + preview
- [x] Tip flow: sign → submit → confirm → sticker arrives (stepper)

#### ✅ Creator Dashboard (Done)
- [x] All 4 stat cards show real numbers
- [x] Sticker grid shows actual templates with mint counts
- [x] "X/20 slots used" counter is accurate
- [x] Add sticker redirects to wizard step 3
- [ ] Delete sticker with 0 mints succeeds
- [ ] Delete sticker with mints fails (409)
- [x] Top fans table loads from leaderboard
- [x] Contract info shows real App ID, version, status
- [x] Pause triggers confirmation → contract pauses
- [x] Unpause triggers confirmation → contract unpauses
- [x] System status shows listener state
- [x] Recent transactions table updates
- [ ] Auto-refresh every 30s works

#### ✅ Fan Dashboard
- [x] Stats load from `/fan/{wallet}/stats`
- [x] Recent tips show with correct formatting
- [x] Creator breakdown cards render with "Tip Again" link
- [x] Golden odds section shows probability
- [x] Balance shows actual wallet balance
- [x] "Add Balance" navigates correctly

#### ✅ Sticker Inventory
- [x] Grid loads with pagination
- [x] Filter tabs work (All / Soulbound / Golden)
- [x] Tab counts match response `totalSoulbound` / `totalGolden`
- [x] Clicking card opens detail modal with full info
- [x] Transfer section appears for golden only
- [x] Transfer to valid address succeeds
- [ ] "Load More" fetches next page (pagination wired but needs backend verify)
- [ ] Pending stickers banner shows claim button (future enhancement)
- [ ] Claim flow: opt-in → sign → submit → claim → delivered (future enhancement)

#### ✅ Add Balance
- [x] Sim mode banner shows when `config.simulationMode`
- [x] Quick-pick buttons select amount
- [x] Fund button sends to backend
- [x] Success card shows with tx link + new balance
- [x] Rate limit toast on 429 (3/min)
- [x] Recent top-ups list tracks session history
- [ ] Transak section (future production feature)

#### ✅ Leaderboard
- [x] Top creators table loads from backend
- [x] Tab switching works (Creators ↔ Fans)
- [x] Creator selector dropdown populates
- [x] Fan leaderboard loads per creator
- [x] Clickable rows navigate to tip page
- [x] Search filters the table

#### ✅ About & 404
- [x] FAQ accordion toggles open/close
- [x] Nav wallet connect works
- [x] "Go Home" navigates to landing page
- [x] "Go Back" uses browser history

### End-to-End Flow
- [ ] **Creator flow:** Connect → Register → Upload 3 stickers → Share link → View dashboard
- [ ] **Fan flow:** Connect → Fund wallet → Tip creator → Receive sticker → View in inventory
- [ ] **Transfer:** Fan transfers golden sticker to another wallet
- [ ] **Dashboard verification:** Creator dashboard reflects the fan's tip
- [ ] **Leaderboard:** Both creator and fan appear in leaderboard
- [ ] **Balance:** Add Balance page funds wallet, balance updates

---

## Backend API Reference

```
Development:  http://localhost:8000
Swagger UI:   http://localhost:8000/docs
OpenAPI JSON: http://localhost:8000/openapi.json
```
