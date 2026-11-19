# StudyFlow 解耦方案：Java 业务主服务 + Python AI 能力服务

> 目标：把现有 FastAPI 单体拆成「Java 管业务与数据 + Python 只管 AI 能力」两个服务。
> 适用范围：个人项目 / 答辩演示 / 求职作品，不追求高可用集群。

> ⚠️ **阅读顺序**：本文档已按代码实况修订。**第 14 节《代码核对后的修正》优先于前文对应段落**（前文若有冲突，以第 14 节为准）。
> 修订涉及的硬伤：聊天 Agent 会写库、出题直接写库、错因判定其实是规则、教材大纲是正则、教材检索是查库打分、FAISS 本期不可用。

---

## 一、结论

**可行，且推荐做。** 但只拆成 **2 个服务**，不要拆成微服务群。

| 判断项 | 结论 |
|---|---|
| 技术上可行吗 | 可行。现有 AI 能力（出题、解析、陪练、变式、推荐）都是"给输入返回输出"的形态，天然适合当独立服务 |
| 值得做吗 | 值得。你现在投的是 Java 后端岗，这套架构本身就是最好的项目叙事：Java 主业务 + Python AI 侧车 |
| 工作量 | 一次性重写约 3800 行 Python 为 6000～8000 行 Java，按每天 4 小时算约 3～4 周 |
| 最大风险 | 两个服务同时写同一张表 → 数据打架、事务断裂。本方案用"AI 服务零数据库"彻底规避 |

---

## 二、三条硬规则（违反任何一条，这个拆分就会失败）

### 规则 1：数据只有一个写入口 —— Java

- **所有业务表只允许 Java 写**（MySQL 单一 owner）
- Python **不连业务库**、不建 ORM 模型、不写任何表
- Python 需要的上下文（章节正文、题目、历史对话）由 Java 通过请求体传入
- 例外只有一个：FAISS 向量索引，它是**派生数据**，允许 Python 自己维护，且必须可从 Java 数据重建

> 这条规则是整套方案的基石。一旦允许 Python 写库，你就要处理分布式事务、双写一致性、ID 冲突——个人项目根本扛不住。

### 规则 2：AI 服务无状态

- Python 不存会话、不存任务状态，重启后不丢任何东西
- 聊天历史由 Java 存（`chat_messages`），每次请求带上最近 N 轮（建议 10 轮）
- 长任务（出题 1～2 分钟）由 Java 建任务表 + 轮询，Python 只管算完返回

### 规则 3：契约先行，前端不改路径

- Java 对外继续暴露 `/api/**`，**路径、请求体、响应体与现在完全一致**
- Python 只暴露 `/ai/**`，仅内网可访问，用共享密钥（`X-Internal-Token`）鉴权
- 好处：前端一行不用改，切流量的那天只是换后端端口

---

## 三、服务划分：现有每个接口归谁

### 3.1 归 Java（业务主服务）

| 现有路由 | 职责 | 说明 |
|---|---|---|
| `auth.py` register / login / me | 用户与 JWT | 原样搬，密码 BCrypt、JWT 签发都在 Java |
| `subjects.py` 全部 | 科目 CRUD | 纯业务 |
| `chapters.py` 除 generate | 章节 CRUD | 纯业务 |
| `knowledge_points.py` 全部 | 知识点 CRUD | 纯业务 |
| `problems.py` 增删改查 / import | 题库管理 | 纯业务 |
| `problems.py` POST /search | 题目检索 | 本期走 **MySQL 关键词检索**；FAISS 语义检索列为二期（§14.11） |
| `attempts.py` 全部 | 作答、判分、统计 | **判分逻辑必须在 Java**，不能交给 AI |
| `wrong_book.py` | 错题本 | 纯业务 |
| `error.py` 增删改查 / meta / statistics / decide | 错因档案 | **整体留 Java**。`/decide` 是纯规则决策树，代码里调 LLM 的痕迹为零 |
| `materials.py` upload / list / chunks / delete | 教材文件与分块存储 | 文件落盘 + 元数据入库 |
| `materials.py` outline / confirm | 章节草案确认 | Java 存草案、确认后写入 chapters |
| `variants.py` 增删改查 | 变式题管理 | 生成走 AI，存储走 Java |
| `uploads.py` | 图片上传 | 静态资源由 Java 托管 |
| `recommend.py` | 推荐编排 | 规则筛选在 Java，候选排序可调 AI |

### 3.2 归 Python（AI 能力服务）

| 能力 | 来源文件 | 说明 |
|---|---|---|
| 教材解析（PDF/TXT → 文本块） | `services/materials.py` | PyMuPDF 留在 Python，解析质量比 Java 好 |
| 章节大纲抽取 | `services/chapter_outline.py` | **正则启发式，不是 LLM**（第X章 / 1.1 等模式匹配）。纯文本输入，留在解析接口里一并返回 |
| 章节/题目生成 | `chapter_builder.py`、`question_generator.py`、`builder.py` | 核心价值。**必须拆成「生成+校验+返回数组」**，不能在 Python 里写库 |
| 变式题生成 | 实际在 `services/recommend.py` 的 `recommend_variants(problem, hierarchy, count)` | 纯函数（入参是题目对象，不是 id），正好适合做 `/ai/variants` |
| AI 陪练（心月狐） | `routers/chat.py` 的生成部分 + `services/llm.py` | **只留 prompt + 历史 + 题目上下文**。`app/agent/` 与 `memory.py` 必须删（它们全量写库） |
| 语义检索 / RAG | `rag/retriever.py`、`vector_store.py` | **本期不做**（零数据库下无数据来源），二期由 Java 推送索引（§14.11） |

### 3.3 明确删掉（不要搬）

- 所有 `app/models/*.py`（SQLAlchemy 模型）→ 数据在 Java
- `services/auth.py`、`core/config` 里的数据库配置
- `routers/*` 里所有 CRUD 路由
- `create_all` 建表逻辑 → 改 Flyway 迁移
- **`app/agent/`（整个目录）**：`tools.py` 里 5 个工具全部 `with SessionLocal()`，`build_chapter_with_ai` / `build_from_material` 还会直接写科目/章节/知识点/题目
- **`services/memory.py`**：直接读写 `chat_messages`
- **`rag/`（本期）**：FAISS 索引依赖库里数据，零数据库下无法自洽
- **`services/error.py` 的 AI 部分不存在**：该文件是规则决策树，整体随 `/api/errors/decide` 留在 Java

---

## 四、数据归属

| 表 | 归属 | Python 是否可见 |
|---|---|---|
| users / subjects / chapters / knowledge_points | Java | 否 |
| problems / variants | Java | 否（需要时由 Java 传） |
| attempts / wrong_book / error_analyses | Java | 否 |
| materials / material_chunks | Java | 否（解析时由 Java 传字节/文本） |
| chat_sessions / chat_messages | Java | 否（历史由 Java 传） |
| FAISS 索引文件 | Python（派生） | 是，可重建 |

Python 侧建一个 `AiJob`? **不建**。任务状态表在 Java：`ai_jobs(id, type, status, request_json, result_json, error, created_at, finished_at)`。

---

## 五、接口契约（Java ↔ Python）

统一约定：
- 全部 `POST`，JSON，UTF-8
- 请求头：`X-Internal-Token: <共享密钥>`
- 响应统一：`{"ok": true, "data": {...}}` 或 `{"ok": false, "error": {"code": "...", "message": "..."}}`
- 超时：解析 60s、出题 180s、聊天 60s、检索 5s
- Java 侧用 `@Async` + 线程池调用，前端轮询任务状态

### 5.1 教材解析

```
POST /ai/parse-material
{ "filename": "高数.pdf", "content_base64": "...",  // 或 "text": "..." }
→ { "ok": true, "data": {
      "title": "高等数学",
      "chunks": [{"seq":1,"heading":"第一章 极限","content":"..."}],
      "outline": [{"title":"第一章 极限","children":[{"title":"1.1 数列极限"}]}],
      "warnings": ["第 37 页为扫描件，已跳过"]
  }}
```

### 5.2 出题

```
POST /ai/generate-questions
{ "chapter_title": "1.1 数列极限", "chapter_content": "……正文……",
  "count": 5, "difficulty": "easy", "existing_titles": ["..."] }
→ { "ok": true, "data": {
      "questions": [{
        "stem": "...", "options": {"1":"...","2":"...","3":"...","4":"..."},
        "answer": "2", "explanation": "...",
        "knowledge_point": "极限的ε-N定义", "difficulty": "easy", "type": "single_choice"
      }],
      "dropped": 1, "drop_reasons": ["第 3 题选项不足 4 个"]
  }}
```

### 5.3 陪练（**不含工具调用**）

```
POST /ai/chat
{ "persona": "xinyuehu",
  "question": {"stem":"...","options":{...},"user_answer":"1","correct_answer":"2"},
  "history": [{"role":"user","content":"..."},{"role":"assistant","content":"..."}],
  "message": "我还是不懂为什么选 2" }
→ { "ok": true, "data": { "reply": "..." } }
```

> 现有 `routers/chat.py` 走的是 LangChain Agent：`app/agent/tools.py` 的工具全部 `with SessionLocal() as db`，还能建科目/章节/题目。**这条路径必须整块去掉**。
> 本期 `/ai/chat` 只做：人设 system prompt + 题目上下文 + 最近 N 轮历史 + 用户消息 → 一段回复。不做 function calling、不查库、不写库。
> 想保留"AI 帮你建章节"这类能力时，由 **Java 编排**：Java 拉数据 → 调 `/ai/generate-questions` → Java 落库。属于二期。

### 5.4 变式题

```
POST /ai/variants
{ "stem":"...", "options":{...}, "answer":"2", "explanation":"...", "count":2 }
→ { "ok": true, "data": { "variants":[{...}], "dropped":0 } }
```

### 5.5 错因判定 —— **本期不做**

原方案设想的 `/ai/analyze-error` 在现有代码里**没有对应实现**。`services/error.py` 是纯规则决策树（按答题模式、连续错误次数等分支），`/api/errors/decide` 全程不调 LLM。
结论：错因模块整体留在 Java。若将来要做"AI 分析错因"，属于**新能力**，另立需求，不要塞进这次迁移。

### 5.6 语义检索 / 索引 —— **本期不做**

零数据库前提下，FAISS 索引没有数据来源；现有 `problems/search` 与教材检索也不是向量检索（见 §14.5、§14.11）。
本期：题目检索走 Java 的 MySQL 关键词匹配；教材检索留在 Java（现有实现是查库后做二元组打分）。二期若要做语义检索，用「Java 推送 `/ai/index/problems` → Python 建索引 → `/ai/search` 返回 id 列表」的方式，Java 再按 id 取正文。

---

## 六、关键流程（时序）

### 6.1 上传教材

```
前端 → Java: POST /api/materials/upload (文件)
Java: 存文件到 uploads/，写 materials 记录(status=parsing)，建 ai_job
Java → Python: POST /ai/parse-material
Python: PyMuPDF 抽取 → 分段 → 正则启发式归并大纲 → 返回 chunks + 大纲草案
Java: 写 material_chunks + 大纲草案，job=success
前端: 轮询 GET /api/materials/{id}/outline 拿草案 → 用户确认 → POST outline/confirm 写入 chapters
```

### 6.2 AI 出题（1～2 分钟，必须异步）

```
前端 → Java: POST /api/chapters/{id}/generate
Java: 校验章节存在 → 建 ai_job(status=running) → 立即返回 job_id
Java(异步线程) → Python: POST /ai/generate-questions
Python: LLM 生成 → 逐题校验 → 返回 questions
Java: 全量校验通过 → 单事务批量插入 problems + 复用/新建 knowledge_points → job=success
前端: 轮询 GET /api/ai-jobs/{id} → success 后刷新题目列表
失败: job=failed，error 写清原因；重试生成新 job，不重复写题
```

### 6.3 判分（纯 Java，不调 AI）

```
前端 → Java: POST /api/attempts {problem_id, answer, client_token}
Java: 查题 → 比对 answer → 写 attempts → 错则 upsert wrong_book → 更新统计
返回: 对错 + 正确答案 + 解析（列表接口永远不返回答案）
```

### 6.4 陪练

```
前端 → Java: POST /api/chat {question_id, message}
Java: 查题 + 查最近 10 轮消息 → 调 Python /ai/chat → 存两条消息 → 返回回复
```

---

## 七、Java 工程结构

技术栈：**JDK 17 + Spring Boot 3.2 + MyBatis-Plus + MySQL 8 + Flyway + Spring Security(JWT)**

```
studyflow-java/
├── pom.xml
├── src/main/java/com/studyflow/
│   ├── StudyFlowApplication.java
│   ├── common/          # 统一响应 R<T>、异常处理、分页
│   ├── config/          # Security、CORS、异步线程池、RestClient
│   ├── security/        # JWT 过滤器、UserContext
│   ├── entity/          # 13 张表实体
│   ├── mapper/          # MyBatis-Plus Mapper
│   ├── service/         # 业务逻辑（含判分、错题本、统计）
│   ├── controller/      # /api/** 路由，与现有路径一一对应
│   ├── ai/              # AiClient、DTO、AiJobService
│   └── job/             # 异步任务执行器
└── src/main/resources/
    ├── application.yml
    └── db/migration/    # Flyway: V1__init.sql（直接复用现有表结构）
```

要点：
- **Flyway 直接抄现有表结构**，字段名不改 → 旧数据零迁移
- 统一响应体 `{code, data, msg}`，和前端现在约定的一致
- AI 调用用 `RestClient`（Spring 6）+ 连接池，超时可配
- 任务表加索引 `(status, created_at)`，配一个每分钟扫超时任务的定时器

---

## 八、Python 瘦身后的结构

```
studyflow-ai-service/
├── app/
│   ├── main.py            # 只注册 /ai/** 路由
│   ├── api/               # parse / generate / chat / variants / error / search
│   ├── core/              # 配置、内网 token 校验、日志
│   ├── llm/               # llm.py（DeepSeek 客户端）、prompts/
│   ├── parsing/           # materials.py（PyMuPDF）、chapter_outline.py
│   ├── generation/        # question_generator.py、builder.py、variant
│   ├── chat/              # 心月狐 prompt、记忆裁剪
│   └── rag/               # FAISS 索引与检索
├── requirements.txt        # 去掉 sqlalchemy / pymysql / passlib / python-jose
└── Dockerfile
```

删除：`app/models/`、`app/routers/`（全部换成 `api/` 的 AI 端点）、`services/auth.py`、数据库配置。
预计代码量从 3800 行降到 1500～1800 行。

---

## 九、迁移顺序（不要一次性重写）

采用**绞杀者模式**，每一步都可运行、可回滚：

| 阶段 | 做什么 | 验收 |
|---|---|---|
| **P0 冻结契约** | 把现有 `/api/**` 响应结构导出成文档；确认表结构不再变 | 前端能对着文档联调 |
| **P1 Java 骨架** | 建工程、Flyway 建表（复用旧库）、JWT 登录、科目/章节/知识点/题目 CRUD | 前端把 baseURL 指到 Java，能登录、能看树、能看题 |
| **P2 业务闭环** | 作答判分、错题本、统计、错因 CRUD、上传存储 | 做题→判分→错题本全通 |
| **P3 Python 瘦身** | 按第八节改造，删业务代码，加内网 token | `curl /ai/generate-questions` 返回 5 题 |
| **P4 接线 AI** | Java 加 AiClient + ai_jobs，接教材解析、出题、陪练、变式 | 四个 AI 功能在前端跑通 |
| **P5 下线旧服务** | 旧 FastAPI 停止对外，前端只连 Java；Python 只监听内网 | 全链路回归 |

**建议在 P1 之前先 git 打 tag**（如 `v1-python-monolith`），随时能回退对照。

---

## 十、八个必踩的坑（提前规避）

1. **两边都连 MySQL** → 坚决禁止。Python 一旦有 `SessionLocal`，就会有人忍不住写库
2. **出题同步等待** → 一定异步。1～2 分钟的 HTTP 请求会被网关掐断，用户也会以为卡死
3. **Java 逐题插入** → 必须"全部校验通过 → 单事务批量插"，否则会留半套题
4. **AI 返回不合规数据** → Python 侧先做校验（4 选项、answer 合法、题干去重），Java 侧再校验一遍（防御性）
5. **把用户 JWT 传给 Python** → 不要。用内网 token，Python 不需要知道用户是谁
6. **聊天历史存在 Python** → 重启就丢。历史必须由 Java 存、按需传入
7. **FAISS 索引和数据库不同步** → 索引必须可重建：提供 `/ai/index/rebuild`，启动时按需全量重建
8. **拆分过细** → 别搞用户服务、题库服务、AI 服务、网关四个。两个服务 + 前端足够，网关都可以省（Nginx 一条 location 就行）

---

## 十一、前端要改什么（只有 3 处，其中 2 处是配置）

前端接口层集中在 `frontend/src/api/index.js`，`baseURL = '/api'`（相对路径），所以**只要 Java 保持同样的路径和字段名，页面代码基本零改动**。

### 11.1 必须改：开发环境代理（1 行）

`frontend/vite.config.js` 里 `/api` 和 `/uploads` 的 target 从 `http://localhost:8002` 改成 Java 的端口（如 `http://localhost:8080`）。

生产环境（Java 托管 `dist`）同源，无需代理，此项不影响。

### 11.2 必须遵守：错误体字段叫 `detail`

前端有约 10 处这样取错误信息：

```js
ElMessage.error(error.response?.data?.detail || '操作失败')
```

Java 的全局异常处理器必须返回 `{"detail": "错误描述"}`（**不是** Spring 默认的 `{"timestamp","status","error","path"}`，也不是 `{"message": ...}`），否则所有报错提示都会退化成兜底文案。

推荐做法：`@RestControllerAdvice` 统一包装，业务异常与参数校验异常都映射成 `{"detail": "..."}`。

### 11.3 必须遵守：JSON 字段用 snake_case

前端到处直接用下划线字段：`access_token`、`subject_id`、`knowledge_point_id`、`question_id`、`correct_answer`、`is_correct`、`client_token`、`session_id`……

Java 实体是驼峰，必须在 `application.yml` 全局开启：

```yaml
spring:
  jackson:
    property-naming-strategy: SNAKE_CASE
```

否则登录拿不到 `access_token`，列表页字段全是 `undefined`。

### 11.4 可选改：AI 出题改异步（2 个调用点）

现前端是同步等（`timeout: 130000`），调用点在：

- `src/api/index.js:45` `generateChapterQuestions`
- `src/views/ChapterList.vue:118`
- `src/views/SubjectList.vue:383`

若采用异步任务方案，这三处改成「提交任务 → 轮询 `GET /api/ai-jobs/{id}` → 成功后刷新列表」。改动约 30 行。

**如果不想动前端**：Java 侧把 `/chapters/{id}/generate` 保持同步（内部调 Python 超时 180s，前端等 130s）。代价是用户要盯着 loading 一两分钟，且一旦网关有 60s 超时会失败。**建议还是改成异步**，这也是面试可讲的点。

### 11.5 不用改的部分

- 登录态：`localStorage.token` + `Authorization: Bearer` 拦截器，原样可用
- 401 跳登录逻辑，原样可用
- 所有业务路径 `/api/subjects`、`/api/chapters`、`/api/attempts` 等，原样可用
- 文件上传的字段名（`file` / `title` / `subject_id`），原样可用
- `/uploads/**` 静态资源路径，Java 需照样挂载

---

## 十二、验收标准

- [ ] 前端 `baseURL` 只改一处，所有页面功能与改造前一致
- [ ] 数据库仍是同一套表，旧数据可直接读
- [ ] 断掉 Python 服务后，除 AI 功能外的所有功能正常（登录、看题、做题、判分、错题本）
- [ ] 出题任务失败时返回明确错误码，且数据库无残留半套题
- [ ] 列表接口响应里搜不到 `answer` / `explanation` 字段
- [ ] Python 服务代码中不存在任何 SQLAlchemy / 数据库连接
- [ ] 两个服务各自能独立启动、独立重启互不影响

---

## 十三、面试怎么讲（顺手准备）

> "项目最初是 FastAPI 单体，AI 与业务耦合，任何一次出题逻辑改动都要重启整个服务，也没法用 Java 生态做权限和事务。我按数据所有权做了服务拆分：Java 作为唯一写入口承担用户、题库、判分、错题本，Python 只保留 AI 能力并做成无状态服务，接口用内网 token 鉴权、统一契约返回。长耗时的出题改成了任务表 + 轮询，避免 HTTP 超时。拆分后 AI 服务代码量降了一半，业务侧可以独立演进。"

这一段的含金量在于：**你不是"用了两个语言"，而是讲清了"为什么按数据所有权切"**。

---

## 十四、代码核对后的修正（**优先级高于前文**）

> 以下 10 条来自对 `代码/` 的实际核对，逐条已确认。前文与本节的冲突，一律以本节为准。

### 14.1 错因判定不走 AI —— 整个模块留 Java

- 事实：`services/error.py` 是纯规则决策树（按练习模式、连续错误等分支），`routers/error.py` 全文没有 LLM 调用
- 前文"只有 `/decide` 走 AI"是错的，已修正
- `/ai/analyze-error`：**本期不做**。若要做"AI 分析错因"，属新能力，另立需求
- Java 侧：`/api/errors/*` 全部按原逻辑实现，含 `/decide` 的规则判断

### 14.2 聊天 Agent 是最大的边界违规 —— P3 必须重写 chat

- 事实：`app/agent/tools.py` 中 `analyze_weak_points`、`search_problems`、`recommend_variants`、`search_materials`、`build_chapter_with_ai`、`build_from_material` **全部 `with SessionLocal() as db`**
- `build_chapter_with_ai` / `build_from_material` 在 `dry_run=False` 时直接写 subjects / chapters / knowledge_points / problems
- `services/memory.py` 直接读写 `chat_messages`
- 结论：`app/agent/`、`services/memory.py` **整块删除**，不进新服务
- 本期 `/ai/chat` 只做三件事：拼 system prompt（心月狐人设）+ 注入题目上下文 + 带历史生成回复。**不支持 function calling**
- 若将来要 agent 能力，由 Java 编排工具调用（Java 查数据 → 调 AI → Java 落库），Python 始终不碰库

### 14.3 出题必须拆成「生成 + 校验 + 返回」

- 事实：`generate_questions(db, chapter, count, difficulty)` 在 Python 内部直接写库，只返回计数
- P3 改法：抽出纯函数 `generate_questions_payload(chapter_title, chapter_content, count, difficulty, existing_titles) -> (questions, dropped, reasons)`
  - 入参是**文本**，不是 chapter_id；不接收 db 参数
  - Python 只做：调 LLM → 校验（4 选项、answer 合法、题干去重）→ 返回数组 + dropped
- Java 负责：知识点同名判重与新建、题目批量插入、事务、统计

### 14.4 变式题的真实位置

- AI 生成在 `services/recommend.py: recommend_variants(problem, hierarchy, count)`，**入参是题目对象，纯函数**，天然适合 `/ai/variants`
- `routers/variants.py` 只是 CRUD；`/api/variants/from-recommendation` 只负责保存前端传来的结果
- Java 侧：`/api/recommend` → 调 `/ai/variants` → 返回候选；`from-recommendation` 保持"只保存"

### 14.5 教材大纲不是 LLM，教材检索也不是向量检索

- `services/chapter_outline.py` 用正则识别「第X章 / 第X节 / 1.1 标题 / Chapter N」等模式，**不调模型**
- 教材关键词检索：查 `material_chunks` 后做二元组打分（`search_materials` 里 `with SessionLocal()`）
- 因此：
  - `/ai/parse-material` 一次返回 **chunks + 大纲草案**（都是纯文本计算，不需要 DB），Java 落库
  - `GET /api/materials/{id}/outline` 从 Java 库里读草案，不再回头调 Python
  - **教材检索留 Java**：SQL 取 chunks → 内存打分（逻辑简单，可照搬）

### 14.6 鉴权现状比方案假设的更宽松

- 事实：只有 `GET /api/auth/me?token=xxx` 用 **query 参数**取 token，其余接口**全部无鉴权**
- 前端登录后所有请求都带 `Authorization: Bearer`，所以 Java 启用 Spring Security 后一般不会 401
- 但必须注意两点：
  1. `/api/auth/me` **必须同时支持 query 参数 `token`**（前端 `getCurrentUser(token)` 就是这么调的），不能只读 Header
  2. 不要顺手"补全"鉴权到所有接口——旧版没有，前端可能有未带 token 的调用路径，加严会导致 401 风暴。**保持现状，安全问题另立需求**

### 14.7 删除级联是 ORM 级，不是数据库级

- 旧实现靠 SQLAlchemy relationship 级联，**DDL 里未必有 `ON DELETE CASCADE`**
- Java 必须手写级联：`Subject → Chapter → KnowledgePoint → Problem → Variant`
- 反例：`attempts`、`wrong_book`、`error_analyses` **不随题目删除**（旧实现如此），Java 保持一致，不要"优化"成级联删除
- 每层删除都要计入返回的 `deletedProblems` 等统计字段（旧接口有这玩意）

### 14.8 删除响应结构不统一，必须原样保留

| 接口 | 删除响应 |
|---|---|
| `DELETE /api/subjects/{id}` | `{"code": 0, "message": "删除成功", "deletedProblems": n}` |
| `DELETE /api/chapters/{id}` | `{"message": "删除成功", "deletedProblems": n}` |
| `DELETE /api/knowledge-points/{id}` | `{"message": "删除成功", "deletedProblems": n}` |

前端可能依赖科目的 `code` 字段，别统一成一种结构。

### 14.9 字段级差异（Java 实现必须注意）

| 项 | 实际情况 | Java 处理 |
|---|---|---|
| `problems.type` | 列名就是 `type`，MySQL 关键字 | MyBatis-Plus `@TableField("`type`")` 或全局转义 |
| `error_analyses.specific_behavior` | 库长 **200**，API 校验 **≤50** | 按 API 的 50 校验（宽度 200 保留） |
| `materials.created_at` | **可空** | 实体用可空类型，勿设 NOT NULL |
| ID 格式 | `user-` `sub-` `chap-` `kp-` `prob-` `var-` `session-` 前缀；materials / chunks 是完整 UUID | Java 必须生成同格式，前端与既有数据都依赖 |
| `attempts` 唯一约束 | **不存在**（代码里 catch IntegrityError 实际打不到） | Flyway 加 `UNIQUE(client_token)`，幂等才真实生效（**有意变更，需在 V2 脚本中说明**） |

### 14.10 路由静态段顺序

- FastAPI 要求 `/search`、`/meta`、`/from-recommendation` 声明在 `/{id}` 之前，否则被吞
- Spring 的精确匹配优先，不存在此问题
- 但写 Controller 时**不要**给这些静态路径再叠一个 `/{id}` 映射，避免歧义

### 14.11 FAISS / RAG 本期下线的理由

- 索引数据来自 `problems`，零数据库后 Python 无从获取
- 强行保留就得设计"Java 推送索引"协议，属于二期工作
- 本期替代方案：`/api/problems/search` 走 MySQL 关键词（标题 + 题干 LIKE / 全文索引），教材检索留 Java

---

## 十五、按修正调整后的 P3 范围（覆盖第九节 P3）

P3 不再是"复制后删几个文件"，精确清单如下：

**删除**
- `app/models/`、`app/routers/`、`app/agent/`、`app/rag/`
- `services/auth.py`、`services/memory.py`、`services/error.py`、`services/recommend.py` 里的 DB 依赖部分
- `core/` 里数据库配置；`requirements.txt` 去掉 sqlalchemy / pymysql / passlib / python-jose / alembic / faiss

**改造（不是重写算法，是拆出纯函数）**
- `question_generator.generate_questions` → `generate_questions_payload(...)`（不接 db、不落库、返回数组）
- `recommend.recommend_variants` → 保持签名，去掉内部 DB 查询
- `materials` 解析 → 返回 `chunks + outline`，不写库
- `chat` → 无 agent、无记忆表，纯 prompt + history

**新增**
- `app/api/` 五个端点：`/ai/parse-material`、`/ai/generate-questions`、`/ai/variants`、`/ai/chat`、`/health`
- `X-Internal-Token` 校验中间件
- 统一响应包装 `{"ok":true,"data":...}`

**验收**
- 全目录 grep 无 `SessionLocal` / `sqlalchemy` / `pymysql` / `chat_messages`
- `curl /ai/chat` 传 history 能返回回复
- `curl /ai/generate-questions` 传文本返回数组与 dropped
