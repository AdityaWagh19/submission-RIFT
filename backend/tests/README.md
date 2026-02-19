# FanForge Test Suite

**Phase 8**: Comprehensive pytest-based test suite for FanForge backend.

## Test Structure

```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures (DB, mocks, test client)
├── test_butki_service.py    # Unit tests: Butki loyalty service
├── test_bauni_service.py    # Unit tests: Bauni membership service
├── test_shawty_service.py   # Unit tests: Shawty utility NFT service
├── test_merch_service.py    # Unit tests: Merch & discount service
├── test_auth_service.py     # Unit tests: Authentication service
├── test_double_tip.py        # Edge case: Idempotency tests
├── test_membership_expiry.py # Edge case: Membership expiry & gating
├── test_discount_usage.py    # Edge case: Discount reuse prevention
├── test_integration.py       # Integration: Full HTTP API tests
└── test_demo_flow_http.py    # Integration: End-to-end demo flow via HTTP
```

## Running Tests

### All Tests
```bash
cd backend
pytest tests/ -v
```

### With Coverage
```bash
pytest tests/ --cov=. --cov-report=html
# Open htmlcov/index.html in browser
```

### Specific Test Categories
```bash
# Unit tests only
pytest tests/test_*_service.py -v

# Edge case tests
pytest tests/test_double_tip.py tests/test_membership_expiry.py tests/test_discount_usage.py -v

# Integration tests
pytest tests/test_integration.py tests/test_demo_flow_http.py -v
```

### Specific Test
```bash
pytest tests/test_butki_service.py::test_record_tip_earns_badge_on_5th -v
```

## Test Categories

### Unit Tests (`test_*_service.py`)
- Test individual services in isolation
- Mock external dependencies (Algorand, IPFS)
- Fast execution, no external calls
- Examples:
  - `test_butki_service.py`: Tip recording, badge earning logic
  - `test_bauni_service.py`: Membership purchase, renewal, expiry
  - `test_shawty_service.py`: Token registration, burn, lock
  - `test_merch_service.py`: Product CRUD, discount rules, quotes

### Edge Case Tests
- Test error conditions and boundary cases
- Verify idempotency and data integrity
- Examples:
  - `test_double_tip.py`: Same tx_id processed twice
  - `test_membership_expiry.py`: Expired membership denial
  - `test_discount_usage.py`: Shawty token reuse prevention

### Integration Tests (`test_integration.py`, `test_demo_flow_http.py`)
- Test full HTTP API endpoints
- Use in-memory SQLite database
- Mock Algorand/IPFS services
- Examples:
  - Health endpoint
  - Creator registration flow
  - Fan inventory endpoint
  - Merch store endpoints
  - End-to-end demo flows

## Fixtures

### `db_session`
- In-memory SQLite database session
- Fresh database for each test
- Auto-creates all tables

### `test_client`
- FastAPI `TestClient` instance
- Overrides `get_db` dependency with test DB
- Use for HTTP endpoint testing

### `mock_algod_client`
- Mocked Algorand algod client
- Returns fake transaction IDs, app info, etc.
- Prevents real blockchain calls

### `mock_indexer`
- Mocked Algorand Indexer responses
- Returns empty transaction lists by default
- Customize per test

### `mock_ipfs`
- Mocked Pinata IPFS service
- Returns fake IPFS hashes
- Prevents real IPFS uploads

### Test Data Fixtures
- `sample_creator_wallet`: Creator address
- `sample_fan_wallet`: Fan address
- `sample_user`: Creator user in DB
- `sample_contract`: TipProxy contract in DB
- `sample_template`: Sticker template in DB

## Writing New Tests

### Unit Test Example
```python
@pytest.mark.asyncio
async def test_my_feature(db_session, sample_creator_wallet):
    # Arrange
    # Act
    result = await my_service.do_something(db_session, ...)
    # Assert
    assert result["success"] is True
```

### Integration Test Example
```python
@pytest.mark.asyncio
async def test_my_endpoint(test_client, db_session):
    response = test_client.get("/my/endpoint")
    assert response.status_code == 200
    assert "data" in response.json()
```

## Markers

- `@pytest.mark.unit`: Unit tests
- `@pytest.mark.integration`: Integration tests
- `@pytest.mark.edge_case`: Edge case tests
- `@pytest.mark.slow`: Tests > 1 second

Run with markers:
```bash
pytest -m unit -v
pytest -m integration -v
```

## CI Integration

Add to `.github/workflows/test.yml` or similar:
```yaml
- name: Run tests
  run: |
    cd backend
    pytest tests/ --cov=. --cov-report=xml
```

## Notes

- All tests use async/await (pytest-asyncio)
- Database is reset between tests
- External services are mocked
- No real blockchain/IPFS calls in tests
- `test_demo_flow.py` (scripts/) still exists for manual on-chain testing
