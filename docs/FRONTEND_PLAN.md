# FanForge — Frontend Implementation Plan

> **Scope:** Build a complete, production-grade multi-page frontend.
> **Design Direction:** Stripe × Coinbase × Linear — institutional clarity, not meme crypto.
> **Rule:** ZERO manual address/mnemonic entry. Everything via Pera Wallet.
> **Stack:** Next.js (preferred) or Vite + React. The vanilla HTML/CSS/JS frontend has been removed.
> **Backend:** FastAPI, security-hardened. Amounts stored as microAlgos (BigInteger). See integration notes below.
> **Last Updated:** 2026-02-18

---

## Table of Contents

1. [Design Philosophy](#1-design-philosophy)
2. [Design System](#2-design-system)
3. [Wallet Security Architecture](#3-wallet-security-architecture)
4. [Backend Integration](#4-backend-integration)
5. [Phase 0: Infrastructure](#5-phase-0-infrastructure)
6. [Phase 1: Core Pages](#6-phase-1-core-pages)
7. [Phase 2: Dashboard & Inventory](#7-phase-2-dashboard--inventory)
8. [Phase 3: Secondary Pages](#8-phase-3-secondary-pages)
9. [Section Architecture](#9-section-architecture)
10. [Build Order](#10-build-order)

---

## 1. Design Philosophy

### Strategic Positioning

FanForge is a **financial platform**, not a meme crypto project. Every design decision must communicate trust, clarity, and professionalism.

| ❌ Remove | ✅ Add |
|-----------|--------|
| Cartoonish tone | Structured hierarchy |
| Floating chaos elements | Intentional spacing |
| Overly colorful 3D | Controlled brand palette |
| Casual typography | Authority typography |
| Glassmorphism cards | Subtle depth cards |
| Neon gradients | Restrained accents |
| Bounce/parallax animations | Confident, subtle motion |

### Visual Identity

The evolved direction should feel like:

- **Stripe-level** clarity
- **Coinbase-level** trust
- **Linear-level** minimalism

Modern UI = generous whitespace + minimal color + clear hierarchy + subtle depth + strong typography + clean motion. Modern ≠ flashy.

---

## 2. Design System

### 2A. Color System (Slate-Based Professional)

```css
/* ── Base System ─────────────────────────────────────── */
--bg-primary:     #FFFFFF;
--bg-secondary:   #F8FAFC;
--bg-elevated:    #F1F5F9;

--text-primary:   #0F172A;
--text-secondary: #475569;
--text-muted:     #64748B;

--border-subtle:  #E2E8F0;
--border-default: #CBD5E1;

/* ── Primary Accent (Professional Blue) ──────────────── */
--accent-primary:   #2563EB;
--accent-hover:     #1D4ED8;
--accent-active:    #1E40AF;
--accent-light:     rgba(37, 99, 235, 0.08);   /* backgrounds */
--accent-shadow:    rgba(37, 99, 235, 0.20);   /* button glow */

/* ── Semantic Colors ─────────────────────────────────── */
--color-success:    #059669;
--color-warning:    #D97706;
--color-error:      #DC2626;
--color-info:       #2563EB;

/* ── Footer / Dark Sections ──────────────────────────── */
--dark-bg:          #0F172A;
--dark-text:        #CBD5E1;
--dark-muted:       #64748B;
```

**Accent Rule:** You get **1 primary color** and **1 subtle highlight tone**. No random purple + yellow combos in layout. Golden sticker badges use `--color-warning` sparingly.

### 2B. Typography (60% of Perceived Professionalism)

```css
/* Font: Inter (Google Fonts) — safe, SaaS standard */
/* Alternatives: Plus Jakarta Sans, Satoshi, General Sans */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
```

**Hierarchy Structure:**

| Element | Size | Weight | Line Height | Max Width | Color |
|---------|------|--------|-------------|-----------|-------|
| Hero headline | 64px | 700 | 1.05 | 720px | `--text-primary` |
| Section heading | 40px | 600 | 1.15 | — | `--text-primary` |
| Subheading | 18–20px | 400 | 1.5 | 560px | `--text-secondary` |
| Body | 16px | 400 | 1.6 | 640px | `--text-secondary` |
| Small / labels | 14px | 500 | 1.4 | — | `--text-muted` |
| Micro / captions | 12px | 500 | 1.3 | — | `--text-muted` |
| Eyebrow label | 14px | 600 | 1.3 | — | `--accent-primary` |

**Avoid:** Overly rounded fonts, excessive italics, playful typefaces.

### 2C. Layout System (Institutional Grid)

```css
/* Container */
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
}

/* Section Spacing */
.section          { padding: 96px 0; }
.section--compact { padding: 72px 0; }
.section--hero    { padding: 120px 0; }

/* Do NOT vary spacing randomly. Consistency kills credibility issues. */
```

### 2D. Component Tokens

**Navigation Bar:**
```css
.nav {
  height: 72px;
  position: sticky;
  top: 0;
  z-index: 100;
  background: #FFFFFF;
  border-bottom: 1px solid var(--border-subtle);
  backdrop-filter: blur(12px);
  background: rgba(255, 255, 255, 0.95);
}
```

**Primary Button:**
```css
.btn-primary {
  height: 48px;
  padding: 0 24px;
  border-radius: 12px;
  font-weight: 500;
  font-size: 15px;
  background: var(--accent-primary);
  color: #FFFFFF;
  border: none;
  box-shadow: 0 4px 12px var(--accent-shadow);
  transition: all 200ms ease-out;
}
.btn-primary:hover {
  background: var(--accent-hover);
  transform: translateY(-1px);
  box-shadow: 0 6px 16px var(--accent-shadow);
}
```

**Secondary Button:**
```css
.btn-secondary {
  height: 48px;
  padding: 0 24px;
  border-radius: 12px;
  font-weight: 500;
  font-size: 15px;
  background: #FFFFFF;
  color: var(--text-primary);
  border: 1px solid var(--border-default);
  transition: all 200ms ease-out;
}
.btn-secondary:hover {
  background: var(--bg-secondary);
  border-color: var(--border-subtle);
}
```

**Card (Premium — Subtle Depth):**
```css
.card {
  background: #FFFFFF;
  border: 1px solid var(--border-subtle);
  border-radius: 16px;
  box-shadow: 0 4px 16px rgba(15, 23, 42, 0.05);
  padding: 24px;
  transition: box-shadow 200ms ease-out, transform 200ms ease-out;
}
.card:hover {
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
  transform: translateY(-2px);
}
```

No heavy shadow. No glassmorphism. No neon gradients. Professional UI uses subtle depth.

**Stat Card:**
```css
.stat-card {
  background: #FFFFFF;
  border: 1px solid var(--border-subtle);
  border-radius: 16px;
  padding: 24px;
  text-align: center;
}
.stat-card__number {
  font-size: 36px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.1;
}
.stat-card__label {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-muted);
  margin-top: 4px;
}
```

### 2E. Motion Philosophy

Motion must feel **confident, subtle, smooth**.

```css
/* Standard transition */
transition: all 200ms ease-out;

/* Use: */
/* - Fade-in on scroll (IntersectionObserver) */
/* - 2px hover lift on cards */
/* - Subtle button press scale(0.98) */

/* Avoid: */
/* - Bounce */
/* - Parallax */
/* - Dramatic float loops */
/* - Heavy entrance animations */
```

### 2F. Visual Depth Strategy

The **only** background treatment allowed:

```css
/* Subtle radial highlight in hero section ONLY */
.hero {
  background: radial-gradient(
    circle at 50% 30%,
    rgba(37, 99, 235, 0.06),
    transparent 60%
  );
}
```

No busy backgrounds. No heavy gradients everywhere.

### 2G. Iconography

| ✅ Use | ❌ Avoid |
|--------|----------|
| Outline icons (Lucide, Heroicons) | Emoji in UI (except sticker badges) |
| 1.5–2px stroke weight | Multicolor cartoon icons |
| Neutral color (`--text-muted`) | Stock random icon packs |
| Minimal fill | Filled heavy icons |

### 2H. Consistency Rules

To look modern, enforce these globally:

- **Same border radius** everywhere: 12px (buttons, inputs) or 16px (cards, modals)
- **Same button height** everywhere: 48px (primary), 40px (compact)
- **Same grid spacing** everywhere: 24px gap
- **Same icon style** everywhere: outline, 20px, 1.5px stroke
- **Inconsistency kills credibility.**

---

## 3. Wallet Security Architecture

### The Rule

**No user (creator or fan) should EVER provide a mnemonic or private key to this application.**

Every signing interaction goes through **Pera Wallet Connect**:
1. User clicks button in UI
2. Frontend builds **unsigned transaction**
3. Pera Wallet opens → user approves
4. Frontend receives **signed bytes** → submits to chain/backend

The **only** server-side key is `PLATFORM_MNEMONIC` in `.env` — used for contract deployment and NFT minting. Users never see this.

### Transaction Signing Map

| User Action | Transaction Built | Signed By |
|-------------|-------------------|-----------|
| Fan tips creator | Atomic group: PaymentTxn + ApplicationCallTxn | Fan via Pera |
| Fan opts into NFT ASA | AssetTransferTxn (self-transfer, amt=0) | Fan via Pera |
| Fan transfers golden NFT | AssetTransferTxn (fan → recipient) | Fan via Pera |
| Creator pauses contract | ApplicationCallTxn (pause method) | Creator via Pera |
| Creator unpauses contract | ApplicationCallTxn (unpause method) | Creator via Pera |
| Creator registers | No signing — backend deploys via PLATFORM wallet | Platform (server) |
| NFT minting | No signing — backend mints via PLATFORM wallet | Platform (server) |
| NFT delivery | Clawback (soulbound) or transfer (golden) | Platform (server) |

### Production Opt-In Flow

```
DEMO MODE (current — TestNet only):
  Listener detects tip → mint NFT → auto-opt-in fan using demo mnemonic → transfer
  ⚠ Requires fan's private key on the server

PRODUCTION MODE (Pera Wallet):
  1. Fan connects Pera Wallet on tip page
  2. Frontend checks if fan needs to opt-in to sticker ASAs
     → GET /creator/{wallet}/templates → get all template info
     → Check fan's account for existing opt-ins
     → If missing: create opt-in txn → Pera signs → submit
  3. Fan tips → Pera signs atomic group → submit
  4. Listener detects tip → mint NFT → fan already opted in → transfer ✅
     No fan private key needed!
```

---

## 4. Backend Integration

### 4A. Recent Backend Changes (Must Reflect in Frontend)

| Change | Impact on Frontend |
|--------|-------------------|
| **`amount_algo` → `amount_micro` (BigInteger)** | API responses still return `"amountAlgo"` as float (converted at boundary). Frontend uses `formatAlgo()` helper for display. No raw microAlgo math in frontend. |
| **Listener state persisted (DB)** | `GET /listener/status` now returns `lastProcessedRound`, `errorsCount`, `pollIntervalSeconds`, `retryEnabled`, `maxRetryAttempts`. Dashboard shows accurate state. |
| **Retry task for failed mints** | `GET /listener/status` includes `retryEnabled: true, maxRetryAttempts: 3`. Show retry status on system health panel. |
| **Alembic migrations** | No frontend impact. Schema changes are now tracked. |
| **Lazy loading relationships** | API response shapes unchanged. Queries are more efficient. |
| **Indexer pagination** | No missed transactions. Listener is more reliable. |
| **Creator-configurable min_tip_algo** | `POST /creator/register` accepts `minTipAlgo` field (0.1–1000 ALGO, default 1.0). Creator setup wizard should include min tip amount input. |
| **Sticker template limits** | Max 20 templates per creator. Backend returns **400** (not 409) when limit reached. Show count: "3/20 sticker slots used". |
| **Duplicate template prevention** | Backend returns **409** on duplicate threshold+type+category. Show appropriate conflict error. |

### 4B. Authentication Header

All state-changing endpoints require `X-Wallet-Address` header matching the URL path wallet.

```javascript
// In API wrapper — automatically attach auth header
async function authRequest(method, path, body = null) {
  const wallet = getConnectedAddress();
  if (!wallet) throw new Error('Wallet not connected');
  return request(method, path, body, {
    headers: { 'X-Wallet-Address': wallet }
  });
}
```

**Authenticated endpoints** (use `require_wallet_auth` / `X-Wallet-Address`):
- `POST /creator/{wallet}/upgrade-contract`
- `POST /creator/{wallet}/pause-contract`
- `POST /creator/{wallet}/sticker-template`

> **Note:** `POST /creator/{wallet}/unpause-contract` and `DELETE /creator/{wallet}/template/{id}` do **not** currently enforce wallet auth — they validate the wallet via URL path matching only. This is a known gap tracked in the Production Roadmap.

**Error handling:**
- `400` → validation error (e.g., max 20 templates reached, invalid sticker type)
- `401` → prompt wallet connection
- `403` → "Permission denied" toast
- `409` → conflict (duplicate template threshold/type combo, or trying to delete template with minted NFTs)
- `429` → "Too many requests. Please wait." toast with `Retry-After` header

### 4C. Pagination

Inventory endpoints support `skip` and `limit`:
```
GET /fan/{wallet}/inventory?skip=0&limit=20
→ {
    wallet: "...",
    nfts: [...],           // array of NFT objects
    total: 20,             // items in THIS page
    totalCount: 87,        // total items across ALL pages
    skip: 0,
    limit: 20,
    hasMore: true,         // (skip + limit) < totalCount
    totalSoulbound: 12,
    totalGolden: 8
  }
```

Implement "Load More" button using `hasMore` flag, incrementing `skip` by `limit`.

### 4D. Error Format

HTTPException errors return:
```json
{ "detail": "Human-readable error message" }
```

Unhandled exceptions return (global catch-all handler):
```json
{ "error": "Internal server error" }
```

In the API client, check for BOTH `response.detail` and `response.error` when extracting messages.

### 4E. Rate Limiting

Only these endpoints have rate limiting:

| Endpoint | Limit |
|----------|-------|
| `POST /creator/register` | 5 requests / hour |
| `POST /simulate/fund-wallet` | 3 requests / minute |

All other endpoints are **unrate-limited**. The rate limiter returns headers:
- `Retry-After` — seconds until window resets
- `X-RateLimit-Limit` — max requests in window
- `X-RateLimit-Remaining` — requests left in window

---

## 5. Phase 0: Infrastructure

Everything below must be built before ANY page. These are shared modules.

### 5A. Config (`lib/config.ts`)

```typescript
export const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
export const EXPLORER_BASE = 'https://lora.algokit.io/testnet';
export const IPFS_GATEWAY = 'https://gateway.pinata.cloud/ipfs';
export const NETWORK = 'testnet';
export const POLL_INTERVAL_MS = 4000;
export const TOAST_DURATION_MS = 5000;
export const MAX_STICKER_TEMPLATES = 20;
export const MIN_TIP_THRESHOLD = 0.1;
export const MAX_TIP_THRESHOLD = 10000;
```

### 5B. API Client (`lib/api.ts`)

Central fetch wrapper for ALL backend calls. Every page imports this.

```typescript
// Core: handles JSON, errors, auth headers
async function request(method, path, body?, options?) {
  // Prepends API_BASE
  // Sets Content-Type: application/json (unless multipart)
  // Attaches X-Wallet-Address if options.authenticated
  // On 401: trigger wallet reconnect
  // On 403: "Permission denied" toast
  // On 429: "Too many requests" toast
  // On 409: "Duplicate" toast (sticker template conflict)
  // On 4xx: throw with response.detail
  // On 5xx: "Something went wrong" message
}

// Named exports for every endpoint:
// Creator endpoints
export async function registerCreator(wallet, username, minTipAlgo = 1.0)
export async function getCreatorContract(wallet)
export async function getCreatorContractStats(wallet)
export async function getCreatorDashboard(wallet)
export async function getCreatorTemplates(wallet)
export async function createStickerTemplate(wallet, formData)  // AUTH + multipart
export async function deleteStickerTemplate(wallet, templateId) // no auth currently
export async function pauseContract(wallet)                     // AUTH
export async function unpauseContract(wallet)                   // no auth currently
export async function upgradeContract(wallet)                   // AUTH

// Fan endpoints
export async function getFanInventory(wallet, skip?, limit?)    // paginated
export async function getFanPending(wallet)
export async function claimPendingNFT(wallet, nftId)
export async function getFanStats(wallet)
export async function getGoldenOdds(wallet, amountAlgo)         // query param: amount_algo

// NFT endpoints
export async function getNFTDetails(assetId)
export async function createOptIn(request)                      // { assetId, fanWallet }
export async function transferNFT(request)                      // { assetId, receiverWallet } — golden only
export async function getNFTInventory(wallet, skip?, limit?)    // GET /nft/inventory/{wallet}

// Transaction endpoints
export async function getTransactionParams()
export async function submitTransaction(signedTxn)              // POST /submit → body: { signed_txn: "base64..." }
export async function submitGroup(signedTxns)                   // POST /submit-group → body: { signed_txns: ["b64...", ...] }
                                                                // ⚠ These use snake_case (no alias), unlike V4 models

// Leaderboard endpoints
export async function getCreatorLeaderboard(wallet, limit?)
export async function getGlobalTopCreators(limit?)

// On-ramp endpoints
export async function getOnrampConfig()
export async function createOnrampOrder(req)                    // POST /onramp/create-order
export async function getOnrampOrderStatus(partnerOrderId)      // GET /onramp/order/{partner_order_id}
export async function getFanOnrampOrders(wallet)                // GET /onramp/fan/{wallet}/orders
export async function simulateFundWallet(wallet, amountAlgo)    // POST /simulate/fund-wallet

// System endpoints
export async function getListenerStatus()                       // GET /listener/status
export async function healthCheck()                             // GET /health

// Contract endpoints (boilerplate — alternative to /creator/register)
export async function getContractInfo(name?)                    // GET /contract/info?name=tip_proxy
export async function listContracts()                           // GET /contract/list
export async function deployContract(sender, contractName?)     // POST /contract/deploy → unsigned txn for Pera
export async function fundContract(sender, appId, amount?)      // POST /contract/fund → unsigned txn for Pera
// Note: Primary flow uses POST /creator/register (platform deploys).
// These endpoints are for advanced use (creator self-deploys via Pera signing).
```

### 5C. Wallet Manager (`lib/wallet.ts`)

The ONLY module that imports Pera Wallet SDK.

```typescript
// State
let peraWallet: PeraWalletConnect | null;
let connectedAccount: string | null;

export async function initWallet()       // reconnect from saved session
export async function connectWallet()    // peraWallet.connect() → dispatch event
export async function disconnectWallet() // peraWallet.disconnect() → dispatch event
export async function signTransactions(txns)  // sign single or group
export function getConnectedAddress(): string | null
export function isConnected(): boolean
export async function getBalance(address): number  // returns ALGO (not microAlgos)
```

### 5D. Global State (`lib/state.ts`)

```typescript
interface AppState {
  walletAddress: string | null;
  balance: number;
  role: 'creator' | 'fan' | null;
  isConnected: boolean;
}

export function getState(): AppState
export function setState(updates: Partial<AppState>): void
export function onStateChange(callback): void
// Persist role to localStorage; wallet comes from Pera reconnect
```

### 5E. Navigation Bar

```
┌─────────────────────────────────────────────────────────────────────┐
│  FanForge    [Explore]  [Leaderboard]  [About]         [Sign In]  │
│                                                   [Get Started →] │
└─────────────────────────────────────────────────────────────────────┘

When connected:
┌─────────────────────────────────────────────────────────────────────┐
│  FanForge    [Dashboard]  [My Stickers]  [Explore]                │
│                                    [Axf3…7Kq │ 12.5 ALGO │ ✕]    │
└─────────────────────────────────────────────────────────────────────┘
```

Rules:
- Height: 72px
- Sticky
- White background with subtle bottom border
- Right side: Sign In + Get Started (disconnected) or wallet info (connected)
- Clean. No icons in nav text. No gradients.
- Hamburger menu on mobile

### 5F. Toast System (`lib/toast.ts`)

```typescript
showToast('Tip sent! Waiting for NFT...', 'success');
showToast('Rate limit exceeded. Please wait.', 'error');
showToast('New sticker arrived!', 'info');

// Slides in from top-right, auto-dismiss after 5s
// Types: success (green), error (red), info (blue), warning (amber)
// No heavy shadows or gradient backgrounds — flat with subtle border
```

### 5G. Utilities (`lib/utils.ts`)

```typescript
export function truncateAddress(addr: string): string      // → "Axf3…7Kq"
export function formatAlgo(microAlgos: number): string     // → "12.345000"
export function formatAlgoFromFloat(algo: number): string  // → "12.35"
export function formatDate(isoString: string): string      // → "Feb 18, 2026"
export function formatTimeAgo(isoString: string): string   // → "2 hours ago"
export function formatNumber(n: number): string            // → "50,000+"
export function copyToClipboard(text: string): boolean
export function explorerLink(type, id): string             // full Lora URL
export function ipfsUrl(hash: string): string              // full IPFS gateway URL
```

---

## 6. Phase 1: Core Pages

### 6A. Landing Page (`/`)

**Purpose:** First impression. Route users to creator or fan flow. Communicate trust.

**Section Architecture (Professional SaaS Flow):**

```
1. HERO
   ├── Left side:
   │   ├── Eyebrow label: "Built on Algorand · Non-custodial"
   │   ├── Headline (64px, weight 700):
   │   │   "The creator economy,
   │   │    on-chain."
   │   ├── Subheading (18px, muted, max 560px):
   │   │   "Fans tip creators with ALGO. Creators reward fans
   │   │    with collectible NFT stickers. Every transaction
   │   │    is transparent, instant, and trustless."
   │   ├── Two CTAs:
   │   │   [Get Started →] (primary)    [Learn More] (secondary)
   │   └── Social proof: "Trusted by 20+ creators on TestNet"
   └── Right side:
       └── Clean product mockup (dashboard screenshot or minimal 3D)
           If using 3D: only 2–3 objects, subtle, balanced

2. LOGO CLOUD (if applicable)
   Grayscale logos · Low opacity · Even spacing
   "Built with" → Algorand, IPFS, Pera Wallet, Pinata

3. METRICS SECTION
   ┌──────────┐  ┌──────────┐  ┌──────────┐
   │  50K+    │  │  120+    │  │  ₹2Cr+   │
   │  Active  │  │ Verified │  │ Payments │
   │  Users   │  │ Creators │  │Processed │
   └──────────┘  └──────────┘  └──────────┘
   Big numbers. Small labels. (Pull from /leaderboard when real data exists)

4. PROBLEM STATEMENT
   "Platforms take 30-50% of creator earnings.
    Fans get nothing in return for their support."

5. SOLUTION BREAKDOWN (3 columns)
   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
   │ [icon]      │  │ [icon]      │  │ [icon]      │
   │ Direct Tips │  │ NFT Rewards │  │ Zero Fees   │
   │ Fans send   │  │ Earn unique │  │ No platform │
   │ ALGO direct │  │ stickers    │  │ middleman   │
   │ to creators │  │ as NFTs     │  │ cuts        │
   └─────────────┘  └─────────────┘  └─────────────┘

6. HOW IT WORKS (3 steps, numbered)
   Step 1: Connect Wallet → Step 2: Tip Creator → Step 3: Collect Stickers
   Clean numbered cards with description text.

7. STICKER TYPES (2 cards side by side)
   ┌──────────────────────┐  ┌──────────────────────┐
   │ Soulbound            │  │ Golden               │
   │ Non-transferable     │  │ Fully tradable       │
   │ Earned forever       │  │ Collectible rarity   │
   │ Proof of support     │  │ True digital         │
   │                      │  │ ownership            │
   └──────────────────────┘  └──────────────────────┘

8. SECURITY / TRUST CALLOUT
   Short lines in a subtle elevated section:
   • "Non-custodial wallet integration via Pera Wallet"
   • "Smart contracts deployed on Algorand — auditable on-chain"
   • "IPFS-pinned metadata — your stickers live forever"

9. FINAL CTA
   "Ready to change how creators earn?"
   [Start as Creator →]    [Start as Fan →]

10. FOOTER (dark slate)
    background: #0F172A; color: #CBD5E1;
    Columns: Product | Developers | Company | Legal
    Subtle divider lines. Copyright line.
```

**Data sources:**
- `GET /health` → node status in nav
- `GET /leaderboard/global/top-creators?limit=3` → social proof
- If connected via Pera: "Welcome back" + direct dashboard link

### 6B. Creator Setup Wizard (`/creator/setup`)

**Purpose:** 4-step onboarding: Connect → Deploy → Upload Stickers → Share.

**Layout: Horizontal stepper with progress indicator**

```
Step 1 of 4: Connect Wallet
────●────────○────────○────────○────

┌─────────────────────────────────────────────────────┐
│                                                     │
│  Connect Your Wallet                                │
│                                                     │
│  Connect your Pera Wallet to get started.          │
│  Your wallet address is your creator identity.      │
│                                                     │
│  [Connect Pera Wallet]                              │
│                                                     │
│  ✓ Connected: Axf3…7Kq  ·  12.5 ALGO              │
│                                          [Next →]   │
└─────────────────────────────────────────────────────┘
```

**Step 2: Deploy Tip Jar**
- Username input (optional)
- **Minimum Tip Amount** input: 0.1–1000 ALGO, default 1.0 ← NEW
- `POST /creator/register` → backend deploys TipProxy
- Response includes `appId`, `appAddress`, `minTipAlgo`
- Show explorer link

**Step 3: Upload Stickers**
- Drag & drop image upload
- Fields: Name, Type (Soulbound/Golden), Threshold (0.1–10,000 ALGO)
- Counter: "3/20 sticker slots used" ← NEW (max 20 per creator)
- `POST /creator/{wallet}/sticker-template` (multipart, AUTH)
- On 409: "You already have a template at this threshold" ← NEW
- Grid of uploaded stickers with delete option

**Step 4: Share Tip Link**
- Generated link with copy button
- Navigate to dashboard

### 6C. Fan Tip Page (`/tip/{creatorWallet}`)

**Purpose:** Core fan experience. Browse stickers → tip → see NFT arrive.

**Layout:**

```
┌─────────────────────────────────────────────────────┐
│  [Nav]                                              │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Creator Name                                       │
│  Axf3…7Kq  ·  47 tips received                     │
│                                                     │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Earn Stickers by Tipping                           │
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐         │
│  │  [img]   │  │  [img]   │  │  [img]   │         │
│  │  Butki   │  │  Bauni   │  │  Shawty  │         │
│  │  1 ALGO  │  │  2 ALGO  │  │  5 ALGO  │         │
│  │ Soulbound│  │ Soulbound│  │  Golden  │         │
│  └──────────┘  └──────────┘  └──────────┘         │
│                                                     │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Tip Amount                                         │
│  [1 ALGO] [2 ALGO] [5 ALGO]   Custom: [___] ALGO  │
│                                                     │
│  Memo (optional): [________________________]        │
│                                                     │
│  You'll earn: Shawty (Golden ⭐)                    │
│  ← updates real-time based on tip amount            │
│                                                     │
│  [Send 5 ALGO →]                                   │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**Post-Tip Flow (Transaction Progress):**
```
① Signing… (Pera Wallet prompt)
② Submitting to Algorand…
③ Confirmed! Waiting for sticker…
④ Your Shawty sticker arrived!
   [View in My Stickers →]  [View on Explorer →]
```

**Logic:**
1. Parse `creatorWallet` from URL → `getCreatorContract()` → validate
2. `getCreatorTemplates()` → render sticker grid
3. `getCreatorContractStats()` → total tips, paused status
4. ASA opt-in check before tipping
5. Amount selection → find matching template (highest threshold ≤ amount)
6. Build atomic group → Pera signs → submit → poll for NFT arrival
7. Zero balance → banner "You need ALGO" → link to Add Balance page
8. Creator visits own page → "This is your tip page. Share this link!"

---

## 7. Phase 2: Dashboard & Inventory

### 7A. Creator Dashboard (`/creator/dashboard`)

**Purpose:** Analytics + sticker management + contract controls.

**Layout:**

```
┌─────────────────────────────────────────────────────┐
│  Creator Dashboard                [Share Tip Link]  │
│                                                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐│
│  │    47    │ │  23.5 A  │ │    12    │ │   35   ││
│  │   Tips   │ │   ALGO   │ │   Fans   │ │  NFTs  ││
│  └──────────┘ └──────────┘ └──────────┘ └────────┘│
│                                                     │
│  ── My Stickers (3/20 slots) ──────── [+ Add] ──  │
│  ┌────────┐ ┌────────┐ ┌────────┐                 │
│  │ [img]  │ │ [img]  │ │ [img]  │                 │
│  │ Butki  │ │ Bauni  │ │ Shawty │                 │
│  │ 1 ALGO │ │ 2 ALGO │ │ 5 ALGO │                 │
│  │ 23 mint│ │ 8 mint │ │ 4 mint │                 │
│  │ [🗑]   │ │ [🗑]   │ │ [🗑]   │                 │
│  └────────┘ └────────┘ └────────┘                 │
│                                                     │
│  ── Top Fans ─────────────────────────────────────  │
│  1. Fan_wallet_1    12.5 ALGO   8 stickers         │
│  2. Fan_wallet_2     8.0 ALGO   5 stickers         │
│  3. Fan_wallet_3     5.0 ALGO   3 stickers         │
│                                                     │
│  ── Contract ─────────────────────────────────────  │
│  App ID: 123456789  ·  Version: 1  ·  Active ✓    │
│  Min Tip: 1.0 ALGO                                  │
│  [Pause]  [Upgrade]  [View on Explorer →]          │
│                                                     │
│  ── System Status ────────────────────────────────  │
│  Listener: ● Running  ·  Round: 45,892,301         │
│  Errors: 0  ·  Retry: Enabled (max 3 attempts)     │
└─────────────────────────────────────────────────────┘
```

**Data sources:**
- Dashboard: `getCreatorDashboard(wallet)` → returns:
  - `walletAddress`, `username`, `totalFans`, `totalStickersMinted`
  - `contract` → `{ creatorWallet, appId, appAddress, version, active, deployedAt }` (or null)
  - `stats` → `{ appId, totalTips, totalAmountAlgo, minTipAlgo, paused, contractVersion }` (from on-chain state, or null)
  - `recentTransactions[]` → `{ txId, fanWallet, amountAlgo, memo, processed, detectedAt }`
  - **Note:** Total ALGO is inside `stats.totalAmountAlgo`, NOT a top-level field
- Stickers: `getCreatorTemplates(wallet)` → `{ creatorWallet, templates[], total }` + count for "X/20 slots"
- Add sticker modal → `createStickerTemplate(wallet, formData)` (AUTH, multipart)
- Delete: only if mint_count=0 → `deleteStickerTemplate(wallet, id)` (⚠ no auth currently)
- Top fans: `getCreatorLeaderboard(wallet, 10)` → `{ creatorWallet, creatorUsername, totalFans, totalAlgoReceived, leaderboard[] }`
- Contract stats: `getCreatorContractStats(wallet)` → includes `minTipAlgo`, `paused`, `totalTips`, `totalAmountAlgo`, `contractVersion`
- Pause/Unpause: returns unsigned txn → Pera signs → submit via `/submit`
- System: `getListenerStatus()` → `{ running, lastProcessedRound, errorsCount, pollIntervalSeconds, retryEnabled, maxRetryAttempts }`
- Note: `amountAlgo` in transaction responses is computed from `amount_micro / 1_000_000`

### 7B. Fan Dashboard (`/fan/dashboard`)

```
┌─────────────────────────────────────────────────────┐
│  My Dashboard                [View My Stickers →]   │
│                                                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐│
│  │    15    │ │  8.5 A   │ │     3    │ │   12   ││
│  │   Tips   │ │  Spent   │ │ Creators │ │Stickers││
│  └──────────┘ └──────────┘ └──────────┘ └────────┘│
│                                                     │
│  ── Recent Tips ──────────────────────────────────  │
│  5 ALGO → Creator_X  ·  Shawty ⭐  ·  2h ago      │
│  2 ALGO → Creator_Y  ·  Bauni     ·  1d ago       │
│  1 ALGO → Creator_X  ·  Butki     ·  3d ago       │
│                                                     │
│  ── Creators I Support ───────────────────────────  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │Creator_X │ │Creator_Y │ │Creator_Z │           │
│  │ 6.5 ALGO │ │ 2.0 ALGO │ │ 1.0 ALGO │           │
│  │ 4 stckrs │ │ 1 stckr  │ │ 1 stckr  │           │
│  │[Tip Agn] │ │[Tip Agn] │ │[Tip Agn] │           │
│  └──────────┘ └──────────┘ └──────────┘           │
│                                                     │
│  ── Golden Odds ──────────────────────────────────  │
│  Current chance: 12%                                │
│  Tips since last golden: 3/10                       │
│  [If you tip __ ALGO → __% chance]                  │
│                                                     │
│  Balance: 3.45 ALGO   [Add Balance →]               │
└─────────────────────────────────────────────────────┘
```

**Data sources:**
- `getFanStats(wallet)` → `GET /fan/{wallet}/stats` returns:
  - `wallet`, `totalTips`, `totalAlgoSpent`, `averageTipAlgo`, `uniqueCreators`
  - `totalSoulbound`, `totalGolden`, `totalNfts`
  - `creatorBreakdown[]` → `{ creatorWallet, tipCount, totalAlgo }` (top 10)
  - `recentTips[]` → `{ txId, creatorWallet, amountAlgo, memo, detectedAt }` (last 10)
- `getGoldenOdds(wallet, amountAlgo)` → `GET /fan/{wallet}/golden-odds?amount_algo=N` returns:
  - `wallet`, `tipAmount`, `baseProbability`, `bonus`, `totalProbability`, `triggerInterval`, `description`
- Note: all amounts in responses are already converted to ALGO (float), not microAlgos

### 7C. Sticker Inventory (`/fan/stickers`)

**Layout:** Grid gallery with filter tabs.

```
MY STICKERS (12)
[All (12)]  [Soulbound (8)]  [Golden ⭐ (4)]

┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐
│ [img]  │ │ [img]  │ │ [img]  │ │ [img]  │
│ Butki  │ │ Shawty │ │ Bauni  │ │ Butki  │
│ 🔒     │ │ ⭐      │ │ 🔒     │ │ 🔒     │
│ CrtrX  │ │ CrtrX  │ │ CrtrY  │ │ CrtrZ  │
│ Feb 18 │ │ Feb 17 │ │ Feb 15 │ │ Feb 14 │
└────────┘ └────────┘ └────────┘ └────────┘
```

**Sticker detail modal (on click):**
- Large image, name, type badge, creator, minted date, ASA ID
- Explorer link
- Golden: [Transfer] button → recipient wallet input → sign via Pera
- Soulbound: "This sticker is yours forever" badge
- Pending opt-in: [Claim] button → opt-in via Pera → backend delivers

**Paginated:** "Load More" button, 20 per page.

### 7D. Add Balance (`/fan/add-balance`)

**Simulation mode:**
- Quick-pick buttons (1, 2, 5 ALGO) → `simulateFundWallet(wallet, amount)`
- Request: `{ walletAddress, amountAlgo }` (default 5.0, max 10 ALGO)
- Rate-limited: 3 requests/minute per IP
- Response: `{ status, txId, amountAlgo, wallet, message, explorerUrl }`

**Production mode:** Transak widget embed → `createOnrampOrder()` → poll status via `getOnrampOrderStatus()`
- Config: `getOnrampConfig()` → `{ simulationMode, environment, platformWallet, platformFeePercent, supportedFiat, supportedCrypto, apiKey, mockConversionRate }`
- Order history: `getFanOnrampOrders(wallet)` → `{ orders[] }`

Shows "⚠ Simulation Mode" banner when `config.simulationMode === true`. Recent top-ups history.

---

## 8. Phase 3: Secondary Pages

### 8A. Leaderboard (`/leaderboard`)

Two tabs: **Top Creators** (global) and **Top Fans** (per creator).

Data tables with clean styling:
- Rank · Wallet · Total ALGO · Fans/Tips · NFTs
- Click creator row → navigate to tip page
- No emoji medals — use numbered rank with subtle weight

### 8B. About Page (`/about`)

Static content. Sections:
1. How it works (3-step visual with numbered cards)
2. Soulbound vs Golden stickers
3. Tech stack (Algorand, ARC-3, IPFS, PyTeal)
4. FAQ accordion

### 8C. 404 Page

"Page not found" with illustration and [Go Home →] button.

---

## 9. Section Architecture

### Trust & Credibility Signals (Include on Landing)

**1. Logo Cloud**
- Grayscale logos, low opacity, even spacing
- Algorand, Pera Wallet, Pinata IPFS, Transak

**2. Metrics Section**
```
50K+          120+              ₹2Cr+
Active Users  Verified Creators Payments Processed
```
Big numbers. Small labels.

**3. Security Callout**
- "Non-custodial wallet integration."
- "End-to-end transparent transactions."
- "Smart contracts auditable on-chain."

### Footer (Professional Finish)

```css
.footer {
  background: #0F172A;
  color: #CBD5E1;
  padding: 64px 0 32px;
}
```

Structured columns: Product | Developers | Company | Legal
Subtle divider lines. Copyright.

---

## 10. Build Order

```
Phase 0 — Foundation (Build First):
  ├── Design system (light theme, slate neutrals, Inter font)
  ├── Component library (buttons, cards, stat cards, inputs)
  ├── API client with auth headers + error handling (401/403/429/409)
  ├── Pera Wallet integration (connect/disconnect/sign)
  ├── Global state + navigation bar + toast system
  └── Utilities (formatAlgo, truncateAddress, etc.)

Phase 1 — Core Pages (P0):
  ├── Landing page (hero + metrics + how it works + trust signals)
  ├── Creator setup wizard (4-step with min tip + sticker limits)
  └── Fan tip page (sticker grid + tip flow + NFT arrival polling)

Phase 2 — Dashboard & Inventory (P1):
  ├── Creator dashboard (stats + sticker CRUD + contract + listener status)
  ├── Fan dashboard (stats + tips + golden odds)
  ├── Sticker inventory (gallery + detail modal + transfer + claim)
  └── Add Balance page (simulated on-ramp + Transak-ready)

Phase 3 — Secondary Pages (P2):
  ├── Leaderboard (creator discovery + fan rankings)
  ├── About page (static)
  ├── 404 page
  ├── Mobile responsive pass
  └── Polish + edge cases + final testing
```

---

## Page ↔ Backend Endpoint Map

| Page | Endpoints Used |
|------|---------------|
| **Landing** | `GET /health`, `GET /leaderboard/global/top-creators` |
| **Creator Setup** | `POST /creator/register` (includes `minTipAlgo`), `POST /creator/{w}/sticker-template` (AUTH), `GET /creator/{w}/contract` |
| **Creator Dashboard** | `GET /creator/{w}/dashboard`, `GET /creator/{w}/templates`, `GET /creator/{w}/contract/stats`, `DELETE /creator/{w}/template/{id}`, `POST /creator/{w}/pause-contract` (AUTH), `POST /creator/{w}/unpause-contract`, `POST /creator/{w}/upgrade-contract` (AUTH), `GET /leaderboard/{w}`, `GET /listener/status` |
| **Tip Page** | `GET /creator/{w}/contract`, `GET /creator/{w}/templates`, `GET /creator/{w}/contract/stats`, `GET /params`, `POST /submit` (single), `POST /submit-group` (atomic), `POST /nft/optin`, `GET /fan/{w}/inventory`, `GET /fan/{w}/pending`, `POST /fan/{w}/claim/{id}` |
| **Fan Dashboard** | `GET /fan/{w}/stats`, `GET /fan/{w}/golden-odds?amount_algo=N` |
| **Add Balance** | `GET /onramp/config`, `POST /simulate/fund-wallet` (rate-limited 3/min), `POST /onramp/create-order`, `GET /onramp/order/{partner_order_id}`, `GET /onramp/fan/{w}/orders` |
| **Inventory** | `GET /fan/{w}/inventory`, `GET /nft/inventory/{w}`, `GET /nft/{assetId}`, `POST /nft/optin`, `POST /fan/{w}/claim/{id}`, `POST /nft/transfer` |
| **Leaderboard** | `GET /leaderboard/global/top-creators?limit=N`, `GET /leaderboard/{w}?limit=N` |
| **All Pages** | `GET /health` (nav status), wallet connect/disconnect |

---

## Backend API Base URL

```
Development:  http://localhost:8000
Swagger UI:   http://localhost:8000/docs
OpenAPI JSON: http://localhost:8000/openapi.json
```
