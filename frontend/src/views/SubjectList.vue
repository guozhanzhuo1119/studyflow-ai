<template>
  <div class="workbench">
    <!-- ============ 左侧：工程文件树 ============ -->
    <aside class="tree-side">
      <div class="tree-scroll">
        <div class="tree-root" @click="rootOpen = !rootOpen">
          <span class="node-icon folder-mint">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#5AE3D0" stroke-width="1.6"><rect x="3" y="4" width="18" height="16" rx="3"/><path d="M7 9h10M7 13h6"/></svg>
          </span>
          <span class="root-caret" :class="{ closed: !rootOpen }">∨</span>
          <span class="tree-name">studyflow-ai</span>
          <span class="badge">题库</span>
          <button class="add-btn" title="新建科目" @click.stop="openCreate">＋</button>
        </div>
        <div class="root-sub" v-show="rootOpen">打开题库工程</div>

        <template v-if="rootOpen">
          <div v-for="subject in subjects" :key="subject.id" class="tree-group">
            <div class="tree-row subject-row" @click="toggleSubject(subject)">
              <span class="caret" :class="{ closed: !subject.expanded }">∨</span>
              <span class="node-icon folder-amber">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="#E8B45A"><path d="M3 6a2 2 0 0 1 2-2h5l2 2h7a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6Z" opacity=".85"/></svg>
              </span>
              <span class="tree-name">{{ subject.name }}</span>
              <button class="del-btn" title="删除科目" @click.stop="removeSubject(subject)">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><path d="M4 7h16M9 7V5h6v2M6 7l1 13h10l1-13"/></svg>
              </button>
            </div>

            <template v-if="subject.expanded">
              <div
                v-for="chapter in subject.chapters"
                :key="chapter.id"
                class="tree-group"
              >
                <div
                  class="tree-row chapter-row"
                  :class="{ active: activeChapter && activeChapter.id === chapter.id }"
                  @click="selectChapter(subject, chapter)"
                >
                  <span class="caret" :class="{ closed: !chapter.expanded }">∨</span>
                  <span class="node-icon folder-amber sm">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="#E8B45A"><path d="M3 6a2 2 0 0 1 2-2h5l2 2h7a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6Z" opacity=".85"/></svg>
                  </span>
                  <span class="tree-name">{{ chapter.name }}</span>
                  <span class="count" v-if="chapter.total !== null">{{ chapter.total }}</span>
                </div>

                <template v-if="chapter.expanded && chapter.loaded">
                  <div
                    v-for="(p, idx) in chapter.problems"
                    :key="p.id"
                    class="tree-row file-row"
                    @click="startQuiz(subject, chapter, p)"
                  >
                    <span class="node-icon file">
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#5AE3D0" stroke-width="1.5"><path d="M6 3h8l4 4v14H6V3Z"/><path d="M14 3v4h4"/></svg>
                    </span>
                    <span class="tree-name file-name">{{ pad(idx + 1) }}_{{ p.title }}.题</span>
                  </div>
                  <div v-if="chapter.loaded && !chapter.problems.length" class="tree-row file-row empty">
                    <span class="node-icon file">
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#6B7280" stroke-width="1.5"><path d="M6 3h8l4 4v14H6V3Z"/></svg>
                    </span>
                    <span class="tree-name file-name" style="color: #566070">本章题目整理中.待</span>
                  </div>
                </template>
              </div>
            </template>
          </div>
        </template>

        <div class="tree-sep"></div>
        <div class="tree-row foot-row">
          <span class="node-icon">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#8B93A1" stroke-width="1.5"><rect x="3" y="4" width="18" height="6" rx="1.5"/><rect x="3" y="14" width="18" height="6" rx="1.5"/></svg>
          </span>
          <span class="tree-name">外部库</span>
        </div>
        <div class="tree-row foot-row">
          <span class="node-icon">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#8B93A1" stroke-width="1.5"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 9l3 3-3 3M12 15h5"/></svg>
          </span>
          <span class="tree-name">临时文件和控制台</span>
        </div>
      </div>
    </aside>

    <!-- ============ 右侧：题目列表 ============ -->
    <section class="list-side">
      <div class="crumb">
        <span>题库</span>
        <template v-if="activeSubject"> / {{ activeSubject.name }}</template>
        <template v-if="activeChapter"> / {{ activeChapter.name }}</template>
      </div>

      <template v-if="activeChapter">
        <div class="panel-head">
          <div>
            <h1 class="chapter-title">{{ activeChapter.name }} · 章节练习</h1>
            <div class="chapter-meta">
              共 <b>{{ activeChapter.problems.length }}</b> 题 · 已答 <b>{{ answeredCount }}</b> 题 · 正确率 <b>{{ correctRate }}</b>
            </div>
            <div class="progress-line">
              <div class="progress-track"><i :style="{ width: progressPercent + '%' }"></i></div>
              <span class="progress-text">本章掌握度 {{ progressPercent }}%</span>
            </div>
          </div>
          <el-button class="gen-btn" :loading="generating" @click="showGenerate = true">AI 出题</el-button>
        </div>

        <div class="filter-tabs">
          <button
            v-for="tab in filterTabs"
            :key="tab.key"
            class="chip"
            :class="{ on: filter === tab.key }"
            @click="onFilter(tab.key)"
          >{{ tab.label }}</button>
        </div>

        <div class="cards" v-if="filteredProblems.length">
          <article v-for="(p, idx) in filteredProblems" :key="p.id" class="q-card">
            <div class="q-head">
              <span class="q-no">{{ pad(p._no) }}</span>
              <span class="tag diff">{{ diffLabel(p.difficulty) }}</span>
              <span class="tag" v-if="p.options && p.options.length">单选题</span>
              <span class="tag plain" v-if="p.kp_name">{{ p.kp_name }}</span>
              <span class="q-status" :class="{ done: isAnswered(p) }">{{ isAnswered(p) ? '已作答' : '未作答' }}</span>
            </div>
            <h3 class="q-title">{{ p.title }}</h3>
            <div class="q-foot">
              <div class="q-meta">
                {{ isAnswered(p) ? `已做 ${p._stats.total} 次 · 正确率 ${Math.round((p._stats.accuracy || 0) * 100)}%` : '预计 2 分钟 · 全站正确率 暂无' }}
              </div>
              <button class="start-btn" @click="startQuiz(activeSubject, activeChapter, p)">
                开始做题
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M5 12h13M13 6l6 6-6 6"/></svg>
              </button>
            </div>
          </article>
        </div>

        <div v-else-if="!loadingProblems" class="empty-box">
          <p>本章还没有可练习的题目</p>
          <el-button type="primary" @click="showGenerate = true">让 AI 出几道题</el-button>
        </div>
        <div v-if="loadingProblems" class="empty-box"><p>正在加载本章题目…</p></div>
      </template>

      <template v-else>
        <h1 class="chapter-title">选择一个章节开始练习</h1>
        <p class="page-sub">在左侧展开科目与章节，点击章节即可加载题目；点击题目文件可直接开始做题。</p>
        <div class="empty-box"><p>左边没有数据？先到「教材」页上传一份教材，或让 AI 帮你建章节。</p></div>
      </template>
    </section>

    <!-- AI 出题弹窗 -->
    <el-dialog v-model="showGenerate" title="AI 出题" width="440px">
      <p style="color: var(--sf-text-muted); font-size: 13px; margin: 0 0 14px">
        AI 出题中，约 1~2 分钟。将阅读「{{ activeChapter?.name }}」的教材正文，生成选择题入库。
      </p>
      <el-form label-width="80px">
        <el-form-item label="题目数量">
          <el-select v-model="genCount" style="width: 100%">
            <el-option :value="3" label="3 道" />
            <el-option :value="5" label="5 道" />
            <el-option :value="10" label="10 道" />
          </el-select>
        </el-form-item>
        <el-form-item label="难度">
          <el-select v-model="genDifficulty" style="width: 100%">
            <el-option :value="1" label="1 · 识记" />
            <el-option :value="2" label="2 · 基础" />
            <el-option :value="3" label="3 · 进阶" />
            <el-option :value="4" label="4 · 综合" />
            <el-option :value="5" label="5 · 挑战" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button :disabled="generating" @click="showGenerate = false">取消</el-button>
        <el-button type="primary" :loading="generating" @click="doGenerate">开始生成</el-button>
      </template>
    </el-dialog>
     <!-- 新建科目 -->
    <el-dialog v-model="showCreate" title="新建科目" width="420px">
      <el-form :model="subjectForm" label-width="80px">
        <el-form-item label="科目名称">
          <el-input v-model="subjectForm.name" placeholder="例如：计算机网络" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="subjectForm.description" type="textarea" :rows="2" placeholder="可留空" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="submitCreate">创建</el-button>
      </template>
    </el-dialog>

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  getSubjects, getChapters, getKnowledgePoints, getProblems,
  getAttemptOverview, generateChapterQuestions, waitForAiJob, createSubject, deleteSubject
} from '../api'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()

// ---------- 目录树 ----------
const rootOpen = ref(true)
const subjects = ref([])
const activeSubject = ref(null)
const activeChapter = ref(null)
const loadingProblems = ref(false)

// 题目作答统计：problem_id -> {total, accuracy}
const statsMap = ref({})

const pad = (n) => String(n).padStart(2, '0')

const loadTree = async () => {
  try {
    const res = await getSubjects()
    subjects.value = (res.data || []).map((s) => ({
      id: s.id,
      name: s.name,
      expanded: false,
      chapters: []
    }))
    // 落地默认展开第一个有章节的科目并选中其第一个章节（与原型一致）
    for (const subject of subjects.value) {
      await toggleSubject(subject)
      if (subject.chapters.length) {
        await selectChapter(subject, subject.chapters[0])
        break
      }
    }
  } catch (error) {
    ElMessage.error('加载科目失败')
  }
}

const toggleSubject = async (subject) => {
  subject.expanded = !subject.expanded
  if (subject.expanded && !subject.chaptersFetched) {
    try {
      const res = await getChapters(subject.id)
      subject.chapters = (res.data || []).map((c) => ({
        id: c.id,
        name: c.name,
        expanded: false,
        loaded: false,
        total: null,
        problems: []
      }))
      subject.chaptersFetched = true
    } catch (error) {
      ElMessage.error('加载章节失败')
    }
  }
}

const loadChapterProblems = async (chapter) => {
  loadingProblems.value = true
  try {
    const kpRes = await getKnowledgePoints(chapter.id)
    const kps = kpRes.data || []
    const problems = []
    for (const kp of kps) {
      const pRes = await getProblems(kp.id)
      for (const p of pRes.data || []) {
        problems.push({ ...p, kp_name: kp.name })
      }
      // 该知识点下的作答统计
      try {
        const sRes = await getAttemptOverview({ knowledge_point_id: kp.id })
        const st = sRes.data.stats || {}
        for (const [pid, v] of Object.entries(st)) statsMap.value[pid] = v
      } catch (error) { /* 统计失败不影响列表 */ }
    }
    problems.forEach((p, i) => {
      p._no = i + 1
      p._stats = statsMap.value[p.id] || null
    })
    chapter.problems = problems
    chapter.total = problems.length
    chapter.loaded = true
  } catch (error) {
    ElMessage.error('加载本章题目失败')
  } finally {
    loadingProblems.value = false
  }
}

const selectChapter = async (subject, chapter) => {
  activeSubject.value = subject
  activeChapter.value = chapter
  chapter.expanded = true
  if (!chapter.loaded) await loadChapterProblems(chapter)
  // 刷新每道题的统计
  chapter.problems.forEach((p) => { p._stats = statsMap.value[p.id] || null })
}

// ---------- 右侧列表 ----------
const filter = ref('all')
const filterTabs = [
  { key: 'all', label: '全部' },
  { key: 'todo', label: '未作答' },
  { key: 'done', label: '已作答' },
  { key: 'wrong', label: '错题' }
]

const onFilter = (key) => {
  if (key === 'wrong') {
    router.push('/wrong-book')
    return
  }
  filter.value = key
}

const isAnswered = (p) => !!(p._stats && p._stats.total > 0)

const filteredProblems = computed(() => {
  const list = activeChapter.value?.problems || []
  if (filter.value === 'todo') return list.filter((p) => !isAnswered(p))
  if (filter.value === 'done') return list.filter((p) => isAnswered(p))
  return list
})

const answeredCount = computed(() =>
  (activeChapter.value?.problems || []).filter(isAnswered).length
)

const correctRate = computed(() => {
  const list = (activeChapter.value?.problems || []).filter(isAnswered)
  if (!list.length) return '暂无'
  const acc = list.reduce((sum, p) => sum + (p._stats.accuracy || 0), 0) / list.length
  return Math.round(acc * 100) + '%'
})

const progressPercent = computed(() => {
  const total = activeChapter.value?.problems.length || 0
  if (!total) return 0
  const answered = (activeChapter.value?.problems || []).filter(
    (p) => isAnswered(p) && (p._stats.accuracy || 0) >= 0.6
  ).length
  return Math.round((answered / total) * 100)
})

const diffLabel = (d) => {
  const n = Number(d)
  if (!n) return '练习'
  if (n <= 2) return '入门'
  if (n === 3) return '进阶'
  return '挑战'
}

// ---------- 做题 ----------
const startQuiz = (subject, chapter, problem) => {
  router.push({
    path: '/quiz',
    query: { chapter_id: chapter.id, problem_id: problem ? String(problem.id) : '' }
  })
}

// ---------- AI 出题 ----------
const showGenerate = ref(false)
const generating = ref(false)
const genCount = ref(5)
const genDifficulty = ref(2)

const doGenerate = async () => {
  if (!activeChapter.value) return
  const chapter = activeChapter.value
  generating.value = true
  try {
    const res = await generateChapterQuestions(chapter.id, {
      count: genCount.value,
      difficulty: genDifficulty.value
    })
    const job = await waitForAiJob(res.data?.job_id)
    const d = job.result || {}
    ElMessage.success(`已生成 ${d.generated ?? 0} 道题${d.dropped ? `，丢弃 ${d.dropped} 道不合格` : ''}`)
    showGenerate.value = false
    chapter.loaded = false
    await loadChapterProblems(chapter)
    chapter.problems.forEach((p) => { p._stats = statsMap.value[p.id] || null })
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || error.message || '出题失败，请稍后重试')
  } finally {
    generating.value = false
  }
}

// ---------- 新建科目 ----------
const showCreate = ref(false)
const creating = ref(false)
const subjectForm = ref({
  name: '',
  description: ''
})

const openCreate = () => {
  subjectForm.value = { name: '', description: '' }
  showCreate.value = true
}

const submitCreate = async () => {
  creating.value = true
  try {
    const res = await createSubject(subjectForm.value)
    const subject = res.data
    subjects.value.push({
      id: subject.id,
      name: subject.name,
      expanded: false,
      chapters: []
    })
    showCreate.value = false
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '创建科目失败，请稍后重试')
  } finally {
    creating.value = false
  }
}

// ---------- 删除科目 ----------
const removeSubject = (subject) => {
  ElMessageBox.confirm(
    `确定要删除科目「${subject.name}」吗？`,
    '删除科目',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      await deleteSubject(subject.id)
      subjects.value = subjects.value.filter((s) => s.id !== subject.id)
      ElMessage.success('科目已删除')
    } catch (error) {
      ElMessage.error(error.response?.data?.detail || '删除科目失败，请稍后重试')
    }
  }).catch(() => {})
}

onMounted(loadTree)
</script>

<style scoped>
.workbench {
  display: grid;
  grid-template-columns: 262px minmax(0, 1fr);
  height: calc(100vh - 56px - 26px);
}

/* ---------- 左侧树 ---------- */
.tree-side {
  border-right: 1px solid var(--sf-line);
  background: rgba(255, 255, 255, 0.012);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.tree-scroll {
  flex: 1;
  overflow: auto;
  padding: 10px 10px 8px;
}

.tree-root {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 7px 8px;
  border-radius: 8px;
  cursor: pointer;
  color: var(--sf-text);
  font-size: 13.5px;
  font-weight: 600;
}

.tree-root:hover { background: rgba(255, 255, 255, 0.04); }

.root-caret {
  color: var(--sf-text-muted);
  font-size: 10px;
  transition: transform 0.18s;
}
.root-caret.closed { transform: rotate(-90deg); }

.root-sub {
  padding: 2px 8px 6px 36px;
  font-size: 11.5px;
  color: #566070;
}

.badge {
  margin-left: auto;
  font-size: 10.5px;
  color: var(--sf-mint);
  background: var(--sf-mint-soft);
  border: 1px solid var(--sf-mint-line);
  border-radius: 5px;
  padding: 1px 6px;
}

.tree-row {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 6px 8px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
  color: var(--sf-text-dim);
  transition: background 0.14s, color 0.14s;
  user-select: none;
}

.tree-row:hover { background: rgba(255, 255, 255, 0.045); color: var(--sf-text); }

.subject-row { margin-top: 2px; }

.chapter-row {
  padding-left: 24px;
}

.chapter-row.active {
  background: var(--sf-mint-soft);
  color: var(--sf-text);
  box-shadow: inset 3px 0 0 var(--sf-mint);
}

.file-row { padding-left: 44px; }

.file-row.empty { cursor: default; opacity: 0.7; }
.file-row.empty:hover { background: none; color: var(--sf-text-muted); }

.caret {
  color: var(--sf-text-muted);
  font-size: 10px;
  width: 10px;
  flex: none;
  transition: transform 0.18s;
}
.caret.closed { transform: rotate(-90deg); }

.node-icon {
  display: grid;
  place-items: center;
  width: 16px;
  flex: none;
}

.tree-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-name { font-size: 12.5px; color: var(--sf-text-muted); }
.file-row:hover .file-name { color: var(--sf-mint); }

.count {
  margin-left: auto;
  font-size: 11px;
  color: var(--sf-text-muted);
  font-variant-numeric: tabular-nums;
}

.tree-sep {
  margin: 10px 8px;
  border-top: 1px solid var(--sf-line);
}

.foot-row { color: var(--sf-text-muted); font-size: 12.5px; }
.foot-row:hover { color: var(--sf-text-dim); }

/* ---------- 右侧列表 ---------- */
.list-side {
  overflow: auto;
  padding: 18px 26px 40px;
}

.crumb {
  font-size: 12.5px;
  color: var(--sf-text-muted);
  margin-bottom: 10px;
}

.panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.chapter-title {
  margin: 0 0 6px;
  font-size: 21px;
  font-weight: 700;
  color: var(--sf-text);
}

.chapter-meta {
  font-size: 13px;
  color: var(--sf-text-muted);
}

.chapter-meta b { color: var(--sf-mint); font-weight: 600; }

.progress-line {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 10px;
  max-width: 460px;
}

.progress-track {
  flex: 1;
  height: 6px;
  border-radius: 99px;
  background: rgba(255, 255, 255, 0.08);
  overflow: hidden;
}

.progress-track i {
  display: block;
  height: 100%;
  border-radius: 99px;
  background: linear-gradient(90deg, rgba(90, 227, 208, 0.45), var(--sf-mint));
  box-shadow: 0 0 8px rgba(90, 227, 208, 0.4);
  transition: width 0.4s ease;
}

.progress-text { font-size: 12px; color: var(--sf-text-muted); white-space: nowrap; }

.gen-btn {
  background: var(--sf-mint-soft);
  border: 1px solid var(--sf-mint-line);
  color: var(--sf-mint);
  font-weight: 600;
}
.gen-btn:hover {
  background: rgba(90, 227, 208, 0.22);
  color: var(--sf-mint);
  border-color: var(--sf-mint);
}

.filter-tabs {
  display: flex;
  gap: 8px;
  margin: 16px 0;
}

.chip {
  padding: 5px 14px;
  border-radius: 99px;
  border: 1px solid var(--sf-line);
  background: rgba(255, 255, 255, 0.03);
  color: var(--sf-text-muted);
  font-size: 13px;
  cursor: pointer;
  transition: 0.16s;
}

.chip:hover { color: var(--sf-text); border-color: var(--sf-mint-line); }

.chip.on {
  background: var(--sf-mint-soft);
  border-color: var(--sf-mint);
  color: var(--sf-mint);
  box-shadow: var(--sf-mint-glow);
}

/* ---------- 题目卡片 ---------- */
.cards {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.q-card {
  background: var(--sf-panel);
  backdrop-filter: blur(12px);
  border: 1px solid var(--sf-line);
  border-radius: var(--sf-radius);
  padding: 16px 18px;
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}

.q-card:hover {
  transform: translateY(-3px);
  border-color: var(--sf-mint-line);
  box-shadow: 0 14px 30px rgba(0, 0, 0, 0.42), var(--sf-mint-glow);
}

.q-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.q-no {
  width: 30px;
  height: 30px;
  border-radius: 8px;
  display: grid;
  place-items: center;
  font-size: 13px;
  font-weight: 700;
  color: var(--sf-mint);
  background: var(--sf-mint-soft);
  border: 1px solid var(--sf-mint-line);
}

.tag {
  font-size: 11.5px;
  padding: 2px 9px;
  border-radius: 6px;
  color: var(--sf-mint);
  background: var(--sf-mint-soft);
  border: 1px solid var(--sf-mint-line);
}

.tag.diff {
  color: #E8B45A;
  background: rgba(232, 180, 90, 0.12);
  border-color: rgba(232, 180, 90, 0.35);
}

.tag.plain {
  color: var(--sf-text-muted);
  background: rgba(255, 255, 255, 0.04);
  border-color: var(--sf-line);
}

.q-status {
  margin-left: auto;
  font-size: 12px;
  color: var(--sf-text-muted);
}

.q-status.done { color: var(--sf-mint); }

.q-title {
  margin: 0 0 12px;
  font-size: 15.5px;
  font-weight: 600;
  color: var(--sf-text);
  line-height: 1.6;
}

.q-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 12px;
  border-top: 1px dashed var(--sf-line);
}

.q-meta { font-size: 12.5px; color: var(--sf-text-muted); }

.start-btn {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 8px 18px;
  border-radius: 9px;
  border: 1px solid var(--sf-mint);
  background: var(--sf-mint);
  color: var(--sf-on-mint);
  font-size: 13.5px;
  font-weight: 600;
  cursor: pointer;
  transition: 0.18s;
}

.start-btn:hover {
  background: #7CE9DB;
  box-shadow: 0 0 16px rgba(90, 227, 208, 0.35);
}

.empty-box {
  padding: 46px 20px;
  text-align: center;
  color: var(--sf-text-muted);
  border: 1px dashed var(--sf-line);
  border-radius: var(--sf-radius);
}

.add-btn {
  flex: none;
  width: 20px;
  height: 20px;
  margin-left: 8px;
  border-radius: 5px;
  border: 1px solid var(--sf-mint-line);
  background: var(--sf-mint-soft);
  color: var(--sf-mint);
  font-size: 15px;
  line-height: 1;
  cursor: pointer;
  display: grid;
  place-items: center;
  transition: 0.15s;
}
.add-btn:hover { background: var(--sf-mint); color: var(--sf-on-mint); }

.del-btn {
  flex: none;
  display: grid;
  place-items: center;
  width: 20px;
  height: 20px;
  margin-left: auto;
  border-radius: 5px;
  border: 1px solid transparent;
  background: transparent;
  color: #8B93A1;
  cursor: pointer;
  opacity: 0;
  transition: 0.15s;
}
.tree-row:hover .del-btn { opacity: 1; }
.del-btn:hover {
  color: #F56C6C;
  border-color: rgba(245, 108, 108, 0.4);
  background: rgba(245, 108, 108, 0.12);
}
.del-btn:hover {
  color: #F56C6C;
  border-color: rgba(245, 108, 108, 0.4);
  background: rgba(245, 108, 108, 0.12);
}
</style>