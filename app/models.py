import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    JSON,
)
from sqlalchemy.orm import relationship
from .database import Base
import pytz


class Server(Base):
    __tablename__ = "servers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    model = Column(String, nullable=False)
    ipmi_host = Column(String, nullable=False)
    ipmi_username = Column(String, nullable=False)
    ipmi_password = Column(String, nullable=False)
    control_mode = Column(String, default="auto", nullable=False)
    manual_fan_speed = Column(Integer, nullable=True)

    fan_curves = relationship("FanCurve", back_populates="server", cascade="all, delete-orphan")
    temp_history = relationship("TemperatureHistory", back_populates="server", cascade="all, delete-orphan")
    fan_speed_history = relationship("FanSpeedHistory", back_populates="server", cascade="all, delete-orphan")


class FanCurve(Base):
    __tablename__ = "fan_curves"

    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=False)
    points = Column(JSON, nullable=False)

    server = relationship("Server", back_populates="fan_curves")


def get_local_time():
    """获取本地时间（上海时区）"""
    shanghai_tz = pytz.timezone('Asia/Shanghai')
    return datetime.datetime.now(shanghai_tz)

class TemperatureHistory(Base):
    __tablename__ = "temperature_history"

    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=False)
    temperature = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=get_local_time, nullable=False)

    server = relationship("Server", back_populates="temp_history")


class FanSpeedHistory(Base):
    __tablename__ = "fan_speed_history"

    id = Column(Integer, primary_key=True, index=True)
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=False)
    average_speed_rpm = Column(Integer, nullable=False)
    timestamp = Column(DateTime, default=get_local_time, nullable=False)

    server = relationship("Server", back_populates="fan_speed_history")