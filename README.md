# StudyFlow AI - AI 刷题推荐系统

基于 Python 全栈的 AI 刷题管理工具，使用 FastAPI + LangChain + FAISS + DeepSeek 实现智能题目推荐和弱项分析。

## 技术栈

- **后端**: Python 3.13 + FastAPI
- **数据库**: MySQL 8.4 + SQLAlchemy
- **AI/LLM**: LangChain 1.x（create_agent + Function Calling）+ DeepSeek API
- **向量检索**: FAISS + sentence-transformers（中文模型 text2vec-base-chinese）
- **Agent**: 工具调用式 Agent，自带三个工具
- **记忆**: LangChain ChatMessageHistory 落地 MySQL，重启不丢

## 项目结构

```
studyflow-ai/
├── app/
│   ├── __init__.py          # 数据库连接配置
│   ├── models/
│   │   ├── problem.py       # 数据模型（Category, Problem）
│   │   ├── user.py          # 用户表
│   │   ├── chat.py          # 会话与消息表（记忆持久化）
│   │   └── error.py         # 错因归因表 + 六类错因枚举 + 字段校验
│   ├── routers/
│   │   ├── categories.py    # 知识点 API
│   │   ├── problems.py      # 题目 API（含语义搜索）
│   │   ├── recommend.py     # AI 推荐 API
│   │   ├── chat.py          # AI 对话 API（多轮记忆）
│   │   └── error.py         # 错因分类 API（决策树 + 统计）
│   ├── services/
│   │   ├── llm.py           # 统一 LLM 客户端
│   │   ├── memory.py        # LangChain 消息历史 -> MySQL
│   │   ├── recommend.py     # 推荐服务（RAG + PydanticOutputParser）
│   │   └── error.py         # 决策树推进、语言坑检测、统计口径
│   ├── rag/
│   │   ├── vector_store.py  # FAISS 向量库（持久化 + 增删改）
│   │   └── retriever.py     # 数据库 <-> 向量库同步、语义检索
│   └── agent/
│       ├── tools.py         # Agent 工具（检索/弱项分析/变体推荐）
│       └── analyzer.py      # create_agent 智能助手
├── data/                    # FAISS 索引与元数据落盘目录
├── .env                     # 环境变量（API Key 等）
├── main.py                  # FastAPI 入口
└── requirements.txt         # 依赖列表
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

编辑 `.env` 文件：

```env
DATABASE_URL=mysql+pymysql://root:你的密码@localhost:3306/studyflow_ai
DEEPSEEK_API_KEY=sk-你的 API Key
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
```

### 3. 创建数据库

```sql
CREATE DATABASE IF NOT EXISTS studyflow_ai DEFAULT CHARSET utf8mb4;
```

### 4. 启动服务

```bash
python main.py
```

访问 API 文档：http://localhost:8002/docs

## API 接口

### 知识点管理
- `GET /api/categories` - 获取所有知识点
- `POST /api/categories` - 创建知识点

### 题目管理
- `GET /api/problems` - 获取所有题目（支持 `?category_id=xxx` 过滤）
- `POST /api/problems/search` - **语义搜索**（向量相似度，body: `{query, top_k}`）
- `POST /api/problems` - 创建题目（自动 embedding 入库）
- `PUT /api/problems/{id}` - 更新题目（自动重新 embedding）
- `DELETE /api/problems/{id}` - 删除题目（自动从索引移除）

### AI 推荐
- `POST /api/recommend` - 根据母题推荐变体题（RAG 检索 + 结构化输出）

### AI 对话
- `POST /api/chat` - 多轮对话（Agent 自动选择工具，历史存库）
- `GET /api/chat/sessions` - 列出所有会话
- `GET /api/chat/sessions/{id}/messages` - 查看某次会话的全部消息
- `DELETE /api/chat/sessions/{id}` - 删除会话

### 错因分类

- `GET /api/errors/meta` - 六类错因、子标签、决策树、预置映射（`?topic=链表` 可过滤）
- `POST /api/errors/decide` - 传决策树回答数组推导错因（body: `{answers, specific_behavior}`）
- `GET /api/errors` - 归因记录（支持 `problem_id` / `error_type` / `reviewed` 过滤）
- `POST /api/errors` - 创建归因（DECOMPOSE 必须带拆解句，否则 422）
- `PUT /api/errors/{id}` - 更新复盘状态 / 补救动作 / 备注
- `DELETE /api/errors/{id}` - 删除记录
- `GET /api/errors/statistics` - 统计（`practice_mode=false` 才解锁正确率等模拟指标）

## 核心功能

### 1. RAG 语义检索

题目入库时用 `text2vec-base-chinese` 编码成 768 维向量写入 FAISS（`IndexIDMap2 + IndexFlatIP`，向量已归一化，内积即余弦相似度）。索引与元数据落盘到 `data/`，重启自动恢复；启动时与数据库做差量对齐（补新增、删多余、刷改动）。

### 2. 智能题目推荐

先用 FAISS 检索题库中与母题语义相近的题目作为上下文（RAG 检索增强），再让 DeepSeek 生成同类型变体题。输出由 `PydanticOutputParser` 约束，保证 `Recommendation(title, difficulty, link, reason)` 结构稳定，解析失败自动重试一次。

### 3. 工具调用 Agent

基于 LangChain `create_agent`，把三个工具交给模型，由模型自己决定调用哪个（真正的 Function Calling，而不是代码里的 if-else）：

| 工具 | 作用 |
| --- | --- |
| `search_problems` | 语义检索题库 |
| `analyze_weak_points` | 统计做题数据、分析薄弱知识点 |
| `recommend_variants` | 基于母题推荐变体题 |

### 4. 多轮对话记忆

自定义 `DBMessageHistory` 实现 LangChain 的 `BaseChatMessageHistory` 接口，消息落到 `chat_sessions` / `chat_messages` 两张表。取最近 20 条作为上下文窗口，支持「刚才那道题」这类指代追问，服务重启不丢会话。

### 5. 错因分类

六类错因按「最早断掉的一环」互斥（READ → IDENTIFY → DECOMPOSE → OPERATE → BOUNDARY → EFFICIENCY），归因入口是决策树问答而不是下拉框，避免自评全选「操作错」。

- `specificBehavior` 强制非空且 ≤50 字；写不出说明还没归因清楚
- DECOMPOSE 类强制写拆解句，且必须同时含「=」「母题」「改」
- OPERATE 且命中语言坑关键词（`->`、`nullptr`、`size_t`、`segfault`、空指针、越界、未初始化）时提示补打 SYNTAX 标签
- 练习阶段只报四个指标：错因分布、识别平均耗时、拆解句覆盖率、待补错因数；正确率等模拟指标需显式切换模式才解锁

## 开发计划

- [x] 基础 CRUD 接口
- [x] AI 题目推荐
- [x] RAG 向量检索
- [x] 弱项分析 Agent
- [ ] 前端界面（Vue 3 + Element Plus）
- [ ] 用户认证
- [ ] 做题记录统计
- [ ] 学习报告生成

## License

MIT
