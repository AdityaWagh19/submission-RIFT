# TODO FOR JULES — Automated Testing Suite Expansion
#
# This file serves as the master task list for Jules to expand the test suite
# to comprehensive coverage of the entire FanForge codebase.
#
# ═══════════════════════════════════════════════════════════════════════
# CONTEXT
# ═══════════════════════════════════════════════════════════════════════
#
# Project: FanForge — Creator Tipping Platform on Algorand
# Backend: FastAPI + SQLAlchemy (async) + PyTeal smart contracts
# Test Framework: pytest + pytest-asyncio + httpx (AsyncClient)
# Database: SQLite (in-memory for tests)
#
# Current test files (in backend/tests/):
#   conftest.py              → Shared fixtures (db, client, factories, mocks)
#   test_validators.py       → Address validation (10 tests)
#   test_models.py           → Pydantic model validation (15 tests)
#   test_auth.py             → Wallet auth middleware (5 tests)
#   test_rate_limit.py       → Rate limiter class (9 tests)
#   test_probability.py      → Golden sticker engine (15 tests)
#   test_membership.py       → Membership tier logic (15 tests)
#   test_transaction_service.py → Base64, submission, error classification (12 tests)
#   test_contract.py         → TipProxy PyTeal compile + metadata (12 tests)
#   test_db_models.py        → ORM model CRUD (9 tests)
#   test_routes.py           → API endpoint smoke tests (12 tests)
#
# Total: ~114 test cases across 11 files
#
# ═══════════════════════════════════════════════════════════════════════
# PHASE 1: EXPAND EXISTING TESTS (Priority: HIGH)
# ═══════════════════════════════════════════════════════════════════════
#
# Each test file has a # TODO FOR JULES: block at the top with specific
# expansion tasks. Read each file's TODO and implement ALL items.
#
# ═══════════════════════════════════════════════════════════════════════
# PHASE 2: ADD MISSING TEST FILES (Priority: MEDIUM)
# ═══════════════════════════════════════════════════════════════════════
#
# Create the following new test files:
#
# 1. test_config.py
#    - Test settings loading from environment variables
#    - Test production mode validation (simulation/demo modes must be False)
#    - Test default values for all settings
#    - Test invalid env var values (non-numeric, empty, etc.)
#
# 2. test_ipfs_service.py
#    - Mock Pinata HTTP calls (httpx.AsyncClient)
#    - Test image upload → returns CID
#    - Test ARC-3 metadata generation and upload
#    - Test error handling (Pinata down, invalid image, rate limit)
#    - Test gateway URL construction
#
# 3. test_nft_service.py
#    - Mock algod client
#    - Test mint_soulbound() — verify ASA config (default_frozen=True, total=1)
#    - Test mint_golden() — verify ASA config (default_frozen=False, total=1)
#    - Test transfer_golden() — verify correct asset transfer txn
#    - Test opt_in() — verify ASA opt-in txn
#    - Test error handling for each operation
#
# 4. test_contract_service.py
#    - Mock algod client and file system
#    - Test load_teal() with valid/missing TEAL files
#    - Test deploy_tip_proxy() — verify txn parameters
#    - Test fund_contract() — verify payment txn
#    - Test decode_global_state() — verify byte/uint parsing
#    - Test get_contract_stats() — verify on-chain state reading
#
# 5. test_listener_service.py
#    - Mock Indexer HTTP responses
#    - Test log parsing (32B address + 8B amount + memo)
#    - Test minting pipeline routing (soulbound vs golden vs membership)
#    - Test checkpoint persistence and recovery
#    - Test pagination (next_token handling)
#    - Test error recovery (failed mint retry)
#
# 6. test_transak_service.py
#    - Test webhook signature verification (valid, invalid, missing)
#    - Test order creation (simulation mode vs production)
#    - Test ALGO delivery routing
#    - Test order status transitions
#
# ═══════════════════════════════════════════════════════════════════════
# PHASE 3: INTEGRATION & E2E TESTS (Priority: LOW)
# ═══════════════════════════════════════════════════════════════════════
#
# 1. test_full_flow.py — End-to-end test:
#    a. Register creator → deploy contract → create sticker template
#    b. Fan tips creator → listener detects → mints NFT → transfers to fan
#    c. Fan checks inventory → sees sticker
#    d. Check leaderboard reflects the tip
#
# 2. test_security.py — Security regression tests:
#    a. All 12 security fixes verified (mirrors test_security_fixes.py logic)
#    b. SQL injection attempts on all string parameters
#    c. XSS attempts in username and memo fields
#    d. Rate limit bypass attempts
#    e. CORS policy enforcement
#
# 3. test_performance.py — Performance benchmarks:
#    a. Endpoint response time < 200ms (p95)
#    b. Database query count per endpoint (no N+1 queries)
#    c. Contract compilation time < 5s
#
# ═══════════════════════════════════════════════════════════════════════
# HOW TO RUN
# ═══════════════════════════════════════════════════════════════════════
#
# Run all tests:
#   cd backend && python -m pytest tests/ -v
#
# Run only unit tests (no DB, no network):
#   cd backend && python -m pytest tests/ -v -m unit
#
# Run only integration tests:
#   cd backend && python -m pytest tests/ -v -m integration
#
# Run only smart contract tests:
#   cd backend && python -m pytest tests/ -v -m contract
#
# Run only API tests:
#   cd backend && python -m pytest tests/ -v -m api
#
# Run with coverage:
#   cd backend && python -m pytest tests/ -v --cov=. --cov-report=html
#
# ═══════════════════════════════════════════════════════════════════════
# DEPENDENCIES TO ADD TO requirements.txt
# ═══════════════════════════════════════════════════════════════════════
#
# pytest>=7.4.0
# pytest-asyncio>=0.23.0
# pytest-cov>=4.1.0
# httpx>=0.25.0  (already in requirements.txt)
#
