from contextlib import asynccontextmanager
from fastapi import FastAPI
from .database import engine, Base
from .services.scheduler import scheduler

# 创建所有数据库表
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 应用启动时执行
    await create_tables()
    scheduler.start()
    print("--- Scheduler started and tables created ---")
    yield
    # 应用关闭时执行
    scheduler.shutdown()
    print("--- Scheduler stopped ---")


app = FastAPI(
    title="Rack Server Fan Controller",
    description="一个通过IPMI控制机架服务器风扇转速的工具",
    version="0.1.0",
    lifespan=lifespan,
)

@app.get("/")
async def read_root():
    return {"message": "Welcome to the Rack Server Fan Controller API"}

# 引入 API 路由
from .api import servers, control

app.include_router(servers.router, prefix="/api/v1/servers", tags=["Servers"])
app.include_router(control.router, prefix="/api/v1/control", tags=["Control"])