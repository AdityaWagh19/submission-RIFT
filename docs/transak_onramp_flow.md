# Transak On-Ramp Integration: UPI → ALGO → NFT Sticker

## Overview

This document explains how fans can **pay in INR (via UPI)** and the system
automatically converts it to ALGO, triggers the tip transaction using
**Pera Wallet on the backend**, and mints + transfers the NFT sticker — all
in a seamless flow.

---

## Architecture Flow

```
┌──────────────────────────────────────────────────────────────────────┐
│                        FAN's PERSPECTIVE                            │
│                                                                      │
│  1. Fan clicks "Tip ₹100" on the frontend                           │
│  2. Transak widget opens → Fan pays via UPI (PhonePe/GPay/Paytm)    │
│  3. Fan sees "Payment Successful! NFT incoming..."                   │
│  4. Fan receives Butki/Bauni/Shawty sticker NFT 🎉                  │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│                     BACKEND FLOW (what happens)                      │
│                                                                      │
│  ┌─────────┐    ┌──────────┐    ┌────────────┐    ┌──────────────┐  │
│  │  Fan's   │    │ Transak  │    │  Platform  │    │  TipProxy    │  │
│  │ Browser  │───▶│ Widget   │───▶│  Backend   │───▶│  Contract    │  │
│  └─────────┘    └──────────┘    └────────────┘    └──────────────┘  │
│       │              │               │                    │          │
│  Clicks "Tip"   Converts INR    Receives ALGO       Records tip     │
│                 → ALGO via UPI   webhook from        on Algorand     │
│                                  Transak             blockchain      │
│                                       │                    │          │
│                                       ▼                    ▼          │
│                                 ┌────────────┐    ┌──────────────┐  │
│                                 │  Pera      │    │  Listener    │  │
│                                 │  Wallet    │    │  Service     │  │
│                                 │  (Backend) │    │              │  │
│                                 └────────────┘    └──────────────┘  │
│                                       │                    │          │
│                                  Signs tip tx        Detects tip     │
│                                  to TipProxy         Mints NFT      │
│                                                     Transfers to    │
│                                                     fan's wallet    │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Detailed Step-by-Step Flow

### Step 1: Fan Initiates Tip (Frontend)
- Fan goes to creator's page, selects tip amount (₹100, ₹200, ₹500)
- Frontend opens the **Transak widget** (iframe/modal)
- Widget is pre-configured:
  - `fiatCurrency = "INR"`
  - `cryptoCurrencyCode = "ALGO"`
  - `network = "algorand"`
  - `paymentMethod = "upi"`
  - `walletAddress = <platform_wallet>` (NOT fan's wallet — we handle routing)

### Step 2: UPI Payment via Transak
- Fan pays using **UPI** (Google Pay, PhonePe, Paytm, etc.)
- Transak converts INR to ALGO at market rate
- ALGO is sent to the **platform's custodial wallet**

### Step 3: Webhook Notification
- Transak sends a **webhook** to our backend (`POST /webhooks/transak`)
- Webhook payload includes:
  - `status: "COMPLETED"`
  - `fiatAmount: 100` (INR)
  - `cryptoAmount: 11.08` (ALGO received)
  - `walletAddress: <platform_wallet>`
  - `partnerOrderId: <our_order_id>` (links to fan + creator)

### Step 4: Backend Routes the Tip
- Backend validates the webhook (HMAC signature verification)
- Reads `partnerOrderId` to identify the fan and creator
- Uses **Pera Wallet** (server-side signing with platform keys) to:
  1. Send the ALGO to the TipProxy smart contract
  2. TipProxy executes the inner payment to the creator
  3. TipProxy emits the tip log

### Step 5: Listener Detects & Mints NFT
- The existing **listener_service** detects the on-chain tip
- Routes through the minting pipeline based on ALGO amount
- Mints the appropriate NFT (Butki/Bauni/Shawty)
- Auto opt-in + transfer to fan's connected wallet

---

## Cost Breakdown Table

| Component | Fee / Cost | Who Pays | Notes |
|-----------|-----------|----------|-------|
| **Transak Processing Fee** | ~1.0% - 5.5% (varies by method) | Fan (deducted from amount) | UPI is typically on the lower end (~1-2%) |
| **Transak Exchange Rate Spread** | ~0.5% - 1.0% | Fan (baked into rate) | Market rate + small slippage |
| **UPI Payment** | ₹0 (free for individuals) | Free | UPI has no charges for P2P in India |
| **Algorand Network Fee** | 0.001 ALGO (~₹0.008) | Platform | Near-zero blockchain fees |
| **NFT Minting (ASA creation)** | 0.1 ALGO (~₹0.85) | Platform | One-time cost per NFT |
| **NFT Transfer (clawback/send)** | 0.002 ALGO (~₹0.017) | Platform | Auto opt-in + transfer |
| **Platform Fee (optional)** | 0% - 5% (configurable) | Fan or Creator | Your revenue model |

> **Key Advantage**: Algorand's fees are negligibly small (~₹1 total for mint + transfer),
> making micro-tipping economically viable even for ₹50-100 tips.

---

## Example: Fan Sends ₹100 Tip

**Current ALGO Price: ~₹8.47** (as of Feb 18, 2026)

```
┌─────────────────────────────────────────────────────────────────┐
│                    ₹100 TIP FLOW BREAKDOWN                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  Fan pays via UPI:                              ₹100.00          │
│                                                                   │
│  ─── Transak Deductions ───                                      │
│  Transak processing fee (~1.5%):                - ₹1.50          │
│  Exchange rate spread (~0.5%):                  - ₹0.50          │
│                                                  ─────────       │
│  Net INR converted to ALGO:                      ₹98.00          │
│                                                                   │
│  ─── Conversion ───                                              │
│  ₹98.00 ÷ ₹8.47/ALGO =                        11.57 ALGO       │
│  Transak network fee:                           - 0.001 ALGO     │
│                                                  ─────────       │
│  ALGO received by platform:                     ≈ 11.57 ALGO     │
│                                                                   │
│  ─── Platform Routing ───                                        │
│  Platform fee (2% example):                     - 0.23 ALGO      │
│  Algorand tip tx fee:                           - 0.002 ALGO     │
│                                                  ─────────       │
│  ALGO sent to creator via TipProxy:             ≈ 11.34 ALGO     │
│                                                                   │
│  ─── NFT Sticker ───                                             │
│  Tip threshold check: 11.34 ALGO ≥ 5 ALGO      → SHAWTY ⭐      │
│  NFT mint cost (from platform):                  0.1 ALGO        │
│  NFT transfer cost (from platform):              0.002 ALGO      │
│                                                                   │
│  ═══════════════════════════════════════════════════════════════  │
│                                                                   │
│  SUMMARY:                                                        │
│  ┌───────────────────────────────────────────────────────────┐   │
│  │  Fan paid:           ₹100 via UPI                         │   │
│  │  Creator received:   ~11.34 ALGO (≈ ₹96.05)              │   │
│  │  Fan received:       🌟 Shawty Golden NFT (tradable!)     │   │
│  │  Platform earned:    ~0.23 ALGO (≈ ₹1.95) + retains fee  │   │
│  │  Total fees:         ~₹3.95 (≈ 3.95%)                    │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Comparison: Different Tip Amounts

| Fan Pays | After Fees (~2%) | ALGO Received | Sticker Earned | Creator Gets |
|----------|-----------------|---------------|----------------|-------------|
| **₹50** | ₹49.00 | ~5.78 ALGO | 🌟 Shawty (golden) | ~5.67 ALGO (₹48.02) |
| **₹100** | ₹98.00 | ~11.57 ALGO | 🌟 Shawty (golden) | ~11.34 ALGO (₹96.05) |
| **₹20** | ₹19.60 | ~2.31 ALGO | 🔒 Bauni (soulbound) | ~2.27 ALGO (₹19.23) |
| **₹10** | ₹9.80 | ~1.16 ALGO | 🔒 Butki (soulbound) | ~1.13 ALGO (₹9.57) |

> **Note**: At current ALGO price (₹8.47), even a ₹10 UPI payment converts to
> enough ALGO for the Butki sticker (1 ALGO threshold). This makes micro-tipping
> very accessible!

---

## Transak Widget Configuration

```javascript
// Frontend: Initialize Transak widget
import { TransakConfig, Transak } from '@transak/ui-js-sdk';

const transakConfig = {
  apiKey: process.env.NEXT_PUBLIC_TRANSAK_API_KEY,
  environment: Transak.ENVIRONMENTS.STAGING,  // or PRODUCTION
  
  // Lock to INR → ALGO
  fiatCurrency: 'INR',
  cryptoCurrencyCode: 'ALGO',
  network: 'algorand',
  
  // Pre-fill amount
  fiatAmount: tipAmountINR,  // e.g., 100
  
  // Send ALGO to platform wallet (NOT fan's wallet)
  walletAddress: PLATFORM_WALLET_ADDRESS,
  
  // Payment method
  paymentMethod: 'upi',
  
  // Track which fan/creator this tip is for
  partnerOrderId: `tip_${fanId}_${creatorId}_${Date.now()}`,
  partnerCustomerId: fanId,
  
  // Skip unnecessary screens
  disableWalletAddressForm: true,
  hideMenu: true,
  
  // Theme
  themeColor: '6366f1',  // Match your brand
};

const transak = new Transak(transakConfig);
transak.init();

// Listen for completion
Transak.on(Transak.EVENTS.TRANSAK_ORDER_SUCCESSFUL, (orderData) => {
  // Notify backend that payment is complete
  fetch('/api/transak/order-complete', {
    method: 'POST',
    body: JSON.stringify({ orderId: orderData.status.id }),
  });
});
```

---

## Backend Webhook Handler

```python
# backend/routes/webhooks.py

@router.post("/webhooks/transak")
async def transak_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Receives Transak webhook when fiat→crypto conversion completes.
    
    Flow:
    1. Validate webhook signature
    2. Parse order details (fan, creator, ALGO amount)
    3. Route ALGO tip through TipProxy contract
    4. Listener will pick up the on-chain tip and mint NFT
    """
    body = await request.body()
    signature = request.headers.get("x-transak-signature")
    
    # Verify HMAC signature
    if not verify_transak_signature(body, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    data = await request.json()
    
    if data["status"] != "COMPLETED":
        return {"status": "ignored"}  # Only process completed orders
    
    # Extract order info
    partner_order_id = data["partnerOrderId"]  # "tip_fanId_creatorId_timestamp"
    crypto_amount = data["cryptoAmount"]        # ALGO received
    
    # Parse fan and creator from order ID
    _, fan_id, creator_id, _ = partner_order_id.split("_")
    
    # Deduct platform fee
    platform_fee = crypto_amount * 0.02  # 2% platform fee
    tip_amount = crypto_amount - platform_fee
    
    # Route tip through TipProxy via Pera Wallet (server-side)
    await route_fiat_tip(
        fan_id=fan_id,
        creator_wallet=creator_id,
        algo_amount=tip_amount,
        original_fiat=data["fiatAmount"],
        fiat_currency=data["fiatCurrency"],
    )
    
    return {"status": "processed"}
```

---

## Environment Variables Needed

```env
# Transak Configuration
TRANSAK_API_KEY=your-transak-api-key
TRANSAK_SECRET_KEY=your-transak-secret-key
TRANSAK_WEBHOOK_SECRET=your-webhook-hmac-secret
TRANSAK_ENVIRONMENT=STAGING  # or PRODUCTION

# Platform wallet (receives ALGO from Transak, then routes tips)
PLATFORM_WALLET_ADDRESS=CFZRI425PCKOE7PN3ICO...
PLATFORM_WALLET_MNEMONIC=your-25-word-mnemonic  # Server-side only!

# Fee configuration
PLATFORM_FEE_PERCENT=2.0  # Configurable platform fee
```

---

## Security Considerations

1. **Webhook Verification**: Always verify Transak's HMAC signature on webhooks
2. **Server-Side Only**: Platform wallet mnemonic never exposed to frontend
3. **Order Deduplication**: Track `partnerOrderId` to prevent double-processing
4. **Amount Validation**: Verify the `cryptoAmount` matches expected conversion
5. **Rate Limiting**: Protect webhook endpoint from abuse

---

## Integration Steps (Implementation Order)

1. **Sign up** for Transak developer account → get API keys
2. **Add Transak SDK** to frontend (`npm install @transak/ui-js-sdk`)
3. **Create webhook endpoint** (`/webhooks/transak`) in backend
4. **Implement `route_fiat_tip()`** function to send ALGO through TipProxy
5. **Add platform fee logic** to the tip routing
6. **Test on Transak Staging** environment with testnet ALGO
7. **Go live** with production keys
