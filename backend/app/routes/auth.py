from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.supabase import get_supabase

router = APIRouter(prefix="/auth")


class AuthRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    user_id: str
    email: str


class SignupResponse(BaseModel):
    message: str
    access_token: str | None = None
    user_id: str | None = None
    email: str | None = None


@router.post("/login", response_model=LoginResponse)
async def login(req: AuthRequest) -> LoginResponse:
    try:
        client = get_supabase()
        res = client.auth.sign_in_with_password({"email": req.email, "password": req.password})
        if not res.session:
            raise HTTPException(status_code=400, detail="Invalid credentials")
        return LoginResponse(
            access_token=res.session.access_token,
            user_id=str(res.user.id),
            email=res.user.email or req.email,
        )
    except HTTPException:
        raise
    except Exception as exc:
        msg = str(exc)
        if "Invalid login credentials" in msg or "invalid_credentials" in msg:
            raise HTTPException(status_code=400, detail="Invalid email or password")
        raise HTTPException(status_code=500, detail=f"Login failed: {msg}")


@router.post("/signup", response_model=SignupResponse)
async def signup(req: AuthRequest) -> SignupResponse:
    try:
        client = get_supabase()
        res = client.auth.sign_up({"email": req.email, "password": req.password})
        if res.session:
            return SignupResponse(
                message="Account created successfully",
                access_token=res.session.access_token,
                user_id=str(res.user.id),
                email=res.user.email or req.email,
            )
        # Email confirmation required
        return SignupResponse(
            message="Account created — check your email to confirm your account",
        )
    except HTTPException:
        raise
    except Exception as exc:
        msg = str(exc)
        if "already registered" in msg.lower() or "already been registered" in msg.lower():
            raise HTTPException(status_code=409, detail="This email is already registered")
        raise HTTPException(status_code=500, detail=f"Signup failed: {msg}")
