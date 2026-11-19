#!/usr/bin/env bash
# P2 业务闭环验收脚本：V2 迁移 / 判分 / 幂等 / 错题本 / 级联删除 / 错因决策树。
# 默认在 18080 启动一个独立 Java 实例，不影响正在运行的 8080 服务。
set -u
export PYTHONIOENCODING=utf-8

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
JAVA_DIR="$ROOT/studyflow-java"
BASE="http://127.0.0.1:18080"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/sf-p2-verify-XXXXXX")"
PASSED=0
FAILED=0
APP_PID=""
APP_LOG="$TMP/app.log"
FIXTURE_PROBLEM_ID=""
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-3306}"
DB_NAME="${DB_NAME:-studyflow_ai}"

pass() { PASSED=$((PASSED + 1)); echo "PASS: $1"; }
fail() { FAILED=$((FAILED + 1)); echo "FAIL: $1"; }

check_eq() {
  if [ "$1" = "$2" ]; then pass "$3"; else fail "$3 (expected [$2], got [$1])"; fi
}

check_contains() {
  case "$1" in
    *"$2"*) pass "$3" ;;
    *) fail "$3 (missing [$2] in [$1])" ;;
  esac
}

jget() {
  python -c "import sys,json;d=json.load(sys.stdin);print($1)" < "$TMP/body" 2>/dev/null
}

http_status() { cat "$TMP/status" 2>/dev/null || true; }

api_get() {
  curl -sS -o "$TMP/body" -w '%{http_code}' "$BASE$1" > "$TMP/status" 2>/dev/null
  http_status
}

api_post() {
  curl -sS -o "$TMP/body" -w '%{http_code}' -X POST "$BASE$1" \
    -H 'Content-Type: application/json; charset=UTF-8' --data-binary @"$2" > "$TMP/status" 2>/dev/null
  http_status
}

api_put() {
  curl -sS -o "$TMP/body" -w '%{http_code}' -X PUT "$BASE$1" \
    -H 'Content-Type: application/json; charset=UTF-8' --data-binary @"$2" > "$TMP/status" 2>/dev/null
  http_status
}

api_delete() {
  curl -sS -o "$TMP/body" -w '%{http_code}' -X DELETE "$BASE$1" > "$TMP/status" 2>/dev/null
  http_status
}

# ---------- database ----------
if [ ! -f "$JAVA_DIR/.env" ]; then
  echo "FAIL: 缺少 $JAVA_DIR/.env（需要 DB_PASSWORD）"
  exit 1
fi
set -a
# shellcheck disable=SC1091
. "$JAVA_DIR/.env"
set +a
DB_USERNAME="${DB_USERNAME:-root}"
if [ -z "${DB_PASSWORD:-}" ]; then
  echo "FAIL: .env 中缺少 DB_PASSWORD"
  exit 1
fi

mysql_exec() {
  MYSQL_PWD="$DB_PASSWORD" mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USERNAME" \
    --default-character-set=utf8mb4 "$DB_NAME"
}

mysql_q() {
  MYSQL_PWD="$DB_PASSWORD" mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USERNAME" \
    --default-character-set=utf8mb4 -N -B -e "$1" "$DB_NAME" 2>/dev/null | tr -d '\r'
}

new_id() {
  python -c "import uuid;print('${1}'+uuid.uuid4().hex[:8])"
}

# ---------- app lifecycle ----------
stop_app() {
  if [ -n "${APP_PID:-}" ]; then
    taskkill //F //PID "$APP_PID" >/dev/null 2>&1 || kill "$APP_PID" >/dev/null 2>&1 || true
    APP_PID=""
  fi
}

wait_down() {
  for _ in $(seq 1 40); do
    if ! curl -s -o /dev/null --max-time 1 "$BASE/health"; then
      return 0
    fi
    sleep 0.5
  done
  return 1
}

start_app() {
  local log="$1"
  : > "$log"
  ( cd "$JAVA_DIR" && exec java -jar "$JAR" --server.port=18080 ) > "$log" 2>&1 &
  local shell_pid=$!
  if ! curl -sS --retry 60 --retry-delay 1 --retry-connrefused "$BASE/health" >/dev/null 2>&1; then
    APP_PID="$shell_pid"
    return 1
  fi
  APP_PID="$(netstat -ano 2>/dev/null | grep ':18080' | grep LISTENING | awk '{print $5}' | head -1)"
  [ -z "$APP_PID" ] && APP_PID="$shell_pid"
  return 0
}

cleanup() {
  stop_app
  if [ -n "$FIXTURE_PROBLEM_ID" ]; then
    mysql_q "DELETE FROM attempts WHERE target_id='$FIXTURE_PROBLEM_ID';" >/dev/null 2>&1 || true
    mysql_q "DELETE FROM wrong_book WHERE target_id='$FIXTURE_PROBLEM_ID';" >/dev/null 2>&1 || true
    mysql_q "DELETE FROM error_analyses WHERE problem_id='$FIXTURE_PROBLEM_ID';" >/dev/null 2>&1 || true
  fi
  rm -rf "$TMP"
}
trap cleanup EXIT

# ---------- locate / build jar ----------
JAR="$(ls "$JAVA_DIR"/target/studyflow-java-*.jar 2>/dev/null | head -1)"
if [ -z "$JAR" ]; then
  echo "jar 不存在，先构建..."
  ( cd "$JAVA_DIR" && ./mvnw -q clean package -DskipTests ) || {
    echo "FAIL: Maven 构建失败"
    exit 1
  }
  JAR="$(ls "$JAVA_DIR"/target/studyflow-java-*.jar 2>/dev/null | head -1)"
fi

if curl -s -o /dev/null --max-time 1 "$BASE/health"; then
  echo "FAIL: 端口 18080 已被占用，请先释放"
  exit 1
fi

echo "== 启动验收实例（18080）=="
if ! start_app "$TMP/app1.log"; then
  echo "FAIL: 第一次启动失败"
  tail -30 "$TMP/app1.log" 2>/dev/null || true
  exit 1
fi
pass "第一次启动成功"

V2_ROWS="$(mysql_q "SELECT COUNT(*) FROM flyway_schema_history WHERE version='2' AND success=1;")"
check_eq "$V2_ROWS" "1" "V2 迁移在 flyway_schema_history 中成功"
COL="$(mysql_q "SELECT COUNT(*) FROM information_schema.columns WHERE table_schema='$DB_NAME' AND table_name='attempts' AND column_name='client_token';")"
check_eq "$COL" "1" "attempts.client_token 列存在"
IDX="$(mysql_q "SELECT COUNT(*) FROM information_schema.statistics WHERE table_schema='$DB_NAME' AND table_name='attempts' AND index_name='uk_attempts_client_token';")"
check_eq "$IDX" "1" "attempts.client_token 唯一索引存在"

stop_app
wait_down || true
echo "== 重启验收实例 =="
if ! start_app "$TMP/app2.log"; then
  echo "FAIL: 第二次启动失败"
  tail -30 "$TMP/app2.log" 2>/dev/null || true
  exit 1
fi
check_contains "$(cat "$TMP/app2.log")" "up to date. No migration necessary." "重启不重复执行迁移"
if grep -q " ERROR " "$TMP/app2.log"; then
  fail "重启日志没有 ERROR"
else
  pass "重启日志没有 ERROR"
fi
V2_ROWS_AGAIN="$(mysql_q "SELECT COUNT(*) FROM flyway_schema_history WHERE version='2';")"
check_eq "$V2_ROWS_AGAIN" "1" "V2 历史记录没有重复"

# ---------- 测试固件 ----------
STAMP="$(date +%s)-$RANDOM"
SUBJECT_NAME="P2 Verify $STAMP"
CHAPTER_NAME="P2 Chapter $STAMP"
KP_NAME="P2 KP $STAMP"

cat > "$TMP/subject.json" <<EOF
{"name":"$SUBJECT_NAME","description":"p2 verify"}
EOF
STATUS="$(api_post /api/subjects "$TMP/subject.json")"
check_eq "$STATUS" "200" "POST /api/subjects 创建科目"
SID="$(jget "d['id']")"
check_contains "$SID" "sub-" "科目 ID 前缀 sub-"

cat > "$TMP/subject_put.json" <<EOF
{"name":"$SUBJECT_NAME updated","description":"p2 verify updated"}
EOF
STATUS="$(api_put "/api/subjects/$SID" "$TMP/subject_put.json")"
check_eq "$STATUS" "200" "PUT /api/subjects/{id} 更新科目"
api_get "/api/subjects/$SID" >/dev/null
check_eq "$(jget "d['name']")" "$SUBJECT_NAME updated" "科目更新已生效"

cat > "$TMP/chapter.json" <<EOF
{"subject_id":"$SID","name":"$CHAPTER_NAME","order_num":0}
EOF
STATUS="$(api_post /api/chapters "$TMP/chapter.json")"
check_eq "$STATUS" "200" "POST /api/chapters 创建章节"
CID="$(jget "d['id']")"
check_contains "$CID" "chap-" "章节 ID 前缀 chap-"

cat > "$TMP/chapter_put.json" <<EOF
{"subject_id":"$SID","name":"$CHAPTER_NAME updated","order_num":1}
EOF
STATUS="$(api_put "/api/chapters/$CID" "$TMP/chapter_put.json")"
check_eq "$STATUS" "200" "PUT /api/chapters/{id} 更新章节"

cat > "$TMP/kp.json" <<EOF
{"chapter_id":"$CID","name":"$KP_NAME"}
EOF
STATUS="$(api_post /api/knowledge-points "$TMP/kp.json")"
check_eq "$STATUS" "200" "POST /api/knowledge-points 创建知识点"
KID="$(jget "d['id']")"
check_contains "$KID" "kp-" "知识点 ID 前缀 kp-"

cat > "$TMP/kp_put.json" <<EOF
{"chapter_id":"$CID","name":"$KP_NAME updated"}
EOF
STATUS="$(api_put "/api/knowledge-points/$KID" "$TMP/kp_put.json")"
check_eq "$STATUS" "200" "PUT /api/knowledge-points/{id} 更新知识点"

cat > "$TMP/problem.json" <<EOF
{"title":"P2 API problem $STAMP","content":"api problem","source":"manual","tags":"p2","knowledge_point_id":"$KID"}
EOF
STATUS="$(api_post /api/problems "$TMP/problem.json")"
check_eq "$STATUS" "200" "POST /api/problems 创建题目"
API_PROBLEM_ID="$(jget "d['id']")"
check_contains "$API_PROBLEM_ID" "prob-" "题目 ID 前缀 prob-"

cat > "$TMP/problem_put.json" <<EOF
{"title":"P2 API problem updated","content":"api problem updated","source":"manual","tags":"p2","knowledge_point_id":"$KID"}
EOF
STATUS="$(api_put "/api/problems/$API_PROBLEM_ID" "$TMP/problem_put.json")"
check_eq "$STATUS" "200" "PUT /api/problems/{id} 更新题目"
api_get "/api/problems/$API_PROBLEM_ID" >/dev/null
check_eq "$(jget "d['title']")" "P2 API problem updated" "题目更新已生效"

cat > "$TMP/attempt_no_answer.json" <<EOF
{"target_type":"problem","target_id":"$API_PROBLEM_ID","user_answers":["A"],"client_token":"p2-$STAMP-noanswer","source":"manual"}
EOF
STATUS="$(api_post /api/attempts "$TMP/attempt_no_answer.json")"
check_eq "$STATUS" "400" "无答案题目判分返回 400"
check_eq "$(jget "d['detail']")" "该题无答案" "无答案题目的 detail 文案"
NO_ANSWER_ROWS="$(mysql_q "SELECT COUNT(*) FROM attempts WHERE target_id='$API_PROBLEM_ID';")"
check_eq "$NO_ANSWER_ROWS" "0" "无答案题目不写 attempts"

STATUS="$(api_delete "/api/problems/$API_PROBLEM_ID")"
check_eq "$STATUS" "200" "DELETE /api/problems/{id} 删除题目"
check_eq "$(jget "d['message']")" "删除成功" "题目删除响应 message"

# 用于判分的题目：手工插入 answer=A，旧版写接口不暴露 answer
FIXTURE_PROBLEM_ID="$(new_id prob-)"
mysql_exec <<SQL
INSERT INTO problems
  (id, title, source, tags, status, knowledge_point_id, created_at, type, options, answer, explanation, difficulty)
VALUES
  ('$FIXTURE_PROBLEM_ID', 'P2 grading problem', 'P2', 'p2', 'todo', '$KID', NOW(),
   'single', '["A","B","C","D"]', 'A', 'P2 explanation', 3);
SQL
EXISTS="$(mysql_q "SELECT COUNT(*) FROM problems WHERE id='$FIXTURE_PROBLEM_ID';")"
check_eq "$EXISTS" "1" "判分用题目已插入"

# 变式：V1 留给级联删除，V2 用于 CRUD 删除
cat > "$TMP/variant.json" <<EOF
{"problem_id":"$FIXTURE_PROBLEM_ID","title":"P2 variant keep","content":null,"difficulty":"easy","link":null,"reason":"verify"}
EOF
STATUS="$(api_post /api/variants "$TMP/variant.json")"
check_eq "$STATUS" "200" "POST /api/variants 创建变题"
V1_ID="$(jget "d['id']")"
check_contains "$V1_ID" "var-" "变题 ID 前缀 var-"

cat > "$TMP/variant_put.json" <<EOF
{"problem_id":"$FIXTURE_PROBLEM_ID","title":"P2 variant keep updated","content":null,"difficulty":"medium","link":null,"reason":"verify"}
EOF
STATUS="$(api_put "/api/variants/$V1_ID" "$TMP/variant_put.json")"
check_eq "$STATUS" "200" "PUT /api/variants/{id} 更新变题"

cat > "$TMP/variant2.json" <<EOF
{"problem_id":"$FIXTURE_PROBLEM_ID","title":"P2 variant delete","content":null,"difficulty":"hard","link":null,"reason":"verify"}
EOF
STATUS="$(api_post /api/variants "$TMP/variant2.json")"
V2_ID="$(jget "d['id']")"
STATUS="$(api_delete "/api/variants/$V2_ID")"
check_eq "$STATUS" "200" "DELETE /api/variants/{id} 删除变题"

# ---------- 判分 / 幂等 / 错题本 ----------
TOKEN_CORRECT="p2-$STAMP-correct"
TOKEN_WRONG="p2-$STAMP-wrong"

cat > "$TMP/attempt_correct.json" <<EOF
{"target_type":"problem","target_id":"$FIXTURE_PROBLEM_ID","user_answers":["A"],"client_token":"$TOKEN_CORRECT","source":"manual"}
EOF
STATUS="$(api_post /api/attempts "$TMP/attempt_correct.json")"
check_eq "$STATUS" "200" "正确作答返回 200"
check_eq "$(jget "d['result']")" "correct" "正确作 answer=A 判为 correct"
check_eq "$(jget "d['correct_answer']")" "A" "判分响应包含 correct_answer"
ATT_COUNT="$(mysql_q "SELECT COUNT(*) FROM attempts WHERE target_id='$FIXTURE_PROBLEM_ID';")"
check_eq "$ATT_COUNT" "1" "正确作答写入 1 条 attempts"

cat > "$TMP/attempt_wrong.json" <<EOF
{"target_type":"problem","target_id":"$FIXTURE_PROBLEM_ID","user_answers":["B"],"client_token":"$TOKEN_WRONG","source":"manual"}
EOF
STATUS="$(api_post /api/attempts "$TMP/attempt_wrong.json")"
check_eq "$STATUS" "200" "错误作答返回 200"
check_eq "$(jget "d['result']")" "wrong" "错误作答 answer=B 判为 wrong"
ATT_COUNT="$(mysql_q "SELECT COUNT(*) FROM attempts WHERE target_id='$FIXTURE_PROBLEM_ID';")"
check_eq "$ATT_COUNT" "2" "错误作答后 attempts 共 2 条"

api_get "/api/wrong-book?mastered=false" >/dev/null
WB_COUNT="$(python -c "import sys,json;d=json.load(sys.stdin);print(sum(1 for i in d['items'] if i['target_id']=='$FIXTURE_PROBLEM_ID'))" < "$TMP/body")"
check_eq "$WB_COUNT" "1" "错误作答后 wrong_book 出现该题"
api_get "/api/wrong-book?mastered=false" >/dev/null
WB_WRONG_COUNT="$(python -c "import sys,json;d=json.load(sys.stdin);print([i['wrong_count'] for i in d['items'] if i['target_id']=='$FIXTURE_PROBLEM_ID'][0])" < "$TMP/body" 2>/dev/null)"
check_eq "$WB_WRONG_COUNT" "1" "wrong_book.wrong_count = 1"

# 同一 client_token 重复提交：即使本次答案不同，也必须返回上次的 wrong
cat > "$TMP/attempt_dup.json" <<EOF
{"target_type":"problem","target_id":"$FIXTURE_PROBLEM_ID","user_answers":["A"],"client_token":"$TOKEN_WRONG","source":"manual"}
EOF
STATUS="$(api_post /api/attempts "$TMP/attempt_dup.json")"
check_eq "$STATUS" "200" "重复 client_token 返回 200"
check_eq "$(jget "d['result']")" "wrong" "重复 client_token 返回上次结果 wrong"
ATT_COUNT="$(mysql_q "SELECT COUNT(*) FROM attempts WHERE target_id='$FIXTURE_PROBLEM_ID';")"
check_eq "$ATT_COUNT" "2" "重复 client_token 没有新增 attempts"
WB_WRONG_COUNT="$(mysql_q "SELECT wrong_count FROM wrong_book WHERE target_id='$FIXTURE_PROBLEM_ID';")"
check_eq "$WB_WRONG_COUNT" "1" "重复 client_token 没有重复累加 wrong_count"
TOKEN_ROWS="$(mysql_q "SELECT COUNT(*) FROM attempts WHERE client_token='$TOKEN_WRONG';")"
check_eq "$TOKEN_ROWS" "1" "同一 client_token 只有一条记录"

api_get "/api/attempts/problem/$FIXTURE_PROBLEM_ID" >/dev/null
check_eq "$(jget "d['stats']['total']")" "2" "GET /api/attempts/{type}/{id} 返回 stats.total=2"
check_eq "$(jget "len(d['attempts'])")" "2" "GET /api/attempts/{type}/{id} 返回 2 条历史"
api_get "/api/attempts/overview?knowledge_point_id=$KID" >/dev/null
check_eq "$(jget "d['stats']['$FIXTURE_PROBLEM_ID']['total']")" "2" "GET /api/attempts/overview 按知识点聚合"

# ---------- 错因：meta / decide / CRUD / statistics ----------
api_get "/api/errors/meta" >/dev/null
check_eq "$(jget "len(d['error_types'])")" "6" "meta 返回 6 类错因"
check_eq "$(jget "len(d['decision_tree'])")" "6" "meta 返回 6 步决策树"
check_eq "$(jget "d['tags'][0]['attach_to']")" "OPERATE" "meta 的 SYNTAX 标签挂到 OPERATE"
check_eq "$(jget "len(d['remedy_status'])")" "2" "meta 返回 2 种补救状态"

decide_case() {
  local answers="$1" expected="$2" label="$3"
  printf '{"answers":%s}' "$answers" > "$TMP/decide.json"
  STATUS="$(api_post /api/errors/decide "$TMP/decide.json")"
  check_eq "$STATUS" "200" "$label HTTP"
  check_eq "$(jget "d['error_type']")" "$expected" "$label"
}

decide_case '[false]' 'READ' 'decide Q1=否 -> READ'
decide_case '[true,false]' 'IDENTIFY' 'decide Q2=否 -> IDENTIFY'
decide_case '[true,true,true]' 'DECOMPOSE' 'decide Q3=是 -> DECOMPOSE'
decide_case '[true,true,false,true]' 'OPERATE' 'decide Q4=是 -> OPERATE'
decide_case '[true,true,false,false,true]' 'BOUNDARY' 'decide Q5=是 -> BOUNDARY'
decide_case '[true,true,false,false,false,true]' 'EFFICIENCY' 'decide Q6=是 -> EFFICIENCY'

cat > "$TMP/decide_syntax.json" <<'EOF'
{"answers":[true,true,false,true],"specific_behavior":"空指针"}
EOF
STATUS="$(api_post /api/errors/decide "$TMP/decide_syntax.json")"
check_eq "$(jget "d['suggest_syntax_tag']")" "True" "OPERATE + 空指针 -> 建议 SYNTAX"

cat > "$TMP/decide_nosyntax.json" <<'EOF'
{"answers":[false],"specific_behavior":"空指针"}
EOF
STATUS="$(api_post /api/errors/decide "$TMP/decide_nosyntax.json")"
check_eq "$(jget "d['suggest_syntax_tag']")" "False" "非 OPERATE -> 不建议 SYNTAX"

cat > "$TMP/error_create.json" <<EOF
{"problem_id":"$FIXTURE_PROBLEM_ID","problem_title":"P2 grading problem","topic":"p2","error_type":"OPERATE","tag":"SYNTAX","specific_behavior":"nullptr","first_break_point":"OPERATE","remedy_status":"待补","reviewed":false}
EOF
STATUS="$(api_post /api/errors "$TMP/error_create.json")"
check_eq "$STATUS" "200" "POST /api/errors 创建归因"
ERROR_ID="$(jget "d['record']['id']")"
check_eq "$(jget "d['record']['error_type']")" "OPERATE" "归因 error_type 正确"
check_eq "$(jget "d['suggest_syntax_tag']")" "True" "OPERATE + nullptr -> 建议 SYNTAX"

python -c "print('{\"problem_id\":\"$FIXTURE_PROBLEM_ID\",\"problem_title\":\"P2\",\"error_type\":\"OPERATE\",\"specific_behavior\":\"' + 'x'*51 + '\",\"first_break_point\":\"OPERATE\"}')" > "$TMP/error_long.json"
STATUS="$(api_post /api/errors "$TMP/error_long.json")"
check_eq "$STATUS" "400" "specific_behavior 超过 50 字返回 400"
check_eq "$(jget "d['detail']")" "specific_behavior 不能超过 50 字" "specific_behavior 50 字校验文案"

cat > "$TMP/error_decompose_ok.json" <<EOF
{"problem_id":"$FIXTURE_PROBLEM_ID","problem_title":"P2","error_type":"DECOMPOSE","specific_behavior":"拆解","decomposition_sentence":"这题 = 母题 + 改条件","first_break_point":"DECOMPOSE"}
EOF
STATUS="$(api_post /api/errors "$TMP/error_decompose_ok.json")"
check_eq "$STATUS" "200" "DECOMPOSE 合法拆解句创建成功"
DECOMPOSE_ID="$(jget "d['record']['id']")"

cat > "$TMP/error_decompose_bad.json" <<EOF
{"problem_id":"$FIXTURE_PROBLEM_ID","problem_title":"P2","error_type":"DECOMPOSE","specific_behavior":"拆解","decomposition_sentence":"只有母题","first_break_point":"DECOMPOSE"}
EOF
STATUS="$(api_post /api/errors "$TMP/error_decompose_bad.json")"
check_eq "$STATUS" "400" "DECOMPOSE 缺关键词返回 400"

api_get "/api/errors?problem_id=$FIXTURE_PROBLEM_ID" >/dev/null
check_eq "$(jget "len(d)")" "2" "GET /api/errors 按 problem_id 过滤"

cat > "$TMP/error_update.json" <<'EOF'
{"reviewed":true}
EOF
STATUS="$(api_put "/api/errors/$ERROR_ID" "$TMP/error_update.json")"
check_eq "$STATUS" "200" "PUT /api/errors/{id} 更新归因"
check_eq "$(jget "d['reviewed']")" "True" "归因 reviewed 更新为 true"

STATUS="$(api_delete "/api/errors/$DECOMPOSE_ID")"
check_eq "$STATUS" "200" "DELETE /api/errors/{id} 删除归因"
check_eq "$(jget "d['message']")" "删除成功" "归因删除响应 message"

api_get "/api/errors/statistics?practice_mode=true" >/dev/null
check_eq "$(jget "'error_distribution' in d and 'remedy_pending_count' in d")" "True" "GET /api/errors/statistics 练习模式字段"
api_get "/api/errors/statistics?practice_mode=false" >/dev/null
check_eq "$(jget "'accuracy' in d and 'avg_time_sec' in d and 'stability' in d")" "True" "statistics 模拟模式附加字段"

if grep -R -l "AiClient" "$JAVA_DIR/src/main/java/com/studyflow" --include='*Error*.java' 2>/dev/null | grep -q .; then
  fail "errors 相关代码无 AiClient 引用"
else
  pass "errors 相关代码无 AiClient 引用"
fi

# ---------- 级联删除 ----------
BEFORE_ATTEMPTS="$(mysql_q "SELECT COUNT(*) FROM attempts WHERE target_id='$FIXTURE_PROBLEM_ID';")"
BEFORE_WRONG="$(mysql_q "SELECT COUNT(*) FROM wrong_book WHERE target_id='$FIXTURE_PROBLEM_ID';")"
BEFORE_ERRORS="$(mysql_q "SELECT COUNT(*) FROM error_analyses WHERE problem_id='$FIXTURE_PROBLEM_ID';")"

STATUS="$(api_delete "/api/knowledge-points/$KID")"
check_eq "$STATUS" "200" "DELETE /api/knowledge-points/{id} 返回 200"
KEYS="$(jget "','.join(sorted(d.keys()))")"
check_eq "$KEYS" "deletedProblems,message" "知识点删除响应只有 message/deletedProblems"
check_eq "$(jget "d['message']")" "删除成功" "知识点删除 message"
DELETED_PROBLEMS="$(jget "d['deletedProblems']")"
if [ "$DELETED_PROBLEMS" -gt 0 ]; then
  pass "知识点级联删除 deletedProblems > 0"
else
  fail "知识点级联删除 deletedProblems > 0 (got $DELETED_PROBLEMS)"
fi

PROBLEMS_LEFT="$(mysql_q "SELECT COUNT(*) FROM problems WHERE knowledge_point_id='$KID';")"
check_eq "$PROBLEMS_LEFT" "0" "知识点下题目已级联删除"
VARIANT_LEFT="$(mysql_q "SELECT COUNT(*) FROM variants WHERE id='$V1_ID';")"
check_eq "$VARIANT_LEFT" "0" "题目下变题已级联删除"

AFTER_ATTEMPTS="$(mysql_q "SELECT COUNT(*) FROM attempts WHERE target_id='$FIXTURE_PROBLEM_ID';")"
check_eq "$AFTER_ATTEMPTS" "$BEFORE_ATTEMPTS" "attempts 不随题目删除"
AFTER_WRONG="$(mysql_q "SELECT COUNT(*) FROM wrong_book WHERE target_id='$FIXTURE_PROBLEM_ID';")"
check_eq "$AFTER_WRONG" "$BEFORE_WRONG" "wrong_book 不随题目删除"
AFTER_ERRORS="$(mysql_q "SELECT COUNT(*) FROM error_analyses WHERE problem_id='$FIXTURE_PROBLEM_ID';")"
check_eq "$AFTER_ERRORS" "$BEFORE_ERRORS" "error_analyses 不随题目删除"

STATUS="$(api_delete "/api/chapters/$CID")"
check_eq "$STATUS" "200" "DELETE /api/chapters/{id} 返回 200"
KEYS="$(jget "','.join(sorted(d.keys()))")"
check_eq "$KEYS" "deletedProblems,message" "章节删除响应只有 message/deletedProblems"

STATUS="$(api_delete "/api/subjects/$SID")"
check_eq "$STATUS" "200" "DELETE /api/subjects/{id} 返回 200"
KEYS="$(jget "','.join(sorted(d.keys()))")"
check_eq "$KEYS" "code,deletedProblems,message" "科目删除响应包含 code/message/deletedProblems"
check_eq "$(jget "d['code']")" "0" "科目删除 code = 0"

# ---------- summary ----------
echo
echo "======================================"
echo "PASS: $PASSED   FAIL: $FAILED"
echo "======================================"
if [ "$FAILED" -gt 0 ]; then
  echo "验收失败，最近的 Java 日志："
  tail -30 "$TMP/app2.log" 2>/dev/null || true
  exit 1
fi
exit 0
