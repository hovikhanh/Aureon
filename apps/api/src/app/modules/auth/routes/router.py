"""HTTP routes for `auth` (10 §4.1): EP-02 login, EP-03 me (GET), EP-06 refresh, EP-07 logout.

EP-02 and EP-06 are the only public auth endpoints (10 §2.2). EP-03 / EP-07 need just a valid
token (`authenticated`). PATCH EP-03, EP-04/05 (demo) and EP-08 come with later tasks.
"""

from typing import Annotated

from fastapi import Depends, Request, Response, status

from app.core.deps import CurrentUser, DbSession
from app.core.routing import EnvelopeRouter
from app.modules.auth.routes.users import router as users_router
from app.modules.auth.schemas import LoginIn, RefreshIn, TokenOut, UserOut
from app.modules.auth.services.auth_service import AuthService, ClientInfo

router = EnvelopeRouter(prefix="/auth", tags=["auth"])


def get_auth_service(db: DbSession) -> AuthService:
    return AuthService(db)


Service = Annotated[AuthService, Depends(get_auth_service)]


def _client(request: Request) -> ClientInfo:
    return ClientInfo(
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )


@router.post("/login", response_model=TokenOut, summary="EP-02 Login")
async def login(body: LoginIn, request: Request, svc: Service) -> TokenOut:
    return await svc.login(body.email, body.password, _client(request))


@router.post("/refresh", response_model=TokenOut, summary="EP-06 Refresh")
async def refresh(body: RefreshIn, request: Request, svc: Service) -> TokenOut:
    return await svc.refresh(body.refresh_token, _client(request))


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="EP-07 Logout",
)
async def logout(body: RefreshIn, user: CurrentUser, svc: Service) -> Response:
    await svc.logout(body.refresh_token, user.user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserOut, summary="EP-03 Current session")
async def me(user: CurrentUser, svc: Service) -> UserOut:
    return await svc.me(user.user_id)


# M1.2 T-614: identity administration lives in `auth`, mounted under `/platform` (07 §1.1).
module_router = EnvelopeRouter(tags=["auth"])
module_router.include_router(router)
module_router.include_router(users_router)
