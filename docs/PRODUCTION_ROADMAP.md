# Production Roadmap

> Items documented here are **known gaps** between the current TestNet boilerplate
> and a production-ready MainNet deployment.  They are intentionally deferred to
> keep the boilerplate focused — but must be addressed before real users interact
> with the platform.

---

## Authentication — Ed25519 Signature Verification

**Current state:** The `X-Wallet-Address` header is compared against the URL path
parameter.  This prevents *accidental* misuse but is trivially bypassable by a
determined attacker.

**Production fix:**
1. Backend generates a random **nonce** (stored server-side with TTL).
2. Frontend signs the nonce with the user's Pera Wallet private key.
3. Backend verifies the Ed25519 signature against the wallet's public key.
4. On success, issue a short-lived JWT for subsequent requests.

**Effort:** ~2 days (backend + frontend integration with Pera Wallet SDK).

---

## Database — PostgreSQL

**Current state:** SQLite via `aiosqlite`.  Single-file, no concurrent write
support, no connection pooling.

**Production fix:**
- Swap `DATABASE_URL` to a PostgreSQL connection string.
- The async SQLAlchemy engine already supports `asyncpg`.
- Free-tier options: Supabase, Neon, Railway.

```env
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/sticker_platform
```

**Effort:** ~30 minutes (URL swap, tested with Alembic migrations).

---

## Key Management — HSM / Multi-Sig

**Current state:** A single `PLATFORM_MNEMONIC` in `.env` controls all platform
operations (contract deployment, NFT minting, transfers, funding).

**Production fix:**
- Use a **Hardware Security Module** (HSM) or **KMS** (AWS KMS, GCP Cloud KMS)
  for the platform signing key.
- Implement **multi-sig** for high-value operations (contract deployment,
  large transfers).
- Separate keys by responsibility: minting key, deployment key, admin key.
- Implement **key rotation** procedures.

**Effort:** ~1 week (architecture + HSM integration + testing).

---

## Rate Limiting — Redis-Backed

**Current state:** In-memory sliding-window counter per (IP, route).  Each
uvicorn worker has its own state; memory grows unbounded.

**Production fix:**
- Replace with **Redis-backed** rate limiter (e.g., `slowapi` or custom
  middleware using `redis.asyncio`).
- Shared state across all workers.
- TTL-based cleanup (no memory leak).

**Effort:** ~2 hours.

---

## Minting Pipeline — Task Queue

**Current state:** NFT minting (`mint_soulbound`, `mint_golden`) runs
synchronously inside the async listener loop, blocking the event loop for
~4.5 seconds per mint (`wait_for_confirmation`).

**Production fix:**
- Offload minting to a **task queue** (Celery with Redis broker, or ARQ for
  async-native).
- Listener enqueues mint tasks; workers process them independently.
- Enables parallel minting and horizontal scaling.

**Effort:** ~3 days (queue setup + worker + retry logic refactor).

---

## Non-Idempotent Contract Deployment

**Current state:** If `deploy_tip_proxy()` succeeds on-chain but the subsequent
DB commit fails, the contract is orphaned — it exists on Algorand but not in
our database.

**Production fix:**
- Implement an **idempotency key** pattern:
  1. Generate a unique deployment ID before the on-chain call.
  2. Store it as `pending` in the DB before deploying.
  3. Update to `active` after on-chain confirmation.
  4. On retry, check if a `pending` deployment exists and recover it.

**Effort:** ~4 hours.

---

## Listener Liveness / Monitoring

**Current state:** The `/listener/status` endpoint reports the `_is_running` flag,
but there's no heartbeat or watchdog.  If the asyncio task hangs silently,
`_is_running` stays `True` forever.

**Production fix:**
- Add a **heartbeat timestamp** updated every poll cycle.
- Health check endpoint returns `unhealthy` if heartbeat is stale (> 2× poll
  interval).
- Integrate with monitoring (Prometheus, Datadog, or simple uptime check).
- Auto-restart listener task on detected hang.

**Effort:** ~2 hours.

---

## Network Abstraction (TestNet → MainNet)

**Current state:** Node URLs are hardcoded to TestNet defaults in `config.py`.
There's no chain-ID validation or protection against accidentally deploying to
MainNet.

**Production fix:**
- Add a `NETWORK` environment variable (`testnet` | `mainnet`).
- Validate chain genesis hash on startup.
- Block MainNet operations if `SIMULATION_MODE` or `DEMO_MODE` is enabled.
- Separate config profiles per network.

**Effort:** ~2 hours.

---

## Automated Testing

**Current state:** No pytest suites.  The `scripts/test_*.py` files are manual
HTTP-request scripts, not proper automated tests.

**Production fix:**
- Unit tests for all services (`contract_service`, `nft_service`,
  `listener_service`, `probability_service`).
- Integration tests for API endpoints with `httpx.AsyncClient`.
- Smart contract tests using Algorand sandbox.
- CI/CD pipeline (GitHub Actions).

**Effort:** Ongoing (~1 week for initial coverage, then continuous).

---

## Priority Order

| Priority | Item | Risk if Skipped |
|----------|------|----------------|
| P0 | Ed25519 auth | Anyone can impersonate any wallet |
| P0 | PostgreSQL | DB locks under concurrent load |
| P1 | Key management | Single point of failure for all funds |
| P1 | Task queue | Event loop blocks under load |
| P1 | Listener liveness | Silent failures go undetected |
| P2 | Redis rate limiter | Multi-worker bypass |
| P2 | Idempotent deploy | Orphaned contracts on failure |
| P2 | Network abstraction | Accidental MainNet ops |
| P3 | Automated testing | Regressions go undetected |
