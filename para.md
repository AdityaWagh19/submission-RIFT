# FanForge Demo — Comprehensive Prompt for Kimi K2

## Project Overview

Build a **single-page React application** (no backend, no blockchain, no wallet SDKs) called **FanForge Demo** — a fully interactive demo of a Web3 creator-economy platform where fans tip creators with ALGO tokens and earn collectible NFT stickers. Everything is **simulated with local state** (React useState/useReducer + localStorage for persistence). The app must feel premium, polished, and production-ready — not like a prototype. Use **React + Vite** with vanilla CSS. Do NOT use Tailwind. Use Google Fonts (Inter or Outfit). The design should be **dark-themed** with glassmorphism cards, gradient buttons, smooth micro-animations, and a color palette of deep navy (#0a0e1a), electric cyan (#00d4ff), vibrant purple (#7b2ff7), and gold (#ffd700).

---

## Architecture Constraints

- **Zero backend** — all data lives in React state + localStorage.
- **Zero blockchain** — no algosdk, no Pera Wallet SDK, no WalletConnect. Everything is mocked.
- **Fake wallet** — clicking "Connect Wallet" instantly generates a fake 58-character Algorand address (e.g., `DEMO7X...QR4A`) and stores it in localStorage. Show a "Connected" pill in the navbar.
- **Fake ALGO balance** — start with 100 ALGO. Tipping deducts from this balance. Buying merch deducts from this balance. Show the balance prominently in the navbar.
- **Persistent state** — use localStorage so the demo survives page refreshes. Include a "Reset Demo" button to clear all state.
- **Single `npm create vite` React project** — no extra dependencies beyond react, react-dom, and react-router-dom.

---

## Pages & Features (Fan Journey)

### 1. Landing Page (`/`)
- Hero section: "FanForge" title with animated gradient text, subtitle: "Web3 creator economy on Algorand. Tip creators, earn NFTs, unlock exclusive perks."
- Three NFT showcase cards (glass morphism) explaining each NFT type:
  - 🏆 **Butki** — Loyalty badge. Tip a creator 5 times → earn 1 Butki badge. Soulbound (non-transferable).
  - 🎫 **Bauni** — Membership pass. Purchase for 1 ALGO → 30-day access to exclusive content & members-only merch. Soulbound.
  - 🌟 **Shawty** — Golden collectible. Random chance to earn when tipping (10% odds). Fully transferable. Can be burned for merch, locked for discounts, or traded.
- "Connect Wallet" button → generates fake wallet + sets balance to 100 ALGO.
- After connecting: show quick action buttons: "Explore Creators", "My Collection", and the ALGO balance.

### 2. Explore Page (`/explore`)
- **Leaderboard** of 5 pre-seeded fake creators with:
  - Creator name & avatar (use emoji avatars like 🎨🎵🎬📸✍️)
  - Truncated wallet address
  - Total tips received, total ALGO earned
  - Number of active fans
- Each creator row expands to show: "💸 Send Tip" button, "🛍️ Visit Store" link, and their sticker template info.
- Creators to seed: "PixelArt Studio", "BeatMaker Jay", "Cinema Shorts", "PhotoLens Pro", "WriterDave"

### 3. Tip Page (`/tip/:creatorId`)
- Shows creator info: name, wallet, active contract (fake App ID like `755795000`, badge "ACTIVE").
- **Tip form**: amount input (default 1.0 ALGO, min 0.1), optional memo text field.
- **"Send X ALGO Tip" button** (gradient cyan-to-purple):
  - Deducts ALGO from fan's balance.
  - Increments the creator's tip count.
  - Shows a **success toast** with a fake transaction ID (random hex string).
  - Triggers Butki check: if tip count for this creator reaches a multiple of 5, auto-award a Butki badge and show a **celebration animation** (confetti or glow effect).
  - Triggers Shawty check: 10% random chance → if triggered, award a Shawty golden token and show a **golden glow celebration**.
- **Butki loyalty card** (bottom-left): shows badge count, progress bar (X/5 tips to next badge).
- **Bauni membership card** (bottom-right): shows membership status. If not a member, show "Not a member — tip to qualify". Include a "Buy Membership (1 ALGO)" button.
- **Golden Sticker odds display**: "🎲 10% chance of golden sticker on this tip"

### 4. My Collection Page (`/fan`) — Tabbed Layout
Four tabs:

**Tab 1: 🖼️ My NFTs**
- Grid of collected NFT cards (earned Butki badges, Bauni passes, Shawty tokens).
- Each card shows: emoji icon, NFT name, type badge (soulbound/golden), creator name, date earned.
- Click a card → Modal with full details (fake Asset ID, type, owner, minted date).
- Empty state: "No NFTs yet. Tip a creator to earn stickers!" with a link to Explore.

**Tab 2: 🏆 Loyalty & Membership**
- Butki section: list all creators the fan has tipped, showing per-creator: tip count, total ALGO tipped, badges earned, progress to next badge (progress bar).
- Bauni section: list all active/expired memberships, showing: creator name, days remaining, "Active"/"Expired" badge, amount paid.

**Tab 3: 🌟 Shawty Tokens**
- Grid of golden Shawty tokens owned.
- Each token shows: Token ID, creator, purchase price, status (Active/Burned/Locked).
- Action buttons on each active token:
  - 🔥 **Burn for Merch** — burns the token, adds a "merch credit" to the fan's account, shows success toast.
  - 🔒 **Lock for Discount** — locks the token, gives 20% discount on next store purchase, shows toast.
  - 📤 **Transfer** — simulates transferring to another wallet address (just marks as transferred).
- Redemption history table below: shows all burns/locks/transfers with dates.

**Tab 4: 📊 Stats**
- Stat cards (4 across): Total Tips Sent, ALGO Spent, Creators Supported, NFTs Collected.
- Per-creator breakdown table: Creator, Tips, ALGO, with "Tip" button.
- Recent tips table: Creator, Amount, Memo, Time (use relative time like "2 mins ago").

### 5. Creator Store Page (`/store/:creatorId`)
- Display 6 fake merch products per creator with:
  - Product image (use emoji: 👕 T-Shirt, 🧢 Cap, 🎨 Print, 📱 Phone Case, 🎒 Backpack, ☕ Mug)
  - Name, description, price in ALGO (range: 2–15 ALGO)
  - Stock quantity
  - "Add to Cart" button
- **Members-only tab**: 2 exclusive products (only visible to Bauni holders): "VIP Hoodie" (8 ALGO), "Signed Print" (12 ALGO).
- **Cart drawer/modal**: list items, quantities, remove button, apply Shawty discount (if fan has locked a Shawty → 20% off), subtotal/discount/total breakdown, "Place Order" button.
- **Order history table**: shows past orders with Order #, Total ALGO, Status (PAID/SHIPPED), Date.

---

## UI/UX Requirements

### Design System
- **Background**: deep navy gradient (`#0a0e1a` to `#0d1321`)
- **Cards**: glassmorphism with `rgba(255,255,255,0.05)` background, subtle border `rgba(255,255,255,0.1)`, `backdrop-filter: blur(10px)`
- **Primary action button**: gradient from cyan `#00d4ff` to purple `#7b2ff7`, with glow on hover
- **Typography**: "Inter" or "Outfit" from Google Fonts, white for headings, `rgba(255,255,255,0.7)` for body, `rgba(255,255,255,0.4)` for muted
- **Accents**: cyan `#00d4ff` for links/highlights, gold `#ffd700` for premium/golden items, green `#00ff88` for success, red `#ff4444` for errors
- **Badges**: small rounded pills — `badge-success` (green), `badge-warning` (gold), `badge-danger` (red), `badge-info` (cyan)

### Animations & Interactions
- Page transitions: fade-in on mount (300ms)
- Button hover: scale(1.02) + glow shadow
- Card hover: translateY(-2px) + enhanced border glow
- Toast notifications: slide in from top-right, auto-dismiss after 3 seconds
- Butki badge earn: confetti burst animation + golden toast
- Shawty golden win: screen flash gold + particle effect + special toast
- Progress bars: smooth width transition
- Tab switching: fade crossfade
- Modal: backdrop blur + scale-in animation

### Navbar
- Left: "FanForge" logo text with purple gradient
- Center: "Explore" | "My Collection" links (only visible when connected)
- Right: if connected → show green dot + truncated wallet address pill + ALGO balance badge + "Disconnect" button. If not connected → "Connect Wallet" button.

### Toast System
- Floating toast stack in top-right corner
- Types: success (green border), error (red border), info (cyan border), golden (gold border with shimmer)
- Each toast: icon + message + close button + auto-dismiss progress bar

---

## Data Seeding

Pre-populate localStorage (if empty) with:
- 5 creators with names, wallets, tip counts, sticker templates
- 3 sample merch products per creator
- The fan starts with 100 ALGO, no tips, no NFTs

---

## File Structure

```
src/
├── main.jsx
├── App.jsx
├── index.css                 // Complete design system
├── pages/
│   ├── Landing.jsx
│   ├── Explore.jsx
│   ├── Tip.jsx
│   ├── FanHub.jsx
│   └── Store.jsx
├── components/
│   ├── Navbar.jsx
│   ├── Toast.jsx
│   ├── Modal.jsx
│   ├── TabPanel.jsx
│   └── Confetti.jsx          // Celebration animation
├── context/
│   ├── WalletContext.jsx      // Fake wallet state + ALGO balance
│   └── ToastContext.jsx
├── data/
│   └── seed.js               // All fake creators, products, NFT templates
└── utils/
    └── helpers.js            // truncateWallet, formatDate, timeAgo, generateFakeId
```

---

## Critical Notes

1. **This is a DEMO** — everything is fake/simulated. No real blockchain, no real wallet, no real money. But it must LOOK and FEEL like a real Web3 app.
2. **ALGO as discount tokens**: When fans accumulate ALGO through the demo, they can "spend" it at creator stores. Shawty tokens provide 20% discount when locked. Burned Shawty tokens give merch credits.
3. **Every interaction must have feedback**: toast notification, animation, state update. No silent actions.
4. **Mobile responsive** but prioritize desktop (1440px+ viewport).
5. **All features must work end-to-end**: Connect → Explore → Tip → Earn NFTs → Visit Store → Buy Merch → View Collection. The full fan journey must be completable in one sitting.
6. **The 3-NFT system (Butki/Bauni/Shawty) is the core innovation** — prominently showcase how each type works differently and what benefits they provide.
