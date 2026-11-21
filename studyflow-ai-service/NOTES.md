# StudyFlow AI Service（P3）— 基线与实现备注

## 基线

- 参考代码：`代码/` @ `a29d3e4`（**工作区状态，含未提交修改**）
- 新仓库分支：`feat/p3-python-slim`
- 本阶段范围：仅 P3，Python 服务瘦身；不改 Java、不改前端、不改 `代码/`
- 设计依据：`解耦方案-Java+Python.md` 第十四、十五节（与前面章节冲突时以第十四节为准）

## 服务边界

- 只暴露 `/ai/**` 与 `/health`，请求头校验 `X-Internal-Token`
- 零数据库：无 SQLAlchemy / PyMySQL / SessionLocal / models / 会话 / 任务表
- 无状态：所有上下文由 Java 通过请求体传入，聊天历史不落库
- 本期不做：`/ai/analyze-error`、`/ai/search`、`/ai/index/*`、FAISS / RAG
- 算法尽量照搬旧实现：PyMuPDF 解析、正则大纲、题目校验、二元组分词逻辑留在 Java、prompt 拼装

## 端点

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/health` | 探活，不需要 token |
| POST | `/ai/parse-material` | PDF/TXT/Markdown → chunks + 大纲草案 |
| POST | `/ai/generate-questions` | 章节文本 → 题目数组 + dropped + drop_reasons |
| POST | `/ai/variants` | 母题 → 变式题推荐 |
| POST | `/ai/chat` | 心月狐陪练，无工具调用 |
| POST | `/ai/index/rebuild` | 全量重建内存向量索引 |
| GET | `/ai/index/status` | 索引条数、维度、模型名 |
| POST | `/ai/search` | 语义检索 top-k |

除 `/health` 外，所有请求必须带 `X-Internal-Token`，默认开发密钥为 `studyflow-dev-token`（生产环境必须用环境变量覆盖）。

## 实现备注

1. **`/ai/parse-material` 的 outline 结构**：与方案 5.1（已修正）和 `build_outline()` 一致，为扁平数组
   `[{name, start_page, end_page, page_count, chunk_count}]`；前端 `OutlineConfirm` 直接按
   `{name, start_page, end_page}` 提交。chunks 采用旧分块字段 `{page_no, seq, content, char_count}`，
   直接对齐 `material_chunks` 表；chunk/material 的 UUID 由 Java 落库时生成。
   响应额外带 `title/file_type/page_count/char_count/quality/warnings`，方便 Java 写 `materials` 记录。
2. **`/ai/generate-questions` 的题目结构**：直接对齐 `problems` 表与前端旧格式：
   `{title, options: ["A文字","B文字","C文字","D文字"], answer: "A"~"D", explanation, knowledge_point}`。
   不返回 `difficulty`、`type`、`source`、`tags`；Java 侧写 `type='single'`、整批统一 `difficulty`、
   `source='AI 生成'`、`tags='{章节名},AI出题'`。内部 prompt/校验继续使用 A/B/C/D、4 选项齐全、answer 合法、
   题干 ≥8 字、解析 ≥20 字、`_normalize_title` 去重。`difficulty` 入参是整数 1~5（`problems.difficulty`）；
   `easy/medium/hard` 只属于 `variants.difficulty`，出题响应不做任何难度归一化。
   若模型返回的题全部被校验丢弃，返回 `ok:true` + 空数组 + drop_reasons，由 Java 决定把任务标记失败；
   若模型一道题都没返回，返回 `empty_generation` 错误。
   出题 prompt 首句因新签名不再包含 `subject_name`，由「你是『{科目}』科目的出题老师」改为「你是一位出题老师」；
   其余 6 条硬性要求与 `PARSER.get_format_instructions()` 逐字保留。
3. **`/ai/variants`**：保留 `recommend_variants(problem, hierarchy, count)` 签名与 prompt/解析/两次重试逻辑。
   FAISS/RAG 本期下线，按 §14.13 删除 `semantic_search` 引用和检索调用，prompt 模板里的 `{retrieval_context}`
   传空字符串（模板保留）；**本期无 RAG 上下文，二期补**。响应为 `{variants, dropped: 0}`，
   两次解析失败时保留旧实现的兜底推荐项。请求体 `options/answer/explanation` 接收但不进 prompt
   （旧实现只用 stem + hierarchy + source + tags）。变式难度是 `easy/medium/hard`（`variants.difficulty`），
   不要与出题接口的整数 1~5 混用。
4. **`/ai/chat`**：删除 `app/agent/` 与 `services/memory.py` 后重写。只拼心月狐人设 + 题目上下文 + 最近 20 条历史
   （对应旧版 `DBMessageHistory(limit=20)`）+ 用户消息，不支持 function calling，不查库、不写库、不存会话。
   题目上下文字段与旧库/前端一致：`title` + `options` A/B/C/D 顺序数组 + `correct_answer`/`user_answer` 字母，
   Java 从库读出来可直接透传。
5. **鉴权**：仅 `X-Internal-Token`，不引入用户 JWT。`/health` 放行。
6. **依赖**：`requirements.txt` 不含 sqlalchemy / pymysql / passlib / python-jose / alembic / faiss。
7. **本地联调**：可设置 `DOTENV_PATH` 指向旧服务 `.env`（如 `代码/.env`）复用 `DEEPSEEK_API_KEY`，
   不需要把密钥复制进本目录，也不要提交 `.env`。

## §14.12 字段对照自查

| 检查项 | 实现 |
|---|---|
| 教材大纲 | 扁平 `{name,start_page,end_page,page_count,chunk_count}` |
| 出题-题干 | `title` |
| 出题-选项 | `["A文字","B文字","C文字","D文字"]` |
| 出题-答案 | `"A"~"D"` |
| 出题-题型 | 不返回；Java 写死 `single` |
| 出题-难度 | 不返回；请求整数 1~5 |
| 变式-难度 | `easy/medium/hard`，与出题难度不混用 |

## 启动

```bash
cd studyflow-ai-service
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

或：

```bash
python -m app.main
```

## 验收命令

```bash
curl http://127.0.0.1:8001/health

curl -X POST http://127.0.0.1:8001/ai/generate-questions \
  -H "Content-Type: application/json" \
  -H "X-Internal-Token: studyflow-dev-token" \
  -d '{"chapter_title":"1.1 数列极限","chapter_content":"……章节正文……","count":5,"difficulty":3,"existing_titles":[]}'

curl -X POST http://127.0.0.1:8001/ai/chat \
  -H "Content-Type: application/json" \
  -H "X-Internal-Token: studyflow-dev-token" \
  -d '{"persona":"xinyuehu","question":{"title":"……","options":["A选项","B选项","C选项","D选项"],"user_answer":"A","correct_answer":"B"},"history":[{"role":"user","content":"上一轮问题"},{"role":"assistant","content":"上一轮回答"}],"message":"我还是不懂为什么选 B"}'
```

## RAG 设计说明

### 内存索引的边界

- 索引只存在于 Python 进程内存（`app/rag/index.py` 的模块级单例），**不落盘、不连数据库**，符合本服务零数据库的定位。
- **服务重启即失**：重启后 `GET /ai/index/status` 返回 `count: 0`，这是预期行为，不是故障；`POST /ai/search` 在空索引上返回空数组，不报错、也不加载模型。
- 数据源始终是 Java 的 MySQL：Java 在启动、题目增删改、或定时任务里调用 `POST /ai/index/rebuild` **全量重建**。本期不做增量 upsert，也不做多进程共享（uvicorn 多 worker 时每个 worker 各有一份索引，如需多 worker 应固定为单 worker 或改成外部向量库）。
- `rebuild` 先算向量、在锁外构建好新的 `IndexFlatIP`，再在锁内原子替换；查询持锁读，embedder 与索引各自加锁，避免并发重建时读到半成品。

### 为什么选 bge-small 而不是更大的模型

- `BAAI/bge-small-zh-v1.5` 是中文检索专用句向量模型，**实际为 24M 参数、512 维**（不是 768 维；768 维的是 bge-base-zh-v1.5），CPU 即可推理，首次加载数秒、内存占用小。
- 本服务的检索对象是题目文本/教材片段，量级有限且查询低频；小模型的延迟和资源开销更适合与 Java 服务同机部署，效果足够区分「极限」与「计网」这类主题。
- 没用 Ollama embedding：避免引入外部服务依赖；本机访问不了 HuggingFace，`app/rag/embedder.py` 在导入 `sentence_transformers` 之前设置 `HF_ENDPOINT=https://hf-mirror.com`，模型从镜像下载。
- 模型懒加载：第一次 rebuild/search 才加载；`status` 不会触发下载。

### 相似度怎么算

1. `SentenceTransformer.encode(..., normalize_embeddings=True)` 输出 **L2 归一化**的 float32 向量；
2. FAISS 用 `IndexFlatIP`（暴力内积检索，精确解）；
3. 归一化后 **内积 = 余弦相似度**，`score` 取值约 [-1, 1]，中文短文本常见 0.3~0.8，越大越相关；
4. 查询侧按 BGE 官方建议加前缀「为这个句子生成表示以用于检索相关文章：」，文档侧不加；
5. 维度取自模型实际输出（当前 512），接口里的 `dim` 是动态值，没有写死 768。

### 端点

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/ai/index/rebuild` | `{"items":[{"id","text"}]}` 全量替换；空数组返回 400 |
| GET | `/ai/index/status` | `{count, dim, model}` |
| POST | `/ai/search` | `{"query","top_k"}` → `{results:[{id,score,text}]}`；空 query 400，空索引返回 `[]` |

三个端点均经过 `X-Internal-Token` 校验，响应沿用 `{"ok": true, "data": ...}` / `{"ok": false, "error": {...}}`。

### 与既有约束的关系

CLAUDE.md 第 14 节的「禁止本期接 FAISS / RAG」是 P3 阶段的范围约束；本期按新需求显式启用 RAG，仍保持零数据库、Java 唯一写库、题目列表不泄露答案。`/ai/variants` 的 `retrieval_context` 本期仍未接入，维持原状。
