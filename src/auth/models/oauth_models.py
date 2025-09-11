from sqlmodel import SQLModel  # type: ignore

try:
    from database.models.oauth import (  # type: ignore
        OAuthUsers as OAuthUser,
        OAuthJWKs as OAuthJWK,
        OAuthAppClients as OAuthApplication,
    )
    __all__ = ["OAuthUser", "OAuthJWK", "OAuthApplication"]
except Exception:  # pragma: no cover
    __all__: list[str] = []
