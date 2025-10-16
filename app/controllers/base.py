import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Optional
from .. import models, crud
from ..database import AsyncSessionLocal
from .. import crud_cache

logger = logging.getLogger(__name__)

class BaseServerController(ABC):
    """
    服务器控制器抽象基类。
    定义了所有具体服务器型号控制器必须实现的通用接口。
    """

    def __init__(self, server: models.Server):
        """
        初始化控制器。
        :param server: 服务器的 SQLAlchemy 模型实例，包含IPMI凭据等信息。
        """
        self.server = server
        self._temp_cache_age = 30  # 温度缓存有效期（秒）
        self._fan_cache_age = 60   # 风扇速度缓存有效期（秒）

    async def get_temperature_realtime(self) -> float:
        """
        实时获取温度数据（用于风扇控制）。
        始终执行IPMI命令获取最新数据，确保控制的及时性。
        注意：此方法不写入数据库，数据存储由指标记录循环负责。
        :return: 浮点型的温度值，如果获取失败返回-1.0。
        """
        try:
            return await self._get_temperature_from_ipmi()
        except Exception as e:
            logger.error(f"Error getting realtime temperature for {self.server.name}: {e}")
            return -1.0
    
    async def get_temperature_cached(self) -> float:
        """
        带缓存机制获取温度数据（用于API和指标显示）。
        优先从数据库缓存获取，如果缓存过期则调用IPMI命令获取最新数据。
        注意：此方法不写入数据库，依赖指标记录循环定期更新数据。
        :return: 浮点型的温度值，如果获取失败返回-1.0。
        """
        try:
            async with AsyncSessionLocal() as db:
                # 尝试从缓存获取（由指标记录循环定期更新）
                cached_temp = await crud_cache.get_latest_temperature(db, self.server.id, self._temp_cache_age)
                if cached_temp is not None:
                    return cached_temp
                
                # 缓存过期或不存在，从IPMI获取（不存储到数据库）
                return await self._get_temperature_from_ipmi()
                
        except Exception as e:
            logger.error(f"Error getting cached temperature for {self.server.name}: {e}")
            return -1.0
    
    @abstractmethod
    async def _get_temperature_from_ipmi(self) -> float:
        """
        从IPMI获取温度数据的实际实现。
        对于多路CPU的服务器，此方法应负责处理并返回一个单一的、有代表性的温度值（如最高温或平均温）。
        :return: 浮点型的温度值。
        """
        pass

    async def get_temperature(self) -> float:
        """
        获取用于风扇控制的决策温度（实时获取）。
        对于多路CPU的服务器，此方法应负责处理并返回一个单一的、有代表性的温度值（如最高温或平均温）。
        :return: 浮点型的温度值。
        """
        return await self.get_temperature_realtime()

    async def get_fan_speed_realtime(self) -> int:
        """
        实时获取风扇速度数据（用于风扇控制）。
        始终执行IPMI命令获取最新数据，确保控制的及时性。
        注意：此方法不写入数据库，数据存储由指标记录循环负责。
        :return: 整型的风扇速度值，如果获取失败返回-1。
        """
        try:
            return await self._get_fan_speed_from_ipmi()
        except Exception as e:
            logger.error(f"Error getting realtime fan speed for {self.server.name}: {e}")
            return -1
    
    async def get_fan_speed_cached(self) -> int:
        """
        带缓存机制获取风扇速度数据（用于API和指标显示）。
        优先从数据库缓存获取，如果缓存过期则调用IPMI命令获取最新数据。
        注意：此方法不写入数据库，依赖指标记录循环定期更新数据。
        :return: 整型的风扇速度值，如果获取失败返回-1。
        """
        try:
            async with AsyncSessionLocal() as db:
                # 尝试从缓存获取（由指标记录循环定期更新）
                cached_speed = await crud_cache.get_latest_fan_speed(db, self.server.id, self._fan_cache_age)
                if cached_speed is not None:
                    return cached_speed
                
                # 缓存过期或不存在，从IPMI获取（不存储到数据库）
                return await self._get_fan_speed_from_ipmi()
                
        except Exception as e:
            logger.error(f"Error getting cached fan speed for {self.server.name}: {e}")
            return -1
    
    @abstractmethod
    async def _get_fan_speed_from_ipmi(self) -> int:
        """
        从IPMI获取风扇速度数据的实际实现。
        :return: 整型的平均转速值。
        """
        pass

    async def get_fan_speed(self) -> int:
        """
        获取服务器风扇的平均转速 (RPM)（实时获取）。
        :return: 整型的平均转速值。
        """
        return await self.get_fan_speed_realtime()

    async def get_all_sensors(self) -> list[dict]:
        """
        (可选实现) 获取所有传感器的原始读数列表，用于详细诊断。
        :return: 一个包含传感器信息的字典列表，例如 [{"name": "CPU1 Temp", "value": 45.0, "unit": "C"}, ...]。
        """
        return []

    @abstractmethod
    async def set_fan_speed(self, speed: int):
        """
        设置风扇转速百分比。
        :param speed: 0到100之间的整数。
        """
        pass

    @abstractmethod
    async def take_over_fan_control(self):
        """
        接管风扇控制权，允许应用程序通过 set_fan_speed() 设置转速。
        （对应 IPMI 的手动模式）
        """
        pass

    @abstractmethod
    async def return_fan_control_to_system(self):
        """
        将风扇控制权交还给服务器系统（iDRAC/BMC）。
        （对应 IPMI 的系统自动模式）
        """
        pass