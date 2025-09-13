from sqlmodel import SQLModel  # type: ignore

try:
    from database.models.oauth import OAuthAppClients as OAuthApplication
    from database.models.oauth import OAuthJWKs as OAuthJWK
    from database.models.oauth import OAuthUsers as OAuthUser  # type: ignore

    __all__ = ["OAuthUser", "OAuthJWK", "OAuthApplication"]
except Exception:  # pragma: no cover
    __all__: list[str] = []
