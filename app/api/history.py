from typing import List
import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from .. import crud, schemas
from ..database import get_db

router = APIRouter(redirect_slashes=False)

@router.get("/{server_id}/temperature", response_model=List[schemas.TemperatureHistory])
async def read_temperature_history(
    server_id: int,
    start_date: datetime.datetime = Query(..., description="查询起始时间 (ISO 8601 格式)"),
    end_date: datetime.datetime = Query(..., description="查询结束时间 (ISO 8601 格式)"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取指定服务器在时间范围内的温度历史记录。
    """
    history = await crud.get_temperature_history(db, server_id=server_id, start_date=start_date, end_date=end_date)
    return history

@router.get("/{server_id}/fan-speed", response_model=List[schemas.FanSpeedHistory])
async def read_fan_speed_history(
    server_id: int,
    start_date: datetime.datetime = Query(..., description="查询起始时间 (ISO 8601 格式)"),
    end_date: datetime.datetime = Query(..., description="查询结束时间 (ISO 8601 格式)"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取指定服务器在时间范围内的风扇转速历史记录。
    """
    history = await crud.get_fan_speed_history(db, server_id=server_id, start_date=start_date, end_date=end_date)
    return history

@router.get("/{server_id}/temperature/recent", response_model=List[schemas.TemperatureHistory])
async def read_recent_temperature_history(
    server_id: int,
    limit: int = Query(540, description="获取最近多少条温度记录，默认540条（约3小时，每30秒一条）"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取指定服务器最近的温度历史记录，用于实时曲线显示。
    默认获取最近540条记录（约3小时，按每30秒一条计算）。
    """
    history = await crud.get_recent_temperature_history(db, server_id=server_id, limit=limit)
    return history

@router.get("/{server_id}/fan-speed/recent", response_model=List[schemas.FanSpeedHistory])
async def read_recent_fan_speed_history(
    server_id: int,
    limit: int = Query(540, description="获取最近多少条风扇转速记录，默认540条（约3小时，每30秒一条）"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取指定服务器最近的风扇转速历史记录，用于实时曲线显示。
    默认获取最近540条记录（约3小时，按每30秒一条计算）。
    """
    history = await crud.get_recent_fan_speed_history(db, server_id=server_id, limit=limit)
    return history