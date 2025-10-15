import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from ..database import AsyncSessionLocal
from .. import crud
from ..controllers.factory import get_controller

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def record_metrics():
    """
    定期任务：记录所有服务器的温度和风扇转速。
    """
    logger.info("Executing scheduled job: record_metrics")
    async with AsyncSessionLocal() as db:
        servers = await crud.get_servers(db, limit=1000)  # Get all servers
        for server in servers:
            try:
                controller = get_controller(server)
                
                # 记录温度
                temperature = await controller.get_temperature()
                if temperature != -1.0:
                    await crud.create_temperature_history(db, server_id=server.id, temperature=temperature)
                    logger.info(f"Recorded temperature for {server.name}: {temperature}°C")

                # 记录风扇转速
                fan_speed = await controller.get_fan_speed()
                if fan_speed != -1:
                    await crud.create_fan_speed_history(db, server_id=server.id, speed_rpm=fan_speed)
                    logger.info(f"Recorded fan speed for {server.name}: {fan_speed} RPM")

            except Exception as e:
                logger.error(f"Error recording metrics for server {server.name}: {e}")

def _calculate_fan_speed_from_curve(temperature: float, curve_points: list) -> int:
    """根据温度和曲线计算目标风扇速度（插值法）"""
    if not curve_points:
        return 20  # 默认值

    # 按温度排序
    curve_points.sort(key=lambda p: p['temp'])

    # 如果温度低于最低点
    if temperature < curve_points[0]['temp']:
        return curve_points[0]['speed']

    # 如果温度高于最高点
    if temperature >= curve_points[-1]['temp']:
        return curve_points[-1]['speed']

    # 找到温度所在的区间
    for i in range(len(curve_points) - 1):
        p1 = curve_points[i]
        p2 = curve_points[i+1]
        if p1['temp'] <= temperature < p2['temp']:
            # 线性插值
            temp_range = p2['temp'] - p1['temp']
            speed_range = p2['speed'] - p1['speed']
            temp_offset = temperature - p1['temp']
            
            speed_offset = (temp_offset / temp_range) * speed_range if temp_range > 0 else 0
            return int(p1['speed'] + speed_offset)
    
    return curve_points[-1]['speed']


async def auto_control_fans():
    """
    定期任务：对处于自动模式的服务器，根据温度曲线调整风扇转速。
    """
    logger.info("Executing scheduled job: auto_control_fans")
    async with AsyncSessionLocal() as db:
        servers = await crud.get_servers(db, limit=1000)
        for server in servers:
            if server.control_mode != "auto":
                continue

            try:
                controller = get_controller(server)
                temperature = await controller.get_temperature()
                
                if temperature == -1.0:
                    logger.warning(f"Cannot auto-control fans for {server.name}, invalid temperature reading.")
                    continue

                curve = await crud.get_fan_curve(db, server_id=server.id)
                if not curve or not curve.points:
                    logger.warning(f"Cannot auto-control fans for {server.name}, no fan curve defined.")
                    continue

                target_speed = _calculate_fan_speed_from_curve(temperature, curve.points)
                logger.info(f"Auto-control for {server.name}: Temp={temperature}°C, Target Speed={target_speed}%")
                await controller.set_fan_speed(target_speed)

            except Exception as e:
                logger.error(f"Error in auto-control for server {server.name}: {e}")


# 初始化调度器
scheduler = AsyncIOScheduler()

# 添加任务
# 你可以根据需要调整这里的间隔时间
scheduler.add_job(record_metrics, 'interval', seconds=30)
scheduler.add_job(auto_control_fans, 'interval', seconds=10)