from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from .. import crud, models, schemas
from ..database import get_db
from ..services import per_server_scheduler

router = APIRouter(redirect_slashes=False)

@router.post("/", response_model=schemas.Server)
async def create_server(server: schemas.ServerCreate, db: AsyncSession = Depends(get_db)):
    """
    添加一台新服务器。
    """
    db_server = await crud.get_server_by_name(db, name=server.name)
    if db_server:
        raise HTTPException(status_code=400, detail="Server with this name already registered")
    
    new_server = await crud.create_server(db=db, server=server)
    
    # 启动新服务器的后台任务
    await per_server_scheduler.start_server_metrics_loop(new_server)
    if new_server.control_mode == "auto":
        await per_server_scheduler.start_server_control_loop(new_server)
        
    return new_server

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
    updated_server = await crud.update_server(db, server_id=server_id, server_update=server)
    if updated_server is None:
        raise HTTPException(status_code=404, detail="Server not found")

    # 根据 control_mode 的变化，启动或停止控制循环
    if server.control_mode is not None:
        if server.control_mode == "auto":
            await per_server_scheduler.start_server_control_loop(updated_server)
        else:
            await per_server_scheduler.stop_server_control_loop(updated_server.id)
            
    return updated_server

@router.delete("/{server_id}", response_model=schemas.Server)
async def delete_server(server_id: int, db: AsyncSession = Depends(get_db)):
    """
    删除一台服务器。
    """
    # 停止相关任务
    await per_server_scheduler.stop_server_control_loop(server_id)
    await per_server_scheduler.stop_server_metrics_loop(server_id)

    db_server = await crud.delete_server(db, server_id=server_id)
    if db_server is None:
        raise HTTPException(status_code=404, detail="Server not found")
    return db_server