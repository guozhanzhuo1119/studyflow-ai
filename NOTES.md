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
