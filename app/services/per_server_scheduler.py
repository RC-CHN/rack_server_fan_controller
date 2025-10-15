import asyncio
import logging
from typing import Dict
from ..database import AsyncSessionLocal
from .. import crud, models
from ..controllers.factory import get_controller

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# {server_id: asyncio.Task}
SERVER_CONTROL_TASKS: Dict[int, asyncio.Task] = {}
SERVER_METRIC_TASKS: Dict[int, asyncio.Task] = {}

# --- Fan Control Logic ---

def _calculate_fan_speed_from_curve(temperature: float, curve_points: list) -> int:
    """根据温度和曲线计算目标风扇速度（插值法）"""
    if not curve_points:
        return 20  # 默认值

    curve_points.sort(key=lambda p: p['temp'])

    if temperature < curve_points[0]['temp']:
        return curve_points[0]['speed']
    if temperature >= curve_points[-1]['temp']:
        return curve_points[-1]['speed']

    for i in range(len(curve_points) - 1):
        p1, p2 = curve_points[i], curve_points[i+1]
        if p1['temp'] <= temperature < p2['temp']:
            temp_range = p2['temp'] - p1['temp']
            speed_range = p2['speed'] - p1['speed']
            temp_offset = temperature - p1['temp']
            speed_offset = (temp_offset / temp_range) * speed_range if temp_range > 0 else 0
            return int(p1['speed'] + speed_offset)
    
    return curve_points[-1]['speed']

async def _server_control_loop(server: models.Server):
    """
    单个服务器的风扇控制循环。
    """
    logger.info(f"Starting control loop for server: {server.name} (ID: {server.id})")
    controller = get_controller(server)
    try:
        await controller.take_over_fan_control()
    except Exception as e:
        logger.error(f"Error taking over fan control for {server.name}: {e}", exc_info=True)

    while True:
        try:
            # 每次循环都重新获取服务器信息，以防其状态（如 control_mode）发生变化
            async with AsyncSessionLocal() as db:
                refreshed_server = await crud.get_server(db, server.id)
            
            if not refreshed_server or refreshed_server.control_mode != "auto":
                logger.info(f"Stopping control loop for {server.name} as it's no longer in 'auto' mode.")
                break

            controller = get_controller(refreshed_server)
            temperature = await controller.get_temperature()

            if temperature == -1.0:
                logger.warning(f"Cannot auto-control fans for {server.name}, invalid temperature reading.")
                await asyncio.sleep(10) # 等待10秒后重试
                continue

            async with AsyncSessionLocal() as db:
                curve = await crud.get_fan_curve(db, server_id=refreshed_server.id)
            
            if not curve or not curve.points:
                logger.warning(f"Cannot auto-control fans for {server.name}, no fan curve defined.")
                await asyncio.sleep(30) # 没有曲线定义，等待较长时间
                continue

            target_speed = _calculate_fan_speed_from_curve(temperature, list(curve.points))
            logger.info(f"Auto-control for {server.name}: Temp={temperature}°C, Target Speed={target_speed}%")
            await controller.set_fan_speed(target_speed)
            
            await asyncio.sleep(10) # 控制间隔

        except asyncio.CancelledError:
            logger.info(f"Control loop for server {server.name} was cancelled.")
            break
        except Exception as e:
            logger.error(f"Error in control loop for server {server.name}: {e}", exc_info=True)
            await asyncio.sleep(30) # 出现异常时，等待较长时间后重试

    # 清理任务字典
    try:
        await controller.return_fan_control_to_system()
    except Exception as e:
        logger.error(f"Error returning fan control for {server.name}: {e}", exc_info=True)

    if server.id in SERVER_CONTROL_TASKS:
        del SERVER_CONTROL_TASKS[server.id]
    logger.info(f"Control loop for server {server.name} has stopped.")


async def start_server_control_loop(server: models.Server):
    """启动或重启指定服务器的控制循环"""
    if server.id in SERVER_CONTROL_TASKS:
        await stop_server_control_loop(server.id)
    
    if server.control_mode == "auto":
        loop = asyncio.get_running_loop()
        task = loop.create_task(_server_control_loop(server))
        SERVER_CONTROL_TASKS[server.id] = task
        return task

async def stop_server_control_loop(server_id: int):
    """停止指定服务器的控制循环"""
    if server_id in SERVER_CONTROL_TASKS:
        task = SERVER_CONTROL_TASKS[server_id]
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass # 任务取消是正常行为
        logger.info(f"Successfully stopped control loop for server ID: {server_id}")
    if server_id in SERVER_CONTROL_TASKS:
        del SERVER_CONTROL_TASKS[server_id]

# --- Metrics Recording Logic ---

async def _server_metrics_loop(server: models.Server):
    """单个服务器的指标记录循环"""
    logger.info(f"Starting metrics loop for server: {server.name} (ID: {server.id})")
    while True:
        try:
            controller = get_controller(server)
            temperature = await controller.get_temperature()
            fan_speed = await controller.get_fan_speed()

            async with AsyncSessionLocal() as db:
                if temperature != -1.0:
                    await crud.create_temperature_history(db, server_id=server.id, temperature=temperature)
                if fan_speed != -1:
                    await crud.create_fan_speed_history(db, server_id=server.id, speed_rpm=fan_speed)
            
            logger.info(f"Recorded metrics for {server.name}: Temp={temperature}°C, Fan={fan_speed} RPM")
            await asyncio.sleep(30) # 指标记录间隔

        except asyncio.CancelledError:
            logger.info(f"Metrics loop for server {server.name} was cancelled.")
            break
        except Exception as e:
            logger.error(f"Error in metrics loop for server {server.name}: {e}", exc_info=True)
            await asyncio.sleep(60)

    if server.id in SERVER_METRIC_TASKS:
        del SERVER_METRIC_TASKS[server.id]
    logger.info(f"Metrics loop for server {server.name} has stopped.")

async def start_server_metrics_loop(server: models.Server):
    if server.id in SERVER_METRIC_TASKS:
        await stop_server_metrics_loop(server.id)
    
    loop = asyncio.get_running_loop()
    task = loop.create_task(_server_metrics_loop(server))
    SERVER_METRIC_TASKS[server.id] = task
    return task

async def stop_server_metrics_loop(server_id: int):
    if server_id in SERVER_METRIC_TASKS:
        task = SERVER_METRIC_TASKS[server_id]
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        logger.info(f"Successfully stopped metrics loop for server ID: {server_id}")
    if server_id in SERVER_METRIC_TASKS:
        del SERVER_METRIC_TASKS[server_id]


# --- Global Control ---

async def start_all_loops():
    """在应用启动时，为所有服务器启动控制和指标记录循环"""
    logger.info("Starting all server loops...")
    async with AsyncSessionLocal() as db:
        servers = await crud.get_servers(db, limit=1000)
    
    for server in servers:
        await start_server_metrics_loop(server)
        if server.control_mode == "auto":
            await start_server_control_loop(server)

def stop_all_loops():
    """在应用关闭时，停止所有正在运行的循环"""
    logger.info("Stopping all server loops...")
    
    # 收集所有任务
    control_tasks = list(SERVER_CONTROL_TASKS.values())
    metric_tasks = list(SERVER_METRIC_TASKS.values())
    all_tasks = control_tasks + metric_tasks

    if not all_tasks:
        return

    # 取消所有任务
    for task in all_tasks:
        task.cancel()

    # 等待所有任务完成取消
    # loop = asyncio.get_running_loop()
    # await asyncio.gather(*all_tasks, return_exceptions=True)
    
    SERVER_CONTROL_TASKS.clear()
    SERVER_METRIC_TASKS.clear()
    logger.info("All server loops have been requested to stop.")
