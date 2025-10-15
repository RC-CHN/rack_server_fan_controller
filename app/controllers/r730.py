import asyncio
import logging
from .base import BaseServerController
from ... import models

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class R730Controller(BaseServerController):
    """
    Dell R730 服务器的具体控制器实现。
    """

    async def _run_ipmi_command(self, *args):
        """
        一个通用的异步方法来执行 ipmitool 命令。
        """
        cmd = [
            'ipmitool', '-I', 'lanplus',
            '-H', self.server.ipmi_host,
            '-U', self.server.ipmi_username,
            '-P', self.server.ipmi_password,
            *args
        ]
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            logger.error(f"IPMI command failed for server {self.server.name}: {stderr.decode().strip()}")
            return None
        
        return stdout.decode().strip()

    async def get_temperature(self) -> float:
        sensor_data = await self._run_ipmi_command('sensor')
        if not sensor_data:
            return -1.0

        temperatures = []
        for line in sensor_data.splitlines():
            if "Temp" in line and "degrees C" in line and "Inlet Temp" not in line and "Exhaust Temp" not in line:
                try:
                    temp_value = float(line.split('|')[1].strip())
                    temperatures.append(temp_value)
                except (ValueError, IndexError):
                    continue
        
        if temperatures:
            # 对于R730（通常是双路），我们返回CPU的最高温度作为决策温度
            return max(temperatures)
        
        logger.warning(f"No valid CPU temperature readings found for server {self.server.name}.")
        return -1.0

    async def get_fan_speed(self) -> int:
        # R730 的 ipmitool sensor 输出中通常不直接显示风扇RPM，
        # 而是以百分比显示。这里我们先返回一个占位符。
        # 实际实现可能需要解析 'Fan' 相关的行。
        logger.warning("get_fan_speed for R730 is not fully implemented and returns a placeholder.")
        return -1

    async def set_fan_speed(self, speed: int):
        if 0 <= speed <= 100:
            hex_speed = hex(int(speed))
            await self._run_ipmi_command('raw', '0x30', '0x30', '0x02', '0xff', hex_speed)
            logger.info(f"Set fan speed to {speed}% for server {self.server.name}")
        else:
            logger.error(f"Invalid fan speed value: {speed}. Must be between 0 and 100.")

    async def set_manual_fan_control(self):
        await self._run_ipmi_command('raw', '0x30', '0x30', '0x01', '0x00')
        logger.info(f"Set fan mode to MANUAL for server {self.server.name}")

    async def set_auto_fan_control(self):
        await self._run_ipmi_command('raw', '0x30', '0x30', '0x01', '0x01')
        logger.info(f"Set fan mode to AUTO for server {self.server.name}")
