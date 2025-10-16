# Docker 部署指南

## 快速开始

### 1. 构建和启动服务
```bash
# 构建并启动所有服务
docker compose up -d

# 查看服务状态
docker compose ps

# 查看日志
docker compose logs -f

# 停止服务
docker compose down
```

### 2. 访问应用
- 前端界面: http://localhost
- API 文档: http://localhost/api/docs (通过前端nginx代理)

### 3. 数据持久化
应用数据会持久化到 Docker volume `app-data` 中，即使容器删除数据也不会丢失。

## 构建说明

### 后端服务 (backend)
- 基于 Python 3.11 slim 镜像
- 包含 ipmitool 工具
- 运行在端口 8000
- 数据库存储在 `/app/data/app.db`

### 前端服务 (frontend)
- 基于 Node.js 22 构建，使用 Nginx 提供服务
- 构建时自动编译 Vue.js 应用
- 通过 Nginx 反向代理 API 请求到后端
- 运行在端口 80

## 文件结构
```
.
├── Dockerfile.backend      # 后端Dockerfile
├── Dockerfile.frontend     # 前端Dockerfile
├── docker-compose.yml      # Docker Compose配置
├── nginx.conf             # Nginx配置
├── .dockerignore          # Docker构建忽略文件
└── README.docker.md       # 本文件
```

## 注意事项
- 确保系统已安装 Docker 和 Docker Compose
- 首次构建可能需要一些时间，请耐心等待
- 数据会自动持久化，重启容器不会丢失数据
- 如需修改端口，请编辑 docker-compose.yml 文件

## 常用命令
```bash
# 重新构建服务
docker compose build

# 只构建后端
docker compose build backend

# 只构建前端
docker compose build frontend

# 查看容器日志
docker compose logs backend
docker compose logs frontend

# 进入容器内部
docker compose exec backend bash
docker compose exec frontend sh