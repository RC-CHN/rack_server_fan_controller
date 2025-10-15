from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

# 数据库文件的路径
DATABASE_URL = "sqlite+aiosqlite:///./app.db"

# 创建异步数据库引擎
# connect_args={"check_same_thread": False} 是 SQLite 特有的配置，
# 用于在 FastAPI 的异步环境中允许多个线程访问同一个连接。
engine = create_async_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

# 创建一个异步会話工厂
# expire_on_commit=False 防止在提交后 SQLAlchemy 对象过期
AsyncSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine, class_=AsyncSession, expire_on_commit=False
)

# 创建一个 ORM 模型基类
Base = declarative_base()

# 依赖注入函数，用于在 API 路由中获取数据库会话
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session