# 学流智学 StudyFlow AI

AI 刷题平台：上传教材 PDF 自动解析章节，用大模型按章节出单项选择题，刷题判分进错题本，另有按人设回复的情感陪练。本项目已完成从 Python 单体到 **Java 业务服务 + 无状态 AI 服务** 的绞杀者模式迁移（完整演进历史见提交记录）。

## 架构

```
浏览器 (frontend/dist)
    │  全部 /api/**
    ▼
Java 业务服务 :8080 ──────────► MySQL studyflow_ai（13 张表 + ai_jobs）
    │  业务 · 判分 · 错题本 · 错因 · 异步任务
    │  仅 4 个 AI 能力走内网（X-Internal-Token）
    ▼
Python AI 服务 :8001 ─────────► DeepSeek / 本地模型
    零数据库 · 无状态
```

**故障隔离**：AI 服务宕机时，登录、看题、做题判分、错题本、错因、检索全部可用；只有出题、教材解析、变式推荐、聊天四个功能失败。

## 目录结构

```
studyflow-java/       Spring Boot 3.5 + MyBatis-Plus + Flyway，15 个 Controller
studyflow-ai-service/ FastAPI，仅 5 个端点，无数据库依赖
frontend/             Vue 3 + Element Plus（构建产物由 Java 托管）
schema/               真实表结构 DDL（Flyway V1 以此为准）
scripts/              verify-p1 / verify-p2 自动化验收脚本
docs/                 解耦方案、原型图、通俗版文档
代码/                  旧 Python 单体（只读存档，未纳入版本管理）
```

## 快速启动

```bash
# 1. 数据库：MySQL 8，执行 studyflow-java 的 Flyway 迁移（自动建表）
#    连接配置走环境变量，参考 studyflow-java/.env.example

# 2. AI 服务
cd studyflow-ai-service
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8001

# 3. Java 服务
cd studyflow-java
./mvnw spring-boot:run     # 默认 8080，托管前端页面
```

## 技术亮点

- **不信任模型输出**：出题走三层防线——prompt 硬约束 → Pydantic 结构化输出 + 超时重试 → 代码逐题校验（4 选项 / 答案合法 / 题干去重），不合格丢弃并计数
- **异步出题**：`ai_jobs` 任务表 + 线程池，POST 立即返回 job_id，前端轮询；失败只更新任务不写业务数据
- **幂等提交**：迁移中发现 `attempts` 表缺失幂等列（旧代码异常捕获永不生效），V2 迁移补 `client_token` 唯一索引
- **绞杀者模式迁移**：接口契约逐字段对齐 → 双跑 → 前端 0 改动切流，全程可回滚
- **95 项自动化验收**：`scripts/verify-p2.sh` 可重复执行，覆盖判分、幂等、级联删除、降级
