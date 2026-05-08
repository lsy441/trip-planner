# LangChain + LangGraph 多智能体旅行规划系统 🌍✈️

基于 **LangChain 1.2 + LangGraph 1.1** 构建的智能旅行规划系统，采用多 Agent 协作架构，支持对话驱动的行程规划与智能调整。

---

## ✨ 核心功能

### 1. 智能行程规划
- **多 Agent 并行协作**：父 Agent 统筹调度，6 个专业子 Agent（景点/天气/酒店/交通/美食/地图）并行执行
- **Plan-Execute-Replan 工作流**：LangGraph 驱动的三阶段循环，支持任务分解→并行执行→结果整合
- **真实数据支撑**：集成高德地图 API，获取实时景点、天气、酒店信息

### 2. AI 对话助手
- **意图识别引擎**：自动识别用户需求，支持表单自动填充、页面跳转、行程调整
- **多轮对话**：上下文感知，支持追问和澄清
- **联动动作**：对话触发实际功能（如"帮我生成"→自动跳转结果页）

### 3. 智能调整机制
- **局部优化**：用户可对已生成计划提出修改（如"酒店太贵"），AI 仅调整目标部分
- **增量更新**：基于反馈增量优化，而非全量重生成
- **对话驱动**：通过自然语言描述调整需求

### 4. 工程优化
- **消息压缩**：Token 截断 + LLM 摘要，控制多轮对话上下文长度
- **智能缓存**：基于请求参数 MD5 缓存，相同查询复用历史结果
- **降级策略**：MCP 协议失败时自动降级为直接 API 调用

---

## 🏗️ 技术架构

### 后端技术栈
| 技术 | 版本 | 用途 |
|------|------|------|
| **Python** | 3.10+ | 主开发语言 |
| **FastAPI** | 0.115+ | Web 框架，RESTful API |
| **LangChain** | 1.2.15 | LLM 编排框架 |
| **LangGraph** | 1.1.8 | 有状态多步工作流 |
| **Pydantic** | v2 | 数据模型校验 |
| **Redis** | - | 会话存储、结果缓存 |
| **高德地图 API** | - | POI 搜索、天气、路线规划 |

### 前端技术栈
| 技术 | 版本 | 用途 |
|------|------|------|
| **Vue 3** | 3.4+ | 前端框架（Composition API） |
| **TypeScript** | 5.0+ | 类型安全 |
| **Vite** | 6.x | 构建工具 |
| **Ant Design Vue** | 4.x | UI 组件库 |
| **Axios** | - | HTTP 客户端 |

---

## 📁 项目结构

```
.
├── backend/                        # 后端服务
│   ├── app/
│   │   ├── agents/                 # 多智能体实现
│   │   │   ├── agents.py           # Agent 定义与创建
│   │   │   ├── tools.py            # 工具函数（高德 API 集成）
│   │   │   ├── nodes.py            # 工作流节点函数
│   │   │   ├── state.py            # 状态定义和缓存系统
│   │   │   ├── react_agent.py      # ReAct 智能体
│   │   │   └── trip_planner_langgraph.py  # LangGraph 工作流编排
│   │   ├── api/
│   │   │   ├── main.py             # FastAPI 应用入口
│   │   │   └── routes/
│   │   │       ├── trip.py         # 行程规划 API
│   │   │       ├── chat.py         # 智能对话 API
│   │   │       └── poi.py          # POI 相关 API
│   │   ├── mcp/                    # MCP 客户端
│   │   │   ├── client.py           # MCP 协议实现
│   │   │   └── cache.py            # MCP 缓存系统
│   │   ├── memory/
│   │   │   └── compressor.py       # 消息压缩器
│   │   └── services/
│   │       ├── observability.py    # 可观测性监控
│   │       ├── redis_session.py    # Redis 会话管理
│   │       └── unsplash_service.py # 图片服务
│   ├── tests/                      # 单元测试
│   ├── Dockerfile                  # 后端 Docker 镜像
│   ├── requirements.txt
│   └── run.py
├── frontend/                       # 前端应用
│   ├── src/
│   │   ├── components/
│   │   │   └── ChatWidget.vue      # 智能对话组件
│   │   ├── services/
│   │   │   └── api.ts              # API 封装
│   │   ├── views/
│   │   │   ├── Home.vue            # 首页
│   │   │   └── Result.vue          # 结果页
│   │   └── App.vue
│   ├── Dockerfile                  # 前端 Docker 镜像
│   ├── nginx.conf                  # Nginx 配置
│   └── package.json
├── docker-compose.yml              # Docker Compose 编排
├── deploy.sh                       # Linux/Mac 部署脚本
├── deploy.ps1                      # Windows 部署脚本
├── DEPLOY.md                       # 部署文档
└── README.md
```

---

## 🚀 快速开始

### 方式一：Docker 部署（推荐）

#### 环境要求
- Docker
- Docker Compose

#### 部署步骤

1. **配置环境变量**
```bash
cp .env.example .env
# 编辑 .env 填入你的 API Key
```

2. **执行部署**
```bash
# Linux/Mac
chmod +x deploy.sh
./deploy.sh

# Windows
.\deploy.ps1
```

或手动：
```bash
docker-compose up -d
```

3. **访问服务**
- 前端界面: http://localhost
- 后端API: http://localhost:8000
- API文档: http://localhost:8000/docs

### 方式二：本地开发

#### 后端
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

#### 前端
```bash
cd frontend
npm install
npm run dev
```

---

## ⚙️ 配置说明

### 必需配置
| 配置项 | 说明 | 获取地址 |
|--------|------|----------|
| `AMAP_API_KEY` | 高德地图 API Key | https://lbs.amap.com |
| `LLM_API_KEY` | 大模型 API Key | DeepSeek/OpenAI/智谱AI |
| `LLM_BASE_URL` | 大模型 API 地址 | 根据服务商填写 |

### 可选配置
| 配置项 | 说明 |
|--------|------|
| `UNSPLASH_ACCESS_KEY` | Unsplash 图片 API |
| `REDIS_URL` | Redis 连接地址 |

---

## 🧪 运行测试

```bash
cd backend
python -m pytest tests/ -v
```

---

## 📄 许可证

MIT License

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！
