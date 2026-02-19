"""
Tests for Pydantic request/response models.

Tests: All V4 models — field validation, aliases, defaults, serialization.
"""
# TODO FOR JULES:
# 1. Add exhaustive boundary tests for min_tip_algo (0.09 should fail, 0.1 should pass, 1000.0 pass, 1000.1 fail)
# 2. Add tests for all model alias roundtrips (Python name ↔ camelCase JSON)
# 3. Add tests for CreatorDashboardResponse nested model serialization
# 4. Add tests for MintSoulboundRequest and MintGoldenRequest models
# 5. Add snapshot tests for response model JSON output
# END TODO

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from pydantic import ValidationError
from models import (
    CreatorRegisterRequest,
    CreatorRegisterResponse,
    ContractInfoResponse,
    ContractStatsResponse,
    StickerTemplateResponse,
    SubmitTransactionRequest,
    SubmitMultiTxnRequest,
)
from conftest import VALID_WALLET_1


class TestCreatorRegisterRequest:
    """Tests for CreatorRegisterRequest model."""

    @pytest.mark.unit
    def test_valid_request_with_defaults(self):
        req = CreatorRegisterRequest(walletAddress=VALID_WALLET_1)
        assert req.wallet_address == VALID_WALLET_1
        assert req.min_tip_algo == 1.0
        assert req.username is None

    @pytest.mark.unit
    def test_valid_request_with_all_fields(self):
        req = CreatorRegisterRequest(
            walletAddress=VALID_WALLET_1,
            username="TestArtist",
            minTipAlgo=2.5,
        )
        assert req.wallet_address == VALID_WALLET_1
        assert req.username == "TestArtist"
        assert req.min_tip_algo == 2.5

    @pytest.mark.unit
    def test_python_name_construction(self):
        """Model should accept Python field names (populate_by_name=True)."""
        req = CreatorRegisterRequest(
            wallet_address=VALID_WALLET_1,
            username="TestArtist",
            min_tip_algo=5.0,
        )
        assert req.wallet_address == VALID_WALLET_1
        assert req.min_tip_algo == 5.0

    @pytest.mark.unit
    def test_min_tip_too_low_raises(self):
        """min_tip_algo below 0.1 should fail validation."""
        with pytest.raises(ValidationError) as exc_info:
            CreatorRegisterRequest(walletAddress=VALID_WALLET_1, minTipAlgo=0.05)
        assert "min_tip_algo" in str(exc_info.value).lower() or "greater" in str(exc_info.value).lower()

    @pytest.mark.unit
    def test_min_tip_too_high_raises(self):
        """min_tip_algo above 1000 should fail validation."""
        with pytest.raises(ValidationError):
            CreatorRegisterRequest(walletAddress=VALID_WALLET_1, minTipAlgo=1001.0)

    @pytest.mark.unit
    def test_missing_wallet_raises(self):
        """walletAddress is required — missing should fail."""
        with pytest.raises(ValidationError):
            CreatorRegisterRequest(username="NoWallet")

    @pytest.mark.unit
    def test_min_tip_boundary_low(self):
        """Exactly 0.1 ALGO should pass."""
        req = CreatorRegisterRequest(walletAddress=VALID_WALLET_1, minTipAlgo=0.1)
        assert req.min_tip_algo == 0.1

    @pytest.mark.unit
    def test_min_tip_boundary_high(self):
        """Exactly 1000.0 ALGO should pass."""
        req = CreatorRegisterRequest(walletAddress=VALID_WALLET_1, minTipAlgo=1000.0)
        assert req.min_tip_algo == 1000.0


class TestSubmitTransactionRequest:
    """Tests for SubmitTransactionRequest model."""

    @pytest.mark.unit
    def test_valid_request(self):
        req = SubmitTransactionRequest(signed_txn="SGVsbG8gV29ybGQ=")
        assert req.signed_txn == "SGVsbG8gV29ybGQ="

    @pytest.mark.unit
    def test_empty_signed_txn_raises(self):
        """Empty signed_txn should fail (min_length=1)."""
        with pytest.raises(ValidationError):
            SubmitTransactionRequest(signed_txn="")

    @pytest.mark.unit
    def test_missing_signed_txn_raises(self):
        with pytest.raises(ValidationError):
            SubmitTransactionRequest()


class TestSubmitMultiTxnRequest:
    """Tests for SubmitMultiTxnRequest model."""

    @pytest.mark.unit
    def test_valid_group(self):
        req = SubmitMultiTxnRequest(signed_txns=["dHhuMQ==", "dHhuMg=="])
        assert len(req.signed_txns) == 2

    @pytest.mark.unit
    def test_empty_list_raises(self):
        with pytest.raises(ValidationError):
            SubmitMultiTxnRequest(signed_txns=[])

    @pytest.mark.unit
    def test_single_txn_valid(self):
        req = SubmitMultiTxnRequest(signed_txns=["dHhuMQ=="])
        assert len(req.signed_txns) == 1


class TestContractStatsResponse:
    """Tests for ContractStatsResponse model."""

    @pytest.mark.unit
    def test_serialization(self):
        resp = ContractStatsResponse(
            appId=12345,
            totalTips=42,
            totalAmountAlgo=100.5,
            minTipAlgo=1.0,
            paused=False,
            contractVersion=1,
        )
        assert resp.app_id == 12345
        assert resp.total_tips == 42
        assert resp.paused is False


class TestStickerTemplateResponse:
    """Tests for StickerTemplateResponse model."""

    @pytest.mark.unit
    def test_serialization_with_defaults(self):
        resp = StickerTemplateResponse(
            id=1,
            creatorWallet=VALID_WALLET_1,
            name="TestSticker",
            stickerType="soulbound",
            category="tip",
            tipThreshold=1.0,
        )
        assert resp.name == "TestSticker"
        assert resp.sticker_type == "soulbound"
        assert resp.mint_count == 0
        assert resp.ipfs_hash is None
