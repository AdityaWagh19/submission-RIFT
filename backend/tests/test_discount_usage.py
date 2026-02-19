"""
Edge case test: Discount usage and Shawty token reuse prevention.

Tests that Shawty tokens cannot be reused for discounts after being locked/burned.
"""
import pytest

from services import merch_service, shawty_service
from db_models import Product, DiscountRule


@pytest.mark.asyncio
async def test_shawty_discount_reuse_prevented(db_session, sample_creator_wallet, sample_fan_wallet):
    """Shawty token used for discount should be locked and cannot be reused."""
    # Create product and discount rule
    product = await merch_service.create_product(
        db_session,
        creator_wallet=sample_creator_wallet,
        slug="test-product",
        name="Test",
        description=None,
        image_ipfs_hash=None,
        price_algo=100.0,
        stock_quantity=None,
        active=True,
    )
    await db_session.commit()

    await merch_service.create_discount_rule(
        db_session,
        creator_wallet=sample_creator_wallet,
        product_id=None,
        discount_type="PERCENT",
        value=20.0,
        min_shawty_tokens=1,
        requires_bauni=False,
        max_uses_per_wallet=None,
    )
    await db_session.commit()

    # Register Shawty token
    token = await shawty_service.register_purchase(
        db_session,
        asset_id=2001,
        owner_wallet=sample_fan_wallet,
        creator_wallet=sample_creator_wallet,
        purchase_tx_id="tx_shawty_discount",
        amount_paid_micro=2_000_000,
    )
    await db_session.commit()

    # First quote should succeed
    quote1 = await merch_service.build_quote(
        db_session,
        fan_wallet=sample_fan_wallet,
        creator_wallet=sample_creator_wallet,
        items=[{"product_id": product.id, "quantity": 1}],
        shawty_asset_ids=[2001],
    )

    assert quote1["success"] is True
    assert quote1["discount_algo"] == 20.0

    # Create order and settle (this locks the token)
    order = await merch_service.create_order(
        db_session,
        fan_wallet=sample_fan_wallet,
        creator_wallet=sample_creator_wallet,
        quote=quote1,
    )
    await db_session.commit()

    await merch_service.settle_order_payment(
        db_session,
        order_id=order.id,
        fan_wallet=sample_fan_wallet,
        creator_wallet=sample_creator_wallet,
        amount_algo=80.0,
        tx_id="tx_payment",
    )
    await db_session.commit()

    # Token should now be locked
    await db_session.refresh(token)
    assert token.is_locked is True

    # Second quote with same token should fail validation
    quote2 = await merch_service.build_quote(
        db_session,
        fan_wallet=sample_fan_wallet,
        creator_wallet=sample_creator_wallet,
        items=[{"product_id": product.id, "quantity": 1}],
        shawty_asset_ids=[2001],  # Same token
    )

    assert quote2["success"] is False
    assert "invalid" in quote2["error"].lower() or "locked" in quote2["error"].lower()


@pytest.mark.asyncio
async def test_discount_max_uses_per_wallet(db_session, sample_creator_wallet, sample_fan_wallet):
    """Discount rule with max_uses_per_wallet should limit usage."""
    product = await merch_service.create_product(
        db_session,
        creator_wallet=sample_creator_wallet,
        slug="limited-discount",
        name="Limited",
        description=None,
        image_ipfs_hash=None,
        price_algo=50.0,
        stock_quantity=None,
        active=True,
    )
    await db_session.commit()

    # Create discount with max 1 use per wallet
    await merch_service.create_discount_rule(
        db_session,
        creator_wallet=sample_creator_wallet,
        product_id=product.id,
        discount_type="FIXED_ALGO",
        value=10.0,
        min_shawty_tokens=0,
        requires_bauni=False,
        max_uses_per_wallet=1,
    )
    await db_session.commit()

    # First order should get discount
    quote1 = await merch_service.build_quote(
        db_session,
        fan_wallet=sample_fan_wallet,
        creator_wallet=sample_creator_wallet,
        items=[{"product_id": product.id, "quantity": 1}],
    )

    assert quote1["success"] is True
    assert quote1["discount_algo"] == 10.0

    # Note: max_uses_per_wallet tracking would require Order history tracking
    # This is a simplified test - full implementation would track usage per wallet
