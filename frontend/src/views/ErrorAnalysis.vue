<template>
  <div>
    <!-- 统计口径：练习模式只显示四指标，正确率等模拟指标需手动解锁 -->
    <el-card style="margin-bottom: 16px">
      <template #header>
        <div class="header-row">
          <span class="title">错因统计</span>
          <el-switch
            v-model="simulateMode"
            active-text="模拟模式"
            inactive-text="练习模式"
            @change="loadStatistics"
          />
        </div>
      </template>

      <el-row :gutter="16">
        <el-col :span="14">
          <div class="section-label">错因分布（看主要矛盾）</div>
          <div v-for="item in distributionRows" :key="item.code" class="dist-row">
            <span class="dist-name">{{ item.name }}</span>
            <el-progress
              :percentage="item.percent"
              :stroke-width="14"
              :show-text="false"
              :color="item.color"
              style="flex: 1"
            />
            <span class="dist-count">{{ item.count }}</span>
          </div>
        </el-col>
        <el-col :span="10">
          <div class="metric-grid">
            <div class="metric">
              <div class="metric-value">{{ latencyText }}</div>
              <div class="metric-label">识别平均耗时（秒）</div>
              <el-alert
                v-if="stats.identify_latency_avg_sec > 30"
                title="&gt;30 秒，说明母题信号没记牢"
                type="warning"
                :closable="false"
                style="margin-top: 6px"
              />
            </div>
            <div class="metric">
              <div class="metric-value">{{ stats.decomposition_coverage || '0/0' }}</div>
              <div class="metric-label">拆解句覆盖率</div>
            </div>
            <div class="metric">
              <div class="metric-value" :class="{ danger: stats.remedy_pending_count > 3 }">
                {{ stats.remedy_pending_count }}
              </div>
              <div class="metric-label">待补错因数</div>
            </div>
            <div v-if="!practiceMode" class="metric">
              <div class="metric-value">{{ stats.accuracy == null ? '—' : stats.accuracy }}</div>
              <div class="metric-label">正确率（模拟）</div>
            </div>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <el-card>
      <template #header>
        <div class="header-row">
          <span class="title">错因归因</span>
          <div>
            <el-button @click="goBack">返回</el-button>
            <el-button type="primary" :disabled="wizardActive" @click="startWizard">开始归因</el-button>
          </div>
        </div>
      </template>

      <!-- 决策树问答：不让用户直接选六类下拉框 -->
      <div v-if="wizardActive" class="wizard">
        <el-steps :active="stepIndex" simple style="margin-bottom: 20px">
          <el-step v-for="s in meta.decision_tree" :key="s.step" :title="`Q${s.step}`" />
        </el-steps>

        <div class="wizard-question">{{ currentQuestion }}</div>
        <div class="wizard-actions">
          <el-button type="primary" size="large" @click="answer(true)">是</el-button>
          <el-button size="large" @click="answer(false)">否</el-button>
          <el-button text @click="resetWizard">重新开始</el-button>
        </div>
      </div>

      <!-- 决策树得出错因后的补录表单 -->
      <div v-else-if="decidedType" class="form-block">
        <el-alert
          :title="`决策树结论：${decidedTypeName}（以决策树为准，自评原话可写入备注）`"
          type="success"
          :closable="false"
          style="margin-bottom: 16px"
        />

        <el-form :model="form" label-width="110px">
          <el-form-item label="题目">
            <el-input v-model="form.problem_title" disabled />
          </el-form-item>
          <el-form-item label="知识点">
            <el-input v-model="form.topic" placeholder="例如：链表" />
          </el-form-item>
          <el-form-item label="母题">
            <el-input v-model="form.mother_problem" placeholder="例如：LC-206" />
          </el-form-item>
          <el-form-item label="具体表现">
            <el-input
              v-model="form.specific_behavior"
              maxlength="50"
              show-word-limit
              placeholder="一句话说清错在哪，≤50 字"
            />
          </el-form-item>

          <!-- DECOMPOSE 类强制写拆解句，且必须含「=」「母题」「改」 -->
          <el-form-item v-if="decidedType === 'DECOMPOSE'" label="拆解句">
            <el-input
              v-model="form.decomposition_sentence"
              type="textarea"
              :rows="2"
              placeholder="例如：24 = 206 + 区间长度固定为2 + prev每组后移到组尾"
            />
            <div class="hint">必须同时包含「=」「母题」「改」三个关键词</div>
          </el-form-item>

          <el-form-item v-if="decidedType === 'OPERATE'" label="语法坑">
            <el-checkbox v-model="syncSyntaxTag">
              打 SYNTAX 标签<span v-if="syntaxSuggested" class="hint-inline">（检测到语言坑关键词，建议勾选）</span>
            </el-checkbox>
          </el-form-item>

          <el-form-item label="识别耗时">
            <el-input-number v-model="form.identify_latency_sec" :min="0" :max="600" />
            <span class="hint-inline">从看题到说出「这是 XX 母题」的秒数</span>
          </el-form-item>

          <el-form-item label="补救动作">
            <el-input v-model="form.remedy_action" placeholder="例如：回看 92 的 pre->next 接回逻辑" />
          </el-form-item>

          <el-form-item label="自评原话">
            <el-input v-model="form.user_note" type="textarea" :rows="2" placeholder="可选，保留你自己的描述" />
          </el-form-item>
        </el-form>

        <div class="footer-actions">
          <el-button @click="resetWizard">取消</el-button>
          <el-button type="primary" :loading="saving" @click="submit">保存归因</el-button>
        </div>
      </div>

      <el-empty v-else description="点击「开始归因」，按决策树一步步定位错因" />
    </el-card>

    <!-- 归因历史 -->
    <el-card style="margin-top: 16px">
      <template #header><span class="title">归因记录</span></template>
      <el-table :data="records" stripe style="width: 100%">
        <el-table-column prop="problem_title" label="题目" min-width="160" />
        <el-table-column label="错因" width="110">
          <template #default="scope">
            <el-tag :type="errorTagType(scope.row.error_type)">{{ scope.row.error_type_name }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="specific_behavior" label="具体表现" min-width="200" />
        <el-table-column prop="decomposition_sentence" label="拆解句" min-width="220" />
        <el-table-column label="补救" width="100">
          <template #default="scope">
            <el-tag :type="scope.row.remedy_status === '已补' ? 'success' : 'warning'">
              {{ scope.row.remedy_status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="已复盘" width="100">
          <template #default="scope">
            <el-switch
              :model-value="scope.row.reviewed"
              @change="(val) => toggleReviewed(scope.row, val)"
            />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100">
          <template #default="scope">
            <el-button type="danger" size="small" @click="removeRecord(scope.row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getErrorMeta,
  decideErrorType,
  getErrors,
  createError,
  updateError,
  deleteError,
  getErrorStatistics,
  getProblems
} from '../api'

const route = useRoute()
const router = useRouter()

const meta = ref({ decision_tree: [], error_types: [], presets: {} })
const stats = ref({ error_distribution: {}, identify_latency_avg_sec: null, decomposition_coverage: '0/0', remedy_pending_count: 0 })
const records = ref([])
const problems = ref([])
const simulateMode = ref(false)

const wizardActive = ref(false)
const stepIndex = ref(0)
const answers = ref([])
const decidedType = ref('')
const decidedTypeName = ref('')
const syntaxSuggested = ref(false)
const syncSyntaxTag = ref(false)
const saving = ref(false)
const currentProblem = ref(null)

const form = reactive({
  problem_id: '',
  problem_title: '',
  topic: '',
  mother_problem: '',
  specific_behavior: '',
  decomposition_sentence: '',
  remedy_action: '',
  user_note: '',
  identify_latency_sec: 0
})

const practiceMode = computed(() => !simulateMode.value)

const currentQuestion = computed(() => {
  const step = meta.value.decision_tree[stepIndex.value]
  return step ? step.question : ''
})

const latencyText = computed(() =>
  stats.value.identify_latency_avg_sec == null ? '—' : stats.value.identify_latency_avg_sec
)

const TYPE_COLORS = {
  READ: '#f56c6c',
  IDENTIFY: '#e6a23c',
  DECOMPOSE: '#409eff',
  OPERATE: '#909399',
  BOUNDARY: '#67c23a',
  EFFICIENCY: '#8e44ad'
}

const distributionRows = computed(() => {
  const dist = stats.value.error_distribution || {}
  const total = Object.values(dist).reduce((a, b) => a + b, 0)
  return (meta.value.error_types || []).map((t) => {
    const count = dist[t.code] || 0
    return {
      code: t.code,
      name: t.name,
      count,
      percent: total ? Math.round((count / total) * 100) : 0,
      color: TYPE_COLORS[t.code] || '#409eff'
    }
  })
})

onMounted(async () => {
  await loadMeta()
  await loadProblems()
  await loadStatistics()
  await loadRecords()

  // 从题目列表跳过来时，直接进入归因
  const problemId = route.query.problem_id
  if (problemId) {
    const target = problems.value.find((p) => p.id === problemId)
    if (target) {
      currentProblem.value = target
      startWizard()
    }
  }
})

const loadMeta = async () => {
  try {
    const res = await getErrorMeta()
    meta.value = res.data
  } catch (error) {
    ElMessage.error('加载错因元数据失败')
  }
}

const loadProblems = async () => {
  try {
    const res = await getProblems()
    problems.value = res.data
  } catch (error) {
    problems.value = []
  }
}

const loadStatistics = async () => {
  try {
    const res = await getErrorStatistics(practiceMode.value)
    stats.value = res.data
  } catch (error) {
    ElMessage.error('加载统计失败')
  }
}

const loadRecords = async () => {
  try {
    const res = await getErrors()
    records.value = res.data
  } catch (error) {
    ElMessage.error('加载归因记录失败')
  }
}

const startWizard = async () => {
  if (!currentProblem.value) {
    const picked = await pickProblem()
    if (!picked) return
    currentProblem.value = picked
  }
  resetWizard()
  wizardActive.value = true
}

// 选一道要归因的题
const pickProblem = () => {
  return new Promise((resolve) => {
    if (!problems.value.length) {
      ElMessage.warning('题库为空，请先添加题目')
      resolve(null)
      return
    }
    ElMessageBox.prompt('输入题目 ID（可从题目列表复制）', '选择要归因的题目', {
      confirmButtonText: '确定',
      cancelButtonText: '取消'
    })
      .then(({ value }) => {
        const target = problems.value.find(
          (p) => p.id === value || p.title.includes(value)
        )
        if (!target) {
          ElMessage.error('没找到这道题')
          resolve(null)
          return
        }
        resolve(target)
      })
      .catch(() => resolve(null))
  })
}

const answer = async (yes) => {
  answers.value.push(yes)
  const step = meta.value.decision_tree[stepIndex.value]
  if (!step) return

  // 命中即停：以决策树为准
  if (yes === step.match_answer) {
    try {
      const res = await decideErrorType(answers.value, form.specific_behavior)
      decidedType.value = res.data.error_type
      const found = meta.value.error_types.find((t) => t.code === res.data.error_type)
      decidedTypeName.value = found ? found.name : res.data.error_type
      syntaxSuggested.value = res.data.suggest_syntax_tag
      syncSyntaxTag.value = res.data.suggest_syntax_tag
    } catch (error) {
      ElMessage.error('决策树判定失败')
      return
    }

    Object.assign(form, {
      problem_id: currentProblem.value.id,
      problem_title: currentProblem.value.title,
      topic: currentProblem.value.tags || ''
    })
    wizardActive.value = false
    return
  }

  // 未命中，继续下一问
  if (step.next_step == null) {
    ElMessage.info('已到决策树末端')
    resetWizard()
    return
  }
  stepIndex.value = meta.value.decision_tree.findIndex((s) => s.step === step.next_step)
}

const resetWizard = () => {
  wizardActive.value = false
  stepIndex.value = 0
  answers.value = []
  decidedType.value = ''
  decidedTypeName.value = ''
  syntaxSuggested.value = false
  syncSyntaxTag.value = false
  Object.assign(form, {
    problem_id: '',
    problem_title: '',
    topic: '',
    mother_problem: '',
    specific_behavior: '',
    decomposition_sentence: '',
    remedy_action: '',
    user_note: '',
    identify_latency_sec: 0
  })
  currentProblem.value = null
}

const submit = async () => {
  if (!form.specific_behavior.trim()) {
    ElMessage.warning('必须用一句话说清错在哪（≤50 字），写不出说明还没归因清楚')
    return
  }
  if (decidedType.value === 'DECOMPOSE') {
    const missing = ['=', '母题', '改'].filter((kw) => !form.decomposition_sentence.includes(kw))
    if (missing.length) {
      ElMessage.warning(`拆解句缺少关键词：${missing.join('、')}`)
      return
    }
  }

  saving.value = true
  try {
    await createError({
      problem_id: form.problem_id,
      problem_title: form.problem_title,
      topic: form.topic || null,
      mother_problem: form.mother_problem || null,
      error_type: decidedType.value,
      tag: syncSyntaxTag.value ? 'SYNTAX' : null,
      specific_behavior: form.specific_behavior,
      decomposition_sentence: decidedType.value === 'DECOMPOSE' ? form.decomposition_sentence : null,
      remedy_status: '待补',
      remedy_action: form.remedy_action || null,
      user_note: form.user_note || null,
      identify_latency_sec: form.identify_latency_sec || null,
      reviewed: false
    })
    ElMessage.success('归因已保存')
    resetWizard()
    await loadStatistics()
    await loadRecords()
  } catch (error) {
    const detail = error.response?.data?.detail
    ElMessage.error(typeof detail === 'string' ? detail : '保存失败，请检查字段')
  } finally {
    saving.value = false
  }
}

const toggleReviewed = async (row, val) => {
  try {
    await updateError(row.id, { reviewed: val })
    row.reviewed = val
  } catch (error) {
    ElMessage.error('更新失败')
  }
}

const removeRecord = async (id) => {
  try {
    await deleteError(id)
    ElMessage.success('已删除')
    await loadStatistics()
    await loadRecords()
  } catch (error) {
    ElMessage.error('删除失败')
  }
}

const errorTagType = (code) => {
  const map = {
    READ: 'danger',
    IDENTIFY: 'warning',
    DECOMPOSE: 'primary',
    OPERATE: 'info',
    BOUNDARY: 'success',
    EFFICIENCY: 'info'
  }
  return map[code] || 'info'
}

const goBack = () => router.back()
</script>

<style scoped>
.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.title {
  font-size: 18px;
  font-weight: bold;
}
.section-label {
  font-size: 13px;
  color: #909399;
  margin-bottom: 10px;
}
.dist-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}
.dist-name {
  width: 70px;
  font-size: 13px;
  color: #606266;
}
.dist-count {
  width: 30px;
  text-align: right;
  font-weight: bold;
}
.metric-grid {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.metric-value {
  font-size: 22px;
  font-weight: bold;
  color: #303133;
}
.metric-value.danger {
  color: #f56c6c;
}
.metric-label {
  font-size: 12px;
  color: #909399;
}
.wizard-question {
  font-size: 18px;
  font-weight: bold;
  margin: 24px 0;
  color: #303133;
}
.wizard-actions {
  display: flex;
  gap: 12px;
}
.form-block {
  padding: 8px 0;
}
.footer-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 8px;
}
.hint {
  font-size: 12px;
  color: #909399;
}
.hint-inline {
  font-size: 12px;
  color: #909399;
  margin-left: 8px;
}
</style>
