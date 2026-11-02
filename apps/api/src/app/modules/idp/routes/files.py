"""EP-DC-14b `GET /files/{storage_key}` — serve the original capture file (R-DEC-80).

The presigned URL minted by EP-DC-14 (`core.storage.presign_get`) points here (through the BFF
proxy). This route is the serving side of "Xem tài liệu gốc": it re-checks `idp:read` + the
caller's document scope + tenant **and** the HMAC signature/expiry before streaming the stored
object. Neither the signature alone nor the session alone is sufficient (defense in depth).

The response streams the file inline with its real `Content-Type` so the browser renders a PDF
or image in an <iframe>/<img>; `X-Content-Type-Options: nosniff` + `Cache-Control: private,
no-store` keep it from being sniffed or cached. The internal storage path is never exposed.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.core.deps import DbSession, Principal, require_permission
from app.core.storage import get_object_store, iter_file_chunks
from app.modules.idp.services.inbox_service import InboxService

# Plain APIRouter (no envelope): a file stream is not wrapped in `{data, meta}`. Top-level path
# (no `/idp` prefix) — mounted under `/api/v1` by the app factory → `/api/v1/files/{key}`.
router = APIRouter(tags=["idp"])

IdpReader = Annotated[Principal, Depends(require_permission("idp", "read"))]

# Keep the inline-viewable set narrow (04 §15 whitelist); everything else downloads as an
# attachment so an unexpected type is never rendered as active content in the browser.
_INLINE_MIME = frozenset({"application/pdf", "image/png", "image/jpeg", "image/webp", "image/gif"})


@router.get(
    "/files/{storage_key:path}",
    summary="EP-DC-14b Serve a signed source file (idp:read + scope + tenant)",
    responses={200: {"content": {"application/octet-stream": {}}}},
)
async def serve_file(
    storage_key: str,
    user: IdpReader,
    db: DbSession,
    expires: Annotated[int, Query(ge=0)],
    signature: Annotated[str, Query(min_length=1, max_length=128)],
) -> StreamingResponse:
    doc, mime = await InboxService(db).serve_file(user, storage_key, expires, signature)
    await db.commit()  # `idp.source_view` audit (sensitivity ≥ 3)
    path = get_object_store().open(doc.storage_key or storage_key)
    disposition = "inline" if mime in _INLINE_MIME else "attachment"
    # original_filename may be null / may contain unsafe chars → use a stable, safe fallback.
    safe_name = f'{disposition}; filename="source-{doc.id}"'
    return StreamingResponse(
        iter_file_chunks(path),
        media_type=mime,
        headers={
            "Content-Disposition": safe_name,
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
            # `default-src 'none'` blocks the framed file from running scripts or loading ANY
            # sub-resource, and `frame-ancestors 'self'` stops it being embedded by a foreign origin
            # — so a hostile upload cannot execute even though the SourceDrawer iframe is NOT
            # sandboxed. We deliberately dropped the CSP `sandbox` directive: Chromium's built-in
            # PDF viewer refuses to render in any sandboxed context, which left PDFs blank in drawer
            # (images were unaffected). This header + `nosniff` is what enforces isolation now.
            "Content-Security-Policy": "default-src 'none'; frame-ancestors 'self'",
        },
    )
