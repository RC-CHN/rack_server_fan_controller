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

    async def _get_temperature_from_ipmi(self) -> float:
        """从IPMI获取 CPU 温度 (CPU1 和 CPU2 中的最大值)"""
        cpu1_temp = await self._get_single_sensor_temp("CPU1_Temp")
        cpu2_temp = await self._get_single_sensor_temp("CPU2_Temp")

        valid_temps = [temp for temp in [cpu1_temp, cpu2_temp] if temp is not None]

        if not valid_temps:
            logger.warning(f"Could not retrieve any valid CPU temperature for server {self.server.name}.")
            return -1.0
        
        return max(valid_temps)

    async def _get_fan_speed_from_ipmi(self) -> int:
        """
        获取R4900 G3风扇转速（所有风扇的平均RPM）
        使用批量获取：ipmitool sensor get FAN1_Speed FAN2_Speed ... FAN6_Speed
        """
        fan_sensors = ["FAN1_Speed", "FAN2_Speed", "FAN3_Speed",
                      "FAN4_Speed", "FAN5_Speed", "FAN6_Speed"]
        
        # 批量获取所有风扇传感器数据
        cmd_args = ['sensor', 'get'] + fan_sensors
        batch_output = await self._run_ipmi_command(*cmd_args)
        
        if not batch_output:
            logger.warning(f"批量获取风扇转速失败 for {self.server.name}")
            return -1
        
        total_rpm = 0
        valid_fans = 0
        
        # 解析批量输出中的每个风扇转速
        for fan_sensor in fan_sensors:
            # 查找每个风扇传感器的输出段
            # 格式: "Sensor Reading        : 2600 (+/- 0) RPM"
            sensor_pattern = f"{fan_sensor}.*?Sensor Reading\\s*:\\s*([\\d\\.-]+)"
            match = re.search(sensor_pattern, batch_output, re.DOTALL)
            
            if match:
                try:
                    rpm_value = float(match.group(1))
                    if rpm_value > 0:  # 确保是有效的RPM值
                        total_rpm += rpm_value
                        valid_fans += 1
                        logger.debug(f"{self.server.name} {fan_sensor}: {rpm_value} RPM")
                    else:
                        logger.debug(f"{self.server.name} {fan_sensor}: 无效RPM值 {rpm_value}")
                except ValueError:
                    logger.warning(f"无法解析风扇转速值 '{match.group(1)}' 从传感器 {fan_sensor}")
            else:
                logger.debug(f"{self.server.name} {fan_sensor}: 未找到传感器数据")
        
        if valid_fans > 0:
            average_rpm = int(total_rpm / valid_fans)  # 取整数
            logger.info(f"{self.server.name} 风扇平均转速: {average_rpm} RPM (基于{valid_fans}个有效风扇)")
            return average_rpm
        else:
            logger.warning(f"无法获取{self.server.name}的任何风扇转速")
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

    async def take_over_fan_control(self):
        """
        [PLACEHOLDER] 接管风扇控制权。此功能当前为占位符，不做任何操作。
        """
        logger.info(f"take_over_fan_control for {self.server.name} is a placeholder. No action taken.")
        pass

    async def return_fan_control_to_system(self):
        """
        [PLACEHOLDER] 交还风扇控制权。此功能当前为占位符，不做任何操作。
        """
        logger.info(f"return_fan_control_to_system for {self.server.name} is a placeholder. No action taken.")
        pass