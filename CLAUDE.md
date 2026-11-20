# CLAUDE.md — StudyFlow 项目约定（必须遵守）

## 项目构成

| 目录 | 角色 | 说明 |
|---|---|---|
| `代码/` | **旧版 Python 单体（只读参考）** | FastAPI + LangChain + FAISS + Vue3。**禁止修改**，只作为接口与表结构的基准 |
| `studyflow-java/` | **新建：Java 业务主服务** | Spring Boot 3 + MyBatis-Plus + MySQL + Flyway，唯一写库方 |
| `studyflow-ai-service/` | **新建：Python AI 能力服务** | 从 `代码/` 瘦身而来，只暴露 `/ai/**`，**零数据库** |
| `docs/解耦方案-Java+Python.md` | 架构方案（唯一设计依据） | 切分边界、接口契约、迁移顺序都在里面 |

## 绝对禁止（违反即返工）

1. **禁止修改 `代码/` 目录下任何文件**（迁移阶段除外，且需用户确认）
2. **Python 服务禁止连接数据库**：不得出现 sqlalchemy / pymysql / SessionLocal / models
3. **禁止两个服务写同一张表**：所有业务表只有 Java 能写
4. **禁止改动对外接口路径**：必须保持 `/api/subjects`、`/api/chapters`、`/api/attempts` 等与旧版完全一致
5. **禁止在题目列表/详情响应中返回 `answer` 或 `explanation`**（只在交卷/判分响应里返回）
6. **禁止一次性重写整个项目**：严格按 P1→P5 阶段推进，每阶段可独立运行

## 依据代码核对后的额外约束（方案第 14 节）

- **禁止搬 `app/agent/` 与 `services/memory.py`**：它们全部 `with SessionLocal()`，还会直接写科目/章节/题目。`/ai/chat` 只做 prompt + 历史 + 题目上下文，不支持 function calling
- **禁止本期实现 `/ai/analyze-error`**：现有 `/api/errors/decide` 是规则决策树，错因整体留 Java
- **禁止本期接 FAISS / RAG**：零数据库下无数据来源，`/api/problems/search` 走 MySQL 关键词
- **教材大纲是正则启发式不是 LLM**：`/ai/parse-material` 一次返回 chunks + outline，Java 落库，`GET /api/materials/{id}/outline` 读 Java 库
- **教材检索留 Java**（旧实现是查库后二元组打分）
- **出题函数必须拆成纯函数**：不接 db、不落库、返回题目数组 + dropped
- **删除级联手写**：`Subject → Chapter → KnowledgePoint → Problem → Variant`；attempts / wrong_book / error_analyses **不随题目删除**（保持旧行为）
- **删除响应结构不同，原样保留**：subject 带 `code:0`，chapter / kp 只有 `message` + `deletedProblems`
- **ID 前缀必须一致**：`user-` `sub-` `chap-` `kp-` `prob-` `var-` `session-`；materials / chunks 为完整 UUID
- **`problems` 的列名 `type` 是 MySQL 关键字**：MyBatis-Plus 用 `@TableField("`type`")`
- **`error_analyses.specific_behavior` 按 API 的 50 校验**（库宽 200）
- **`materials.created_at` 可空**
- **`GET /api/auth/me` 必须支持 query 参数 `token`**（前端就是这么调的）；其余接口保持旧版宽松策略，**不要顺手加严鉴权**
- **`attempts` 加 `UNIQUE(client_token)`** 才能真正幂等（旧库没有该约束，属有意变更，V2 脚本注明）

## 前端契约（不改前端的前提）

- **JSON 字段全部 snake_case**：
  ```yaml
  spring.jackson.property-naming-strategy: SNAKE_CASE
  ```
- **错误响应体必须是 `{"detail": "错误描述"}`**（前端读取 `error.response.data.detail`）
- 成功响应结构沿用旧版，例如列表直接返回数组、单个对象直接返回对象
- 登录响应字段：`access_token`、`token_type`、`user_id`、`username`
- 静态资源：`/uploads/**` 必须照样可访问

## 数据库

- 表结构**完全复用现有库**（字段名、类型不改），Flyway `V1__init.sql` 照抄
- 现有表：`users` `subjects` `chapters` `knowledge_points` `problems` `variants`
  `attempts` `wrong_book` `error_analyses` `materials` `material_chunks`
  `chat_sessions` `chat_messages`
- 新增仅一张表：`ai_jobs`（异步任务）
- 判分逻辑在 Java，不允许交给 AI

## Java 技术栈（不要引入其他框架）

- JDK 21 + Spring Boot 3.2.x + MyBatis-Plus + MySQL 8 + Flyway + Spring Security(JWT)
- HTTP 客户端用 Spring 6 `RestClient`（不用 Feign、不用 WebClient）
- 不引入 Redis、RabbitMQ、Nacos、Docker Compose（本期不需要）
- 构建用 Maven Wrapper（`mvnw`），本机未安装 Maven

## Python 服务

- 保留：PyMuPDF 解析、章节大纲、出题、变式题、陪练、错因判定、FAISS 检索
- 端点统一 `/ai/**`，请求头校验 `X-Internal-Token`
- 响应统一 `{"ok": true, "data": {...}}` / `{"ok": false, "error": {"code","message"}}`
- 无状态：不存会话、不存任务

## 工作方式

- 每个阶段结束必须：真实执行验证命令 → 贴出真实输出 → `git commit`
- 不确定的表结构或接口，去读 `代码/app/models/` 和 `代码/app/routers/`，**不要猜**
- 实现与方案冲突时，以 `docs/解耦方案-Java+Python.md` 为准；方案未覆盖的，选改动更小的方案并写入 `实现备注.md`
