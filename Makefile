# NewAPI Monitor Makefile

.PHONY: help build up down logs clean install dev test

# 默认目标
help:
	@echo "NewAPI Monitor 项目管理命令："
	@echo ""
	@echo "  build     构建所有Docker镜像"
	@echo "  up        启动所有服务"
	@echo "  down      停止所有服务"
	@echo "  logs      查看服务日志"
	@echo "  clean     清理Docker资源"
	@echo "  install   安装开发依赖"
	@echo "  dev       启动开发环境"
	@echo "  test      运行测试"
	@echo "  db-init   初始化数据库"
	@echo ""

# 构建Docker镜像
build:
	docker-compose build

# 启动服务
up:
	docker-compose up -d

# 停止服务
down:
	docker-compose down

# 查看日志
logs:
	docker-compose logs -f

# 清理Docker资源
clean:
	docker-compose down -v
	docker system prune -f

# 安装开发依赖
install:
	@echo "安装后端依赖..."
	cd api && pip install -r requirements.txt
	cd worker && pip install -r requirements.txt
	@echo "安装前端依赖..."
	cd frontend && npm install

# 启动开发环境
dev:
	@echo "启动开发环境..."
	@echo "请确保已配置 .env 文件"
	@echo "后端API: http://localhost:8080"
	@echo "前端: http://localhost:3000"

# 运行测试
test:
	@echo "运行测试..."
	# TODO: 添加测试命令

# 初始化数据库
db-init:
	@echo "初始化数据库..."
	@echo "请手动执行: mysql -h your-host -u root -p < scripts/db_optimization.sql"

# 检查服务状态
status:
	docker-compose ps

# 重启服务
restart:
	docker-compose restart

# 查看特定服务日志
logs-api:
	docker-compose logs -f api

logs-worker:
	docker-compose logs -f worker

logs-frontend:
	docker-compose logs -f frontend

logs-redis:
	docker-compose logs -f redis
