from typing import Annotated

from fastapi import Header, HTTPException, status

from app.core.config import settings

API_KEY_HEADER_NAME = "X-API-Key"


def get_expected_api_key() -> str | None:
    return settings.API_KEY or None


def verify_api_key(
    api_key: Annotated[
        str | None,
        Header(
            alias=API_KEY_HEADER_NAME,
            description="Backend API key from the API_KEY environment variable.",
        ),
    ] = None,
) -> bool:
    expected_api_key = get_expected_api_key()

    if not expected_api_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API_KEY is not configured on the server",
        )

    if not api_key or api_key != expected_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )

    return True
