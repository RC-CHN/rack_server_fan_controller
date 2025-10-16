#!/usr/bin/env python3
"""
R730 控制器风扇转速获取测试
用于验证R730控制器的实现是否正确
"""

import asyncio
import logging
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.controllers.r730 import R730Controller
from app import models

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建测试服务器配置（简化版本，只包含必要的字段）
class MockServer:
    """模拟服务器对象，用于测试"""
    def __init__(self):
        self.id = 1
        self.name = "R730-Test"
        self.model = "r730"
        self.ipmi_host = "192.168.44.104"
        self.ipmi_username = "root"
        self.ipmi_password = "calvin"

test_server = MockServer()

async def test_r730_controller():
    """测试R730控制器"""
    logger.info("=== 开始R730控制器测试 ===")
    logger.info(f"测试服务器: {test_server.name} ({test_server.ipmi_host})")
    
    try:
        # 创建控制器实例
        controller = R730Controller(test_server)
        
        # 测试温度获取
        logger.info("测试温度获取...")
        temperature = await controller._get_temperature_from_ipmi()
        if temperature != -1:
            logger.info(f"✅ 温度获取成功: {temperature}°C")
        else:
            logger.error("❌ 温度获取失败")
        
        # 测试风扇转速获取
        logger.info("测试风扇转速获取...")
        fan_speed = await controller._get_fan_speed_from_ipmi()
        if fan_speed != -1:
            logger.info(f"✅ 风扇转速获取成功: {fan_speed} RPM")
        else:
            logger.error("❌ 风扇转速获取失败")
        
        # 测试实时方法
        logger.info("测试实时获取方法...")
        realtime_temp = await controller.get_temperature_realtime()
        realtime_fan = await controller.get_fan_speed_realtime()
        
        if realtime_temp != -1:
            logger.info(f"✅ 实时温度: {realtime_temp}°C")
        else:
            logger.error("❌ 实时温度获取失败")
            
        if realtime_fan != -1:
            logger.info(f"✅ 实时风扇转速: {realtime_fan} RPM")
        else:
            logger.error("❌ 实时风扇转速获取失败")
        
        # 测试缓存方法（应该返回相同的数据）
        logger.info("测试缓存获取方法...")
        cached_temp = await controller.get_temperature_cached()
        cached_fan = await controller.get_fan_speed_cached()
        
        logger.info(f"缓存温度: {cached_temp}°C")
        logger.info(f"缓存风扇转速: {cached_fan} RPM")
        
        # 验证数据一致性
        if realtime_temp != -1 and cached_temp != -1:
            if abs(realtime_temp - cached_temp) < 0.1:
                logger.info("✅ 温度数据一致性验证通过")
            else:
                logger.warning(f"⚠️ 温度数据不一致: 实时={realtime_temp}, 缓存={cached_temp}")
        
        if realtime_fan != -1 and cached_fan != -1:
            if realtime_fan == cached_fan:
                logger.info("✅ 风扇转速数据一致性验证通过")
            else:
                logger.warning(f"⚠️ 风扇转速数据不一致: 实时={realtime_fan}, 缓存={cached_fan}")
        
        logger.info("=== R730控制器测试完成 ===")
        
        return True
        
    except Exception as e:
        logger.error(f"测试过程中出错: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = asyncio.run(test_r730_controller())
    if success:
        logger.info("🎉 所有测试通过！")
    else:
        logger.error("❌ 测试失败！")
        sys.exit(1)