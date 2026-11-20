# 用 Claude Code 改造 StudyFlow：分阶段提示词

> 前置：本目录已有 `CLAUDE.md`（Claude Code 会自动读取）和 `解耦方案-Java+Python.md`（唯一设计依据）。
> 环境已确认：JDK 21、Node 22、Claude Code 2.1.325 可用；本机无 Maven，用项目自带 `mvnw`。

---

## 一、开工前的 4 件事（10 分钟）

在 `D:\编程软件\项目汇总\studyflow-ai` 目录下打开终端：

```bash
# 1. 给旧代码打个 tag，随时可回退对照
cd 代码 && git tag v1-python-monolith && cd ..

# 2. 确认旧项目工作区干净（避免 Claude 误改旧代码后无法回滚）
cd 代码 && git status --short && cd ..

# 3. 导出当前数据库表结构（Flyway 要用，必须是真的表结构，不能让 AI 猜）
#    MySQL 有密码就加 -p
mysqldump -u root -p --no-data studyflow > schema-dump.sql

# 4. 启动 Claude Code（在项目根目录启动，才能读到 CLAUDE.md）
claude
```

> 第 3 步如果 mysqldump 不可用，可以让 Claude 直接读 `代码/app/models/*.py` 反推建表语句，但**必须让它把生成的 DDL 和数据库实际结构核对一遍**（`SHOW CREATE TABLE xxx`）。

---

## 二、使用节奏（关键）

| 做法 | 原因 |
|---|---|
| **一次只做一个阶段**，做完 `/clear` 再开下一阶段 | 上下文越干净，改得越准 |
| 每个阶段先按 **Shift+Tab** 进 Plan 模式，让它先给方案 | 避免它上来就狂写文件 |
| 每阶段结束让它 **真实跑接口 + 贴输出** | 防止"应该可以"式汇报 |
| 每阶段结束 `git commit` | 出问题能单阶段回退 |
| 它报"找不到表/字段"时，**直接指路到文件**：`代码/app/models/problem.py` | 比让它猜快得多 |

---

## 三、阶段提示词（逐条复制）

### P0 · 摸底与契约核对（不写代码）

```text
先不要写任何代码。请完成四件事：

1. 读 CLAUDE.md 和 解耦方案-Java+Python.md，确认你理解服务边界。
2. 重点读方案第十四、十五节（代码核对后的修正），确认你接受这 11 条既定事实，
   特别是：聊天 agent 会写库、出题直接写库、错因不走 AI、大纲是正则、FAISS 本期不做。
3. 通读 代码/app/routers/ 下全部路由文件，输出《现有接口清单》表格：
   方法 + 路径 + 请求字段 + 响应字段 + 是否依赖 AI（依赖的注明调用了哪个 service）。
4. 读 代码/app/models/ 下全部模型，输出《表结构清单》：表名 + 字段名 + 类型 + 索引/唯一约束。

输出后停下等我确认。不要创建任何文件，不要开始写 Java。
```

> 拿到清单后重点核对三处：`attempts` 有没有 `client_token`（旧库**没有**唯一约束，要新增）、`problems.knowledge_point_id` 是否非空外键、`problems.type` 是否是 MySQL 关键字。

---

### P1 · Java 骨架 + 登录 + 只读链路

```text
执行 P1 阶段，严格按照 CLAUDE.md 与方案的第七节工程结构。

范围（只做这些）：
1. 在 studyflow-java/ 创建 Spring Boot 3.2 + JDK 21 工程，必须带 Maven Wrapper（mvnw）。
   依赖：web、validation、security、mybatis-plus、mysql-connector-j、flyway、jjwt。
2. Flyway V1__init.sql：完全照抄现有表结构（参考 schema-dump.sql，若无则读 代码/app/models/），
   只新增 ai_jobs 表（id, type, status, request_json, result_json, error, created_at, finished_at）。
3. 全局配置：
   - spring.jackson.property-naming-strategy: SNAKE_CASE
   - @RestControllerAdvice 统一异常 → {"detail": "..."}
   - CORS
4. JWT 登录：POST /api/auth/register、POST /api/auth/login、GET /api/auth/me
   - 响应字段必须与旧版一致：access_token / token_type / user_id / username
   - 密码 BCrypt；JWT 过滤器把 userId 放入请求上下文
   - GET /api/auth/me 必须同时支持 query 参数 token（前端 getCurrentUser(token) 就是这么调），不能只读 Header
   - 其余接口保持旧版宽松策略，不要顺手加严鉴权（会导致前端 401 风暴）
5. 只读接口（先不做写）：
   GET /api/subjects、/api/subjects/{id}
   GET /api/chapters?subject_id=、/api/chapters/{id}
   GET /api/knowledge-points?chapter_id=
   GET /api/problems?knowledge_point_id=、/api/problems/{id}
   注意：题目响应里绝对不能有 answer / explanation 字段。
6. 静态资源：挂载 /uploads/**，并托管 frontend/dist（同现有 main.py 的做法）。
7. 实体注意：problems 的列名 type 是 MySQL 关键字，MyBatis-Plus 用 @TableField("`type`")；
   materials.created_at 可空，其余业务表字段多为 NOT NULL；
   ID 必须沿用旧前缀：user- / sub- / chap- / kp- / prob- / var- / session-，
   materials 与 material_chunks 是完整 UUID（前端和既有数据都依赖这个格式）。

验收（必须真实执行并贴输出）：
- ./mvnw -q clean package -DskipTests 成功
- 启动后 curl 登录拿到 access_token
- 用 token curl GET /api/subjects 返回真实数据（不是空数组也要说明为什么）
- curl GET /api/problems?knowledge_point_id=xxx 的输出里 grep 不到 answer

完成后 git add + commit，message 写 "feat(java): P1 骨架与只读链路"。然后停下等我确认。
```

---

### P2 · 业务闭环（判分 / 错题本 / 上传）

```text
执行 P2 阶段，继续在 studyflow-java/ 内实现，不改动已有 P1 代码结构。

范围：
1. 作答与判分：POST /api/attempts
   - 请求含 problem_id、answer、client_token
   - 服务端查题比对 answer，写 attempts；答错则 upsert wrong_book；更新统计
   - client_token 幂等：唯一索引冲突时返回上次结果，不重复计分
   - 该题 answer 为空时返回 400 {"detail":"该题无答案"}
2. GET /api/attempts/overview、GET /api/attempts/{target_type}/{target_id}
3. GET /api/wrong-book（支持 mastered 过滤）
4. 错因档案：/api/errors 的 CRUD + /api/errors/meta + /api/errors/statistics + /api/errors/decide
   —— 全部用 Java 业务代码实现，/decide 是规则决策树，**不调 AI**
   （specific_behavior 按 API 的 50 字校验，库宽 200）
5. 写接口补齐：subjects / chapters / knowledge-points / problems / variants 的 POST/PUT/DELETE
6. 删除必须手写级联（DB 没有 ON DELETE CASCADE）：
   Subject → Chapter → KnowledgePoint → Problem → Variant
   但 attempts / wrong_book / error_analyses **不随题目删除**，保持旧行为
7. 删除响应结构各不相同，原样保留：
   subjects → {"code":0,"message":"删除成功","deletedProblems":n}
   chapters / knowledge-points → {"message":"删除成功","deletedProblems":n}
8. Flyway 追加 V2：给 attempts 加 UNIQUE(client_token)（旧库没有此约束，注明是有意变更）
9. 上传：POST /api/upload（图片）、POST /api/materials/upload（教材，先只存文件和元数据）、
   GET /api/materials、GET /api/materials/{id}/chunks、DELETE /api/materials/{id}

验收（真实执行贴输出）：
- 答对一次：attempts 新增 1 条，wrong_book 无记录
- 同一 client_token 重复提交：attempts 仍只有 1 条
- 答错一次：wrong_book 出现该题；再答对：mastered=1
- 上传一个 txt 到 /api/materials/upload，能在 GET /api/materials 里看到

完成后 commit，message 写 "feat(java): P2 判分错题本与上传"。停下等我确认。
```

---

### P3 · Python 服务瘦身

```text
执行 P3 阶段：基于 代码/ 复制出 studyflow-ai-service/，做减法而不是重写。
（本阶段范围以 解耦方案 第十四、十五节为准，前文与此冲突以那两节为准）

删除（必须彻底，不留入口）：
1. app/models/、app/routers/、app/agent/、app/rag/
2. services/auth.py、services/memory.py
3. services/recommend.py、services/error.py 里的数据库依赖部分
4. core/ 里的数据库配置；requirements.txt 去掉 sqlalchemy / pymysql / passlib /
   python-jose / alembic / faiss

改造（拆纯函数，不要重写算法）：
5. question_generator.generate_questions → generate_questions_payload(
   chapter_title, chapter_content, count, difficulty, existing_titles)
   不接 db、不落库、返回 (questions, dropped, reasons)；
   Python 侧校验：4 选项齐全、answer 合法、题干去重
6. recommend.recommend_variants → 保持签名（入参是题目对象，不是 id），去掉内部查库
7. materials 解析 → 返回 chunks + outline（chapter_outline.py 是正则启发式，不是 LLM），不写库
8. chat → 删掉 agent 与记忆表，只保留：心月狐 system prompt + 题目上下文 + history + message
   → 返回 {"reply": "..."}，不支持 function calling

新增 app/api/（全部 POST，校验 X-Internal-Token，响应 {"ok":true,"data":...}）：
9. /ai/parse-material    → {chunks, outline, warnings}
10. /ai/generate-questions → {questions, dropped, drop_reasons}
11. /ai/variants          → {variants, dropped}
12. /ai/chat              → {reply}
13. /health
注意：不要做 /ai/analyze-error、/ai/search、/ai/index/*（本期不做）

验收（真实执行贴输出）：
- curl /health 返回 ok
- curl /ai/generate-questions 传真实章节文字，返回 5 题且 dropped 有值
- curl /ai/chat 传 history，能返回回复
- 全目录 grep：不存在 sqlalchemy / SessionLocal / pymysql / chat_messages / faiss

完成后 commit，message 写 "refactor(py): P3 瘦身为无状态 AI 服务"。停下等我确认。
```

---

### P4 · Java 接 AI（异步任务）

```text
执行 P4 阶段：把 Java 与 Python 服务接起来。

范围：
1. AiClient（Spring RestClient）：统一带 X-Internal-Token，超时可配（默认 180s）
2. ai_jobs 任务：AiJobService + 异步线程池
   - POST /api/chapters/{id}/generate → 建 job 立即返回 {job_id}
   - GET /api/ai-jobs/{id} → {status, result, error}
   - 任务失败不写任何业务数据
3. 出题落库：Python 返回后，Java 再校验一遍 → 单事务批量插 problems
   + 知识点按名称在本章内先查后建（同名判重）
4. 教材解析链路：POST /api/materials/upload → 建 job 调 /ai/parse-material
   → 写 material_chunks + 大纲草案；GET /api/materials/{id}/outline；POST outline/confirm 写 chapters
5. 陪练：POST /api/chat 查题 + 最近 10 轮消息 → 调 /ai/chat → 存两条消息 → 返回
6. 变式题：POST /api/recommend 调 /ai/variants 拿候选；
   POST /api/variants/from-recommendation 仍然只是保存前端传来的结果
7. /api/problems/search 用 MySQL 关键词检索（题干 + 标题），**不调 AI**
8. /api/errors/decide 用 Java 规则实现，**不调 AI**
9. GET /api/materials/{id}/outline 从 Java 库读草案，不回头调 Python；
   教材检索留在 Java（SQL 取 chunks + 二元组打分）

验收（真实执行贴输出）：
- 触发一次出题 → 轮询 job 到 success → GET /api/problems 看到新题，日志里 dropped 有值
- 上传 PDF → 轮询 → 拿到大纲 → confirm 后 GET /api/chapters 能看到新章节
- 调一次 /api/chat（带 question_id）→ 返回回复，且 chat_messages 新增 2 条
- 停掉 Python 服务后：登录、看题、做题、错题本、题目检索仍正常（解耦是否成功的硬指标）
- 停掉 Python 后只有这四个功能会失败：出题、教材解析、变式推荐、聊天

完成后 commit，message 写 "feat(java): P4 AI 接线与异步任务"。
```

---

### P5 · 切流与回归

```text
执行 P5 阶段：完成切换，不写新功能。

1. 前端 vite.config.js 的 /api 与 /uploads 代理目标改为 http://localhost:8080
2. 前端出题调用改为异步（api/index.js 的 generateChapterQuestions、
   ChapterList.vue:118、SubjectList.vue:383）：提交任务 → 轮询 → 刷新
3. npm run build，确认 Java 能托管 dist 且界面正常
4. 全链路回归并贴每步真实输出：
   登录 → 看树 → 看题 → 做题判分 → 错题本 → 上传教材 → 解析 → 确认章节
   → AI 出题 → 做题 → 问心月狐
5. 输出《迁移报告.md》：接口对照表、剩余差异、已知问题、启动方式

完成后 commit，message 写 "chore: P5 切流与全链路回归"。
```

---

## 四、每个阶段怎么验收（不用懂代码也能判断）

| 看什么 | 合格 | 不合格信号 |
|---|---|---|
| curl 输出 | 有真实数据（真实章节名、真实题目） | 字段完美但全 `null`、`example` 之类假数据 |
| 报错信息 | 是中文 `{"detail":"..."}` | Spring 默认的 `{"timestamp","status","error","path"}` |
| 字段名 | `access_token`、`subject_id` 这种下划线 | `accessToken`、`subjectId` 驼峰 |
| commit | 每个阶段都有 hash | 一次 commit 覆盖全部阶段 |
| 停掉 Python | 业务功能照常 | 登录/做题也挂了 → 说明还有依赖没切断 |

---

## 五、卡住了怎么办

| 现象 | 处理 |
|---|---|
| 它说找不到 Maven | 让它用 `./mvnw`，第一次会自动下载 Maven |
| Flyway 报表已存在 | 让它先 `baseline` 或改用 `flyway.baseline-on-migrate=true` |
| 中文乱码 | 检查 `server.servlet.encoding.charset=UTF-8` 与数据库连接串 `characterEncoding=utf8` |
| 它开始改 `代码/` 目录 | 立刻打断：`不要修改 代码/ 目录，那是只读参考` |
| 上下文太长开始胡说 | `/clear`，重新贴该阶段提示词，让它先读 CLAUDE.md |
| 一次改太多导致跑不起来 | `git diff` 看改动，`git checkout -- .` 回退到上个 commit 重来 |

---

## 六、Claude 网页版能不能用

能，但**不推荐做这个改造**：它读不到你本地文件的真实内容，你得手工贴 13 张表结构 + 20 多个接口定义，贴漏一处它就编一个字段出来，最后对不上。网页版适合做单点任务，比如"帮我把这个 Vue 组件的出题调用改成轮询"，改完你自己贴回文件。整体改造用 Claude Code。
