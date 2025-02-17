import os
from modules.logger_tool import initialise_logger
logger = initialise_logger(__name__, os.getenv("LOG_LEVEL"), os.getenv("LOG_PATH"), 'default', True)

from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt.exceptions import InvalidTokenError
import os

class SupabaseBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)

    async def __call__(self, credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
        if not credentials:
            raise HTTPException(status_code=403, detail="Invalid authorization code.")

        try:
            token = credentials.credentials
            payload = verify_supabase_token(token)
            return payload
        except Exception as e:
            logger.error(f"Token verification failed: {str(e)}")
            raise HTTPException(status_code=403, detail="Invalid token or expired token.")

def verify_supabase_token(token: str) -> dict:
    """Verify a Supabase JWT token and return its payload."""
    try:
        jwt_secret = os.getenv("JWT_SECRET")
        if not jwt_secret:
            raise ValueError("JWT_SECRET not configured")

        # Decode the token with proper audience check
        payload = jwt.decode(
            token,
            jwt_secret,
            algorithms=["HS256"],
            audience="authenticated"
        )
        
        logger.debug(f"Token payload: {payload}")
        
        return payload
    except jwt.ExpiredSignatureError:
        logger.error("Token has expired")
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError as e:
        logger.error(f"Invalid token: {str(e)}")
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception as e:
        logger.error(f"Token verification failed: {str(e)}")
        raise HTTPException(status_code=401, detail="Token verification failed")

def decodeSupabaseJWT(token: str) -> dict:
    try:
        jwt_secret = os.getenv('SUPABASE_JWT_SECRET')
        payload = jwt.decode(token, jwt_secret, algorithms=["HS256"], audience="authenticated")
        return payload
    except Exception:
        return None

# Initialize the security instance
security = HTTPBearer()

async def verify_supabase_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        # Verify token using your Supabase JWT secret
        decoded_token = jwt.decode(
            token,
            os.getenv('SUPABASE_JWT_SECRET'),
            algorithms=["HS256"],
            audience="authenticated"
        )
        return decoded_token
    except InvalidTokenError as e:
        raise HTTPException(
            status_code=401,
            detail=f"Invalid authentication token: {str(e)}"
        )