from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import datetime

# ====================
# 基础模型
# ====================

class FanCurvePoint(BaseModel):
    temp: float
    speed: int

class FanCurveBase(BaseModel):
    points: List[FanCurvePoint]

class FanCurveCreate(FanCurveBase):
    pass

class FanCurve(FanCurveBase):
    id: int
    server_id: int

    class Config:
        orm_mode = True

class ServerBase(BaseModel):
    name: str
    model: str
    ipmi_host: str
    ipmi_username: str

class ServerCreate(ServerBase):
    ipmi_password: str

class ServerUpdate(ServerBase):
    name: Optional[str] = None
    model: Optional[str] = None
    ipmi_host: Optional[str] = None
    ipmi_username: Optional[str] = None
    ipmi_password: Optional[str] = None
    control_mode: Optional[str] = None
    manual_fan_speed: Optional[int] = None

class Server(ServerBase):
    id: int
    control_mode: str
    manual_fan_speed: Optional[int] = None
    fan_curves: List[FanCurve] = []

    class Config:
        orm_mode = True

# ====================
# API 响应模型
# ====================

class TemperatureReading(BaseModel):
    server_id: int
    temperature: float

class FanSpeedReading(BaseModel):
    server_id: int
    average_speed_rpm: int

class FanConfig(BaseModel):
    server_id: int
    mode: str
    curve: Optional[FanCurveBase] = None
    speed: Optional[int] = None

class TemperatureHistory(BaseModel):
    id: int
    server_id: int
    temperature: float
    timestamp: datetime.datetime

    class Config:
        orm_mode = True

class FanSpeedHistory(BaseModel):
    id: int
    server_id: int
    average_speed_rpm: int
    timestamp: datetime.datetime

    class Config:
        orm_mode = True