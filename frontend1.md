# FanForge Frontend — Detailed 2-Phase Build Plan

## Phase 1: Foundation + Core (Landing, Creator Hub, Fan Hub)
## Phase 2: Commerce + Social (Store, Explore, Tip) + Polish

---

# PHASE 1

## Step 1.1 — Project Setup

```bash
npx -y create-vite@latest ./ --template react
npm install @perawallet/connect algosdk react-router-dom
```

### Files to Create

```
src/
├── main.jsx                  # ReactDOM.render + BrowserRouter
├── App.jsx                   # Routes: /, /creator, /fan, /store/:w, /explore, /tip/:w
├── index.css                 # Design tokens + global styles
├── api/client.js             # fetch wrapper with JWT
├── api/auth.js               # challenge + verify
├── api/creator.js            # 17 creator endpoints
├── api/fan.js                # 5 fan endpoints
├── api/nft.js                # 6 NFT endpoints
├── api/loyalty.js            # butki(3) + bauni(3) + shawty(6)
├── api/merch.js              # store + quote + order
├── api/leaderboard.js        # 2 leaderboard endpoints
├── api/system.js             # health + params + onramp + simulate
├── context/AuthContext.jsx   # JWT + wallet + role
├── context/WalletContext.jsx # Pera SDK
├── components/Navbar.jsx
├── components/TabPanel.jsx
├── components/StatCard.jsx
├── components/Modal.jsx
├── components/Toast.jsx
├── components/LoadingSpinner.jsx
├── components/EmptyState.jsx
```

### API Client (`api/client.js`)

```
Base URL: http://localhost:8000
Every request: Content-Type: application/json
Auth requests: Authorization: Bearer <JWT from localStorage>
Error handling: parse { success, error } envelope → throw on !success
```

---

## Step 1.2 — API Service Files (Exact Endpoint Mapping)

### `api/auth.js`
```
createChallenge(walletAddress)
  POST /auth/challenge
  Body: { walletAddress }  ← uses alias, NOT wallet_address
  Returns: { walletAddress, nonce, expiresAt, message }

verifySignature(walletAddress, nonce, signature)
  POST /auth/verify
  Body: { walletAddress, nonce, signature }  ← signature is base64
  Returns: { walletAddress, role, accessToken, tokenType, expiresInSeconds }
```

### `api/creator.js`
```
register(walletAddress, minTipAlgo)
  POST /creator/register
  Auth: JWT (any wallet)
  Body: { wallet_address, min_tip_algo }

getDashboard(wallet)
  GET /creator/{wallet}/dashboard
  Auth: JWT (creator)
  Returns: { contract, stats, fans, templates, recent_transactions }

getContract(wallet)
  GET /creator/{wallet}/contract
  Auth: JWT (creator)

getContractStats(wallet)
  GET /creator/{wallet}/contract/stats
  Auth: JWT (creator)

upgradeContract(wallet)
  POST /creator/{wallet}/upgrade-contract
  Auth: JWT (creator)

pauseContract(wallet)
  POST /creator/{wallet}/pause-contract
  Auth: JWT (creator)
  Returns: unsigned txn → Pera signs → POST /submit

unpauseContract(wallet)
  POST /creator/{wallet}/unpause-contract
  Auth: JWT (creator)
  Returns: unsigned txn → Pera signs → POST /submit

getTemplates(wallet)
  GET /creator/{wallet}/templates
  Auth: JWT (creator)

createTemplate(wallet, formData)
  POST /creator/{wallet}/sticker-template
  Auth: JWT (creator)
  Content-Type: multipart/form-data
  FormData: { name, category, sticker_type, tip_threshold, image }

deleteTemplate(wallet, templateId)
  DELETE /creator/{wallet}/template/{templateId}
  Auth: JWT (creator)

getProducts(wallet)
  GET /creator/{wallet}/products
  Auth: JWT (creator)

createProduct(wallet, data)
  POST /creator/{wallet}/products
  Auth: JWT (creator)
  Body: { slug, name, description, image_ipfs_hash, price_algo, stock_quantity, active }

updateProduct(wallet, productId, updates)
  PATCH /creator/{wallet}/products/{productId}
  Auth: JWT (creator)

deleteProduct(wallet, productId)
  DELETE /creator/{wallet}/products/{productId}
  Auth: JWT (creator)

getDiscounts(wallet)
  GET /creator/{wallet}/discounts
  Auth: JWT (creator)

createDiscount(wallet, data)
  POST /creator/{wallet}/discounts
  Auth: JWT (creator)
  Body: { productId, discountType, value, minShawtyTokens, requiresBauni, maxUsesPerWallet }
```

### `api/fan.js`
```
getInventory(wallet, skip=0, limit=50)
  GET /fan/{wallet}/inventory?skip={skip}&limit={limit}
  Returns: { success, data: [...nfts], meta: { limit, offset, total, hasMore, totalSoulbound, totalGolden } }

getPending(wallet)
  GET /fan/{wallet}/pending
  Returns: { success, data: { wallet, pending: [...] } }

claimNFT(wallet, nftId)
  POST /fan/{wallet}/claim/{nftId}
  Returns: { status: "delivered", assetId, txId }

getStats(wallet)
  GET /fan/{wallet}/stats
  Returns: { wallet, totalTips, totalAlgoSpent, averageTipAlgo, uniqueCreators,
             totalSoulbound, totalGolden, creatorBreakdown, recentTips }

getGoldenOdds(wallet, amountAlgo=1.0)
  GET /fan/{wallet}/golden-odds?amount_algo={amountAlgo}
```

### `api/nft.js`
```
getInventory(wallet, skip=0, limit=50)
  GET /nft/inventory/{wallet}?skip={skip}&limit={limit}

getDetails(assetId)
  GET /nft/{assetId}

createOptIn(fanWallet, assetId)
  POST /nft/optin
  Body: { fan_wallet, asset_id }
  Returns: unsigned txn → Pera signs → POST /submit

transferNFT(fromWallet, toWallet, assetId)
  POST /nft/transfer
  Body: { from_wallet, to_wallet, asset_id }

mintSoulbound(templateId, fanWallet)
  POST /nft/mint/soulbound  (listener-triggered, not called directly)

mintGolden(templateId, fanWallet)
  POST /nft/mint/golden  (listener-triggered, not called directly)
```

### `api/loyalty.js`
```
── Butki ──
getFanLoyalty(wallet)
  GET /butki/{wallet}/loyalty
  Returns: { fan_wallet, creators: [...], total_creators_supported }

getFanLoyaltyForCreator(wallet, creatorWallet)
  GET /butki/{wallet}/loyalty/{creatorWallet}
  Returns: { fan_wallet, creator_wallet, tip_count, butki_badges_earned, tips_to_next_badge }

getButkiLeaderboard(creatorWallet, limit=50)
  GET /butki/leaderboard/{creatorWallet}?limit={limit}
  Returns: { creator_wallet, leaderboard: [{rank, fan_wallet, butki_badges_earned, tip_count}] }

── Bauni ──
getMembershipStatus(wallet, creatorWallet)
  GET /bauni/{wallet}/membership/{creatorWallet}
  Returns: { fan_wallet, creator_wallet, is_valid, expires_at, days_remaining, cost_algo }

getAllMemberships(wallet, activeOnly=true)
  GET /bauni/{wallet}/memberships?active_only={activeOnly}
  Returns: { fan_wallet, memberships: [...], total }

verifyMembership(fanWallet, creatorWallet)
  POST /bauni/verify
  Body: { fan_wallet, creator_wallet }
  Returns: { is_valid, fan_wallet, creator_wallet, expires_at, days_remaining, message }

── Shawty ──
getTokens(wallet, includeSpent=false)
  GET /shawty/{wallet}/tokens?include_spent={includeSpent}
  Auth: JWT (fan)

burnForMerch(fanWallet, assetId, itemDescription)
  POST /shawty/burn
  Auth: JWT (fan)
  Body: { fan_wallet, asset_id, item_description }

lockForDiscount(fanWallet, assetId, discountDescription)
  POST /shawty/lock
  Auth: JWT (fan)
  Body: { fan_wallet, asset_id, discount_description }

transfer(fromWallet, toWallet, assetId)
  POST /shawty/transfer
  Auth: JWT (fan)
  Body: { from_wallet, to_wallet, asset_id }

validateOwnership(wallet, assetId)
  GET /shawty/{wallet}/validate/{assetId}

getRedemptions(wallet, limit=50)
  GET /shawty/{wallet}/redemptions?limit={limit}
```

### `api/merch.js`
```
getStoreCatalog(creatorWallet, limit=50, offset=0)
  GET /creator/{creatorWallet}/store?limit={limit}&offset={offset}
  Auth: NONE (public)
  Returns: { success, data: [...products], meta: { limit, offset, total, hasMore } }

getMembersOnlyCatalog(creatorWallet, fanWallet)
  GET /creator/{creatorWallet}/store/members-only?fanWallet={fanWallet}
  Auth: JWT (fan)

getQuote(creatorWallet, data)
  POST /creator/{creatorWallet}/store/quote
  Auth: JWT (fan)
  Body: { fanWallet, items: [{productId, quantity}], shawtyAssetIds: [], requireMembership: false }

createOrder(creatorWallet, data)
  POST /creator/{creatorWallet}/store/order
  Auth: JWT (fan)
  Body: same as quote

getFanOrders(wallet, limit=50, offset=0)
  GET /fan/{wallet}/orders?limit={limit}&offset={offset}
  Auth: JWT (fan)
```

### `api/leaderboard.js`
```
getGlobalTopCreators(limit=50)
  GET /leaderboard/global/top-creators?limit={limit}
  Auth: NONE
  Returns: { success, data: { leaderboard: [{rank, creatorWallet, username, appId, tipCount, totalAlgoReceived, uniqueFans}] } }

getCreatorLeaderboard(creatorWallet, limit=20)
  GET /leaderboard/{creatorWallet}?limit={limit}
  Auth: NONE
  ⚠️ Requires creator to exist in DB (returns 404 if not registered)
  Returns: { success, data: { creatorWallet, creatorUsername, leaderboard: [...] } }
```

### `api/system.js`
```
getHealth()
  GET /health
  Returns: { status, algorand_connected, last_round, timestamp }

getParams()
  GET /params
  Returns: { fee, firstValidRound, lastValidRound, genesisId, genesisHash }

getOnrampConfig()
  GET /onramp/config
  Returns: { simulation_mode, platform_wallet, supported_currencies, ... }

fundWallet(walletAddress, amountAlgo=5.0)
  POST /simulate/fund-wallet
  Body: { walletAddress, amountAlgo }

createOnrampOrder(fanWallet, creatorWallet, fiatAmount, fiatCurrency)
  POST /onramp/create-order
  Body: { fanWallet, creatorWallet, fiatAmount, fiatCurrency }

getOnrampOrderStatus(partnerOrderId)
  GET /onramp/order/{partnerOrderId}

getFanOnrampOrders(wallet)
  GET /onramp/fan/{wallet}/orders

submitTxn(signedTxn, idempotencyKey=null)
  POST /submit
  Body: { signed_txn }
  Headers: X-Idempotency-Key (optional)

submitGroup(signedTxns, idempotencyKey=null)
  POST /submit-group
  Body: { signed_txns: [...] }

getContractInfo(name="tip_proxy")
  GET /contract/info?name={name}

listContracts()
  GET /contract/list

deployContract(sender, contractName)
  POST /contract/deploy
  Body: { sender, contract_name }

fundContract(sender, appId, amount)
  POST /contract/fund
  Body: { sender, app_id, amount }
```

---

## Step 1.3 — Page 1: Landing (`/`)

### Sections & API Links

```
┌─────────────────────────────────────────────────────────────┐
│ NAVBAR: Logo | [Connect Wallet] | Health: ✅ Round #606913  │
│         ↑ GET /health                                       │
├─────────────────────────────────────────────────────────────┤
│ HERO SECTION                                                │
│ "FanForge — Web3 Patreon on Algorand"                      │
│ 3 NFT cards: Butki (loyalty) | Bauni (membership) | Shawty │
├─────────────────────────────────────────────────────────────┤
│ CONNECT SECTION (shown if !connected)                       │
│ [🔗 Connect Pera Wallet]                                   │
│   → peraWallet.connect() → accounts[0]                     │
│   → POST /auth/challenge { walletAddress }                  │
│   → peraWallet.signBytes(nonce)                             │
│   → POST /auth/verify { walletAddress, nonce, signature }   │
│   → store JWT → show role badge                             │
├─────────────────────────────────────────────────────────────┤
│ FUND SECTION (shown if connected)                           │
│ "Fund your wallet for testing"                              │
│ Amount: [5.0] ALGO  [💰 Fund Wallet]                       │
│   → GET /onramp/config (check simulation_mode)              │
│   → POST /simulate/fund-wallet { walletAddress, amountAlgo }│
├─────────────────────────────────────────────────────────────┤
│ NAVIGATION (shown if connected)                             │
│ role=creator: [Go to Creator Hub →]  links to /creator      │
│ role=fan:     [Browse Creators →]    links to /explore       │
│ both:         [Explore Stores →]     links to /explore       │
└─────────────────────────────────────────────────────────────┘
```

### Inter-Page Links from Landing
| Action | Destination | Condition |
|--------|------------|-----------|
| "Creator Hub" button | `/creator` | role === "creator" |
| "Browse Creators" button | `/explore` | Always |
| "My Collection" button | `/fan` | role === "fan" |
| Navbar logo click | `/` | Always |

---

## Step 1.4 — Page 2: Creator Hub (`/creator`)

### Auth Guard: Redirect to `/` if not authenticated or role !== "creator"
### Show "Register" UI if creator has no contract yet

### Tab Structure & API Links

```
[Dashboard] [Templates] [Products & Discounts] [Contract]
```

#### Tab 1: Dashboard
```
┌─────────────────────────────────────────────────────┐
│ GET /creator/{wallet}/dashboard → populates:        │
│                                                     │
│ ┌──────────┐ ┌──────────┐ ┌──────┐ ┌────────────┐ │
│ │Total Tips│ │ALGO Earned│ │ Fans │ │NFTs Minted │ │
│ │    47    │ │  245.5   │ │  18  │ │    62      │ │
│ └──────────┘ └──────────┘ └──────┘ └────────────┘ │
│                                                     │
│ GET /creator/{wallet}/contract/stats → on-chain:    │
│ Contract: app_id 755779 | Status: Active | v1      │
│                                                     │
│ Recent Transactions (from dashboard response):      │
│ ┌──────────────────────────────────────────────────┐│
│ │ Fan K2N7.. → 2.5 ALGO │ 5 min ago │ "love it!" ││
│ │ Fan ABCD.. → 1.0 ALGO │ 12 min ago│ "thanks"   ││
│ └──────────────────────────────────────────────────┘│
│                                                     │
│ Links: [View Store →] /store/{wallet}               │
│        [View Leaderboard →] /explore                │
└─────────────────────────────────────────────────────┘
```

#### Tab 2: Templates
```
┌─────────────────────────────────────────────────────┐
│ GET /creator/{wallet}/templates → grid of cards     │
│                                                     │
│ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌───────────┐│
│ │ Butki   │ │ Bauni   │ │ Shawty  │ │[+ Create] ││
│ │ Badge   │ │ Member  │ │ Collect │ │           ││
│ │ 15 mints│ │ 8 mints │ │ 39 mints│ │           ││
│ │ [🗑️]    │ │         │ │         │ │           ││
│ └─────────┘ └─────────┘ └─────────┘ └───────────┘│
│                                                     │
│ Create Modal (on [+ Create] click):                 │
│   POST /creator/{wallet}/sticker-template           │
│   multipart: { name, category, sticker_type,        │
│                tip_threshold, image }                │
│                                                     │
│ Delete (🗑️ only if mint_count === 0):               │
│   DELETE /creator/{wallet}/template/{templateId}    │
└─────────────────────────────────────────────────────┘
```

#### Tab 3: Products & Discounts
```
┌─────────────────────────────────────────────────────┐
│ PRODUCTS: GET /creator/{wallet}/products            │
│ ┌────────────────────────────────────────┐          │
│ │ Name    │ Price │ Stock │ Active │ Actions │       │
│ │ T-Shirt │ 10 A  │ 50   │ ✅    │ ✏️ 🗑️  │       │
│ │ Sticker │ 2 A   │ ∞    │ ✅    │ ✏️ 🗑️  │       │
│ └────────────────────────────────────────┘          │
│ [+ Add Product] → POST /creator/{wallet}/products   │
│ ✏️ Edit → PATCH /creator/{wallet}/products/{id}     │
│ 🗑️ Delete → DELETE /creator/{wallet}/products/{id}  │
│                                                     │
│ DISCOUNTS: GET /creator/{wallet}/discounts          │
│ ┌────────────────────────────────────────┐          │
│ │ Type   │ Value │ Min Shawty │ Bauni?  │           │
│ │ PERCENT│ 20%   │ 1 token    │ No      │           │
│ │ FIXED  │ 5 ALGO│ 0          │ Yes     │           │
│ └────────────────────────────────────────┘          │
│ [+ Add Discount] → POST /creator/{wallet}/discounts │
└─────────────────────────────────────────────────────┘
```

#### Tab 4: Contract
```
┌─────────────────────────────────────────────────────┐
│ GET /creator/{wallet}/contract                      │
│ GET /contract/info + GET /contract/list              │
│                                                     │
│ App ID: 755779  |  Address: CFZR...HM4  |  v1      │
│ Status: ● Active                                    │
│                                                     │
│ [⏸ Pause]  → POST /creator/{w}/pause-contract      │
│              → returns unsigned txn                  │
│              → peraWallet.signTxn(txn)               │
│              → POST /submit { signed_txn }           │
│                                                     │
│ [▶ Unpause] → POST /creator/{w}/unpause-contract    │
│              → same Pera sign + submit flow          │
│                                                     │
│ [⬆ Upgrade] → POST /creator/{w}/upgrade-contract    │
│                                                     │
│ Contract Deploy: POST /contract/deploy               │
│ Contract Fund:   POST /contract/fund                 │
└─────────────────────────────────────────────────────┘
```

### Inter-Page Links from Creator Hub
| Action | Destination |
|--------|------------|
| "View Store" | `/store/{wallet}` |
| "View Leaderboard" | `/explore` |
| Navbar "Fan" link | `/fan` |
| Navbar "Tip" link (self-test) | `/tip/{wallet}` |

---

## Step 1.5 — Page 3: Fan Hub (`/fan`)

### Auth Guard: Redirect to `/` if not authenticated

### Tab Structure
```
[My NFTs] [Loyalty & Membership] [Shawty Tokens] [Stats]
```

#### Tab 1: My NFTs
```
GET /fan/{wallet}/inventory?skip=0&limit=50 → NFT grid
GET /fan/{wallet}/pending → alert: "3 NFTs awaiting claim!"
GET /fan/{wallet}/golden-odds → "Golden chance: 12.3%"

Each NFT card shows: image, name, type badge, creator
Click card → Modal: GET /nft/{assetId} → full details

Pending Claim Flow:
  1. GET /fan/{wallet}/pending → list
  2. Click "Claim" on pending NFT
  3. POST /nft/optin { fan_wallet, asset_id } → unsigned txn
  4. peraWallet.signTxn(txn) → signed
  5. POST /submit { signed_txn }
  6. POST /fan/{wallet}/claim/{nftId}
  7. Refresh inventory

Alt view: GET /nft/inventory/{wallet} (same data, different endpoint)
```

#### Tab 2: Loyalty & Membership
```
BUTKI LOYALTY:
  GET /butki/{wallet}/loyalty → cards per creator
  Each card: tip_count, badges_earned, tips_to_next_badge
  Click card → GET /butki/{wallet}/loyalty/{creatorWallet}

BAUNI MEMBERSHIP:
  GET /bauni/{wallet}/memberships?active_only=false → all
  Each card: creator, expires_at, days_remaining, is_active
  Click check → GET /bauni/{wallet}/membership/{creatorWallet}
  Verify button → POST /bauni/verify { fan_wallet, creator_wallet }
```

#### Tab 3: Shawty Tokens
```
GET /shawty/{wallet}/tokens?include_spent=true → token grid

Each token card: asset_id, creator, status (Active/Burned/Locked)

Actions (on active tokens only):
  🔥 Burn → POST /shawty/burn { fan_wallet, asset_id, item_description }
  🔒 Lock → POST /shawty/lock { fan_wallet, asset_id, discount_description }
  📤 Transfer → POST /shawty/transfer { from_wallet, to_wallet, asset_id }

Before actions: GET /shawty/{wallet}/validate/{assetId}

History: GET /shawty/{wallet}/redemptions?limit=50

Transfer NFT (golden): POST /nft/transfer { from_wallet, to_wallet, asset_id }
```

#### Tab 4: Stats
```
GET /fan/{wallet}/stats → all data

Stat cards: totalTips, totalAlgoSpent, uniqueCreators, totalNfts
Creator breakdown table: creatorWallet, tipCount, totalAlgo
Recent tips timeline: txId, creatorWallet, amountAlgo, memo, detectedAt
```

### Inter-Page Links from Fan Hub
| Action | Destination |
|--------|------------|
| Creator name click (in stats) | `/store/{creatorWallet}` |
| "Tip this creator" | `/tip/{creatorWallet}` |
| "Browse store" | `/store/{creatorWallet}` |
| "View Leaderboard" | `/explore` |

---

# PHASE 2

## Step 2.1 — Page 4: Store (`/store/:creatorWallet`)

### No auth for browsing. Auth required for checkout.

```
┌─────────────────────────────────────────────────────┐
│ Store: CreatorA (CFZR...HM4)                        │
│ [All Products] [Members Only]                       │
│                                                     │
│ All Products tab:                                   │
│   GET /creator/{w}/store?limit=50&offset=0 (public) │
│                                                     │
│ Members Only tab:                                   │
│   GET /bauni/{fan}/membership/{creator} → check     │
│   GET /creator/{w}/store/members-only?fanWallet=... │
│                                                     │
│ Product Grid:                                       │
│ ┌──────┐ ┌──────┐ ┌──────┐                         │
│ │T-Shrt│ │Poster│ │Badge │  [Add to Cart]           │
│ │10 A  │ │5 A   │ │2 A   │                          │
│ └──────┘ └──────┘ └──────┘                          │
│                                                     │
│ Cart Drawer (slide-out):                            │
│   Items list → [Get Quote]                          │
│   POST /creator/{w}/store/quote                     │
│   { fanWallet, items, shawtyAssetIds }              │
│                                                     │
│   Shawty discount selector:                         │
│   GET /shawty/{fan}/tokens → available tokens       │
│   GET /shawty/{fan}/validate/{id} → validate each   │
│                                                     │
│   Quote displays: subtotal, discount, total          │
│   [Place Order]                                     │
│   POST /creator/{w}/store/order → order created     │
│                                                     │
│ Order History (bottom section):                     │
│   GET /fan/{wallet}/orders?limit=50                 │
│   GET /onramp/fan/{wallet}/orders                   │
│   GET /onramp/order/{partnerOrderId}                │
│                                                     │
│ Links: [Tip Creator] → /tip/{creatorWallet}         │
│        [Back to Explore] → /explore                 │
│                                                     │
│ Txn submission: POST /submit, POST /submit-group    │
└─────────────────────────────────────────────────────┘
```

---

## Step 2.2 — Page 5: Explore (`/explore`)

```
┌─────────────────────────────────────────────────────┐
│ 🏆 Global Leaderboard                               │
│ GET /leaderboard/global/top-creators?limit=50       │
│                                                     │
│ #  Creator        ALGO Received  Tips  Fans         │
│ 1  CFZR...HM4    245.5          47    18            │
│ 2  ABCD...XYZ    180.2          35    12            │
│                                                     │
│ Click row → expand inline detail:                   │
│ ┌─────────────────────────────────────────────────┐ │
│ │ GET /leaderboard/{creatorWallet}?limit=10       │ │
│ │ Top Fans by ALGO:                               │ │
│ │ #1 K2N7..  50.2 ALGO  12 tips  3 NFTs          │ │
│ │                                                 │ │
│ │ GET /butki/leaderboard/{creatorWallet}?limit=10 │ │
│ │ Top Fans by Butki Badges:                       │ │
│ │ #1 K2N7..  4 badges  12 tips                    │ │
│ │                                                 │ │
│ │ [View Store →] /store/{creatorWallet}            │ │
│ │ [Tip Creator →] /tip/{creatorWallet}             │ │
│ └─────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

---

## Step 2.3 — Page 6: Tip (`/tip/:creatorWallet`)

```
┌─────────────────────────────────────────────────────┐
│ 💸 Tip CreatorA                                     │
│                                                     │
│ GET /creator/{w}/contract → app_id, app_address     │
│ Contract: 755779 | Address: CFZR...HM4              │
│                                                     │
│ Amount: [____] ALGO     Memo: [________] (optional) │
│                                                     │
│ GET /butki/{fan}/loyalty/{creator}                   │
│ Loyalty: 3/5 tips → next Butki badge 🏆             │
│                                                     │
│ GET /bauni/{fan}/membership/{creator}                │
│ Membership: ✅ Active (24 days left) 🎫             │
│                                                     │
│ GET /fan/{fan}/golden-odds?amount_algo=X             │
│ Golden Odds: 12.3% at this amount ⭐                │
│                                                     │
│ [ 💸 Send Tip via Pera Wallet ]                     │
│   1. GET /params → txn params                       │
│   2. Build ApplicationCallTxn (app_id, amount, memo)│
│   3. peraWallet.signTxn(txn) → signed               │
│   4. POST /submit { signed_txn }                    │
│   5. Show success toast                             │
│   6. Listener auto-processes → mints NFT            │
│   7. Refresh loyalty + golden odds                  │
│                                                     │
│ Links: [View Store →] /store/{creatorWallet}         │
│        [My Collection →] /fan                        │
│        [Back →] /explore                             │
└─────────────────────────────────────────────────────┘
```

---

## Step 2.4 — Polish

### Navbar (all pages)
```
┌──────────────────────────────────────────────────────┐
│ 🌟 FanForge  │ Explore │ [Creator Hub|Fan Hub] │ Tip │
│              │ /explore│ /creator or /fan       │     │
│              │         │ (based on role)        │     │
│              │                    [CFZR...HM4 🔌]    │
│              │                    wallet badge        │
│              │                    click → disconnect   │
└──────────────────────────────────────────────────────┘
Health indicator: GET /health → green/red dot
```

### Cross-Page Navigation Summary

```
Landing  ──→  Creator Hub  ──→  Store (own)
   │              │                │
   │              ├──→  Explore    │
   │              │       │        │
   │              │       ├──→ Store (any creator)
   │              │       │        │
   ├──→  Fan Hub  │       ├──→ Tip (any creator)
   │       │      │       │
   │       ├──→ Store ←───┘
   │       │
   │       ├──→ Tip
   │       │
   └──→  Explore
```

### Animations
- Page transitions: fade-in 200ms
- Tab switches: slide 150ms
- Card hover: scale(1.02) + shadow lift
- Modal: fade + scale from 0.95
- Toast: slide-in from top-right
- Loading: skeleton pulse animation

### Responsive Breakpoints
- Desktop: > 1024px (full sidebar + grid)
- Tablet: 768-1024px (collapsed sidebar)
- Mobile: < 768px (bottom nav, stacked cards)
