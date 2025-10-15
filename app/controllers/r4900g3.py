import asyncio
import logging
import re
from .base import BaseServerController
from .. import models

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class R4900G3Controller(BaseServerController):
    """
    H3C R4900 G3 服务器的具体控制器实现。
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
            # 记录完整的命令以便调试
            full_cmd = ' '.join(cmd)
            logger.error(f"IPMI command failed for server {self.server.name} ({full_cmd}): {stderr.decode().strip()}")
            return None
        
        return stdout.decode().strip()

    async def _get_single_sensor_temp(self, sensor_name: str) -> float | None:
        """获取单个传感器的温度值"""
        output = await self._run_ipmi_command('sensor', 'get', sensor_name)
        if output is None:
            return None
        
        match = re.search(r"Sensor Reading\s*:\s*([\d\.-]+)", output)
        if match:
            try:
                return float(match.group(1))
            except (ValueError, IndexError):
                logger.warning(f"Could not parse temperature from sensor '{sensor_name}' for server {self.server.name}. Output: {output}")
                return None
        return None

    async def get_temperature(self) -> float:
        """获取 CPU 温度 (CPU1 和 CPU2 中的最大值)"""
        cpu1_temp = await self._get_single_sensor_temp("CPU1_Temp")
        cpu2_temp = await self._get_single_sensor_temp("CPU2_Temp")

        valid_temps = [temp for temp in [cpu1_temp, cpu2_temp] if temp is not None]

        if not valid_temps:
            logger.warning(f"Could not retrieve any valid CPU temperature for server {self.server.name}.")
            return -1.0
        
        return max(valid_temps)

    async def get_fan_speed(self) -> int:
        """
        R4900 G3 无法直接读取风扇转速，因此返回一个占位符。
        控制逻辑是只写的。
        """
        logger.debug("get_fan_speed for R4900G3 is a placeholder as it's not directly readable.")
        return -1

    async def set_fan_speed(self, speed: int):
        """统一设置所有风扇的转速百分比"""
        if not (0 <= speed <= 100):
            logger.error(f"Invalid fan speed value for {self.server.name}: {speed}. Must be between 0 and 100.")
            return

        # 将 0-100 的百分比转换为 0x00-0xFF 的十六进制值
        speed_value = int((speed / 100) * 255)
        speed_hex = f"0x{speed_value:02x}"

        logger.info(f"Setting all fans to {speed}% ({speed_hex}) for server {self.server.name}.")

        # R4900 G3 需要为每个风扇单独设置
        for fan_id in range(6): # 风扇 0 到 5
            fan_hex = f"0x{fan_id:02x}"
            await self._run_ipmi_command(
                'raw', '0x36', '0x03', '0x20', '0x14', '0x00', '0x01',
                fan_hex,    # 风扇 ID
                '0x01',     # 固定字节
                speed_hex   # 风扇转速
            )

    async def _set_system_fan_mode(self, mode: str):
        """
        设置系统风扇模式 (0x00: 静音, 0x01: 均衡, 0x02: 强劲, 0x03: 自定义)
        并重新加载配置使其生效。
        """
        mode_hex = {
            "silent": "0x00",
            "balanced": "0x01",
            "performance": "0x02",
            "custom": "0x03"
        }.get(mode, "0x00") # 默认为静音

        # 1. 设置模式
        await self._run_ipmi_command('raw', '0x36', '0x03', '0xa2', '0x63', '0x00', '0x60', '0x00', mode_hex)
        logger.info(f"Set R4900G3 system fan mode to '{mode}' for server {self.server.name}.")
        
        # 2. 重新加载配置以应用模式
        await self._run_ipmi_command('raw', '0x36', '0x03', '0x20', '0x14', '0x00', '0x22')
        logger.info(f"Reloaded fan configuration for server {self.server.name}.")

    async def take_over_fan_control(self):
        """
        接管风扇控制权，通过将系统模式设置为“静音”来实现。
        """
        logger.info(f"Taking over fan control for {self.server.name} by setting system mode to 'silent'.")
        await self._set_system_fan_mode("silent")

    async def return_fan_control_to_system(self):
        """
        交还风扇控制权，通过将系统模式恢复为“静音”来实现。
        """
        logger.info(f"Returning fan control for {self.server.name} by setting system mode to 'silent'.")
        await self._set_system_fan_mode("silent")