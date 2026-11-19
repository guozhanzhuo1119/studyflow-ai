<template>
  <div class="quiz-page">
    <!-- 顶部专注条 -->
    <header class="quiz-top">
      <button class="back-btn" @click="goBack">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M19 12H6M11 6l-6 6 6 6"/></svg>
        返回题库
      </button>
      <div class="top-mid">
        <span class="q-pos">第 {{ currentNo }} 题 <i>/</i> 共 {{ total }} 题</span>
        <div class="seg-progress">
          <span
            v-for="(q, i) in questions"
            :key="q.id"
            class="seg"
            :class="{ done: i < index, cur: i === index, ok: results[i] === 'correct', bad: results[i] && results[i] !== 'correct' }"
          ></span>
        </div>
      </div>
      <span class="timer">{{ timerText }}</span>
    </header>

    <!-- 题卡 -->
    <main class="quiz-body" v-if="current">
      <article class="quiz-card" :key="current.id">
        <div class="q-head">
          <span class="q-no">{{ pad(index + 1) }}</span>
          <span class="tag">{{ diffLabel(current.difficulty) }}</span>
          <span class="tag plain">单选题</span>
          <span class="tag plain" v-if="current.kp_name">{{ current.kp_name }}</span>
        </div>

        <h2 class="q-stem">{{ current.title }}</h2>
        <div class="q-content" v-if="current.content">
          <MarkdownViewer :source="current.content" />
        </div>

        <div class="options">
          <div
            v-for="(text, i) in current.options"
            :key="i"
            class="option"
            :class="optionClass(i)"
            @click="pick(i)"
          >
            <span class="opt-no">{{ i + 1 }}</span>
            <span class="opt-text">{{ text }}</span>
            <svg v-if="result && isCorrectOption(i)" class="opt-mark ok" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#5AE3D0" stroke-width="2.4" stroke-linecap="round"><path d="M5 13l4 4L19 7"/></svg>
            <svg v-else-if="result && picked === i && result.result !== 'correct'" class="opt-mark bad" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#F06A6A" stroke-width="2.4" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18"/></svg>
          </div>
        </div>

        <!-- 解析：提交后平滑展开 -->
        <div class="explain" :class="{ open: !!result }">
          <div class="explain-inner" v-if="result">
            <div class="explain-title">
              {{ result.result === 'correct' ? '回答正确，已标记为掌握' : '回答错误，已记入错题本' }}
            </div>
            <div class="explain-line">正确答案：{{ answerNoText }}</div>
            <div class="explain-line">解析：{{ result.explanation || '暂无解析' }}</div>
          </div>
        </div>

        <div class="quiz-actions">
          <p class="key-tip" v-if="!result">按数字键 1–4 选择 · 回车提交</p>
          <el-button
            v-if="!result"
            type="primary"
            size="large"
            :disabled="picked === null"
            :loading="submitting"
            @click="submit"
          >提交答案</el-button>
          <el-button
            v-else
            type="primary"
            size="large"
            @click="next"
          >{{ index === total - 1 ? '完成练习' : '下一题' }}</el-button>
        </div>
      </article>
    </main>

    <main class="quiz-body" v-else>
      <div class="quiz-card empty">
        <p v-if="loading">正在加载题目…</p>
        <template v-else>
          <p>本章暂无可作答的选择题</p>
          <el-button type="primary" @click="goBack">返回题库</el-button>
        </template>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getKnowledgePoints, getProblems, getChapter, createAttempt } from '../api'
import { ElMessage } from 'element-plus'
import MarkdownViewer from '../components/MarkdownViewer.vue'

const route = useRoute()
const router = useRouter()

const questions = ref([])
const index = ref(0)
const picked = ref(null)
const result = ref(null)
const submitting = ref(false)
const loading = ref(true)

// 专注计时
const seconds = ref(0)
let timer = null
const timerText = computed(() => {
  const m = String(Math.floor(seconds.value / 60)).padStart(2, '0')
  const s = String(seconds.value % 60).padStart(2, '0')
  return `本次练习 ${m}:${s}`
})

const pad = (n) => String(n).padStart(2, '0')
const total = computed(() => questions.value.length)
const current = computed(() => questions.value[index.value] || null)
const currentNo = computed(() => (total.value ? index.value + 1 : 0))
const results = ref([])

const diffLabel = (d) => {
  const n = Number(d)
  if (!n) return '练习'
  if (n <= 2) return '入门'
  if (n === 3) return '进阶'
  return '挑战'
}

// 字母答案 -> 展示编号
const answerNoText = computed(() => {
  if (!result.value?.correct_answer) return '-'
  const raw = Array.isArray(result.value.correct_answer)
    ? result.value.correct_answer
    : [result.value.correct_answer]
  return raw.map((a) => (typeof a === 'string' ? 'ABCD'.indexOf(a.toUpperCase()) + 1 : a)).join('、')
})

const isCorrectOption = (i) => {
  if (!result.value?.correct_answer) return false
  const raw = Array.isArray(result.value.correct_answer)
    ? result.value.correct_answer
    : [result.value.correct_answer]
  return raw.some((a) => 'ABCD'.indexOf(String(a).toUpperCase()) === i)
}

const optionClass = (i) => ({
  picked: picked.value === i && !result.value,
  correct: !!result.value && isCorrectOption(i),
  wrong: !!result.value && picked.value === i && result.value.result !== 'correct' && !isCorrectOption(i)
})

const pick = (i) => {
  if (result.value) return
  picked.value = i
}

const submit = async () => {
  if (picked.value === null || submitting.value) return
  submitting.value = true
  try {
    const letter = 'ABCD'[picked.value]
    const res = await createAttempt({
      target_type: 'problem',
      target_id: current.value.id,
      user_answers: [letter],
      source: 'ai'
    })
    result.value = res.data
    results.value[index.value] = res.data.result
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '提交失败，请稍后重试')
  } finally {
    submitting.value = false
  }
}

const next = () => {
  if (index.value < total.value - 1) {
    index.value += 1
    picked.value = null
    result.value = null
  } else {
    goBack(true)
  }
}

const goBack = (finished = false) => {
  if (finished) ElMessage.success('练习完成，已同步作答记录')
  router.push('/')
}

const onKey = (e) => {
  if (route.path !== '/quiz') return
  if (!result.value && ['1', '2', '3', '4'].includes(e.key)) {
    const i = Number(e.key) - 1
    if (current.value?.options && i < current.value.options.length) pick(i)
  } else if (e.key === 'Enter') {
    result.value ? next() : submit()
  }
}

onMounted(async () => {
  window.addEventListener('keydown', onKey)
  timer = setInterval(() => { seconds.value += 1 }, 1000)
  try {
    // 章节名（面包屑备用）+ 章节下全部知识点 -> 题目
    const chapterId = route.query.chapter_id
    const kpRes = await getKnowledgePoints(chapterId)
    const kps = kpRes.data || []
    const list = []
    for (const kp of kps) {
      const pRes = await getProblems(kp.id)
      for (const p of pRes.data || []) {
        if (p.options && p.options.length) list.push({ ...p, kp_name: kp.name })
      }
    }
    questions.value = list
    results.value = new Array(list.length).fill(null)
    // 指定了起始题则从该题开始
    const startId = route.query.problem_id
    if (startId) {
      const i = list.findIndex((p) => String(p.id) === String(startId))
      if (i > 0) index.value = i
    }
  } catch (error) {
    ElMessage.error('加载题目失败')
  } finally {
    loading.value = false
  }
})

onUnmounted(() => {
  window.removeEventListener('keydown', onKey)
  if (timer) clearInterval(timer)
})
</script>

<style scoped>
.quiz-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background:
    radial-gradient(ellipse 90% 55% at 50% -8%, rgba(90, 227, 208, 0.05), transparent 60%),
    repeating-linear-gradient(0deg, rgba(255, 255, 255, 0.02) 0 1px, transparent 1px 44px),
    repeating-linear-gradient(90deg, rgba(255, 255, 255, 0.02) 0 1px, transparent 1px 44px),
    var(--sf-bg);
}

/* ---------- 顶部专注条 ---------- */
.quiz-top {
  flex: none;
  height: 54px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 22px;
  border-bottom: 1px solid var(--sf-line);
  background: rgba(21, 24, 31, 0.75);
  backdrop-filter: blur(12px);
}

.back-btn {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 7px 14px;
  border-radius: 9px;
  border: 1px solid var(--sf-line);
  background: transparent;
  color: var(--sf-text-dim);
  font-size: 13px;
  cursor: pointer;
  transition: 0.16s;
}

.back-btn:hover {
  border-color: var(--sf-mint-line);
  color: var(--sf-mint);
}

.top-mid {
  display: flex;
  align-items: center;
  gap: 16px;
}

.q-pos {
  font-size: 13.5px;
  color: var(--sf-text);
}

.q-pos i { color: var(--sf-text-muted); font-style: normal; }

.seg-progress {
  display: flex;
  gap: 5px;
}

.seg {
  width: 26px;
  height: 5px;
  border-radius: 99px;
  background: rgba(255, 255, 255, 0.1);
}

.seg.cur { background: var(--sf-mint); box-shadow: 0 0 8px rgba(90, 227, 208, 0.5); }
.seg.ok { background: rgba(90, 227, 208, 0.55); }
.seg.bad { background: rgba(240, 106, 106, 0.55); }

.timer {
  font-size: 12.5px;
  color: var(--sf-text-muted);
  font-variant-numeric: tabular-nums;
}

/* ---------- 题卡 ---------- */
.quiz-body {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  overflow: auto;
}

.quiz-card {
  width: 720px;
  max-width: 100%;
  background: var(--sf-panel);
  backdrop-filter: blur(18px);
  -webkit-backdrop-filter: blur(18px);
  border: 1px solid var(--sf-mint-line);
  border-radius: 16px;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.45), var(--sf-mint-glow);
  padding: 26px 30px;
}

.quiz-card.empty {
  text-align: center;
  color: var(--sf-text-muted);
}

.q-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
}

.q-no {
  width: 34px;
  height: 34px;
  border-radius: 9px;
  display: grid;
  place-items: center;
  font-weight: 700;
  color: var(--sf-mint);
  background: var(--sf-mint-soft);
  border: 1px solid var(--sf-mint-line);
}

.tag {
  font-size: 11.5px;
  padding: 2px 10px;
  border-radius: 6px;
  color: var(--sf-mint);
  background: var(--sf-mint-soft);
  border: 1px solid var(--sf-mint-line);
}

.tag.plain {
  color: var(--sf-text-muted);
  background: rgba(255, 255, 255, 0.04);
  border-color: var(--sf-line);
}

.q-stem {
  margin: 0 0 6px;
  font-size: 17px;
  line-height: 1.7;
  color: var(--sf-text);
}

.q-content { margin-bottom: 8px; color: var(--sf-text-dim); font-size: 14px; }

/* ---------- 选项 ---------- */
.options {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin: 14px 0 0;
}

.option {
  display: flex;
  align-items: center;
  gap: 13px;
  padding: 13px 16px;
  border-radius: 11px;
  border: 1px solid var(--sf-line);
  background: rgba(255, 255, 255, 0.03);
  cursor: pointer;
  transition: 0.16s;
  user-select: none;
}

.option:hover {
  border-color: var(--sf-mint-line);
  background: rgba(90, 227, 208, 0.05);
}

.option.picked {
  border-color: var(--sf-mint);
  background: var(--sf-mint-soft);
  box-shadow: var(--sf-mint-glow);
}

.option.correct {
  border-color: var(--sf-mint);
  background: rgba(90, 227, 208, 0.12);
}

.option.wrong {
  border-color: rgba(240, 106, 106, 0.6);
  background: rgba(240, 106, 106, 0.08);
}

.opt-no {
  width: 26px;
  height: 26px;
  border-radius: 7px;
  display: grid;
  place-items: center;
  font-size: 12.5px;
  font-weight: 700;
  color: var(--sf-text-dim);
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid var(--sf-line);
  flex: none;
}

.option.picked .opt-no,
.option.correct .opt-no {
  color: var(--sf-on-mint);
  background: var(--sf-mint);
  border-color: var(--sf-mint);
}

.option.wrong .opt-no {
  color: #1c1013;
  background: var(--sf-danger);
  border-color: var(--sf-danger);
}

.opt-text {
  font-size: 14px;
  color: var(--sf-text-dim);
  line-height: 1.6;
}

.opt-mark { margin-left: auto; flex: none; }

/* ---------- 解析 ---------- */
.explain {
  max-height: 0;
  overflow: hidden;
  opacity: 0;
  transition: max-height 0.4s ease, opacity 0.4s ease, margin 0.4s ease;
}

.explain.open {
  max-height: 240px;
  opacity: 1;
  margin-top: 16px;
}

.explain-inner {
  border-top: 1px dashed var(--sf-line);
  padding-top: 14px;
  font-size: 13.5px;
  color: var(--sf-text-dim);
  line-height: 1.8;
}

.explain-title {
  font-weight: 600;
  margin-bottom: 6px;
  color: var(--sf-text);
}

.quiz-actions {
  margin-top: 22px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.key-tip {
  margin: 0;
  font-size: 12px;
  color: var(--sf-text-muted);
}
</style>
