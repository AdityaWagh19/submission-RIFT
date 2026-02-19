"""
Merch service — products, discounts, and merch orders.

This is an off-chain commerce layer that integrates with on-chain payments via TipProxy.
Payments are detected by the listener using memo prefixes (e.g., ORDER:<id>).
"""

import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db_models import Product, DiscountRule, Order, OrderItem


async def create_product(
    db: AsyncSession,
    *,
    creator_wallet: str,
    slug: str,
    name: str,
    description: str | None,
    image_ipfs_hash: str | None,
    price_algo: float,
    stock_quantity: int | None,
    active: bool,
) -> Product:
    product = Product(
        creator_wallet=creator_wallet,
        slug=slug,
        name=name,
        description=description,
        image_ipfs_hash=image_ipfs_hash,
        price_algo=price_algo,
        stock_quantity=stock_quantity,
        active=active,
    )
    db.add(product)
    await db.flush()
    return product


async def list_creator_products(db: AsyncSession, *, creator_wallet: str) -> list[Product]:
    res = await db.execute(
        select(Product)
        .where(Product.creator_wallet == creator_wallet)
        .order_by(Product.created_at.desc())
    )
    return res.scalars().all()


async def get_product(db: AsyncSession, *, product_id: int, creator_wallet: str) -> Product | None:
    """Get a single product by ID, ensuring it belongs to the creator."""
    res = await db.execute(
        select(Product).where(
            Product.id == product_id,
            Product.creator_wallet == creator_wallet,
        )
    )
    return res.scalar_one_or_none()


async def update_product(
    db: AsyncSession,
    *,
    product_id: int,
    creator_wallet: str,
    slug: str | None = None,
    name: str | None = None,
    description: str | None = None,
    image_ipfs_hash: str | None = None,
    price_algo: float | None = None,
    max_per_order: int | None = None,
    stock_quantity: int | None = None,
    active: bool | None = None,
) -> Product:
    """Update a product's fields. Only provided fields are updated."""
    product = await get_product(db, product_id=product_id, creator_wallet=creator_wallet)
    if not product:
        from domain.errors import NotFoundError
        raise NotFoundError("Product", str(product_id))

    if slug is not None:
        product.slug = slug
    if name is not None:
        product.name = name
    if description is not None:
        product.description = description
    if image_ipfs_hash is not None:
        product.image_ipfs_hash = image_ipfs_hash
    if price_algo is not None:
        product.price_algo = price_algo
    if max_per_order is not None:
        product.max_per_order = max_per_order
    if stock_quantity is not None:
        product.stock_quantity = stock_quantity
    if active is not None:
        product.active = active

    product.updated_at = datetime.utcnow()
    await db.flush()
    return product


async def soft_delete_product(db: AsyncSession, *, product_id: int, creator_wallet: str) -> Product:
    """Soft-delete a product by setting active=False."""
    product = await get_product(db, product_id=product_id, creator_wallet=creator_wallet)
    if not product:
        from domain.errors import NotFoundError
        raise NotFoundError("Product", str(product_id))

    # Check if product has pending orders
    from db_models import OrderItem, Order
    items_res = await db.execute(
        select(OrderItem)
        .join(Order, OrderItem.order_id == Order.id)
        .where(
            OrderItem.product_id == product_id,
            Order.status == "PENDING_PAYMENT",
        )
    )
    pending_items = items_res.scalars().all()
    if pending_items:
        from domain.errors import ConflictError
        raise ConflictError(
            f"Cannot delete product {product.slug}: {len(pending_items)} pending order(s) exist"
        )

    product.active = False
    product.updated_at = datetime.utcnow()
    await db.flush()
    return product


async def list_store_products(db: AsyncSession, *, creator_wallet: str, limit: int = 50, offset: int = 0) -> list[Product]:
    res = await db.execute(
        select(Product)
        .where(Product.creator_wallet == creator_wallet, Product.active == True)
        .order_by(Product.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return res.scalars().all()


async def create_discount_rule(
    db: AsyncSession,
    *,
    creator_wallet: str,
    product_id: int | None,
    discount_type: str,
    value: float,
    min_shawty_tokens: int,
    requires_bauni: bool,
    max_uses_per_wallet: int | None,
) -> DiscountRule:
    rule = DiscountRule(
        creator_wallet=creator_wallet,
        product_id=product_id,
        discount_type=discount_type,
        value=value,
        min_shawty_tokens=min_shawty_tokens,
        requires_bauni=requires_bauni,
        max_uses_per_wallet=max_uses_per_wallet,
        active=True,
    )
    db.add(rule)
    await db.flush()
    return rule


async def list_discount_rules(db: AsyncSession, *, creator_wallet: str) -> list[DiscountRule]:
    res = await db.execute(
        select(DiscountRule)
        .where(DiscountRule.creator_wallet == creator_wallet)
        .order_by(DiscountRule.created_at.desc())
    )
    return res.scalars().all()


async def build_quote(
    db: AsyncSession,
    *,
    fan_wallet: str,
    creator_wallet: str,
    items: list[dict],
    shawty_asset_ids: list[int] | None = None,
    require_membership: bool = False,
) -> dict:
    """
    items: [{product_id:int, quantity:int}]
    """
    if not items:
        return {"success": False, "error": "Cart is empty"}

    # Membership gating (optional)
    if require_membership:
        from services import bauni_service

        m = await bauni_service.verify_membership(db, fan_wallet, creator_wallet)
        if not m["is_valid"]:
            return {"success": False, "error": "Active Bauni membership required"}

    product_ids = [int(i["product_id"]) for i in items]
    res = await db.execute(
        select(Product).where(Product.creator_wallet == creator_wallet, Product.id.in_(product_ids))
    )
    products = {p.id: p for p in res.scalars().all()}

    subtotal = 0.0
    normalized_items: list[dict] = []
    for i in items:
        pid = int(i["product_id"])
        qty = int(i.get("quantity", 1))
        if qty <= 0:
            return {"success": False, "error": "Quantity must be positive"}
        p = products.get(pid)
        if not p or not p.active:
            return {"success": False, "error": f"Product {pid} not available"}
        if p.stock_quantity is not None and qty > p.stock_quantity:
            return {"success": False, "error": f"Insufficient stock for {p.slug}"}
        if qty > p.max_per_order:
            return {"success": False, "error": f"Max {p.max_per_order} per order for {p.slug}"}

        line = p.price_algo * qty
        subtotal += line
        normalized_items.append(
            {"product_id": pid, "slug": p.slug, "name": p.name, "quantity": qty, "unit_price_algo": p.price_algo}
        )

    shawty_asset_ids = shawty_asset_ids or []
    if shawty_asset_ids:
        from services import shawty_service

        for aid in shawty_asset_ids:
            v = await shawty_service.validate_ownership(db, int(aid), fan_wallet)
            if not v["is_valid"]:
                return {"success": False, "error": f"Invalid Shawty token for discount: {aid}"}

    # Apply best matching discount rule
    rules_res = await db.execute(
        select(DiscountRule).where(
            DiscountRule.creator_wallet == creator_wallet,
            DiscountRule.active == True,
        )
    )
    rules = rules_res.scalars().all()

    discount = 0.0
    applied_rule_id = None
    for r in rules:
        if r.requires_bauni and not require_membership:
            continue
        if len(shawty_asset_ids) < (r.min_shawty_tokens or 0):
            continue
        if r.discount_type == "PERCENT":
            d = subtotal * (max(0.0, r.value) / 100.0)
        elif r.discount_type == "FIXED_ALGO":
            d = max(0.0, r.value)
        else:
            continue
        if d > discount:
            discount = d
            applied_rule_id = r.id

    discount = min(discount, subtotal)
    total = max(0.0, subtotal - discount)

    return {
        "success": True,
        "subtotal_algo": round(subtotal, 6),
        "discount_algo": round(discount, 6),
        "total_algo": round(total, 6),
        "items": normalized_items,
        "shawty_asset_ids_used": shawty_asset_ids,
        "applied_discount_rule_id": applied_rule_id,
    }


async def create_order(
    db: AsyncSession,
    *,
    fan_wallet: str,
    creator_wallet: str,
    quote: dict,
) -> Order:
    order = Order(
        fan_wallet=fan_wallet,
        creator_wallet=creator_wallet,
        status="PENDING_PAYMENT",
        subtotal_algo=quote["subtotal_algo"],
        discount_algo=quote["discount_algo"],
        total_algo=quote["total_algo"],
        shawty_asset_ids_used=json.dumps(quote.get("shawty_asset_ids_used") or []),
        created_at=datetime.utcnow(),
    )
    db.add(order)
    await db.flush()

    for i in quote["items"]:
        db.add(
            OrderItem(
                order_id=order.id,
                product_id=i["product_id"],
                quantity=i["quantity"],
                unit_price_algo=i["unit_price_algo"],
                discount_algo=0.0,
            )
        )

    return order


async def settle_order_payment(
    db: AsyncSession,
    *,
    order_id: int,
    fan_wallet: str,
    creator_wallet: str,
    amount_algo: float,
    tx_id: str,
) -> bool:
    """
    Mark an order as paid when a TipProxy payment with memo ORDER:<id> is detected.

    Idempotent:
      - If order is already PAID with this tx_id, returns False (no change).
      - If order is PAID with a different tx_id, logs and returns False.
    """
    res = await db.execute(
        select(Order).where(
            Order.id == order_id,
            Order.fan_wallet == fan_wallet,
            Order.creator_wallet == creator_wallet,
        )
    )
    order = res.scalar_one_or_none()
    if not order:
        return False

    # Already paid or cancelled
    if order.status != "PENDING_PAYMENT":
        return False

    # Basic amount check (allow slight overpay; exact or higher)
    if amount_algo + 1e-6 < order.total_algo:
        return False

    order.status = "PAID"
    order.tx_id = tx_id
    order.paid_at = datetime.utcnow()

    # Adjust inventory
    items_res = await db.execute(
        select(OrderItem).where(OrderItem.order_id == order.id)
    )
    items = items_res.scalars().all()
    if items:
        product_ids = [i.product_id for i in items]
        products_res = await db.execute(
            select(Product).where(Product.id.in_(product_ids))
        )
        products = {p.id: p for p in products_res.scalars().all()}
        for it in items:
            p = products.get(it.product_id)
            if p and p.stock_quantity is not None:
                if p.stock_quantity >= it.quantity:
                    p.stock_quantity -= it.quantity

    # Consume Shawty tokens used for discount by locking them
    try:
        asset_ids = json.loads(order.shawty_asset_ids_used or "[]")
    except Exception:
        asset_ids = []

    if asset_ids:
        from services import shawty_service

        for aid in asset_ids:
            desc = f"Discount for merch order {order.id}"
            await shawty_service.lock_for_discount(
                db=db,
                asset_id=int(aid),
                fan_wallet=fan_wallet,
                discount_description=desc,
            )

    return True


async def list_fan_orders(
    db: AsyncSession,
    *,
    fan_wallet: str,
    limit: int = 50,
    offset: int = 0,
) -> list[Order]:
    res = await db.execute(
        select(Order)
        .where(Order.fan_wallet == fan_wallet)
        .order_by(Order.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return res.scalars().all()

