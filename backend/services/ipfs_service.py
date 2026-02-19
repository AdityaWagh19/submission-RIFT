"""
IPFS Service — uploads images and ARC-3 metadata to Pinata.

Pinata is a hosted IPFS pinning service. Free tier supports:
  - 500 uploads/month
  - 1 GB storage
  - Public gateway access

All sticker images and NFT metadata are pinned to IPFS for permanent,
platform-independent storage.
"""
import json
import logging
from typing import Optional

import httpx

from config import settings

logger = logging.getLogger(__name__)

PINATA_BASE = "https://api.pinata.cloud"


def _get_headers() -> dict:
    """Build Pinata authentication headers."""
    if not settings.pinata_api_key or not settings.pinata_secret:
        raise ValueError(
            "Pinata API key and secret must be set in .env "
            "(PINATA_API_KEY, PINATA_SECRET)"
        )
    return {
        "pinata_api_key": settings.pinata_api_key,
        "pinata_secret_api_key": settings.pinata_secret,
    }


async def test_authentication() -> bool:
    """Verify Pinata API credentials are valid."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{PINATA_BASE}/data/testAuthentication",
                headers=_get_headers(),
            )
            return response.status_code == 200
    except Exception as e:
        logger.error(f"Pinata auth test failed: {e}")
        return False


async def upload_image(
    file_bytes: bytes,
    filename: str,
    mimetype: str = "image/jpeg",
    metadata_name: Optional[str] = None,
) -> dict:
    """
    Upload an image file to Pinata IPFS.

    Args:
        file_bytes: Raw image bytes
        filename: Original filename (e.g., 'sticker.jpg')
        mimetype: MIME type (default: 'image/jpeg')
        metadata_name: Optional Pinata pin name for dashboard

    Returns:
        dict: {cid, url, size}
    """
    headers = _get_headers()

    # Pinata metadata for their dashboard
    pinata_options = json.dumps({"cidVersion": 1})
    pinata_metadata = json.dumps({
        "name": metadata_name or filename,
    })

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{PINATA_BASE}/pinning/pinFileToIPFS",
            headers=headers,
            files={"file": (filename, file_bytes, mimetype)},
            data={
                "pinataOptions": pinata_options,
                "pinataMetadata": pinata_metadata,
            },
        )
        response.raise_for_status()
        result = response.json()

    cid = result["IpfsHash"]
    size = result.get("PinSize", 0)
    url = f"{settings.pinata_gateway}/{cid}"

    logger.info(f"Image pinned to IPFS: {cid} ({size} bytes)")

    return {
        "cid": cid,
        "url": url,
        "size": size,
    }


async def upload_metadata(
    name: str,
    description: str,
    image_url: str,
    creator_wallet: str,
    category: str,
    sticker_type: str,
    extra_properties: Optional[dict] = None,
) -> dict:
    """
    Upload ARC-3 compliant metadata JSON to Pinata IPFS.

    ARC-3 is the Algorand standard for NFT metadata. The JSON includes
    the image URL (already on IPFS), descriptive fields, and custom
    properties for the sticker platform.

    Args:
        name: NFT display name
        description: NFT description
        image_url: IPFS URL of the sticker image (already uploaded)
        creator_wallet: Creator's Algorand address
        category: Sticker category ('tip', 'membership_bronze', etc.)
        sticker_type: 'soulbound' or 'golden'
        extra_properties: Additional key-value pairs for metadata

    Returns:
        dict: {cid, url}
    """
    headers = _get_headers()
    headers["Content-Type"] = "application/json"

    # ARC-3 metadata schema
    metadata = {
        "name": name,
        "description": description,
        "image": image_url,
        "image_mimetype": _guess_mimetype(image_url),
        "properties": {
            "creator": creator_wallet,
            "category": category,
            "type": sticker_type,
            "platform": "Creator Sticker Platform",
            **(extra_properties or {}),
        },
    }

    payload = {
        "pinataContent": metadata,
        "pinataMetadata": {
            "name": f"metadata_{name}",
        },
        "pinataOptions": {
            "cidVersion": 1,
        },
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{PINATA_BASE}/pinning/pinJSONToIPFS",
            headers=headers,
            content=json.dumps(payload),
        )
        response.raise_for_status()
        result = response.json()

    cid = result["IpfsHash"]
    url = f"{settings.pinata_gateway}/{cid}"

    logger.info(f"Metadata pinned to IPFS: {cid}")

    return {
        "cid": cid,
        "url": url,
    }


async def unpin(cid: str) -> bool:
    """
    Unpin a file from Pinata (remove from IPFS).

    Args:
        cid: IPFS content identifier to unpin

    Returns:
        True if successful, False otherwise
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.delete(
                f"{PINATA_BASE}/pinning/unpin/{cid}",
                headers=_get_headers(),
            )
            return response.status_code == 200
    except Exception as e:
        logger.warning(f"Failed to unpin {cid}: {e}")
        return False


def _guess_mimetype(url: str) -> str:
    """Guess MIME type from URL extension."""
    url_lower = url.lower()
    if url_lower.endswith(".png"):
        return "image/png"
    elif url_lower.endswith(".gif"):
        return "image/gif"
    elif url_lower.endswith(".webp"):
        return "image/webp"
    elif url_lower.endswith(".svg"):
        return "image/svg+xml"
    return "image/jpeg"
