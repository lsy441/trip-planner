# 智能旅行助手 - 部署指南

## 快速部署 (推荐)

### 1. 准备工作

确保已安装：
- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

### 2. 配置环境变量

```bash
# 复制配置文件
cp .env.example .env

# 编辑 .env 文件，填入你的API Key
vim .env
```

需要配置的项：
- `AMAP_API_KEY` - 高德地图API Key ([申请地址](https://lbs.amap.com/))
- `LLM_API_KEY` - 大模型API Key (OpenAI/智谱AI等)
- `LLM_BASE_URL` - 大模型API地址
- `LLM_MODEL_ID` - 模型ID

### 3. 执行部署

**Linux/Mac:**
```bash
chmod +x deploy.sh
./deploy.sh
```

**Windows:**
```powershell
.\deploy.ps1
```

或手动执行：
```bash
docker-compose up -d
```

### 4. 访问服务

- 前端界面: http://localhost
- 后端API: http://localhost:8000
- API文档: http://localhost:8000/docs

---

## 手动部署

### 后端部署

```bash
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入配置

# 启动服务
python run.py
```

### 前端部署

```bash
cd frontend

# 安装依赖
npm install

# 开发模式
npm run dev

# 生产构建
npm run build
```

---

## 常用命令

```bash
# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 重新构建并启动
docker-compose up -d --build

# 查看容器状态
docker-compose ps
```

---

## 架构说明

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Nginx     │────▶│  Frontend   │────▶│   Backend   │
│   (80)      │     │   (Vue3)    │     │  (FastAPI)  │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                                │
                                       ┌────────▼────────┐
                                       │  LangGraph      │
                                       │  Workflow       │
                                       └────────┬────────┘
                                                │
                          ┌─────────────────────┼─────────────────────┐
                          ▼                     ▼                     ▼
                   ┌─────────────┐      ┌─────────────┐      ┌─────────────┐
                   │  高德API    │      │   LLM API   │      │   Redis     │
                   └─────────────┘      └─────────────┘      └─────────────┘
```

---

## 故障排查

### 容器启动失败

```bash
# 查看详细日志
docker-compose logs backend
docker-compose logs frontend
```

### API Key 错误

检查 `.env` 文件是否正确配置，确保没有使用 `your_xxx` 占位符。

### 端口被占用

修改 `docker-compose.yml` 中的端口映射：
```yaml
ports:
  - "8080:80"  # 前端改为8080
  - "8001:8000"  # 后端改为8001
```

---

## 生产环境建议

1. **使用HTTPS**: 配置Nginx SSL证书
2. **限制CORS**: 修改 `backend/app/config.py` 中的 `cors_origins`
3. **日志轮转**: 配置Docker日志驱动
4. **监控告警**: 接入Prometheus/Grafana
5. **备份策略**: 定期备份Redis数据
