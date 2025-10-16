from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func, delete
import datetime
from . import models, schemas

# ====================
# Server CRUD
# ====================

async def get_server(db: AsyncSession, server_id: int):
    """根据 ID 获取单个服务器"""
    result = await db.execute(
        select(models.Server)
        .filter(models.Server.id == server_id)
        .options(selectinload(models.Server.fan_curves))
    )
    return result.scalars().first()

async def get_server_by_name(db: AsyncSession, name: str):
    """根据名称获取单个服务器"""
    result = await db.execute(select(models.Server).filter(models.Server.name == name))
    return result.scalars().first()

async def get_servers(db: AsyncSession, skip: int = 0, limit: int = 100):
    """获取服务器列表"""
    result = await db.execute(
        select(models.Server)
        .offset(skip)
        .limit(limit)
        .options(selectinload(models.Server.fan_curves))
    )
    return result.scalars().all()

async def create_server(db: AsyncSession, server: schemas.ServerCreate):
    """创建一台新服务器"""
    db_server = models.Server(**server.dict())
    db.add(db_server)
    await db.commit()
    await db.refresh(db_server)
    # After creation, we need to get the full object with the relationship loaded
    return await get_server(db, db_server.id)

async def update_server(db: AsyncSession, server_id: int, server_update: schemas.ServerUpdate):
    """更新服务器信息"""
    db_server = await get_server(db, server_id)
    if not db_server:
        return None
    
    update_data = server_update.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_server, key, value)
        
    await db.commit()
    await db.refresh(db_server)
    return db_server

async def delete_server(db: AsyncSession, server_id: int):
    """删除一台服务器"""
    db_server = await get_server(db, server_id)
    if not db_server:
        return None
    
    await db.delete(db_server)
    await db.commit()
    return db_server


# ====================
# Fan Curve & History CRUD
# ====================

async def set_fan_curve(db: AsyncSession, server_id: int, curve: schemas.FanCurveCreate):
    """为服务器设置新的风扇曲线（覆盖旧的）"""
    # First, delete any existing curve for this server
    existing_curve_result = await db.execute(select(models.FanCurve).filter(models.FanCurve.server_id == server_id))
    existing_curve = existing_curve_result.scalars().first()
    
    if existing_curve:
        await db.delete(existing_curve)
        await db.flush()

    # Create the new curve
    db_curve = models.FanCurve(**curve.dict(), server_id=server_id)
    db.add(db_curve)
    await db.commit()
    await db.refresh(db_curve)
    return db_curve

async def get_fan_curve(db: AsyncSession, server_id: int):
    """根据服务器ID获取风扇曲线"""
    result = await db.execute(select(models.FanCurve).filter(models.FanCurve.server_id == server_id))
    return result.scalars().first()

async def create_temperature_history(db: AsyncSession, server_id: int, temperature: float):
    """创建一条温度历史记录，并清理旧数据"""
    db_history = models.TemperatureHistory(server_id=server_id, temperature=temperature)
    db.add(db_history)
    await db.flush()
    
    # 清理旧数据，只保留最近3600条
    await cleanup_old_temperature_history(db, server_id)
    
    await db.commit()
    await db.refresh(db_history)
    return db_history

async def create_fan_speed_history(db: AsyncSession, server_id: int, speed_rpm: int):
    """创建一条风扇转速历史记录，并清理旧数据"""
    db_history = models.FanSpeedHistory(server_id=server_id, average_speed_rpm=speed_rpm)
    db.add(db_history)
    await db.flush()
    
    # 清理旧数据，只保留最近3600条
    await cleanup_old_fan_speed_history(db, server_id)
    
    await db.commit()
    await db.refresh(db_history)
    return db_history

async def cleanup_old_temperature_history(db: AsyncSession, server_id: int):
    """清理旧的温度历史记录，只保留最近3600条"""
    # 获取该服务器的记录总数
    count_result = await db.execute(
        select(func.count(models.TemperatureHistory.id))
        .filter(models.TemperatureHistory.server_id == server_id)
    )
    total_count = count_result.scalar()
    
    if total_count > 3600:
        # 获取要删除的记录的ID（最旧的记录）
        old_records_result = await db.execute(
            select(models.TemperatureHistory.id)
            .filter(models.TemperatureHistory.server_id == server_id)
            .order_by(models.TemperatureHistory.timestamp.desc())
            .offset(3600)
        )
        old_record_ids = old_records_result.scalars().all()
        
        if old_record_ids:
            # 删除最旧的记录
            await db.execute(
                delete(models.TemperatureHistory)
                .filter(models.TemperatureHistory.id.in_(old_record_ids))
            )

async def cleanup_old_fan_speed_history(db: AsyncSession, server_id: int):
    """清理旧的风扇转速历史记录，只保留最近3600条"""
    # 获取该服务器的记录总数
    count_result = await db.execute(
        select(func.count(models.FanSpeedHistory.id))
        .filter(models.FanSpeedHistory.server_id == server_id)
    )
    total_count = count_result.scalar()
    
    if total_count > 3600:
        # 获取要删除的记录的ID（最旧的记录）
        old_records_result = await db.execute(
            select(models.FanSpeedHistory.id)
            .filter(models.FanSpeedHistory.server_id == server_id)
            .order_by(models.FanSpeedHistory.timestamp.desc())
            .offset(3600)
        )
        old_record_ids = old_records_result.scalars().all()
        
        if old_record_ids:
            # 删除最旧的记录
            await db.execute(
                delete(models.FanSpeedHistory)
                .filter(models.FanSpeedHistory.id.in_(old_record_ids))
            )

async def get_temperature_history(db: AsyncSession, server_id: int, start_date: datetime.datetime, end_date: datetime.datetime):
    """获取指定时间范围内的温度历史记录"""
    result = await db.execute(
        select(models.TemperatureHistory)
        .filter(
            models.TemperatureHistory.server_id == server_id,
            models.TemperatureHistory.timestamp >= start_date,
            models.TemperatureHistory.timestamp <= end_date
        )
        .order_by(models.TemperatureHistory.timestamp)
    )
    return result.scalars().all()

async def get_fan_speed_history(db: AsyncSession, server_id: int, start_date: datetime.datetime, end_date: datetime.datetime):
    """获取指定时间范围内的风扇转速历史记录"""
    result = await db.execute(
        select(models.FanSpeedHistory)
        .filter(
            models.FanSpeedHistory.server_id == server_id,
            models.FanSpeedHistory.timestamp >= start_date,
            models.FanSpeedHistory.timestamp <= end_date
        )
        .order_by(models.FanSpeedHistory.timestamp)
    )
    return result.scalars().all()

async def get_recent_temperature_history(db: AsyncSession, server_id: int, limit: int = 540):
    """获取最近的温度历史记录"""
    result = await db.execute(
        select(models.TemperatureHistory)
        .filter(models.TemperatureHistory.server_id == server_id)
        .order_by(models.TemperatureHistory.timestamp.desc())
        .limit(limit)
    )
    return result.scalars().all()

async def get_recent_fan_speed_history(db: AsyncSession, server_id: int, limit: int = 540):
    """获取最近的风扇转速历史记录"""
    result = await db.execute(
        select(models.FanSpeedHistory)
        .filter(models.FanSpeedHistory.server_id == server_id)
        .order_by(models.FanSpeedHistory.timestamp.desc())
        .limit(limit)
    )
    return result.scalars().all()