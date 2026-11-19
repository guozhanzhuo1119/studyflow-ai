# P1 实现备注

日期：2026-11-19　分支：`feat/p3-python-slim`

## 1. 版本选择（与方案 3.2 的偏差）

| 项 | 采用版本 | 原因 |
|---|---|---|
| Spring Boot | **3.5.16** | 方案写的是 3.2.x，但 start.spring.io 当前只接受 `>=4.0.0`（实测 `bootVersion=3.5.16` 返回 400）。Boot 4 与 MyBatis-Plus 的 `spring-boot3-starter` 不配套，因此取 Maven Central 上最新的 3.x 稳定版 3.5.16，属于“当前支持的 3.x 稳定版” |
| JDK | 21 | 本机 21.0.12 |
| MyBatis-Plus | 3.5.18.1 | Boot 3 专用 starter；已在 3.5.16 下编译并启动通过 |
| JJWT | 0.12.6 | HS256 签发/解析 |
| Flyway | Boot 3.5.16 管理版本（11.x） | 额外引入 `flyway-mysql` |

工程骨架（`mvnw`、`.mvn`）来自 Initializr，仅把 parent 改为 3.5.16 并替换为 Boot 3 的依赖坐标，**没有手写整套 pom**。

## 2. 鉴权与密码哈希（有意与方案文字不同）

- 方案第七节写“密码 BCrypt”，但旧库 `users.password_hash` 是 **SHA-256 十六进制**（`代码/app/services/auth.py`），且库里有 4 个既有账号。
- 若改用 BCrypt，老账号全部无法登录。P1 必须保证“前端切过来能登录”，因此 **原样使用 SHA-256**，登录逻辑与旧版逐行对齐。
- JWT：HS256，claims 为 `user_id` / `username` / `exp`，默认密钥 `your-secret-key-change-in-production`、有效期 7 天，均与旧版一致；旧 token 可直接解析。
- 除 `GET /api/auth/me?token=` 外全部 `permitAll`，未加严鉴权（方案 §14.6）。

## 3. 数据库与 Flyway

- 真实 DDL 来源：`schema/studyflow_ai.sql`（13 张表）。
- `V1__init.sql` 全部为 `CREATE TABLE IF NOT EXISTS`，**没有 DROP / TRUNCATE / ALTER**；额外新建 `ai_jobs`（P4 用，本期只建表）。
- 配置：`baseline-on-migrate: true`、`baseline-version: 0`。首次启动建立 baseline 0 后执行 V1；既有表只产生“already exists”告警，数据不动。
- 验证：首次启动 `Successfully applied 1 migration ... now at version v1`；重启后 `Current version: 1` / `Schema is up to date. No migration necessary.`。
- 迁移前已备份：`/tmp/studyflow_backup_1795097274.sql`（1.1 MB）。
- 数据核对：subjects 7、materials 1、material_chunks 555、attempts 15 均保持不变；users 由 4 变为 5（验收新建的测试账号）。

## 4. 只读接口契约（照抄 `代码/app/routers/`）

已实现：

- `GET /api/subjects`、`GET /api/subjects/{id}`
- `GET /api/chapters?subject_id=`、`GET /api/chapters/{id}`（按 `order_num, created_at` 排序）
- `GET /api/knowledge-points?chapter_id=`、`GET /api/knowledge-points/{id}`
- `GET /api/problems?knowledge_point_id=`、`GET /api/problems/{id}`
- `POST /api/problems/search`（旧版真实契约），另加 `GET /api/problems/search?query=&top_k=` 便于按文档联调

字段、嵌套与列表包装均逐字对齐旧 serializer：

- 列表直接返回数组，单个对象直接返回对象；
- 错误体统一 `{"detail": "..."}`；
- 全局 `spring.jackson.property-naming-strategy: SNAKE_CASE`；
- `problems` 的 `type` 列使用 `@TableField("`type`")`；
- **题目列表与详情都不返回 `answer` / `explanation`**（与旧 serializer 和 CLAUDE.md 一致）；
- `options` 按 JSON 数组解析，空/非法 JSON 返回 `[]`；
- 时间字段为无时区 ISO 字符串，如 `2026-11-18T20:17:33`。

`/api/problems/search` 本期按方案 §14.11 走 MySQL 关键词（title/content LIKE），返回 `{query,total,results}`；`score` 为 1.0（标题命中）/ 0.5（正文命中），仅用于展示排序，二期接回向量检索。语义检索结果字段与原 `_clean` 对齐。

## 5. 静态资源

- `/uploads/**` 映射到 `studyflow.uploads-dir`（默认 `studyflow-java/uploads/`，启动时自动创建）。
- 迁移期如需继续展示旧图片，可设 `UPLOADS_DIR=../代码/uploads`（只读引用，不修改 `代码/`）。
- `studyflow.frontend-dist` 预留：配置为存在的目录后挂载 `/**` 托管 `dist`；为空则不挂载。

## 6. 本地运行

```bash
cd studyflow-java
cp .env.example .env   # 填 DB_PASSWORD
./mvnw -q clean package -DskipTests
java -jar target/studyflow-java-0.0.1-SNAPSHOT.jar
```

`.env` 已被 gitignore；`application.yml` 通过 `spring.config.import` 加载，从仓库根目录或 `studyflow-java/` 启动均可。

## 7. 验收用测试账号

- 用户名：`p1_smoke_20261119`
- 密码：`P1Smoke#2026`
- 仅用于 P1 烟测，已写入真实库 `users`（第 5 个用户）。

## 8. 本阶段未做

- P2：作答判分、错题本、统计、错因 CRUD、上传存储；
- P4：AiClient、ai_jobs 任务执行、AI 接线；
- 删除级联、写接口等均未实现，保持“只读链路”范围。

---

# P4 实现备注（2026-11-19）

## 1. 范围与依赖

- 接入 P3 Python 服务的 `/ai/generate-questions`、`/ai/parse-material`、`/ai/variants`、`/ai/chat`。
- 未新增 Maven 依赖：`RestClient`、`@Async` 均由 Spring Boot 3.5.16 提供。
- `application.yml` 新增 `studyflow.ai`：
  - `base-url` 默认 `http://127.0.0.1:8001`
  - `internal-token` 默认 `studyflow-dev-token`（可用 `AI_INTERNAL_TOKEN` 覆盖）
  - 连接超时 10s、读超时 180s
- `AiClient` 使用 Spring Boot 自动配置的 `RestClient.Builder`，确保复用全局 SNAKE_CASE
  `ObjectMapper`（否则请求/响应字段会与 Python 的 snake_case 对不上）。
  连接失败返回 503；Python 非 2xx、信封 `ok=false` 返回 502，均带明确 `detail`，不吞异常。

## 2. 异步出题

- `POST /api/chapters/{id}/generate` 只做参数校验、建 `ai_jobs(status=pending)`，立即返回 `{"job_id":"job-xxxxxxxx"}`。
- `GET /api/ai-jobs/{id}` 返回 `{status, result, error}`；状态：`pending / running / success / failed`。
- 线程池 `aiTaskExecutor`（core 2 / max 4 / queue 50），线程名 `ai-job-*`。
- 章节正文由 Java 从 `material_chunks` 中按旧算法定位（`ChapterTextService`，
  照搬 `extract_chapter_text` 的正则与匹配规则），不回调 Python。
- 落库规则：
  - Python 的 `options` 用 Jackson 序列化为 A/B/C/D 顺序 JSON 数组文本；
  - 固定 `type='single'`、`source='AI 生成'`、`tags='{章节名},AI出题'`；
  - `difficulty` 整批使用请求里的整数；
  - `prob-{8hex}` / `kp-{8hex}`；知识点在本章内按去空白名称先查后建、同名复用；
  - 知识点 + 题目在 `GenerationPersistenceService.persist` 的**同一事务**中提交，任一失败全回滚；
  - Java 侧再次校验题干/4 选项/答案/解析/知识点，任一题不合规则整批失败；
  - 全部被 Python 丢弃（questions 为空）时任务失败，不写任何业务数据。
  - 成功时 `result_json` 存 `{generated,dropped,total_in_chapter,drop_reasons}`，日志打印 dropped 与原因。

## 3. 教材链路

- `POST /api/materials/upload`（multipart：`file` / `title` / `subject_id`）：
  - 文件落盘 `uploads/materials/{12hex}_{原文件名}`，再 base64 调 `/ai/parse-material`；
  - Python 返回的 `chunks` 直接写 `material_chunks`（完整 UUID）；
  - `materials.id` 也是完整 UUID；`created_at` 可空（本实现写入当前时间）；
  - 解析失败/落库失败都会删除刚写入的磁盘文件；落库事务包含 materials + chunks + 解析任务。
- **大纲草案持久化**：数据库只允许新增 `ai_jobs`，因此把 Python 的 `outline + warnings`
  存进一条 `ai_jobs(type='parse-material', status='success')` 的 `result_json`
  （对应方案 6.1 的「Java 写 material_chunks + 大纲草案，job=success」）。
  job id 采用确定性格式 `job-{materialId去掉连字符}`，`GET /api/materials/{id}/outline`
  直接按 id 读 Java 库，不回调 Python。
- 旧数据（P1 前的 material）没有这条 job，outline 返回空 chapters +
  「该教材没有解析大纲，请重新上传教材生成大纲」提示，不 500。
- `POST /api/materials/{id}/outline/confirm`：按请求数组顺序写 chapters，
  `order_num = 该科目现有最大 order_num + 创建序号`；同名跳过；
  无 subject_id 时新建科目，**使用 `sub-` 前缀**（旧实现的 `subj-` 是笔误，按 CLAUDE.md 修正）。
- 另补齐 `GET /api/materials`、`GET /api/materials/{id}/chunks`、`DELETE /api/materials/{id}`，
  行为与旧版一致（删除保留磁盘文件）。

## 4. 聊天

- `POST /api/chat`：先校验 `question_id`（题目不存在返回 404，不留下空会话），
  取该会话最近 20 条（10 轮）消息，按正序传给 `/ai/chat`。
- 题目上下文透传 `title / options（A-D 数组）/ correct_answer / explanation`；
  本期尚未做 P2，故不再查询最近一次作答。
- 会话 id：`session-{8hex}`；新建时 `title = message[:40]`，写入 `created_at / updated_at`。
- AI 回复成功后才在一个事务里写两条 `chat_messages`（user + assistant），
  自增 id 不手动赋值；同时更新会话 `updated_at`。AI 失败不会写消息。
- 补齐 `GET /api/chat/sessions`、`GET /api/chat/sessions/{id}/messages`、
  `DELETE /api/chat/sessions/{id}` 供前端恢复历史。

## 5. 变式

- `POST /api/recommend`：查母题与层级 -> `/ai/variants`，响应字段保持旧版
  `{problem_id, problem_title, recommendations}`。
- `POST /api/variants/from-recommendation`：只保存，不调用 AI；
  `origin='ai'`，`var-{8hex}`，批量插入在一个事务中。
- 另补 `GET /api/variants`、`POST /api/variants`（手动保存，`origin='manual'`），
  方便旧前端现有调用。

## 6. 降级行为（实测）

停掉 8001 后：

| 功能 | 结果 |
|---|---|
| `GET /api/subjects`、`GET /api/problems`、登录、`POST /api/problems/search` | 200，正常 |
| `GET /api/materials/{id}/outline`、`GET /api/variants` | 200，读 Java 库 |
| `POST /api/materials/upload` | 503 `AI 服务不可用，请确认 studyflow-ai-service 已启动` |
| `POST /api/chat` | 503，同上 |
| `POST /api/recommend` | 503，同上 |
| `POST /api/chapters/{id}/generate` | 先返回 job_id，随后任务变 `failed`，error 同上，题库无新增 |

## 7. P4 验收产生的数据

- 教材：`73b6df78-7b76-46ce-a9d2-13f0b052249e`（P4 Linear Algebra，2 页 455 字符）
- 科目：`sub-357731e6`；章节：`chap-743e0c40`（第一章 行列式）、`chap-a04e0f84`（第二章 矩阵）
- 出题任务成功：`job-80e8abd3`（generated=2, dropped=0, total_in_chapter=2）
- 题目：`prob-669c15cd`、`prob-98942ab1`；知识点：`kp-7e25d2a3`、`kp-96ae7dae`
- 聊天会话：`session-d86db942`（2 条消息）
- 变式：`var-f659335d`
- 降级任务失败：`job-514aee22`（无业务数据写入）

## 8. 已知缺口

- **P2 未实现**：`/api/attempts`、`/api/wrong-book` 等接口仍不存在（404）。
  因此降级验收中的「做题、错题本仍正常」当前无法演示；需要先做 P2。
- 出题若采用同步等待会超过网关超时，因此按方案改为异步；
  前端 P5 切流时需把 `generateChapterQuestions` 改成「提交任务 + 轮询 `/api/ai-jobs/{id}`」。
- 重启时未增加「把遗留 pending/running 任务标失败」的补偿扫描；本期验收未涉及。
