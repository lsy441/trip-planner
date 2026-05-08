# HelloAgents 智能旅行规划助手 🌍✈️

基于 **LangChain 1.2 + LangGraph 1.1** 构建的智能旅行规划系统，采用多 Agent 协作架构，支持对话驱动的行程规划与智能调整。

---

## ✨ 核心功能

### 1. 智能行程规划
- **多 Agent 并行协作**：父 Agent 统筹调度，6 个专业子 Agent（景点/天气/酒店/交通/美食/预算）并行执行
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
helloagents-trip-planner/
├── backend/                        # 后端服务
│   ├── app/
│   │   ├── agents/                 # 多智能体实现
│   │   │   ├── agents.py           # Agent 定义与创建
│   │   │   ├── tools.py            # 工具函数（高德 API 集成）
│   │   │   └── trip_planner_langgraph.py  # LangGraph 工作流编排
│   │   ├── api/
│   │   │   ├── main.py             # FastAPI 应用入口
│   │   │   └── routes/
│   │   │       ├── trip.py         # 行程规划 API
│   │   │       ├── chat.py         # 智能对话 API
│   │   │       └── poi.py          # POI 相关 API
│   │   ├── mcp/                    # MCP 客户端
│   │   │   └── client.py           # MCP 协议实现
│   │   ├── memory/
│   │   │   └── compressor.py       # 消息压缩器
│   │   └── services/
│   │       └── redis_session.py    # Redis 会话管理
│   ├── requirements.txt
│   └── .env.example
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
│   └── package.json
└── README.md
```

---

## 🚀 快速开始

### 环境要求
- Python 3.10+
- Node.js 18+
- Redis（可选，用于会话持久化）

### 1. 克隆项目
```bash
git clone <repository-url>
cd helloagents-trip-planner
```

### 2. 后端配置
```bash
cd backend

# 创建虚拟环境
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env，填入：
# - LLM_API_KEY（DeepSeek/OpenAI/通义千问）
# - AMAP_API_KEY（高德地图 Web 服务 Key）

# 启动服务
python -m uvicorn app.api.main:app --host 127.0.0.1 --port 8000
```

### 3. 前端配置
```bash
cd frontend

# 安装依赖
npm install

# 配置环境变量
cp .env.example .env
# 编辑 .env，填入：
# - VITE_AMAP_JS_KEY（高德地图 JS API Key）

# 启动开发服务器
npm run dev
```

### 4. 访问应用
打开浏览器访问 `http://localhost:5173`

---

## � 使用指南

### 创建旅行计划
1. **填写表单**：输入目的地、日期、偏好等信息
2. **对话辅助**：通过智能助手快速填写（如"我想去西安，喜欢历史"）
3. **生成计划**：点击生成或说"帮我规划"
4. **查看结果**：浏览每日行程、地图、预算明细

### 调整行程
- 在结果页与智能助手对话
- 示例指令：
  - "景点太多了，每天减少一些"
  - "换一家更便宜的酒店"
  - "全部要最贵的配置"

---

## 🔧 核心架构

### LangGraph 工作流
```
用户请求
    ↓
[Plan 节点] → 分析需求、分解任务
    ↓
[Execute 节点组] → 6 个 Agent 并行执行
    ↓
[Replan 节点] → 整合结果、生成行程
    ↓
旅行计划输出
```

### 多 Agent 协作
| Agent | 职责 | 工具 |
|-------|------|------|
| 景点 Agent | 搜索景点信息 | `search_attractions` |
| 天气 Agent | 获取天气预报 | `get_weather` |
| 酒店 Agent | 搜索酒店 | `search_hotels` |
| 交通 Agent | 路线规划 | `get_route` |
| 美食 Agent | 搜索餐厅 | `search_food` |
| 预算 Agent | 费用估算 | `calculate_budget` |

---

## 🎯 技术亮点

1. **Agent 架构设计**：父 Agent + 子 Agent 分层协作，支持复杂任务分解
2. **意图识别**：基于 LLM 的意图分类，实现对话驱动的产品功能
3. **工作流编排**：LangGraph 状态机管理 Plan-Execute-Replan 循环
4. **工程实践**：缓存、降级、压缩、会话管理等生产级优化

---

## 📝 面试相关

这个项目适合投递：
- **AI 应用工程师**
- **Python 后端开发**
- **Agent 开发工程师**
- **LLM 应用开发**

核心技术点：LangChain、LangGraph、多 Agent 协作、ReAct 推理、意图识别

---

## 📄 License

MIT License

---

## 🤝 贡献

欢迎提交 Issue 和 PR！
