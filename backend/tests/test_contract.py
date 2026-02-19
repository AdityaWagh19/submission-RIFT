"""
Tests for TipProxy smart contract — PyTeal compilation and logic verification.

Tests: Contract compiles, TEAL output structure, metadata, state schema.
"""
# TODO FOR JULES:
# 1. Add tests using algod dryrun to simulate contract execution
# 2. Add tests for tip() method — verify atomic group validation logic
# 3. Add tests for pause/unpause flow — ensure paused contract rejects tips
# 4. Add tests for update_min_tip — verify only creator can call
# 5. Add tests for inner transaction — verify ALGO forwarding
# 6. Add tests for on_creation — verify all global state initialized correctly
# 7. Add tests for unauthorized access (non-creator calling admin methods)
# 8. Add sandbox integration tests using algorand-sandbox Docker container
# END TODO

import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from pyteal import compileTeal, Mode


class TestTipProxyCompilation:
    """Tests for TipProxy contract compilation."""

    @pytest.mark.contract
    def test_approval_program_compiles(self):
        """Approval program should compile without errors."""
        from contracts.tip_proxy.contract import approval_program
        teal = compileTeal(approval_program(), mode=Mode.Application, version=8)
        assert teal is not None
        assert len(teal) > 0
        assert "#pragma version 8" in teal

    @pytest.mark.contract
    def test_clear_program_compiles(self):
        """Clear state program should compile without errors."""
        from contracts.tip_proxy.contract import clear_program
        teal = compileTeal(clear_program(), mode=Mode.Application, version=8)
        assert teal is not None
        assert "#pragma version 8" in teal

    @pytest.mark.contract
    def test_approval_contains_tip_method(self):
        """Compiled TEAL should contain the 'tip' method selector."""
        from contracts.tip_proxy.contract import approval_program
        teal = compileTeal(approval_program(), mode=Mode.Application, version=8)
        # Check for the byte string "tip" in the TEAL
        assert '"tip"' in teal or "0x746970" in teal  # "tip" in hex

    @pytest.mark.contract
    def test_approval_contains_pause_method(self):
        """Compiled TEAL should contain the 'pause' method selector."""
        from contracts.tip_proxy.contract import approval_program
        teal = compileTeal(approval_program(), mode=Mode.Application, version=8)
        assert '"pause"' in teal or "0x7061757365" in teal

    @pytest.mark.contract
    def test_approval_contains_inner_transaction(self):
        """Compiled TEAL should contain inner transaction instructions."""
        from contracts.tip_proxy.contract import approval_program
        teal = compileTeal(approval_program(), mode=Mode.Application, version=8)
        assert "itxn_begin" in teal
        assert "itxn_submit" in teal

    @pytest.mark.contract
    def test_approval_has_log_instruction(self):
        """Compiled TEAL should emit logs for tip events."""
        from contracts.tip_proxy.contract import approval_program
        teal = compileTeal(approval_program(), mode=Mode.Application, version=8)
        assert "log" in teal


class TestTipProxyMetadata:
    """Tests for contract metadata constants."""

    @pytest.mark.contract
    def test_contract_name(self):
        from contracts.tip_proxy.contract import CONTRACT_NAME
        assert CONTRACT_NAME == "TipProxy"

    @pytest.mark.contract
    def test_contract_version(self):
        from contracts.tip_proxy.contract import CONTRACT_VERSION
        assert CONTRACT_VERSION == "1.0.0"

    @pytest.mark.contract
    def test_global_state_schema(self):
        from contracts.tip_proxy.contract import GLOBAL_UINTS, GLOBAL_BYTES
        assert GLOBAL_UINTS == 5  # min_tip, total_tips, total_amount, version, paused
        assert GLOBAL_BYTES == 2  # creator_address, platform_address

    @pytest.mark.contract
    def test_local_state_schema(self):
        from contracts.tip_proxy.contract import LOCAL_UINTS, LOCAL_BYTES
        assert LOCAL_UINTS == 0
        assert LOCAL_BYTES == 0

    @pytest.mark.contract
    def test_methods_list(self):
        from contracts.tip_proxy.contract import CONTRACT_METHODS
        assert "tip" in CONTRACT_METHODS
        assert "update_min_tip" in CONTRACT_METHODS
        assert "pause" in CONTRACT_METHODS
        assert "unpause" in CONTRACT_METHODS
        assert len(CONTRACT_METHODS) == 4

    @pytest.mark.contract
    def test_description_not_empty(self):
        from contracts.tip_proxy.contract import CONTRACT_DESCRIPTION
        assert len(CONTRACT_DESCRIPTION) > 10
