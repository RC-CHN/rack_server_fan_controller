#!/usr/bin/env python3
"""
测试缓存机制的脚本
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import AsyncSessionLocal
from app import crud, crud_cache
from app.controllers.factory import get_controller
from datetime import datetime

async def test_cache_mechanism():
    """测试缓存机制"""
    print("=== 测试缓存机制 ===")
    
    async with AsyncSessionLocal() as db:
        # 获取第一个服务器
        servers = await crud.get_servers(db, limit=1)
        if not servers:
            print("没有找到服务器，请先添加服务器")
            return
        
        server = servers[0]
        print(f"测试服务器: {server.name} (ID: {server.id})")
        
        # 创建控制器
        controller = get_controller(server)
        
        print("\n1. 测试温度缓存机制:")
        
        # 第一次获取温度（应该触发IPMI命令）
        print("第一次获取温度...")
        temp1 = await controller.get_temperature()
        print(f"温度1: {temp1}°C")
        
        # 等待5秒
        await asyncio.sleep(5)
        
        # 第二次获取温度（应该使用缓存）
        print("第二次获取温度（5秒后，应该使用缓存）...")
        temp2 = await controller.get_temperature()
        print(f"温度2: {temp2}°C")
        
        # 验证缓存数据
        cached_temp = await crud_cache.get_latest_temperature(db, server.id, max_age_seconds=30)
        print(f"缓存中的温度: {cached_temp}°C")
        
        print("\n2. 测试风扇速度缓存机制:")
        
        # 第一次获取风扇速度
        print("第一次获取风扇速度...")
        fan1 = await controller.get_fan_speed()
        print(f"风扇速度1: {fan1} RPM")
        
        # 等待5秒
        await asyncio.sleep(5)
        
        # 第二次获取风扇速度（应该使用缓存）
        print("第二次获取风扇速度（5秒后，应该使用缓存）...")
        fan2 = await controller.get_fan_speed()
        print(f"风扇速度2: {fan2} RPM")
        
        # 验证缓存数据
        cached_fan = await crud_cache.get_latest_fan_speed(db, server.id, max_age_seconds=60)
        print(f"缓存中的风扇速度: {cached_fan} RPM")
        
        print("\n3. 测试数据库中的历史记录:")
        
        # 检查温度历史记录
        from datetime import datetime, timedelta
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(minutes=5)
        
        temp_history = await crud.get_temperature_history(db, server.id, start_time, end_time)
        print(f"温度历史记录数量: {len(temp_history)}")
        if temp_history:
            print(f"最新温度记录: {temp_history[-1].temperature}°C at {temp_history[-1].timestamp}")
        
        fan_history = await crud.get_fan_speed_history(db, server.id, start_time, end_time)
        print(f"风扇速度历史记录数量: {len(fan_history)}")
        if fan_history:
            print(f"最新风扇速度记录: {fan_history[-1].average_speed_rpm} RPM at {fan_history[-1].timestamp}")
        
        print("\n=== 测试完成 ===")

if __name__ == "__main__":
    asyncio.run(test_cache_mechanism())