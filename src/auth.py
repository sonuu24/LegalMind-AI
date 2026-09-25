"""
JWT Authentication for MCP Legal Assistant API.
Provides secure user authentication and authorization.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from src.config import get_settings

logger = logging.getLogger(__name__)

# ============================================================
# CONFIGURATION
# ============================================================

settings = get_settings()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

# JWT settings
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours
REFRESH_TOKEN_EXPIRE_DAYS = 7


# ============================================================
# MODELS
# ============================================================

class Token(BaseModel):
    """JWT token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    """Decoded token data."""
    user_id: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    firm_id: Optional[str] = None


class UserCreate(BaseModel):
    """User creation request."""
    email: str
    password: str
    full_name: str
    role: str = "attorney"
    firm_id: str


class UserLogin(BaseModel):
    """User login request."""
    email: str
    password: str


# ============================================================
# PASSWORD HASHING
# ============================================================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash password."""
    return pwd_context.hash(password)


# ============================================================
# JWT TOKEN OPERATIONS
# ============================================================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token.

    Args:
        data: Token payload data
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    })

    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=ALGORITHM
    )

    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """
    Create JWT refresh token.

    Args:
        data: Token payload data

    Returns:
        Encoded JWT refresh token
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    })

    encoded_jwt = jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=ALGORITHM
    )

    return encoded_jwt


def decode_token(token: str) -> Optional[TokenData]:
    """
    Decode and validate JWT token.

    Args:
        token: JWT token to decode

    Returns:
        TokenData if valid, None otherwise
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[ALGORITHM]
        )

        token_type = payload.get("type")
        if token_type not in ["access", "refresh"]:
            return None

        user_id = payload.get("sub")
        email = payload.get("email")
        role = payload.get("role")
        firm_id = payload.get("firm_id")

        if user_id is None:
            return None

        return TokenData(
            user_id=user_id,
            email=email,
            role=role,
            firm_id=firm_id
        )

    except JWTError as e:
        logger.error(f"Token decode error: {e}")
        return None


# ============================================================
# AUTHENTICATION DEPENDENCIES
# ============================================================

async def get_current_user(token: Optional[str] = Depends(oauth2_scheme)) -> Optional[TokenData]:
    """
    Get current authenticated user from token.

    Args:
        token: JWT token from Authorization header

    Returns:
        TokenData if valid, None otherwise
    """
    if not token:
        return None

    token_data = decode_token(token)
    return token_data


async def require_auth(token: Optional[str] = Depends(oauth2_scheme)) -> TokenData:
    """
    Require authentication - raise 401 if not authenticated.

    Args:
        token: JWT token from Authorization header

    Returns:
        TokenData if authenticated

    Raises:
        HTTPException: 401 if not authenticated
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_data = decode_token(token)
    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return token_data


async def require_role(required_role: str):
    """
    Dependency factory for role-based access control.

    Args:
        required_role: Required user role

    Returns:
        Dependency function
    """
    async def role_checker(token: TokenData = Depends(require_auth)) -> TokenData:
        if token.role != required_role and token.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {required_role} role",
            )
        return token

    return role_checker


# ============================================================
# AUTH ROUTES
# ============================================================

def register_auth_routes(app):
    """
    Register authentication routes with FastAPI app.

    Args:
        app: FastAPI application instance
    """
    from fastapi import APIRouter

    router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])

    # In-memory user store (replace with database in production)
    users_db = {}

    @router.post("/register", response_model=dict)
    async def register(user_data: UserCreate):
        """
        Register a new user.

        Returns:
            User registration confirmation
        """
        # Check if user exists
        if user_data.email in users_db:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        # Create user
        user_id = f"user_{len(users_db) + 1}"
        hashed_pw = get_password_hash(user_data.password)

        users_db[user_data.email] = {
            "user_id": user_id,
            "email": user_data.email,
            "full_name": user_data.full_name,
            "role": user_data.role,
            "firm_id": user_data.firm_id,
            "hashed_password": hashed_pw,
        }

        return {
            "success": True,
            "message": "User registered successfully",
            "user_id": user_id,
        }

    @router.post("/login", response_model=Token)
    async def login(form_data: OAuth2PasswordRequestForm = Depends()):
        """
        Login and get access token.

        Returns:
            JWT tokens
        """
        # Find user
        user = users_db.get(form_data.username)
        if not user or not verify_password(form_data.password, user["hashed_password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Create tokens
        access_token = create_access_token(
            data={
                "sub": user["user_id"],
                "email": user["email"],
                "role": user["role"],
                "firm_id": user["firm_id"],
            }
        )

        refresh_token = create_refresh_token(
            data={
                "sub": user["user_id"],
                "email": user["email"],
            }
        )

        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    @router.post("/refresh", response_model=Token)
    async def refresh_token(refresh_token: str):
        """
        Refresh access token.

        Returns:
            New JWT tokens
        """
        token_data = decode_token(refresh_token)
        if not token_data or token_data.user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        # Find user
        user = None
        for u in users_db.values():
            if u["user_id"] == token_data.user_id:
                user = u
                break

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
            )

        # Create new tokens
        new_access_token = create_access_token(
            data={
                "sub": user["user_id"],
                "email": user["email"],
                "role": user["role"],
                "firm_id": user["firm_id"],
            }
        )

        new_refresh_token = create_refresh_token(
            data={
                "sub": user["user_id"],
                "email": user["email"],
            }
        )

        return Token(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    @router.get("/me")
    async def get_current_user_info(current_user: TokenData = Depends(require_auth)):
        """
        Get current user information.

        Returns:
            Current user details
        """
        # Find user
        user = None
        for u in users_db.values():
            if u["user_id"] == current_user.user_id:
                user = u
                break

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        return {
            "user_id": user["user_id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "role": user["role"],
            "firm_id": user["firm_id"],
        }

    # Register router with app
    app.include_router(router)

    logger.info("Authentication routes registered")
