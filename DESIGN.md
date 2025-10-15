# 机架服务器风扇控制工具 - 后端设计文档

## 1. 简介

本文档旨在为机架服务器风扇控制工具的后端服务提供详细的设计规范。

该工具旨在通过 IPMI 协议集中管理多台不同型号的机架式服务器，提供统一的 API 接口用于监控温度和调整风扇策略。

### 1.1. 技术选型

- **语言**: Python 3.9+
- **Web 框架**: FastAPI
- **数据库**: SQLite
- **ORM**: SQLAlchemy (异步模式)
- **后台任务**: APScheduler (或 FastAPI 的 `BackgroundTasks`)

## 2. 系统架构

```mermaid
graph TD
    subgraph "用户/客户端"
        A[API 请求 <br> e.g., POST /servers]
    end

    subgraph "后端应用 (FastAPI + SQLAlchemy)"
        B[API Endpoints]
        C[业务逻辑 <br> Server Management]
        D[数据库 ORM <br> (SQLAlchemy)]
        DB[(SQLite Database <br> app.db)]
    end

    subgraph "服务器控制抽象层"
        E{Controller 工厂}
        F[BaseServerController <br> (抽象接口)]
        G[R730Controller <br> (具体实现)]
        H[OtherController <br> (未来扩展)]
    end

    subgraph "物理服务器"
        I[服务器1 (R730)]
        J[服务器2 (Other)]
    end

    A --> B
    B --> C
    C --> D
    D <--> DB
    C --> E
    E -- "根据服务器型号" --> G
    E -- "根据服务器型号" --> H
    F <|-- G
    F <|-- H
    G -- "ipmitool" --> I
    H -- "ipmitool" --> J
```

## 3. 项目文件结构

```
/
|-- app/
|   |-- __init__.py
|   |-- main.py             # FastAPI 应用入口, 组织 API 路由
|   |-- crud.py             # 数据库 CRUD 操作函数
|   |-- models.py           # SQLAlchemy 数据库模型 (表结构)
|   |-- schemas.py          # Pydantic 数据模型 (用于 API 数据校验和响应)
|   |-- database.py         # 数据库连接和会话管理
|   |-- controllers/
|   |   |-- __init__.py
|   |   |-- base.py         # 定义 BaseServerController 抽象基类
|   |   |-- r730.py         # R730 型号的具体实现
|   |   `-- factory.py      # Controller 工厂, 根据型号创建对应实例
|   |-- services/
|   |   |-- __init__.py
|   |   `-- scheduler.py    # 后台任务调度器 (记录温度、自动控制风扇)
|   `-- api/
|       |-- __init__.py
|       |-- servers.py      # 服务器管理相关的 API Endpoints
|       `-- control.py      # 风扇和温度控制相关的 API Endpoints
|-- .gitignore
|-- requirements.txt
`-- DESIGN.md
```

## 4. 数据库设计 (SQLAlchemy 模型)

我们将使用 SQLAlchemy ORM 来定义数据模型。

### 4.1. `servers` 表

存储服务器的基本信息和控制状态。

- **模型**: `Server`
- **字段**:
    - `id`: `Integer`, 主键, 自增
    - `name`: `String`, 服务器别名, 唯一
    - `model`: `String`, 服务器型号 (e.g., "R730"), 用于匹配 Controller
    - `ipmi_host`: `String`, IPMI 地址
    - `ipmi_username`: `String`, IPMI 用户名
    - `ipmi_password`: `String`, IPMI 密码 (注: 初始版本明文存储, 后续可考虑加密)
    - `control_mode`: `String`, 控制模式, "auto" 或 "manual", 默认为 "auto"
    - `manual_fan_speed`: `Integer`, 手动模式下的风扇转速 (0-100), 可为空

### 4.2. `fan_curves` 表

存储用于自动模式的风扇温度曲线。

- **模型**: `FanCurve`
- **字段**:
    - `id`: `Integer`, 主键, 自增
    - `server_id`: `Integer`, 外键, 关联 `servers.id`
    - `points`: `JSON`, 存储曲线点位, 格式为 `[{"temp": 40, "speed": 20}, {"temp": 60, "speed": 80}]`

### 4.3. `temperature_history` 表

存储服务器的历史温度数据。

- **模型**: `TemperatureHistory`
- **字段**:
    - `id`: `Integer`, 主键, 自增
    - `server_id`: `Integer`, 外键, 关联 `servers.id`
    - `temperature`: `Float`, 温度读数
    - `timestamp`: `DateTime`, 记录时间戳, 自动生成

### 4.4. `fan_speed_history` 表

存储服务器的历史平均风扇转速数据。

- **模型**: `FanSpeedHistory`
- **字段**:
    - `id`: `Integer`, 主键, 自增
    - `server_id`: `Integer`, 外键, 关联 `servers.id`
    - `average_speed_rpm`: `Integer`, 平均风扇转速 (RPM)
    - `timestamp`: `DateTime`, 记录时间戳, 自动生成

## 5. API 接口定义

所有 API 均以 `/api/v1` 为前缀。

### 5.1. 服务器管理 (`/api/v1/servers`)

- **`POST /`**: 添加一台新服务器
    - **请求体**: `schemas.ServerCreate` (包含 name, model, ipmi_host, ipmi_username, ipmi_password)
    - **响应**: `schemas.Server` (包含创建后的服务器信息, 不含密码)
- **`GET /`**: 获取所有服务器列表
    - **响应**: `List[schemas.Server]`
- **`GET /{server_id}`**: 获取指定服务器的详细信息
    - **响应**: `schemas.Server`
- **`PUT /{server_id}`**: 更新服务器信息
    - **请求体**: `schemas.ServerUpdate` (可更新部分字段)
    - **响应**: `schemas.Server`
- **`DELETE /{server_id}`**: 删除一台服务器
    - **响应**: `{"message": "Server deleted successfully"}`

### 5.2. 状态与控制 (`/api/v1/control`)

- **`GET /{server_id}/temperature`**: 获取服务器用于风扇控制的**决策温度** (例如，多路CPU中的最高温或平均温)。
    - **响应**: `{"server_id": 1, "temperature": 45.5}`
- **`GET /{server_id}/sensors`**: (可选实现) 获取服务器所有原始传感器读数，用于详细诊断。
    - **响应**: `{"server_id": 1, "sensors": [{"name": "CPU1 Temp", "value": 45.0, "unit": "C"}, ...]}`
- **`GET /{server_id}/fan/speed`**: 获取服务器当前平均风扇转速
    - **响应**: `{"server_id": 1, "average_speed_rpm": 3000}`
- **`POST /{server_id}/fan/manual`**: 设置服务器为手动风扇控制模式
    - **请求体**: `{"speed": 50}` (0-100)
    - **响应**: `{"message": "Fan speed set to 50%"}`
- **`POST /{server_id}/fan/auto`**: 设置服务器为自动风扇控制模式, 并更新其温度曲线
    - **请求体**: `{"points": [{"temp": 40, "speed": 20}, ...]`
    - **响应**: `{"message": "Fan control set to auto with updated curve"}`
- **`GET /{server_id}/fan/config`**: 获取服务器当前的完整风扇配置
    - **响应**: `{"server_id": 1, "mode": "auto", "curve": {"points": [...]}}` 或 `{"server_id": 1, "mode": "manual", "speed": 50}`

### 5.3. 历史数据 (`/api/v1/history`)

- **`GET /{server_id}/temperature`**: 获取指定服务器的历史温度数据
    - **查询参数**: `start_date` (ISO 格式), `end_date` (ISO 格式)
    - **响应**: `List[schemas.TemperatureHistory]`
- **`GET /{server_id}/fan-speed`**: 获取指定服务器的历史平均风扇转速数据
    - **查询参数**: `start_date` (ISO 格式), `end_date` (ISO 格式)
    - **响应**: `List[schemas.FanSpeedHistory]`

## 6. 核心组件设计

### 6.1. Controller 抽象层

- **`app/controllers/base.py`**: 定义 `BaseServerController` 抽象类, 包含以下必须被子类实现的方法:
    - `async def get_temperature(self) -> float`: 获取用于风扇控制的**决策温度**。具体实现应处理好多路CPU等情况（如取最高温或平均温），向上层返回单一浮点数。
    - `async def get_fan_speed(self) -> int`
    - `async def get_all_sensors(self) -> list[dict]`: (可选实现) 获取所有传感器的原始读数。
    - `async def set_fan_speed(self, speed: int)`
    - `async def set_manual_fan_control(self)`
    - `async def set_auto_fan_control(self)`
- **`app/controllers/r730.py`**: `R730Controller` 类继承 `BaseServerController`, 使用 `asyncio.create_subprocess_exec` 执行 `ipmitool` 命令, 实现上述方法。
- **`app/controllers/factory.py`**: 提供一个函数 `get_controller(server: models.Server) -> BaseServerController`, 根据 `server.model` 字段返回对应的 Controller 实例。

### 6.2. 后台任务调度器

- **`app/services/scheduler.py`**:
    - **任务1: 记录数据**: 定期 (e.g., 每分钟) 遍历所有服务器, 调用其 Controller 的 `get_temperature` 和 `get_fan_speed` 方法, 并将结果分别存入 `temperature_history` 和 `fan_speed_history` 表。
    - **任务2: 自动风扇控制**: 定期 (e.g., 每 10 秒) 遍历所有处于 "auto" 模式的服务器, 获取当前温度, 根据其风扇曲线计算目标转速, 并调用 `set_fan_speed` 方法。