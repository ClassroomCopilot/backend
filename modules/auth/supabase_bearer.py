import os
from modules.logger_tool import initialise_logger
logger = initialise_logger(__name__, os.getenv("LOG_LEVEL"), os.getenv("BACKEND_LOG_PATH"), 'default', True)

from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from jwt.exceptions import InvalidTokenError
import os

class SupabaseBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super(SupabaseBearer, self).__init__(auto_error=auto_error)
        self.jwt_secret = os.getenv('SUPABASE_JWT_SECRET')

    async def __call__(self, request: Request) -> str:
        credentials: HTTPAuthorizationCredentials = await super(SupabaseBearer, self).__call__(request)
        if not credentials:
            raise HTTPException(status_code=403, detail="Invalid authorization code.")
        
        if not credentials.scheme == "Bearer":
            raise HTTPException(status_code=403, detail="Invalid authentication scheme.")

        try:
            payload = jwt.decode(
                credentials.credentials,
                self.jwt_secret,
                algorithms=["HS256"],
                audience="authenticated"
            )
            return payload
        except InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token or expired token.")

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