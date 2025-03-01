from conditional_method import conditional_method
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

# Environment setup
ENVIRONMENT_KEY = "ENVIRONMENT_KEY"
# Default to development for safety
os.environ.setdefault(ENVIRONMENT_KEY, "development")

# Constants for different environments
SECRET_KEYS = {
    "production": "prod_super_secret_key_never_share",
    "staging": "staging_secret_key",
    "development": "dev_secret_key_1234",
}

# JWT configuration
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Initialize security
security = HTTPBearer()

# Get the appropriate secret key based on environment
def get_secret_key():
    current_env = os.environ[ENVIRONMENT_KEY]
    return SECRET_KEYS.get(current_env, SECRET_KEYS["development"])

# Helper functions for environment checking that will be evaluated at runtime
def is_production(f):
    return os.environ[ENVIRONMENT_KEY] == "production"

def is_staging(f):
    return os.environ[ENVIRONMENT_KEY] == "staging"

def is_development(f):
    return os.environ[ENVIRONMENT_KEY] == "development"

class AuthService:
    """Service handling authentication logic with different implementations per environment"""
    
    @conditional_method(condition=is_production)
    def authenticate_user(self, authorization: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
        """Production authentication - strict JWT validation with role checking"""
        try:
            payload = jwt.decode(
                authorization.credentials, 
                get_secret_key(), 
                algorithms=[JWT_ALGORITHM]
            )
            
            print("IN PRODUCTION::authenticate_user")
            print("AUTHORIZATION: ", authorization)
            print("PAYLOAD: ", payload)
            
            # In production, we require specific claims
            if "sub" not in payload or "role" not in payload:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token claims"
                )
                
            # In production, only admins can access certain endpoints
            if payload.get("role") not in ["admin", "superuser"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions"
                )
                
            return payload
        except jwt.PyJWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
            
    @conditional_method(condition=is_development)
    def authenticate_user(self, authorization: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Dict[str, Any]:
        """Development authentication - very permissive, allows test accounts"""
        # In development, we accept any token structure or a special test token
        try:
            if authorization is None:
                # For convenience in development, allow no auth
                return {"sub": "test_user", "role": "developer"}
                
            print("IN DEVELOPMENT::authenticate_user")
            print("AUTHORIZATION: ", authorization)
            
            # Try to decode the token but allow failing
            try:
                payload = jwt.decode(
                    authorization.credentials,
                    get_secret_key(),
                    algorithms=[JWT_ALGORITHM],
                    options={"verify_signature": True, "verify_exp": False}  # Don't check expiration in dev
                )
                return payload
            except jwt.PyJWTError:
                # Even on error, in development we allow a test user
                return {"sub": "test_user", "role": "developer"}
        except Exception:
            # Catch any other exceptions and return default test user
            return {"sub": "test_user", "role": "developer"}
    
    @conditional_method(condition=is_staging)
    def authenticate_user(self, authorization: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
        """Staging authentication - JWT validation with relaxed role requirements"""
        try:
            payload = jwt.decode(
                authorization.credentials, 
                get_secret_key(), 
                algorithms=[JWT_ALGORITHM]
            )
            
            print("IN STAGING::authenticate_user")
            print("AUTHORIZATION: ", authorization)
            print("PAYLOAD: ", payload)
            
            # In staging, we check for subject but role can be any value
            if "sub" not in payload:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token claims"
                )
                
            return payload
        except jwt.PyJWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
    

# Helper to create tokens for testing
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, get_secret_key(), algorithm=JWT_ALGORITHM)

# Create a function that creates and configures a new FastAPI application
app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello World", "environment": os.environ[ENVIRONMENT_KEY]}

@app.get("/protected")
def protected_route(user_data: Dict[str, Any] = Depends(AuthService().authenticate_user)):
    return {
        "message": "This is a protected route",
        "environment": os.environ[ENVIRONMENT_KEY],
        "user": user_data.get("sub"),
        "role": user_data.get("role")
    }

# API endpoints for demonstration purposes
@app.get("/users/me")
def read_user_me(user_data: Dict[str, Any] = Depends(AuthService().authenticate_user)):
    return {
        "user_id": user_data.get("sub"),
        "role": user_data.get("role"),
        "environment": os.environ[ENVIRONMENT_KEY]
    }

@app.get("/admin")
def admin_only(user_data: Dict[str, Any] = Depends(AuthService().authenticate_user)):
    # In production and staging, the decorator already handles role checks
    # In development, we'll do an explicit check for demonstration
    if os.environ[ENVIRONMENT_KEY] == "development" and user_data.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required"
        )
    
    return {
        "message": "Admin dashboard",
        "environment": os.environ[ENVIRONMENT_KEY],
        "user": user_data.get("sub")
    }
