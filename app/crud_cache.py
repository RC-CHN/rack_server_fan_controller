from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc
import datetime
from . import models

async def get_latest_temperature(db: AsyncSession, server_id: int, max_age_seconds: int = 30) -> float | None:
    """
    获取服务器最新的温度数据（带缓存机制）
    
    Args:
        db: 数据库会话
        server_id: 服务器ID
        max_age_seconds: 缓存最大有效期（秒）
    
    Returns:
        最新的温度值，如果缓存过期或不存在则返回None
    """
    cutoff_time = datetime.datetime.utcnow() - datetime.timedelta(seconds=max_age_seconds)
    
    result = await db.execute(
        select(models.TemperatureHistory)
        .filter(
            models.TemperatureHistory.server_id == server_id,
            models.TemperatureHistory.timestamp >= cutoff_time
        )
        .order_by(desc(models.TemperatureHistory.timestamp))
        .limit(1)
    )
    
    latest_record = result.scalars().first()
    return latest_record.temperature if latest_record else None


async def get_latest_fan_speed(db: AsyncSession, server_id: int, max_age_seconds: int = 60) -> int | None:
    """
    获取服务器最新的风扇速度数据（带缓存机制）
    
    Args:
        db: 数据库会话
        server_id: 服务器ID
        max_age_seconds: 缓存最大有效期（秒）
    
    Returns:
        最新的风扇速度值，如果缓存过期或不存在则返回None
    """
    cutoff_time = datetime.datetime.utcnow() - datetime.timedelta(seconds=max_age_seconds)
    
    result = await db.execute(
        select(models.FanSpeedHistory)
        .filter(
            models.FanSpeedHistory.server_id == server_id,
            models.FanSpeedHistory.timestamp >= cutoff_time
        )
        .order_by(desc(models.FanSpeedHistory.timestamp))
        .limit(1)
    )
    
    latest_record = result.scalars().first()
    return latest_record.average_speed_rpm if latest_record else None