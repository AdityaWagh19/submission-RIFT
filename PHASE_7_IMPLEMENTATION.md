# Phase 7 Implementation: Performance & Scalability

**Date**: February 19, 2026  
**Status**: Complete

---

## Summary

Phase 7 improves async correctness, listener resilience, and reduces redundant external calls per `plan.md` Section 8.

---

## 8.1 Async Correctness & Blocking Operations

### Thread Pool Executor
- **`backend/services/async_executor.py`** – New module
  - `run_blocking(func, *args, **kwargs)` – Runs synchronous functions in a `ThreadPoolExecutor`
  - 4-worker pool for concurrent Algorand operations
  - `shutdown_executor()` called on app shutdown

### NFT Service Async Wrappers
- **`backend/services/nft_service.py`** – Async wrappers for blocking algod calls:
  - `mint_soulbound_sticker_async()` – Thread-pool wrapper for soulbound mint
  - `mint_golden_sticker_async()` – Thread-pool wrapper for golden mint
  - `send_nft_to_fan_async()` – Thread-pool wrapper for NFT transfer
- Listener uses these so minting no longer blocks the event loop (~4–5 s per mint offloaded).

### Existing Async Components
- Indexer queries: `httpx.AsyncClient`
- IPFS: `ipfs_service` uses async `httpx`
- Database: SQLAlchemy async session

---

## 8.2 Listener Throughput and Resilience

### Metrics
- **`backend/services/listener_metrics.py`** – New module
  - `tips_processed_total` – Total tips processed
  - `failed_mints_count` – Failed mint events
  - `retry_success_count` / `retry_fail_count` – Retry results
  - `indexer_query_errors` – Indexer request errors
  - `tips_per_minute` – Rolling 60s rate
  - `listener_lag_rounds` – `current_round - last_processed_round`
  - `heartbeat_age_seconds` – Time since last poll cycle

### Metrics Exposure
- `/listener/status` response includes a `metrics` object with all fields above.

### Retry Strategy
- **Exponential backoff** – 60s, 120s, 240s between retry cycles
- **Error classification** – `_is_transient_error()` for timeouts, connection, 502/503
- **Permanent errors** – Abandon after one retry when error looks non-transient

### Indexer Query Retry
- `_query_indexer()` retries on transient failures (Timeout, ConnectError, etc.)
- Backoff: 2s, 4s, 8s over up to 4 attempts

---

## 8.3 Caching and Repeated Calls

### TEAL Binaries
- **`contract_service.py`** – `_compiled_program_cache` (unchanged)
  - In-memory cache for compiled approval/clear programs
  - Avoids recompiling TEAL on each deployment

### Contract Stats
- **`contract_service.py`** – TTL cache for `get_contract_stats(app_id)`
  - 60-second TTL
  - Reduces repeated `application_info()` calls for dashboards
  - Key: `app_id`; value: `(stats_dict, expires_at)`

---

## Files Created

1. `backend/services/async_executor.py` – Thread pool for blocking calls
2. `backend/services/listener_metrics.py` – In-memory listener metrics

## Files Modified

1. `backend/services/nft_service.py` – Async mint/transfer wrappers
2. `backend/services/listener_service.py` – Async mints, metrics, retries, indexer backoff
3. `backend/services/contract_service.py` – Contract stats TTL cache
4. `backend/main.py` – Executor shutdown on app stop

---

## Verification

- Listener mint operations no longer block the event loop
- Metrics available at `GET /listener/status` under `metrics`
- Indexer retries with exponential backoff on transient failures
- Retry task uses exponential backoff and error classification
- Contract stats cached for 60 seconds
- Thread pool shut down cleanly on app shutdown

---

*Phase 7 completed: February 19, 2026*
