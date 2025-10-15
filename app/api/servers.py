from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from .. import crud, models, schemas
from ..database import get_db

router = APIRouter(redirect_slashes=False)

@router.post("/", response_model=schemas.Server)
async def create_server(server: schemas.ServerCreate, db: AsyncSession = Depends(get_db)):
    """
    添加一台新服务器。
    """
    db_server = await crud.get_server_by_name(db, name=server.name)
    if db_server:
        raise HTTPException(status_code=400, detail="Server with this name already registered")
    return await crud.create_server(db=db, server=server)

@router.get("/", response_model=List[schemas.Server])
async def read_servers(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    """
    获取服务器列表。
    """
    servers = await crud.get_servers(db, skip=skip, limit=limit)
    return servers

@router.get("/{server_id}", response_model=schemas.Server)
async def read_server(server_id: int, db: AsyncSession = Depends(get_db)):
    """
    获取指定服务器的详细信息。
    """
    db_server = await crud.get_server(db, server_id=server_id)
    if db_server is None:
        raise HTTPException(status_code=404, detail="Server not found")
    return db_server

@router.put("/{server_id}", response_model=schemas.Server)
async def update_server(server_id: int, server: schemas.ServerUpdate, db: AsyncSession = Depends(get_db)):
    """
    更新服务器信息。
    """
    db_server = await crud.update_server(db, server_id=server_id, server_update=server)
    if db_server is None:
        raise HTTPException(status_code=404, detail="Server not found")
    return db_server

@router.delete("/{server_id}", response_model=schemas.Server)
async def delete_server(server_id: int, db: AsyncSession = Depends(get_db)):
    """
    删除一台服务器。
    """
    db_server = await crud.delete_server(db, server_id=server_id)
    if db_server is None:
        raise HTTPException(status_code=404, detail="Server not found")
    return db_server