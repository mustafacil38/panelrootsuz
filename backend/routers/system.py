from fastapi import APIRouter, Depends
from backend.routers.auth import get_current_user, User
from backend.utils.system_info import get_all_system_info
import psutil

router = APIRouter()

@router.get("/status")
async def read_system_status(current_user: User = Depends(get_current_user)):
    return get_all_system_info()
    
