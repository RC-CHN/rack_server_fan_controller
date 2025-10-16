import asyncio
import logging
import re
from .base import BaseServerController
from .. import models

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

    async def _get_temperature_from_ipmi(self) -> float:
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

    async def _get_fan_speed_from_ipmi(self) -> int:
        """
        获取R730风扇转速（RPM）
        使用批量获取所有6个风扇传感器，返回平均转速
        """
        fan_sensors = ['Fan1', 'Fan2', 'Fan3', 'Fan4', 'Fan5', 'Fan6']
        
        try:
            # 批量获取所有风扇传感器
            sensor_data = await self._run_ipmi_command('sensor', 'get', *fan_sensors)
            if not sensor_data:
                logger.warning(f"Failed to get fan speed data for server {self.server.name}")
                return -1
            
            # 解析风扇转速
            fan_speeds = []
            current_sensor = None
            
            for line in sensor_data.splitlines():
                line = line.strip()
                
                # 查找传感器ID行
                if line.startswith('Sensor ID') and 'Fan' in line:
                    # 提取传感器名称，如 "Fan1 (0x30)"
                    sensor_match = re.search(r'Fan\d+', line)
                    if sensor_match:
                        current_sensor = sensor_match.group(0)
                
                # 查找传感器读数行
                elif line.startswith('Sensor Reading') and current_sensor:
                    # 提取RPM值，格式如 "3720 (+/- 120) RPM"
                    rpm_match = re.search(r'(\d+)\s*\(\+/-\s*\d+\)\s*RPM', line)
                    if rpm_match:
                        rpm = int(rpm_match.group(1))
                        fan_speeds.append(rpm)
                        logger.debug(f"Found fan speed for {current_sensor}: {rpm} RPM")
                        current_sensor = None  # 重置当前传感器
            
            if fan_speeds:
                # 计算平均转速并取整数
                avg_speed = int(sum(fan_speeds) / len(fan_speeds))
                logger.info(f"Retrieved fan speeds for {self.server.name}: {fan_speeds}, average: {avg_speed} RPM")
                return avg_speed
            else:
                logger.warning(f"No valid fan speed readings found for server {self.server.name}")
                return -1
                
        except Exception as e:
            logger.error(f"Error getting fan speed for server {self.server.name}: {e}", exc_info=True)
            return -1

    async def set_fan_speed(self, speed: int):
        if 0 <= speed <= 100:
            hex_speed = hex(int(speed))
            await self._run_ipmi_command('raw', '0x30', '0x30', '0x02', '0xff', hex_speed)
            logger.info(f"Set fan speed to {speed}% for server {self.server.name}")
        else:
            logger.error(f"Invalid fan speed value: {speed}. Must be between 0 and 100.")

    async def take_over_fan_control(self):
        await self._run_ipmi_command('raw', '0x30', '0x30', '0x01', '0x00')
        logger.info(f"Took over fan control for server {self.server.name} (set to manual).")

    async def return_fan_control_to_system(self):
        await self._run_ipmi_command('raw', '0x30', '0x30', '0x01', '0x01')
        logger.info(f"Returned fan control to system for server {self.server.name} (set to auto).")
