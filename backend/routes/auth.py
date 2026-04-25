from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from bson import ObjectId
from datetime import datetime

from database import get_db
from models.schemas import UserRegister, UserLogin, TokenResponse
from utils.auth_utils import hash_password, verify_password, create_token, decode_token

router = APIRouter(prefix="/api/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    if not credentials:
        return None
    user_id = decode_token(credentials.credentials)
    if not user_id:
        return None
    db = get_db()
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    return user


@router.post("/register", response_model=TokenResponse)
async def register(data: UserRegister):
    db = get_db()
    if await db.users.find_one({"$or": [{"email": data.email}, {"username": data.username}]}):
        raise HTTPException(400, "Username or email already exists")

    user_doc = {
        "username": data.username,
        "email": data.email,
        "password": hash_password(data.password),
        "display_name": data.display_name or data.username,
        "created_at": datetime.utcnow(),
    }
    result = await db.users.insert_one(user_doc)
    user_id = str(result.inserted_id)
    token = create_token(user_id)
    return {
        "token": token,
        "user": {
            "id": user_id,
            "username": data.username,
            "email": data.email,
            "display_name": data.display_name or data.username,
        },
    }


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin):
    db = get_db()
    user = await db.users.find_one({"email": data.email})
    if not user or not verify_password(data.password, user["password"]):
        raise HTTPException(401, "Invalid credentials")

    user_id = str(user["_id"])
    token = create_token(user_id)
    return {
        "token": token,
        "user": {
            "id": user_id,
            "username": user["username"],
            "email": user["email"],
            "display_name": user.get("display_name", user["username"]),
        },
    }


@router.get("/me")
async def me(current_user=Depends(get_current_user)):
    if not current_user:
        raise HTTPException(401, "Not authenticated")
    return {
        "id": str(current_user["_id"]),
        "username": current_user["username"],
        "email": current_user["email"],
        "display_name": current_user.get("display_name"),
    }
