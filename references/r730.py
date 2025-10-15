import subprocess
import os
import json
import time

# 从环境变量读取配置信息
IPMI_HOST = os.getenv('IPMI_HOST')
IPMI_USERNAME = os.getenv('IPMI_USERNAME')
IPMI_PASSWORD = os.getenv('IPMI_PASSWORD')

# 从环境变量读取风扇曲线（JSON字符串），并解析为Python对象
FAN_CURVE_JSON = os.getenv('FAN_CURVE')

if not all([IPMI_HOST, IPMI_USERNAME, IPMI_PASSWORD, FAN_CURVE_JSON]):
    print("Missing required environment variables. Please set IPMI_HOST, IPMI_USERNAME, IPMI_PASSWORD, and FAN_CURVE.")
    exit(1)

try:
    FAN_CURVE = json.loads(FAN_CURVE_JSON)
except json.JSONDecodeError:
    print("Invalid FAN_CURVE JSON format.")
    exit(1)

def get_ipmi_sensor_data():
    try:
        result = subprocess.check_output([
            'ipmitool', '-I', 'lanplus', '-H', IPMI_HOST, '-U', IPMI_USERNAME, '-P', IPMI_PASSWORD, 'sensor'
        ]).decode('utf-8')
        #print(result)
        return result
    except subprocess.CalledProcessError as e:
        print(f"Error executing IPMI command: {e}")
        return None

def parse_temperature(sensor_data):
    # 解析温度，只提取 CPU 的两个 "Temp" 行的温度值
    temperatures = []
    for line in sensor_data.splitlines():
        # 只选择名称是 "Temp" 且不包括 "Inlet Temp" 和 "Exhaust Temp" 的行
        if "Temp" in line and "degrees C" in line and "Inlet Temp" not in line and "Exhaust Temp" not in line:
            try:
                # 提取温度值，假设温度值是第二个字段
                temp_value = float(line.split('|')[1].strip())
                temperatures.append(temp_value)
            except (ValueError, IndexError):
                continue

    # 如果找到了温度值，计算平均值
    if temperatures:
        average_temp = sum(temperatures) / len(temperatures)
        print(f"Average CPU temperature calculated from sensors: {average_temp} °C")
        return average_temp
    else:
        print("No valid CPU temperature readings found.")
        return None

def set_fan_speed(speed):
    if 0 <= speed <= 100:
        # 将百分比转换为 IPMI 的十六进制值 (0x00 - 0x64)
        hex_speed = hex(int(speed))  # 转换为十六进制字符串
        cmd = [
            'ipmitool', '-I', 'lanplus', '-H', IPMI_HOST, '-U', IPMI_USERNAME, '-P', IPMI_PASSWORD,
            'raw', '0x30', '0x30', '0x02', '0xff', hex_speed
        ]
        print(f"Setting fan speed to {speed}% using command: {cmd}")
        try:
            subprocess.call(cmd)
            print("Fan speed set successfully.")
            return True
        except Exception as e:
            print(f"Error setting fan speed: {e}")
            return False
    else:
        print(f"Invalid fan speed value: {speed}. Must be between 0 and 100.")
        return False

def set_manual_fan_mode():
    cmd = [
        'ipmitool', '-I', 'lanplus', '-H', IPMI_HOST, '-U', IPMI_USERNAME, '-P', IPMI_PASSWORD,
        'raw', '0x30', '0x30', '0x01', '0x00'
    ]
    print(f"Setting fan mode to manual using command: {cmd}")
    try:
        subprocess.call(cmd)
        print("Fan mode set to manual successfully.")
    except Exception as e:
        print(f"Error setting fan mode to manual: {e}")

def calculate_fan_speed(temperature):
    # 根据温度找到最适合的风扇速度
    for i in range(len(FAN_CURVE) - 1):
        temp1, speed1 = FAN_CURVE[i]["temp"], FAN_CURVE[i]["speed"]
        temp2, speed2 = FAN_CURVE[i + 1]["temp"], FAN_CURVE[i + 1]["speed"]
        if temp1 <= temperature < temp2:
            # 插值计算风扇速度
            return speed1 + (speed2 - speed1) * (temperature - temp1) / (temp2 - temp1)
    # 超过定义的最大温度时，使用最后一个节点的风扇速度
    return FAN_CURVE[-1]["speed"]

def main():
    print("Starting IPMI fan control...")
    set_manual_fan_mode()
    while True:
        sensor_data = get_ipmi_sensor_data()
        if sensor_data:
            temperature = parse_temperature(sensor_data)
            if temperature is not None:
                print(f"Current temperature: {temperature} °C")
                target_speed = calculate_fan_speed(temperature)
                print(f"Calculated target fan speed: {target_speed}%")
                set_fan_speed(target_speed)
            else:
                print("Could not parse temperature from IPMI data.")
        else:
            print("Failed to retrieve sensor data.")
        
        time.sleep(5)  # 每5秒获取一次数据并调整风扇速度

if __name__ == '__main__':
    main()