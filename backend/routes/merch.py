"""
Merch endpoints — creator product management + fan store/quote/order.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from domain.responses import success_response, paginated_response
from deps import require_creator, require_fan, require_bauni_membership
from utils.validators import validate_algorand_address

logger = logging.getLogger(__name__)
router = APIRouter(tags=["merch"])


class ProductCreateRequest(BaseModel):
    slug: str = Field(..., min_length=2, max_length=100)
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    image_ipfs_hash: str | None = None
    price_algo: float = Field(..., gt=0)
    stock_quantity: int | None = Field(default=None, ge=0)
    active: bool = True


class CartItem(BaseModel):
    product_id: int = Field(..., gt=0, alias="productId")
    quantity: int = Field(1, ge=1, le=20)


class QuoteRequest(BaseModel):
    fan_wallet: str = Field(..., alias="fanWallet", min_length=58, max_length=58)
    items: list[CartItem]
    shawty_asset_ids: list[int] = Field(default_factory=list, alias="shawtyAssetIds")
    require_membership: bool = Field(False, alias="requireMembership")


class OrderCreateRequest(BaseModel):
    fan_wallet: str = Field(..., alias="fanWallet", min_length=58, max_length=58)
    items: list[CartItem]
    shawty_asset_ids: list[int] = Field(default_factory=list, alias="shawtyAssetIds")
    require_membership: bool = Field(False, alias="requireMembership")


class ProductUpdateRequest(BaseModel):
    slug: str | None = Field(default=None, min_length=2, max_length=100)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    image_ipfs_hash: str | None = None
    price_algo: float | None = Field(default=None, gt=0)
    max_per_order: int | None = Field(default=None, ge=1)
    stock_quantity: int | None = Field(default=None, ge=0)
    active: bool | None = None


class DiscountRuleCreateRequest(BaseModel):
    product_id: int | None = Field(default=None, alias="productId")
    discount_type: str = Field("PERCENT", alias="discountType")
    value: float = Field(..., gt=0)
    min_shawty_tokens: int = Field(0, alias="minShawtyTokens", ge=0)
    requires_bauni: bool = Field(False, alias="requiresBauni")
    max_uses_per_wallet: int | None = Field(default=None, alias="maxUsesPerWallet", ge=1)


@router.post("/creator/{wallet}/products")
async def create_product(
    request: ProductCreateRequest,
    wallet: str = Depends(require_creator),
    db: AsyncSession = Depends(get_db),
):
    validate_algorand_address(wallet)
    from services import merch_service

    p = await merch_service.create_product(
        db,
        creator_wallet=wallet,
        slug=request.slug,
        name=request.name,
        description=request.description,
        image_ipfs_hash=request.image_ipfs_hash,
        price_algo=request.price_algo,
        stock_quantity=request.stock_quantity,
        active=request.active,
    )
    await db.commit()
    await db.refresh(p)
    return success_response(
        data={
            "id": p.id,
            "slug": p.slug,
            "name": p.name,
            "description": p.description,
            "image_ipfs_hash": p.image_ipfs_hash,
            "price_algo": p.price_algo,
            "stock_quantity": p.stock_quantity,
            "active": p.active,
        }
    )


@router.get("/creator/{wallet}/products")
async def list_creator_products(
    wallet: str = Depends(require_creator),
    db: AsyncSession = Depends(get_db),
):
    validate_algorand_address(wallet)
    from services import merch_service
    from domain.responses import success_response

    products = await merch_service.list_creator_products(db, creator_wallet=wallet)
    return success_response(
        data={
            "creator_wallet": wallet,
            "products": [
                {
                    "id": p.id,
                    "slug": p.slug,
                    "name": p.name,
                    "description": p.description,
                    "image_ipfs_hash": p.image_ipfs_hash,
                    "price_algo": p.price_algo,
                    "stock_quantity": p.stock_quantity,
                    "active": p.active,
                }
                for p in products
            ],
        },
        meta={"total": len(products)},
    )


@router.patch("/creator/{wallet}/products/{product_id}")
async def update_product(
    product_id: int,
    request: ProductUpdateRequest,
    wallet: str = Depends(require_creator),
    db: AsyncSession = Depends(get_db),
):
    validate_algorand_address(wallet)
    from services import merch_service
    from domain.responses import success_response

    product = await merch_service.update_product(
        db,
        product_id=product_id,
        creator_wallet=wallet,
        slug=request.slug,
        name=request.name,
        description=request.description,
        image_ipfs_hash=request.image_ipfs_hash,
        price_algo=request.price_algo,
        max_per_order=request.max_per_order,
        stock_quantity=request.stock_quantity,
        active=request.active,
    )
    await db.commit()
    await db.refresh(product)

    return success_response(
        data={
            "id": product.id,
            "slug": product.slug,
            "name": product.name,
            "description": product.description,
            "image_ipfs_hash": product.image_ipfs_hash,
            "price_algo": product.price_algo,
            "max_per_order": product.max_per_order,
            "stock_quantity": product.stock_quantity,
            "active": product.active,
        }
    )


@router.delete("/creator/{wallet}/products/{product_id}")
async def delete_product(
    product_id: int,
    wallet: str = Depends(require_creator),
    db: AsyncSession = Depends(get_db),
):
    validate_algorand_address(wallet)
    from services import merch_service
    from domain.responses import success_response

    product = await merch_service.soft_delete_product(
        db,
        product_id=product_id,
        creator_wallet=wallet,
    )
    await db.commit()

    return success_response(
        data={
            "id": product.id,
            "slug": product.slug,
            "message": f"Product '{product.slug}' soft-deleted (active=False)",
        }
    )


@router.post("/creator/{wallet}/discounts")
async def create_discount_rule(
    request: DiscountRuleCreateRequest,
    wallet: str = Depends(require_creator),
    db: AsyncSession = Depends(get_db),
):
    validate_algorand_address(wallet)
    from services import merch_service

    rule = await merch_service.create_discount_rule(
        db,
        creator_wallet=wallet,
        product_id=request.product_id,
        discount_type=request.discount_type,
        value=request.value,
        min_shawty_tokens=request.min_shawty_tokens,
        requires_bauni=request.requires_bauni,
        max_uses_per_wallet=request.max_uses_per_wallet,
    )
    await db.commit()
    await db.refresh(rule)
    return success_response(
        data={
            "id": rule.id,
            "product_id": rule.product_id,
            "discount_type": rule.discount_type,
            "value": rule.value,
            "min_shawty_tokens": rule.min_shawty_tokens,
            "requires_bauni": rule.requires_bauni,
            "max_uses_per_wallet": rule.max_uses_per_wallet,
            "active": rule.active,
        }
    )


@router.get("/creator/{wallet}/discounts")
async def list_discount_rules(
    wallet: str = Depends(require_creator),
    db: AsyncSession = Depends(get_db),
):
    validate_algorand_address(wallet)
    from services import merch_service

    rules = await merch_service.list_discount_rules(db, creator_wallet=wallet)
    return success_response(
        data={
            "creator_wallet": wallet,
            "discount_rules": [
                {
                    "id": r.id,
                    "product_id": r.product_id,
                    "discount_type": r.discount_type,
                    "value": r.value,
                    "min_shawty_tokens": r.min_shawty_tokens,
                    "requires_bauni": r.requires_bauni,
                    "max_uses_per_wallet": r.max_uses_per_wallet,
                    "active": r.active,
                }
                for r in rules
            ],
        },
        meta={"total": len(rules)},
    )


@router.get("/creator/{wallet}/store")
async def list_store(
    wallet: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0, le=10_000),
    db: AsyncSession = Depends(get_db),
):
    validate_algorand_address(wallet)
    from services import merch_service

    products = await merch_service.list_store_products(db, creator_wallet=wallet, limit=limit, offset=offset)
    # Note: For accurate pagination, we'd need a count query, but for now use len(products)
    # In production, add a count query for accurate total/hasMore
    product_list = [
        {
            "id": p.id,
            "slug": p.slug,
            "name": p.name,
            "description": p.description,
            "image_ipfs_hash": p.image_ipfs_hash,
            "price_algo": p.price_algo,
            "stock_quantity": p.stock_quantity,
        }
        for p in products
    ]
    return paginated_response(
        items=product_list,
        limit=limit,
        offset=offset,
        total=len(products),  # Approximate; should query count separately for accuracy
    )


@router.post("/creator/{wallet}/store/quote")
async def quote_order(
    wallet: str,
    request: QuoteRequest,
    db: AsyncSession = Depends(get_db),
    auth_wallet: str = Depends(require_fan),
):
    validate_algorand_address(wallet)
    validate_algorand_address(request.fan_wallet)
    if auth_wallet != request.fan_wallet:
        raise HTTPException(status_code=403, detail="Authenticated wallet does not match fanWallet.")

    from services import merch_service

    quote = await merch_service.build_quote(
        db,
        fan_wallet=request.fan_wallet,
        creator_wallet=wallet,
        items=[{"product_id": i.product_id, "quantity": i.quantity} for i in request.items],
        shawty_asset_ids=request.shawty_asset_ids,
        require_membership=request.require_membership,
    )
    if not quote.get("success"):
        raise HTTPException(status_code=400, detail=quote.get("error", "Quote failed"))
    return quote


@router.post("/creator/{wallet}/store/order")
async def create_order(
    wallet: str,
    request: OrderCreateRequest,
    db: AsyncSession = Depends(get_db),
    auth_wallet: str = Depends(require_fan),
):
    validate_algorand_address(wallet)
    validate_algorand_address(request.fan_wallet)
    if auth_wallet != request.fan_wallet:
        raise HTTPException(status_code=403, detail="Authenticated wallet does not match fanWallet.")

    from services import merch_service

    quote = await merch_service.build_quote(
        db,
        fan_wallet=request.fan_wallet,
        creator_wallet=wallet,
        items=[{"product_id": i.product_id, "quantity": i.quantity} for i in request.items],
        shawty_asset_ids=request.shawty_asset_ids,
        require_membership=request.require_membership,
    )
    if not quote.get("success"):
        raise HTTPException(status_code=400, detail=quote.get("error", "Quote failed"))

    order = await merch_service.create_order(db, fan_wallet=request.fan_wallet, creator_wallet=wallet, quote=quote)
    await db.commit()
    await db.refresh(order)

    return success_response(
        data={
            "order": {
                "id": order.id,
                "status": order.status,
                "subtotal_algo": order.subtotal_algo,
                "discount_algo": order.discount_algo,
                "total_algo": order.total_algo,
            },
            "payment": {
                "memo": f"ORDER:{order.id}",
                "amount_algo": order.total_algo,
                "instructions": "Pay the creator via TipProxy with this memo; the listener will mark the order as paid.",
            },
        }
    )


@router.get("/fan/{wallet}/orders")
async def list_fan_orders(
    wallet: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0, le=10_000),
    db: AsyncSession = Depends(get_db),
    auth_wallet: str = Depends(require_fan),
):
    validate_algorand_address(wallet)
    if auth_wallet != wallet:
        raise HTTPException(status_code=403, detail="Authenticated wallet does not match path wallet.")

    from services import merch_service

    orders = await merch_service.list_fan_orders(db, fan_wallet=wallet, limit=limit, offset=offset)
    order_list = [
        {
            "id": o.id,
            "creator_wallet": o.creator_wallet,
            "status": o.status,
            "subtotal_algo": o.subtotal_algo,
            "discount_algo": o.discount_algo,
            "total_algo": o.total_algo,
            "tx_id": o.tx_id,
            "created_at": o.created_at.isoformat() if o.created_at else None,
            "paid_at": o.paid_at.isoformat() if o.paid_at else None,
        }
        for o in orders
    ]
    return paginated_response(
        items=order_list,
        limit=limit,
        offset=offset,
        total=len(orders),  # Approximate; should query count separately for accuracy
    )


@router.get("/creator/{wallet}/store/members-only")
async def list_store_members_only(
    wallet: str,
    fan_wallet: str = Query(..., alias="fanWallet", min_length=58, max_length=58),
    db: AsyncSession = Depends(get_db),
    auth_wallet: str = Depends(require_fan),
):
    """
    Members-only merch catalog — requires active Bauni membership.
    """
    from services import merch_service

    validate_algorand_address(wallet)
    validate_algorand_address(fan_wallet)

    if auth_wallet != fan_wallet:
        raise HTTPException(status_code=403, detail="Authenticated wallet does not match fanWallet.")

    # Enforce Bauni membership
    await require_bauni_membership(fan_wallet=fan_wallet, creator_wallet=wallet, db=db)

    products = await merch_service.list_store_products(db, creator_wallet=wallet, limit=50, offset=0)
    product_list = [
        {
            "id": p.id,
            "slug": p.slug,
            "name": p.name,
            "description": p.description,
            "image_ipfs_hash": p.image_ipfs_hash,
            "price_algo": p.price_algo,
            "stock_quantity": p.stock_quantity,
        }
        for p in products
    ]
    return success_response(
        data={
            "creator_wallet": wallet,
            "fan_wallet": fan_wallet,
            "products": product_list,
        },
        meta={"total": len(products)},
    )

