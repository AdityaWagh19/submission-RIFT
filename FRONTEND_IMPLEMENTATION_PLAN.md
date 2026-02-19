# FanForge Frontend — Hackathon Build Plan (24hrs)

> **Goal**: 6 polished pages that demo EVERY backend feature
> **Stack**: React (Vite) + Vanilla CSS + Pera Wallet Connect
> **Time Budget**: ~4 hrs per page

---

## The 6-Page Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  /              Landing + Connect Wallet + Fund Wallet       │
│  /creator       Creator Hub (dashboard + templates + merch)  │
│  /fan           Fan Hub (inventory + loyalty + shawty)        │
│  /store/:w      Store + Checkout + Orders (combined)         │
│  /explore       Leaderboards + Creator Profiles              │
│  /tip/:w        Tip Flow (send ALGO to creator's contract)   │
└─────────────────────────────────────────────────────────────┘
```

**vs. Original**: 24 pages → 6 pages. Same 54 endpoints. Zero features cut.

---

## Page 1: Landing (`/`)
**One page that handles**: Welcome → Connect Wallet → Fund Wallet → Auth

### Sections (scrollable single-page)

| Section | What It Shows | Backend Endpoints |
|---------|--------------|-------------------|
| **Hero** | FanForge tagline, 3-NFT explainer (Butki/Bauni/Shawty) | None |
| **Connect Wallet** | Pera Wallet button → auth flow | `POST /auth/challenge` → `POST /auth/verify` |
| **Fund Wallet** | After connecting: "Fund your wallet with TestNet ALGO" | `GET /onramp/config` → `POST /simulate/fund-wallet` |
| **Health Status** | Small footer badge: "Algorand TestNet ✅ Round #60691305" | `GET /health` |
| **Quick Actions** | Buttons: "I'm a Creator" → `/creator`, "I'm a Fan" → `/explore` | — |

### Auth Flow (happens right here, no separate page)
```
1. Click "Connect Pera Wallet"
2. Pera popup → select account → approve
3. POST /auth/challenge { walletAddress } → get nonce
4. peraWallet.signBytes(nonce) → get signature
5. POST /auth/verify { walletAddress, nonce, signature } → get JWT + role
6. Store JWT in localStorage
7. Show role badge: "Creator" or "Fan"
8. Show Fund Wallet section + navigation buttons
```

### Endpoints Used (7)
```
GET  /health                              → connection status
GET  /params                              → txn params (for tipping flow)
POST /auth/challenge                      → nonce for signing
POST /auth/verify                         → JWT token
GET  /onramp/config                       → simulation mode check
POST /simulate/fund-wallet                → fund with TestNet ALGO
POST /onramp/create-order                 → fiat on-ramp (production)
```

---

## Page 2: Creator Hub (`/creator`)
**One page with tabs**: Dashboard | Templates | Products & Discounts | Contract

### Tab 1: Dashboard
| Component | Data Source |
|-----------|-----------|
| Stat cards (Total Tips, ALGO Earned, Fans, NFTs Minted) | `GET /creator/{wallet}/dashboard` |
| On-chain contract stats (paused status, global state) | `GET /creator/{wallet}/contract/stats` |
| Recent transactions table (last 10 tips) | Included in dashboard response |
| "Register as Creator" button (if not yet registered) | `POST /creator/register` |

### Tab 2: Templates
| Component | Data Source |
|-----------|-----------|
| Sticker template grid (image, name, category, mint count) | `GET /creator/{wallet}/templates` |
| "Create Template" modal (image upload + metadata) | `POST /creator/{wallet}/sticker-template` |
| Delete button (only for 0-mint templates) | `DELETE /creator/{wallet}/template/{id}` |

### Tab 3: Products & Discounts
| Component | Data Source |
|-----------|-----------|
| Products table (name, price, stock, status toggle) | `GET /creator/{wallet}/products` |
| "Add Product" modal | `POST /creator/{wallet}/products` |
| Inline edit (price, name, stock, active toggle) | `PATCH /creator/{wallet}/products/{id}` |
| Delete product | `DELETE /creator/{wallet}/products/{id}` |
| Discount rules table | `GET /creator/{wallet}/discounts` |
| "Add Discount" modal (%, fixed, Shawty requirement, Bauni gate) | `POST /creator/{wallet}/discounts` |

### Tab 4: Contract
| Component | Data Source |
|-----------|-----------|
| Contract info card (app_id, app_address, version) | `GET /creator/{wallet}/contract` |
| Pause/Unpause button → Pera sign → submit | `POST /creator/{wallet}/pause-contract` → `POST /submit` |
| | `POST /creator/{wallet}/unpause-contract` → `POST /submit` |
| Upgrade button | `POST /creator/{wallet}/upgrade-contract` |
| Contract info (TEAL status) | `GET /contract/info` |
| Available contracts | `GET /contract/list` |

### Endpoints Used (17)
```
POST /creator/register                          → one-time onboarding
GET  /creator/{wallet}/dashboard                → all-in-one stats
GET  /creator/{wallet}/contract                 → active contract
GET  /creator/{wallet}/contract/stats           → on-chain state
POST /creator/{wallet}/upgrade-contract         → deploy new version
POST /creator/{wallet}/pause-contract           → unsigned txn
POST /creator/{wallet}/unpause-contract         → unsigned txn
GET  /creator/{wallet}/templates                → list templates
POST /creator/{wallet}/sticker-template         → create (multipart)
DELETE /creator/{wallet}/template/{id}          → remove
GET  /creator/{wallet}/products                 → list products
POST /creator/{wallet}/products                 → create
PATCH /creator/{wallet}/products/{id}           → update
DELETE /creator/{wallet}/products/{id}          → remove
GET  /creator/{wallet}/discounts                → list rules
POST /creator/{wallet}/discounts                → create rule
GET  /contract/info                             → TEAL metadata
GET  /contract/list                             → available contracts
POST /submit                                    → signed txn submission
```

---

## Page 3: Fan Hub (`/fan`)
**One page with tabs**: My NFTs | Loyalty & Membership | Shawty Tokens | Stats

### Tab 1: My NFTs
| Component | Data Source |
|-----------|-----------|
| NFT grid with type filter tabs (All / Soulbound / Golden) | `GET /fan/{wallet}/inventory?skip=0&limit=50` |
| Pending claims alert banner (count) | `GET /fan/{wallet}/pending` |
| Claim flow: opt-in → sign → claim | `POST /nft/optin` → Pera sign → `POST /submit` → `POST /fan/{wallet}/claim/{nftId}` |
| NFT detail modal (click any card) | `GET /nft/{assetId}` |
| Golden sticker probability widget | `GET /fan/{wallet}/golden-odds` |
| Pagination | `meta.total`, `meta.hasMore` |

### Tab 2: Loyalty & Membership
| Component | Data Source |
|-----------|-----------|
| Butki loyalty cards (per creator) with badge progress ring | `GET /butki/{wallet}/loyalty` |
| Specific creator loyalty detail (on card click) | `GET /butki/{wallet}/loyalty/{creatorWallet}` |
| Bauni membership cards with expiry countdown | `GET /bauni/{wallet}/memberships` |
| Membership status check (per creator) | `GET /bauni/{wallet}/membership/{creatorWallet}` |
| Membership verification (used internally) | `POST /bauni/verify` |

### Tab 3: Shawty Tokens
| Component | Data Source |
|-----------|-----------|
| Token cards with status badges (Active/Burned/Locked) | `GET /shawty/{wallet}/tokens?include_spent=true` |
| "Burn for Merch" action → modal | `POST /shawty/burn` |
| "Lock for Discount" action → modal | `POST /shawty/lock` |
| "Transfer" action → wallet input modal | `POST /shawty/transfer` |
| Ownership validator (before actions) | `GET /shawty/{wallet}/validate/{assetId}` |
| Redemption history table | `GET /shawty/{wallet}/redemptions` |

### Tab 4: Stats
| Component | Data Source |
|-----------|-----------|
| Stat cards (Total Tips, ALGO Spent, Creators Supported, NFTs) | `GET /fan/{wallet}/stats` |
| Per-creator breakdown table | Included in stats response |
| Recent tips timeline | Included in stats response |
| Alt NFT inventory view | `GET /nft/inventory/{wallet}` |

### Endpoints Used (19)
```
GET  /fan/{wallet}/inventory                    → NFT collection
GET  /fan/{wallet}/pending                      → pending claims
POST /fan/{wallet}/claim/{nftId}                → claim after opt-in
GET  /fan/{wallet}/stats                        → tipping analytics
GET  /fan/{wallet}/golden-odds                  → probability calc
GET  /nft/inventory/{wallet}                    → alt inventory view
GET  /nft/{assetId}                             → single NFT detail
POST /nft/optin                                 → unsigned opt-in txn
POST /nft/transfer                              → golden NFT transfer
GET  /butki/{wallet}/loyalty                    → all creators loyalty
GET  /butki/{wallet}/loyalty/{creator}          → specific creator
GET  /bauni/{wallet}/memberships                → all memberships
GET  /bauni/{wallet}/membership/{creator}       → specific check
POST /bauni/verify                              → membership gate
GET  /shawty/{wallet}/tokens                    → collectible tokens
POST /shawty/burn                               → burn for merch
POST /shawty/lock                               → lock for discount
POST /shawty/transfer                           → P2P transfer
GET  /shawty/{wallet}/validate/{assetId}        → ownership check
GET  /shawty/{wallet}/redemptions               → history
```

---

## Page 4: Store (`/store/:creatorWallet`)
**One page with sections**: Catalog → Cart Drawer → Checkout → Order History

### Layout
```
┌────────────────────────────────────────────────────┐
│  Creator Store Header (name, wallet, member badge) │
├────────────────────────────────────────────────────┤
│  [All Products] [Members Only]  ← toggle tabs      │
├────────────────────────────────────────────────────┤
│  Product Grid (cards with Add to Cart)             │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐              │
│  │ Prod │ │ Prod │ │ Prod │ │ Prod │              │
│  │ $2.5 │ │ $5.0 │ │ $10  │ │ $3.5 │              │
│  │ [Add]│ │ [Add]│ │ [Add]│ │ [Add]│              │
│  └──────┘ └──────┘ └──────┘ └──────┘              │
├────────────────────────────────────────────────────┤
│  Cart Drawer (slide out) → Quote → Place Order     │
├────────────────────────────────────────────────────┤
│  My Orders (collapsible section at bottom)          │
└────────────────────────────────────────────────────┘
```

| Feature | Data Source |
|---------|-----------|
| Public product catalog | `GET /creator/{wallet}/store?limit=50&offset=0` |
| Members-only tab (Bauni gated) | `GET /creator/{wallet}/store/members-only?fanWallet=...` |
| Membership check (show/hide members tab) | `GET /bauni/{fanWallet}/membership/{creatorWallet}` |
| Cart → Quote preview (subtotal, discounts, total) | `POST /creator/{wallet}/store/quote` |
| Available Shawty tokens for discount | `GET /shawty/{fanWallet}/tokens` |
| Place order | `POST /creator/{wallet}/store/order` |
| Order history | `GET /fan/{wallet}/orders` |
| On-ramp order history | `GET /onramp/fan/{wallet}/orders` |
| On-ramp order status | `GET /onramp/order/{partnerOrderId}` |

### Endpoints Used (9)
```
GET  /creator/{wallet}/store                    → public catalog
GET  /creator/{wallet}/store/members-only       → bauni-gated catalog
POST /creator/{wallet}/store/quote              → pricing with discounts
POST /creator/{wallet}/store/order              → place order
GET  /fan/{wallet}/orders                       → order history
GET  /onramp/fan/{wallet}/orders                → on-ramp orders
GET  /onramp/order/{partnerOrderId}             → order tracking
POST /submit                                    → payment txn (reused)
POST /submit-group                              → atomic group txn
```

---

## Page 5: Explore (`/explore`)
**One page with sections**: Top Creators → Creator Detail (expandable) → Fan Leaderboards

### Layout
```
┌───────────────────────────────────────────┐
│  🏆 Global Leaderboard — Top Creators     │
│  ┌──────────────────────────────────────┐ │
│  │ #1  CreatorA   245.5 ALGO   18 fans │ │
│  │ #2  CreatorB   180.2 ALGO   12 fans │ │
│  │ #3  CreatorC   95.0 ALGO    8 fans  │ │
│  └──────────────────────────────────────┘ │
│                                           │
│  Click any creator → expands inline:      │
│  ┌──────────────────────────────────────┐ │
│  │ CreatorA's Top Fans (by ALGO tipped) │ │
│  │ #1 FanX  50.2 ALGO  12 tips  3 NFTs │ │
│  │ #2 FanY  35.1 ALGO   8 tips  2 NFTs │ │
│  ├──────────────────────────────────────┤ │
│  │ CreatorA's Butki Leaderboard (badges)│ │
│  │ #1 FanX  4 badges  12 tips          │ │
│  │ #2 FanZ  2 badges   6 tips          │ │
│  ├──────────────────────────────────────┤ │
│  │ [View Store] [Tip This Creator]      │ │
│  └──────────────────────────────────────┘ │
└───────────────────────────────────────────┘
```

| Feature | Data Source |
|---------|-----------|
| Global creator ranking | `GET /leaderboard/global/top-creators?limit=50` |
| Creator's top fans (by ALGO) | `GET /leaderboard/{creatorWallet}?limit=20` |
| Creator's Butki leaderboard (by badges) | `GET /butki/leaderboard/{creatorWallet}?limit=20` |

### Endpoints Used (3)
```
GET  /leaderboard/global/top-creators           → ranked creators
GET  /leaderboard/{creatorWallet}               → fans by ALGO
GET  /butki/leaderboard/{creatorWallet}         → fans by badges
```

---

## Page 6: Tip (`/tip/:creatorWallet`)
**Purpose**: The core user action — send ALGO tip to a creator's TipProxy contract

### Layout
```
┌───────────────────────────────────────────┐
│  Tip CreatorA                              │
│  Contract: CFZRI4...HM4 (app_id: 755779) │
│                                           │
│  Amount: [____] ALGO                      │
│  Memo:   [____] (optional)                │
│                                           │
│  Your Loyalty: 3/5 tips → next Butki badge│
│  Membership: ✅ Active (24 days left)     │
│  Golden Odds: 12.3% at this amount        │
│                                           │
│  [ 💸 Send Tip via Pera Wallet ]          │
│                                           │
│  Recent Activity:                         │
│  ✅ Tip 2.0 ALGO — 5 min ago             │
│  🏆 Butki Badge #2 earned!               │
│  🎫 Bauni Membership renewed             │
└───────────────────────────────────────────┘
```

| Feature | Data Source |
|---------|-----------|
| Creator's contract (for building tip txn) | `GET /creator/{wallet}/contract` |
| Loyalty status (tips to next badge) | `GET /butki/{fanWallet}/loyalty/{creatorWallet}` |
| Membership status (active/expired) | `GET /bauni/{fanWallet}/membership/{creatorWallet}` |
| Golden odds preview | `GET /fan/{fanWallet}/golden-odds?amount_algo=X` |
| Build + sign tip txn via Pera | `GET /params` → build ApplicationCallTxn → Pera sign → `POST /submit` |
| NFT minting endpoints (triggered by listener) | `POST /nft/mint/soulbound`, `POST /nft/mint/golden` |
| Deploy contract (reused from creator) | `POST /contract/deploy`, `POST /contract/fund` |

### Endpoints Used (9)
```
GET  /creator/{wallet}/contract                 → contract address
GET  /butki/{fan}/loyalty/{creator}            → loyalty status
GET  /bauni/{fan}/membership/{creator}         → membership check
GET  /fan/{fan}/golden-odds                    → probability
GET  /params                                   → txn params
POST /submit                                   → signed tip txn
POST /nft/mint/soulbound                       → (listener-triggered)
POST /nft/mint/golden                          → (listener-triggered)
POST /contract/deploy                          → (used in registration)
POST /contract/fund                            → (used in registration)
```

---

## Full Endpoint Coverage Verification

### ✅ All 54 Backend Endpoints Mapped

| # | Endpoint | Page |
|---|----------|------|
| 1 | `GET /health` | Landing |
| 2 | `GET /params` | Landing, Tip |
| 3 | `GET /listener/status` | Creator Hub |
| 4 | `POST /auth/challenge` | Landing |
| 5 | `POST /auth/verify` | Landing |
| 6 | `POST /creator/register` | Creator Hub |
| 7 | `GET /creator/{w}/dashboard` | Creator Hub |
| 8 | `GET /creator/{w}/contract` | Creator Hub, Tip |
| 9 | `GET /creator/{w}/contract/stats` | Creator Hub |
| 10 | `POST /creator/{w}/upgrade-contract` | Creator Hub |
| 11 | `POST /creator/{w}/pause-contract` | Creator Hub |
| 12 | `POST /creator/{w}/unpause-contract` | Creator Hub |
| 13 | `GET /creator/{w}/templates` | Creator Hub |
| 14 | `POST /creator/{w}/sticker-template` | Creator Hub |
| 15 | `DELETE /creator/{w}/template/{id}` | Creator Hub |
| 16 | `GET /creator/{w}/products` | Creator Hub |
| 17 | `POST /creator/{w}/products` | Creator Hub |
| 18 | `PATCH /creator/{w}/products/{id}` | Creator Hub |
| 19 | `DELETE /creator/{w}/products/{id}` | Creator Hub |
| 20 | `GET /creator/{w}/discounts` | Creator Hub |
| 21 | `POST /creator/{w}/discounts` | Creator Hub |
| 22 | `GET /creator/{w}/store` | Store |
| 23 | `GET /creator/{w}/store/members-only` | Store |
| 24 | `POST /creator/{w}/store/quote` | Store |
| 25 | `POST /creator/{w}/store/order` | Store |
| 26 | `GET /fan/{w}/inventory` | Fan Hub |
| 27 | `GET /fan/{w}/pending` | Fan Hub |
| 28 | `POST /fan/{w}/claim/{id}` | Fan Hub |
| 29 | `GET /fan/{w}/stats` | Fan Hub |
| 30 | `GET /fan/{w}/golden-odds` | Fan Hub, Tip |
| 31 | `GET /fan/{w}/orders` | Store |
| 32 | `GET /nft/inventory/{w}` | Fan Hub |
| 33 | `GET /nft/{assetId}` | Fan Hub |
| 34 | `POST /nft/mint/soulbound` | Tip (listener-triggered) |
| 35 | `POST /nft/mint/golden` | Tip (listener-triggered) |
| 36 | `POST /nft/optin` | Fan Hub |
| 37 | `POST /nft/transfer` | Fan Hub |
| 38 | `GET /butki/{w}/loyalty` | Fan Hub |
| 39 | `GET /butki/{w}/loyalty/{creator}` | Fan Hub, Tip |
| 40 | `GET /butki/leaderboard/{creator}` | Explore |
| 41 | `GET /bauni/{w}/membership/{creator}` | Fan Hub, Store, Tip |
| 42 | `GET /bauni/{w}/memberships` | Fan Hub |
| 43 | `POST /bauni/verify` | Fan Hub |
| 44 | `GET /shawty/{w}/tokens` | Fan Hub, Store |
| 45 | `POST /shawty/burn` | Fan Hub |
| 46 | `POST /shawty/lock` | Fan Hub |
| 47 | `POST /shawty/transfer` | Fan Hub |
| 48 | `GET /shawty/{w}/validate/{assetId}` | Fan Hub, Store |
| 49 | `GET /shawty/{w}/redemptions` | Fan Hub |
| 50 | `GET /onramp/config` | Landing |
| 51 | `POST /onramp/create-order` | Landing |
| 52 | `GET /onramp/order/{id}` | Store |
| 53 | `GET /onramp/fan/{w}/orders` | Store |
| 54 | `POST /simulate/fund-wallet` | Landing |
| 55 | `GET /contract/info` | Creator Hub |
| 56 | `GET /contract/list` | Creator Hub |
| 57 | `POST /contract/deploy` | Creator Hub |
| 58 | `POST /contract/fund` | Creator Hub |
| 59 | `POST /submit` | Creator Hub, Fan Hub, Store, Tip |
| 60 | `POST /submit-group` | Store |
| 61 | `GET /leaderboard/global/top-creators` | Explore |
| 62 | `GET /leaderboard/{creator}` | Explore |

---

## Project Structure (Simplified)

```
frontend/
├── index.html
├── vite.config.js
├── package.json
│
└── src/
    ├── main.jsx
    ├── App.jsx                     # 6 routes only
    ├── index.css                   # Design system
    │
    ├── api/
    │   ├── client.js               # Base fetch + JWT injection
    │   ├── auth.js                 # challenge, verify
    │   ├── creator.js              # all /creator/* calls
    │   ├── fan.js                  # all /fan/* calls
    │   ├── merch.js                # store, quote, order
    │   ├── nft.js                  # mint, optin, transfer
    │   ├── loyalty.js              # butki + bauni + shawty
    │   ├── leaderboard.js          # global + per-creator
    │   └── system.js               # health, params, onramp, simulate
    │
    ├── context/
    │   ├── AuthContext.jsx         # wallet + JWT + role
    │   └── WalletContext.jsx       # Pera SDK wrapper
    │
    ├── pages/
    │   ├── Landing.jsx             # Page 1: hero + connect + fund
    │   ├── CreatorHub.jsx          # Page 2: 4 tabs
    │   ├── FanHub.jsx              # Page 3: 4 tabs
    │   ├── Store.jsx               # Page 4: catalog + checkout
    │   ├── Explore.jsx             # Page 5: leaderboards
    │   └── Tip.jsx                 # Page 6: send tip
    │
    └── components/
        ├── Navbar.jsx
        ├── TabPanel.jsx            # Reusable tab container
        ├── StatCard.jsx
        ├── NFTCard.jsx
        ├── ProductCard.jsx
        ├── LeaderboardRow.jsx
        ├── MembershipBadge.jsx
        ├── BadgeProgress.jsx
        ├── Modal.jsx
        ├── Toast.jsx
        ├── LoadingSpinner.jsx
        └── EmptyState.jsx
```

**Total files**: ~30 (vs ~60+ in the original plan)

---

## Time Budget (24 hours)

| Phase | Hours | Deliverable |
|-------|-------|-------------|
| **Setup** | 1 | Vite project, design tokens, API client, auth context |
| **Page 1: Landing** | 2 | Hero, connect wallet, fund wallet, auth flow |
| **Page 2: Creator Hub** | 5 | 4 tabs, registration, templates, products, discounts, contract mgmt |
| **Page 3: Fan Hub** | 5 | 4 tabs, NFT grid, claims, loyalty, memberships, Shawty actions |
| **Page 4: Store** | 4 | Catalog, cart, quote, checkout, orders |
| **Page 5: Explore** | 2 | Global leaderboard, creator detail, Butki leaderboard |
| **Page 6: Tip** | 2 | Tip form, Pera signing, loyalty preview |
| **Polish** | 3 | Animations, responsive, dark mode, error states, demo recording |
| **Total** | **24** | |

---

## Design Approach

### Color Palette
```css
--bg-primary: #0a0a0f;          /* Deep space black */
--bg-secondary: #12121a;        /* Card backgrounds */
--bg-glass: rgba(255,255,255,0.03); /* Glassmorphism */
--accent-purple: #8b5cf6;       /* Primary brand */
--accent-cyan: #06b6d4;         /* Secondary accent */
--accent-gold: #f59e0b;         /* Golden NFTs */
--accent-green: #10b981;        /* Success / active */
--accent-red: #ef4444;          /* Errors / burned */
--text-primary: #f1f5f9;
--text-secondary: #94a3b8;
```

### Key UI Patterns
- **Glassmorphism cards** with backdrop-blur
- **Tab panels** for section switching (no routing, just state)
- **Slide-out drawers** for cart and action modals
- **Skeleton loading** states (no jarring layout shifts)
- **Toast notifications** for success/error feedback
- **Truncated wallet addresses** everywhere (CFZR...HM4)

---

## Demo Flow (for judges)

**One continuous path that touches every feature:**

```
1. Landing → Connect Pera Wallet → Auth → Fund 5 ALGO
2. Creator Hub → Register → Create template → Add 2 products → Set discount
3. Explore → See yourself on global leaderboard (new creator)
4. Tip → Send 0.5 ALGO tip to self (triggers listener → mints NFT)
5. Fan Hub → See NFT appear → Claim it → Check loyalty (1/5 to badge)
6. Fan Hub → Shawty tab → See tokens → Transfer one
7. Store → Browse products → Get quote with Shawty discount → Place order
8. Fan Hub → Membership tab → Check Bauni status
```

**This 3-minute demo path exercises 40+ API endpoints end-to-end.**
