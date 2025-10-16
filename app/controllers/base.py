import asyncio
from abc import ABC, abstractmethod
from typing import Optional
from .. import models, crud
from ..database import AsyncSessionLocal
from .. import crud_cache

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

    async def get_temperature_with_cache(self) -> float:
        """
        带缓存机制获取温度数据。
        优先从数据库缓存获取，如果缓存过期则调用IPMI命令获取最新数据。
        :return: 浮点型的温度值，如果获取失败返回-1.0。
        """
        try:
            async with AsyncSessionLocal() as db:
                # 尝试从缓存获取
                cached_temp = await crud_cache.get_latest_temperature(db, self.server.id, self._temp_cache_age)
                if cached_temp is not None:
                    return cached_temp
                
                # 缓存过期或不存在，从IPMI获取
                ipmi_temp = await self._get_temperature_from_ipmi()
                if ipmi_temp != -1.0:
                    # 将新数据写入数据库作为新的缓存点
                    await crud.create_temperature_history(db, server_id=self.server.id, temperature=ipmi_temp)
                return ipmi_temp
                
        except Exception as e:
            print(f"Error getting temperature with cache for {self.server.name}: {e}")
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
        获取用于风扇控制的决策温度（使用缓存机制）。
        对于多路CPU的服务器，此方法应负责处理并返回一个单一的、有代表性的温度值（如最高温或平均温）。
        :return: 浮点型的温度值。
        """
        return await self.get_temperature_with_cache()

    async def get_fan_speed_with_cache(self) -> int:
        """
        带缓存机制获取风扇速度数据。
        优先从数据库缓存获取，如果缓存过期则调用IPMI命令获取最新数据。
        :return: 整型的风扇速度值，如果获取失败返回-1。
        """
        try:
            async with AsyncSessionLocal() as db:
                # 尝试从缓存获取
                cached_speed = await crud_cache.get_latest_fan_speed(db, self.server.id, self._fan_cache_age)
                if cached_speed is not None:
                    return cached_speed
                
                # 缓存过期或不存在，从IPMI获取
                ipmi_speed = await self._get_fan_speed_from_ipmi()
                if ipmi_speed != -1:
                    # 将新数据写入数据库作为新的缓存点
                    await crud.create_fan_speed_history(db, server_id=self.server.id, speed_rpm=ipmi_speed)
                return ipmi_speed
                
        except Exception as e:
            print(f"Error getting fan speed with cache for {self.server.name}: {e}")
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
        获取服务器风扇的平均转速 (RPM)（使用缓存机制）。
        :return: 整型的平均转速值。
        """
        return await self.get_fan_speed_with_cache()

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