from fastapi import APIRouter, HTTPException, status
from app.utils.auth import (
    LoginRequest,
    TokenResponse,
    authenticate_user,
    create_token,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest):
    """
    Demo login — checks username/password against .env values.
    Returns a JWT token valid for 24 hours.
    """
    if not authenticate_user(payload.username, payload.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    token = create_token(payload.username)
    return TokenResponse(access_token=token)