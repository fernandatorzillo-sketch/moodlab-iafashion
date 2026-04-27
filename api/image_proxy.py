import re
from urllib.parse import unquote

import httpx
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

router = APIRouter(prefix="/api/v1", tags=["image-proxy"])

_ALLOWED_HOSTS = re.compile(
    r"^https?://(aguadecoco|lojaaguadecoco)\.(vteximg|vtexassets|vtexcommercestable)\.com(\.br)?(/|$)",
    re.IGNORECASE,
)

_MAX_SIZE = 2 * 1024 * 1024  # 2 MB — imagens de produto nunca passam disso


@router.get("/image-proxy")
async def image_proxy(url: str = Query(..., description="URL da imagem VTEX")):
    decoded = unquote(url)

    if not _ALLOWED_HOSTS.match(decoded):
        raise HTTPException(status_code=400, detail="URL não permitida.")

    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            resp = await client.get(
                decoded,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; MoodLabCloset/1.0)",
                    "Referer": "https://aguadecoco.com.br/",
                },
            )
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail=f"Erro ao buscar imagem: {exc}")

    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail="Imagem não encontrada na VTEX.")

    content = resp.content
    if len(content) > _MAX_SIZE:
        raise HTTPException(status_code=413, detail="Imagem muito grande.")

    content_type = resp.headers.get("content-type", "image/jpeg")

    return Response(
        content=content,
        media_type=content_type,
        headers={
            "Cache-Control": "public, max-age=86400",  # cache 24h no browser
            "Access-Control-Allow-Origin": "*",
        },
    )
