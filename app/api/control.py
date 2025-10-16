from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from .. import crud, schemas
from ..database import get_db
from ..controllers.factory import get_controller, UnsupportedModelError

router = APIRouter(redirect_slashes=False)

@router.get("/{server_id}/temperature", response_model=schemas.TemperatureReading)
async def get_temperature(server_id: int, db: AsyncSession = Depends(get_db)):
    """获取服务器当前温度（使用缓存机制）"""
    db_server = await crud.get_server(db, server_id=server_id)
    if db_server is None:
        raise HTTPException(status_code=404, detail="Server not found")
    
    try:
        controller = get_controller(db_server)
        temperature = await controller.get_temperature_cached()
        return {"server_id": server_id, "temperature": temperature}
    except UnsupportedModelError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{server_id}/fan/speed", response_model=schemas.FanSpeedReading)
async def get_fan_speed(server_id: int, db: AsyncSession = Depends(get_db)):
    """获取服务器当前平均风扇转速（使用缓存机制）"""
    db_server = await crud.get_server(db, server_id=server_id)
    if db_server is None:
        raise HTTPException(status_code=404, detail="Server not found")

    try:
        controller = get_controller(db_server)
        speed_rpm = await controller.get_fan_speed_cached()
        return {"server_id": server_id, "average_speed_rpm": speed_rpm}
    except UnsupportedModelError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{server_id}/fan/manual")
async def set_manual_fan_mode(server_id: int, speed_setting: schemas.ServerUpdate, db: AsyncSession = Depends(get_db)):
    """设置服务器为手动风扇控制模式"""
    if speed_setting.manual_fan_speed is None:
        raise HTTPException(status_code=400, detail="Manual fan speed must be provided.")

    db_server = await crud.get_server(db, server_id=server_id)
    if db_server is None:
        raise HTTPException(status_code=404, detail="Server not found")

    try:
        controller = get_controller(db_server)
        await controller.take_over_fan_control()
        await controller.set_fan_speed(speed_setting.manual_fan_speed)
        
        # 更新数据库状态
        await crud.update_server(db, server_id, schemas.ServerUpdate(
            control_mode="manual",
            manual_fan_speed=speed_setting.manual_fan_speed
        ))
        
        return {"message": f"Fan speed for server {server_id} set to manual at {speed_setting.manual_fan_speed}%"}
    except UnsupportedModelError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{server_id}/fan/auto")
async def set_auto_fan_mode(server_id: int, curve: schemas.FanCurveCreate, db: AsyncSession = Depends(get_db)):
    """设置服务器为自动风扇控制模式, 并更新其温度曲线"""
    db_server = await crud.get_server(db, server_id=server_id)
    if db_server is None:
        raise HTTPException(status_code=404, detail="Server not found")

    try:
        # 更新数据库中的曲线
        await crud.set_fan_curve(db, server_id=server_id, curve=curve)
        
        # 接管服务器风扇控制权，以便我们的应用可以动态设置转速
        controller = get_controller(db_server)
        await controller.take_over_fan_control()

        # 更新数据库状态
        await crud.update_server(db, server_id, schemas.ServerUpdate(control_mode="auto", manual_fan_speed=None))

        return {"message": f"Fan control for server {server_id} set to auto with updated curve."}
    except UnsupportedModelError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{server_id}/fan/config", response_model=schemas.FanConfig)
async def get_fan_config(server_id: int, db: AsyncSession = Depends(get_db)):
    """获取服务器当前的完整风扇配置"""
    db_server = await crud.get_server(db, server_id=server_id)
    if db_server is None:
        raise HTTPException(status_code=404, detail="Server not found")

    response = {"server_id": server_id, "mode": db_server.control_mode}
    if db_server.control_mode == "manual":
        response["speed"] = db_server.manual_fan_speed
    else:
        curve = await crud.get_fan_curve(db, server_id=server_id)
        if curve:
            response["curve"] = {"points": curve.points}
            
    return response