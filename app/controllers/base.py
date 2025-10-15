from abc import ABC, abstractmethod
from .. import models

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

    @abstractmethod
    async def get_temperature(self) -> float:
        """
        获取用于风扇控制的决策温度。
        对于多路CPU的服务器，此方法应负责处理并返回一个单一的、有代表性的温度值（如最高温或平均温）。
        :return: 浮点型的温度值。
        """
        pass

    @abstractmethod
    async def get_fan_speed(self) -> int:
        """
        获取服务器风扇的平均转速 (RPM)。
        :return: 整型的平均转速值。
        """
        pass

    @abstractmethod
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
    async def set_manual_fan_control(self):
        """
        将服务器风扇设置为手动控制模式。
        """
        pass

    @abstractmethod
    async def set_auto_fan_control(self):
        """
        将服务器风扇恢复为系统自动（动态）控制模式。
        """
        pass