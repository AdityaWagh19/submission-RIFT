"""
Unit tests for merch service.

Tests product CRUD, discount rules, quote building, and order settlement.
"""
import pytest

from services import merch_service
from db_models import Product, DiscountRule, Order, OrderItem


@pytest.mark.asyncio
async def test_create_product(db_session, sample_creator_wallet):
    """Create a new product."""
    product = await merch_service.create_product(
        db_session,
        creator_wallet=sample_creator_wallet,
        slug="test-tshirt",
        name="Test T-Shirt",
        description="A test product",
        image_ipfs_hash="QmTest123",
        price_algo=10.0,
        stock_quantity=100,
        active=True,
    )
    await db_session.commit()

    assert product.slug == "test-tshirt"
    assert product.price_algo == 10.0
    assert product.stock_quantity == 100
    assert product.active is True


@pytest.mark.asyncio
async def test_build_quote_no_discount(db_session, sample_creator_wallet, sample_fan_wallet):
    """Quote without discounts should equal subtotal."""
    product = await merch_service.create_product(
        db_session,
        creator_wallet=sample_creator_wallet,
        slug="test-product",
        name="Test",
        description=None,
        image_ipfs_hash=None,
        price_algo=10.0,
        stock_quantity=None,
        active=True,
    )
    await db_session.commit()

    quote = await merch_service.build_quote(
        db_session,
        fan_wallet=sample_fan_wallet,
        creator_wallet=sample_creator_wallet,
        items=[{"product_id": product.id, "quantity": 2}],
    )

    assert quote["success"] is True
    assert quote["subtotal_algo"] == 20.0
    assert quote["discount_algo"] == 0.0
    assert quote["total_algo"] == 20.0


@pytest.mark.asyncio
async def test_build_quote_with_percent_discount(db_session, sample_creator_wallet, sample_fan_wallet):
    """Quote with percentage discount should apply correctly."""
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

    # Create 10% discount rule
    await merch_service.create_discount_rule(
        db_session,
        creator_wallet=sample_creator_wallet,
        product_id=None,  # Global discount
        discount_type="PERCENT",
        value=10.0,
        min_shawty_tokens=0,
        requires_bauni=False,
        max_uses_per_wallet=None,
    )
    await db_session.commit()

    quote = await merch_service.build_quote(
        db_session,
        fan_wallet=sample_fan_wallet,
        creator_wallet=sample_creator_wallet,
        items=[{"product_id": product.id, "quantity": 1}],
    )

    assert quote["success"] is True
    assert quote["subtotal_algo"] == 100.0
    assert quote["discount_algo"] == 10.0  # 10% of 100
    assert quote["total_algo"] == 90.0


@pytest.mark.asyncio
async def test_build_quote_with_shawty_discount(db_session, sample_creator_wallet, sample_fan_wallet):
    """Quote requiring Shawty tokens should validate ownership."""
    from services import shawty_service

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

    # Create discount requiring 1 Shawty token
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

    # Register a Shawty token
    token = await shawty_service.register_purchase(
        db_session,
        asset_id=2001,
        owner_wallet=sample_fan_wallet,
        creator_wallet=sample_creator_wallet,
        purchase_tx_id="tx_shawty",
        amount_paid_micro=2_000_000,
    )
    await db_session.commit()

    quote = await merch_service.build_quote(
        db_session,
        fan_wallet=sample_fan_wallet,
        creator_wallet=sample_creator_wallet,
        items=[{"product_id": product.id, "quantity": 1}],
        shawty_asset_ids=[2001],
    )

    assert quote["success"] is True
    assert quote["discount_algo"] == 20.0  # 20% discount applied


@pytest.mark.asyncio
async def test_build_quote_requires_bauni(db_session, sample_creator_wallet, sample_fan_wallet):
    """Quote requiring Bauni membership should check membership."""
    from services import bauni_service

    product = await merch_service.create_product(
        db_session,
        creator_wallet=sample_creator_wallet,
        slug="members-only",
        name="Members Only",
        description=None,
        image_ipfs_hash=None,
        price_algo=50.0,
        stock_quantity=None,
        active=True,
    )
    await db_session.commit()

    # Create discount requiring Bauni
    await merch_service.create_discount_rule(
        db_session,
        creator_wallet=sample_creator_wallet,
        product_id=None,
        discount_type="PERCENT",
        value=15.0,
        min_shawty_tokens=0,
        requires_bauni=True,
        max_uses_per_wallet=None,
    )
    await db_session.commit()

    # Quote without membership should fail
    quote_no_membership = await merch_service.build_quote(
        db_session,
        fan_wallet=sample_fan_wallet,
        creator_wallet=sample_creator_wallet,
        items=[{"product_id": product.id, "quantity": 1}],
        require_membership=True,
    )

    assert quote_no_membership["success"] is False
    assert "membership" in quote_no_membership["error"].lower()

    # Create membership
    await bauni_service.purchase_membership(
        db_session,
        fan_wallet=sample_fan_wallet,
        creator_wallet=sample_creator_wallet,
        asset_id=1001,
        purchase_tx_id="tx_bauni",
        amount_paid_micro=5_000_000,
    )
    await db_session.commit()

    # Quote with membership should succeed
    quote_with_membership = await merch_service.build_quote(
        db_session,
        fan_wallet=sample_fan_wallet,
        creator_wallet=sample_creator_wallet,
        items=[{"product_id": product.id, "quantity": 1}],
        require_membership=True,
    )

    assert quote_with_membership["success"] is True
    assert quote_with_membership["discount_algo"] == 7.5  # 15% of 50


@pytest.mark.asyncio
async def test_settle_order_payment(db_session, sample_creator_wallet, sample_fan_wallet):
    """Order settlement should mark order as PAID and adjust inventory."""
    product = await merch_service.create_product(
        db_session,
        creator_wallet=sample_creator_wallet,
        slug="test-product",
        name="Test",
        description=None,
        image_ipfs_hash=None,
        price_algo=10.0,
        stock_quantity=100,
        active=True,
    )
    await db_session.commit()

    quote = await merch_service.build_quote(
        db_session,
        fan_wallet=sample_fan_wallet,
        creator_wallet=sample_creator_wallet,
        items=[{"product_id": product.id, "quantity": 5}],
    )

    order = await merch_service.create_order(
        db_session,
        fan_wallet=sample_fan_wallet,
        creator_wallet=sample_creator_wallet,
        quote=quote,
    )
    await db_session.commit()

    assert order.status == "PENDING_PAYMENT"

    # Settle payment
    settled = await merch_service.settle_order_payment(
        db_session,
        order_id=order.id,
        fan_wallet=sample_fan_wallet,
        creator_wallet=sample_creator_wallet,
        amount_algo=50.0,
        tx_id="tx_payment_123",
    )
    await db_session.commit()

    assert settled is True
    await db_session.refresh(order)
    assert order.status == "PAID"
    assert order.tx_id == "tx_payment_123"

    # Inventory should be reduced
    await db_session.refresh(product)
    assert product.stock_quantity == 95  # 100 - 5
