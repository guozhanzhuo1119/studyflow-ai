<template>
  <div>
    <el-card>
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span style="font-size: 18px; font-weight: bold">
            {{ pathText }} · 母题列表
          </span>
          <div>
            <el-button @click="goBack">返回知识点</el-button>
            <el-button @click="openImport">批量导入</el-button>
            <el-button type="primary" @click="openAdd">新建题目</el-button>
          </div>
        </div>
      </template>

      <div style="display: flex; gap: 10px; margin-bottom: 16px">
        <el-input
          v-model="searchQuery"
          placeholder="语义搜索，比如「求极限」「链表反转」"
          style="max-width: 420px"
          clearable
          @keyup.enter="searchFn"
        />
        <el-button type="primary" :loading="searching" @click="searchFn">搜索</el-button>
        <el-button v-if="searchMode" @click="clearSearch">退出搜索</el-button>
      </div>

      <el-alert
        v-if="searchMode"
        :title="`语义搜索结果：共 ${problems.length} 条（按相似度排序）`"
        type="success"
        :closable="false"
        style="margin-bottom: 12px"
      />

      <el-table :data="problems" stripe style="width: 100%">
        <el-table-column label="题目">
          <template #default="scope">
            <div>{{ scope.row.title }}</div>
            <div v-if="scope.row.options && scope.row.options.length" class="option-list">
              <div v-for="(text, index) in scope.row.options" :key="index">
                {{ optionLabel(index) }}. {{ text }}
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="难度" width="70">
          <template #default="scope">{{ scope.row.difficulty || '-' }}</template>
        </el-table-column>
        <el-table-column prop="source" label="来源" width="120" />
        <el-table-column prop="tags" label="标签" width="160" />
        <el-table-column prop="status" label="状态" width="90" />
        <el-table-column label="作答" width="150">
          <template #default="scope">
            <span v-if="attemptStats[scope.row.id]">
              已做 {{ attemptStats[scope.row.id].total }} 次 · 正确率 {{ Math.round((attemptStats[scope.row.id].accuracy || 0) * 100) }}%
            </span>
            <span v-else style="color: #c0c4cc">未做</span>
          </template>
        </el-table-column>
        <el-table-column v-if="searchMode" prop="score" label="相似度" width="100" />
        <el-table-column label="操作" width="690">
          <template #default="scope">
            <el-button type="success" size="small" @click="recordAttempt(scope.row, 'correct')">对</el-button>
            <el-button type="warning" size="small" @click="openWrongDialog(scope.row)">错</el-button>
            <el-button size="small" @click="recordAttempt(scope.row, 'giveup')">放弃</el-button>
            <el-button type="primary" size="small" @click="showDetailDialog(scope.row)">查看</el-button>
            <el-button type="primary" size="small" @click="goVariants(scope.row)">变题</el-button>
            <el-button size="small" @click="openRecommend(scope.row)">AI 推荐</el-button>
            <el-button size="small" @click="goError(scope.row)">错因归因</el-button>
            <el-button size="small" @click="openEdit(scope.row)">编辑</el-button>
            <el-button type="danger" size="small" @click="removeFn(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新建 / 编辑题目 -->
    <el-dialog v-model="showDialog" :title="editingId ? '编辑题目' : '新建题目'" width="720px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="题目标题">
          <el-input v-model="form.title" placeholder="题目标题" />
        </el-form-item>
        <el-form-item label="题目正文">
          <div style="width: 100%">
            <div style="margin-bottom: 6px; display: flex; gap: 8px; align-items: center">
              <span style="color: #909399; font-size: 13px">Markdown 支持：KaTeX 公式 `$...$`、`$$...$$`，图片 `![](uploads/xxx.png)`</span>
              <el-upload :show-file-list="false" :auto-upload="false" :on-change="insertImage" accept="image/*">
                <el-button size="small" plain>插入图片</el-button>
              </el-upload>
            </div>
            <el-input
              v-model="form.content"
              type="textarea"
              :rows="8"
              placeholder="例如：&#10;求极限 $\lim_{x \to 0} \frac{\sin x}{x}$&#10;&#10;![](uploads/problem_xxx.png)&#10;&#10;选项：A. 0 B. 1 C. ∞ D. 不存在"
            />
          </div>
        </el-form-item>
        <el-form-item label="来源">
          <el-input v-model="form.source" placeholder="例如：考研真题" />
        </el-form-item>
        <el-form-item label="标签">
          <el-input v-model="form.tags" placeholder="用逗号分隔，例如：极限,泰勒" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submit">确定</el-button>
      </template>
    </el-dialog>

    <!-- 查看题目详情 -->
    <el-dialog v-model="showDetail" :title="'题目：' + (detailData.title || '')" width="760px">
      <MarkdownViewer v-if="detailData.content" :source="detailData.content" />
      <div v-if="detailData.options && detailData.options.length" class="detail-options">
        <div v-for="(text, index) in detailData.options" :key="index" class="detail-option">
          {{ optionLabel(index) }}. {{ text }}
        </div>
      </div>
      <div v-if="detailData.options && detailData.options.length" class="answer-block">
        <div class="answer-label">选择答案后提交，由服务端按标准答案判分</div>
        <div class="answer-actions">
          <el-radio-group v-model="choiceAnswer" :disabled="!!choiceResult">
            <el-radio v-for="(text, index) in detailData.options" :key="index" :label="optionLabel(index)">
              {{ optionLabel(index) }}
            </el-radio>
          </el-radio-group>
          <el-button
            type="primary"
            size="small"
            :loading="submittingAnswer"
            :disabled="!choiceAnswer || !!choiceResult"
            @click="submitChoice"
          >
            提交答案
          </el-button>
        </div>
        <el-alert
          v-if="choiceResult"
          :closable="false"
          style="margin-top: 10px"
          :type="choiceResult.result === 'correct' ? 'success' : 'error'"
          :title="choiceResult.result === 'correct' ? '回答正确，已标记为掌握' : '回答错误，已记入错题本'"
        >
          <div>正确答案：{{ choiceResult.correct_answer }}</div>
          <div>解析：{{ choiceResult.explanation || '暂无解析' }}</div>
        </el-alert>
      </div>
      <div v-if="!detailData.content && !(detailData.options && detailData.options.length)" style="color: #909399; text-align: center; padding: 20px">
        暂无正文，点击编辑按钮填写
      </div>
      <div style="margin-top: 12px; color: #909399; font-size: 13px">
        来源：{{ detailData.source || '-' }} · 标签：{{ detailData.tags || '-' }}
      </div>
      <template #footer>
        <el-button @click="showDetail = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- AI 推荐 -->
    <el-dialog v-model="showRecommend" title="AI 推荐变题" width="720px">
      <div v-if="recommendLoading" style="text-align: center; padding: 30px">正在检索相似题并生成推荐...</div>
      <div v-else>
        <div v-for="(item, index) in recommendations" :key="index" class="recommend-item">
          <div class="recommend-title">{{ item.title }}</div>
          <div class="recommend-meta">
            难度：{{ item.difficulty || '未知' }}
            <span v-if="item.link"> · <a v-if="isUrl(item.link)" :href="item.link" target="_blank" rel="noopener">题目链接</a><template v-else>{{ item.link }}</template></span>
          </div>
          <div class="recommend-reason">{{ item.reason }}</div>
          <el-button size="small" type="primary" plain @click="saveOne(item, index)">保存为变题</el-button>
        </div>
      </div>
      <template #footer>
        <el-button @click="showRecommend = false">关闭</el-button>
        <el-button type="primary" :disabled="!recommendations.length" @click="saveAll">全部保存为变题</el-button>
      </template>
    </el-dialog>

    <!-- 批量导入母题 -->
    <el-dialog v-model="showImport" title="批量导入母题" width="680px">
      <el-alert
        title="每行一道题，用 | 分隔：标题|来源|标签（来源和标签可省略）。csv 文件也支持逗号分隔。"
        type="info"
        :closable="false"
        style="margin-bottom: 12px"
      />
      <el-upload
        drag
        :auto-upload="false"
        :show-file-list="false"
        accept=".txt,.csv,.md"
        :on-change="readFile"
        style="margin-bottom: 12px"
      >
        <div style="padding: 10px">把 txt / csv 文件拖到这里，或点击选择</div>
      </el-upload>
      <el-input
        v-model="importText"
        type="textarea"
        :rows="10"
        placeholder="求极限 lim(x->0) sin x / x|考研真题|极限,等价无穷小&#10;三指针反转链表|LeetCode 206|链表"
      />
      <div style="margin-top: 8px; color: #909399; font-size: 13px">
        已识别 {{ importItems.length }} 道题
      </div>
      <template #footer>
        <el-button @click="showImport = false">取消</el-button>
        <el-button type="primary" :loading="importing" :disabled="!importItems.length" @click="submitImport">
          导入
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showWrongDialog" title="记录错因" width="560px">
      <el-form label-width="90px">
        <el-form-item label="题目">
          <span>{{ wrongTarget?.title }}</span>
        </el-form-item>
        <el-form-item label="错因">
          <el-select v-model="wrongType" placeholder="选最接近的一类" style="width: 100%">
            <el-option
              v-for="item in errorTypes"
              :key="item.code"
              :label="item.priority + '. ' + item.name"
              :value="item.code"
            >
              <span>{{ item.name }}</span>
              <span style="float: right; color: #909399; font-size: 12px">{{ item.signal }}</span>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="具体表现">
          <el-input v-model="wrongNote" maxlength="50" placeholder="例：没看出是滑动窗口 / 边界少判空链表" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showWrongDialog = false">取消</el-button>
        <el-button type="primary" @click="submitWrong">保存并记一次做错</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  getProblems, getKnowledgePoint, createProblem, updateProblem, deleteProblem,
  searchProblems, recommend, createVariant, importProblems, uploadImage,
  createAttempt, getAttemptOverview, getErrorMeta
} from '../api'
import MarkdownViewer from '../components/MarkdownViewer.vue'
import { ElMessage, ElMessageBox } from 'element-plus'

// 只有完整 URL 才当链接渲染，否则相对路径会跳到错误页面
const isUrl = (value) => /^https?:\/\/\S+/i.test((value || '').trim())

const route = useRoute()
const router = useRouter()

const problems = ref([])
const knowledgePointName = ref('')
const chapterName = ref('')
const subjectName = ref('')
const chapterId = ref('')

const showDialog = ref(false)
const editingId = ref('')
const form = ref({ title: '', content: '', source: '', tags: '' })
const saving = ref(false)

const showDetail = ref(false)
const detailData = ref({})
const choiceAnswer = ref('')
const choiceResult = ref(null)
const submittingAnswer = ref(false)

const searchQuery = ref('')
const searching = ref(false)
const searchMode = ref(false)
// 按题目 id 聚合作答次数，来自 attempts 表
const attemptStats = ref({})
// 记录错因弹窗
const showWrongDialog = ref(false)
const wrongTarget = ref(null)
const wrongType = ref('')
const wrongNote = ref('')
const errorTypes = ref([])

const showRecommend = ref(false)
const recommendLoading = ref(false)
const recommendations = ref([])
const recommendProblemId = ref('')

const showImport = ref(false)
const importText = ref('')
const importing = ref(false)

const splitImportLine = (line) => {
  if (line.includes('|')) return line.split('|')
  if (line.includes('\t')) return line.split('\t')
  if (line.includes(',')) return line.split(',')
  return [line]
}

const importItems = computed(() =>
  importText.value
    .split(/\r?\n/)
    .map((line) => line.replace(/^\uFEFF/, '').trim())
    .filter((line) => line && !line.startsWith('#'))
    .map((line) => {
      const parts = splitImportLine(line).map((part) => part.trim())
      return { title: parts[0] || '', source: parts[1] || '', tags: parts[2] || '' }
    })
    .filter((item) => item.title)
)

const pathText = computed(() =>
  [subjectName.value, chapterName.value, knowledgePointName.value].filter(Boolean).join(' / ')
)

onMounted(() => {
  loadProblems()
  loadPath()
  loadAttemptStats()
  loadErrorTypes()
})

const loadPath = async () => {
  try {
    const res = await getKnowledgePoint(route.params.kpId)
    knowledgePointName.value = res.data.name
    chapterName.value = res.data.chapter_name || ''
    subjectName.value = res.data.subject_name || ''
    chapterId.value = res.data.chapter_id || ''
  } catch (error) {
    knowledgePointName.value = ''
  }
}

const loadProblems = async () => {
  try {
    const res = await getProblems(route.params.kpId)
    problems.value = res.data
    searchMode.value = false
  } catch (error) {
    ElMessage.error('加载题目失败')
  }
}

const loadAttemptStats = async () => {
  try {
    const res = await getAttemptOverview({ knowledge_point_id: route.params.kpId })
    attemptStats.value = res.data.stats || {}
  } catch (error) {
    attemptStats.value = {}
  }
}

const recordAttempt = async (row, result) => {
  try {
    const res = await createAttempt({ target_type: 'problem', target_id: row.id, result })
    attemptStats.value = { ...attemptStats.value, [row.id]: res.data.stats }
    const text = { correct: '已记一次：做对', wrong: '已记一次：做错', giveup: '已记一次：放弃' }[result]
    ElMessage.success(text)
  } catch (error) {
    ElMessage.error('记录失败')
  }
}

const openWrongDialog = (row) => {
  wrongTarget.value = row
  wrongType.value = ''
  wrongNote.value = ''
  showWrongDialog.value = true
}

const submitWrong = async () => {
  if (!wrongType.value) {
    ElMessage.warning('先选一个错因')
    return
  }
  try {
    const res = await createAttempt({
      target_type: 'problem',
      target_id: wrongTarget.value.id,
      result: 'wrong',
      error_type: wrongType.value,
      error_reason: wrongNote.value,
    })
    attemptStats.value = { ...attemptStats.value, [wrongTarget.value.id]: res.data.stats }
    showWrongDialog.value = false
    ElMessage.success('已记一次做错，并生成归因记录')
  } catch (error) {
    ElMessage.error('保存失败')
  }
}

const loadErrorTypes = async () => {
  try {
    const res = await getErrorMeta()
    errorTypes.value = res.data.error_types || []
  } catch (error) {
    errorTypes.value = []
  }
}

const searchFn = async () => {
  const query = searchQuery.value.trim()
  if (!query) {
    ElMessage.warning('请输入搜索内容')
    return
  }
  searching.value = true
  try {
    const res = await searchProblems(query, 5)
    problems.value = res.data.results
    searchMode.value = true
    if (!problems.value.length) ElMessage.info('没有找到相似题目')
  } catch (error) {
    ElMessage.error('搜索失败')
  } finally {
    searching.value = false
  }
}

const clearSearch = () => {
  searchQuery.value = ''
  loadProblems()
}

const openAdd = () => {
  editingId.value = ''
  form.value = { title: '', content: '', source: '', tags: '' }
  showDialog.value = true
}

const openEdit = (row) => {
  editingId.value = row.id
  form.value = { title: row.title, content: row.content || '', source: row.source || '', tags: row.tags || '' }
  showDialog.value = true
}

const showDetailDialog = (row) => {
  detailData.value = {
    id: row.id,
    title: row.title,
    content: row.content || '',
    options: row.options || [],
    difficulty: row.difficulty,
    source: row.source,
    tags: row.tags
  }
  choiceAnswer.value = ''
  choiceResult.value = null
  showDetail.value = true
}

const submitChoice = async () => {
  submittingAnswer.value = true
  try {
    const res = await createAttempt({
      target_type: 'problem',
      target_id: detailData.value.id,
      user_answers: [choiceAnswer.value],
      source: 'ai'
    })
    choiceResult.value = res.data
    attemptStats.value = { ...attemptStats.value, [detailData.value.id]: res.data.stats }
    if (res.data.result === 'correct') {
      ElMessage.success('回答正确')
    } else {
      ElMessage.error('回答错误，已加入错题本')
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '提交失败，请稍后重试')
  } finally {
    submittingAnswer.value = false
  }
}

const optionLabel = (index) => ['A', 'B', 'C', 'D'][index] || String(index + 1)

const insertImage = async (uploadFile) => {
  const file = uploadFile.raw
  if (!file) return
  try {
    ElMessage.info('上传中...')
    const res = await uploadImage(file)
    const url = res.data.url
    form.value.content = (form.value.content || '').trimEnd() + `\n\n![](${url})\n`
    ElMessage.success('已插入图片')
  } catch (error) {
    ElMessage.error('图片上传失败')
  }
}

const submit = async () => {
  if (!form.value.title) {
    ElMessage.warning('请输入题目')
    return
  }
  saving.value = true
  const payload = {
    title: form.value.title,
    content: form.value.content || null,
    source: form.value.source,
    tags: form.value.tags,
    knowledge_point_id: route.params.kpId
  }
  try {
    if (editingId.value) {
      await updateProblem(editingId.value, payload)
      ElMessage.success('修改成功')
    } else {
      await createProblem(payload)
      ElMessage.success('创建成功')
    }
    showDialog.value = false
    loadProblems()
  } catch (error) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

const removeFn = async (row) => {
  try {
    await ElMessageBox.confirm(`确定删除「${row.title}」吗？它下面的变题也会一起删除。`, '提示', { type: 'warning' })
    await deleteProblem(row.id)
    ElMessage.success('删除成功')
    loadProblems()
  } catch (error) {
    if (error !== 'cancel') ElMessage.error('删除失败')
  }
}

const openRecommend = async (row) => {
  recommendProblemId.value = row.id
  recommendations.value = []
  showRecommend.value = true
  recommendLoading.value = true
  try {
    const res = await recommend(row.id, 5)
    recommendations.value = res.data.recommendations || []
  } catch (error) {
    ElMessage.error('AI 推荐失败，请稍后重试')
    showRecommend.value = false
  } finally {
    recommendLoading.value = false
  }
}

const saveOne = async (item, index) => {
  try {
    await createVariant({
      problem_id: recommendProblemId.value,
      title: item.title,
      difficulty: item.difficulty,
      link: item.link,
      reason: item.reason
    })
    ElMessage.success('已保存为变题')
    recommendations.value.splice(index, 1)
  } catch (error) {
    ElMessage.error('保存失败')
  }
}

const saveAll = async () => {
  if (!recommendations.value.length) return
  try {
    const items = [...recommendations.value]
    for (const item of items) {
      await createVariant({
        problem_id: recommendProblemId.value,
        title: item.title,
        difficulty: item.difficulty,
        link: item.link,
        reason: item.reason
      })
    }
    ElMessage.success(`已保存 ${items.length} 道变题`)
    recommendations.value = []
  } catch (error) {
    ElMessage.error('保存失败')
  }
}

const openImport = () => {
  importText.value = ''
  showImport.value = true
}

const readFile = (uploadFile) => {
  const file = uploadFile.raw
  if (!file) return
  const reader = new FileReader()
  reader.onload = () => {
    importText.value = String(reader.result || '')
  }
  reader.readAsText(file, 'utf-8')
}

const submitImport = async () => {
  if (!importItems.value.length) return
  importing.value = true
  try {
    const res = await importProblems(route.params.kpId, importItems.value)
    const created = res.data.created
    const skipped = res.data.skipped || []
    ElMessage.success(
      `成功导入 ${created} 道题${skipped.length ? `，跳过 ${skipped.length} 道重复题` : ''}`
    )
    showImport.value = false
    loadProblems()
  } catch (error) {
    ElMessage.error('导入失败')
  } finally {
    importing.value = false
  }
}

const goVariants = (row) => {
  router.push(`/problems/${row.id}/variants`)
}

const goError = (row) => {
  router.push({
    path: '/errors',
    query: {
      problem_id: row.id,
      problem_title: row.title,
      topic: knowledgePointName.value
    }
  })
}

const goBack = () => {
  router.push(`/chapters/${chapterId.value}`)
}
</script>

<style scoped>
.option-list {
  margin-top: 4px;
  color: #606266;
  font-size: 13px;
  line-height: 1.8;
}
.detail-options {
  margin-top: 12px;
  color: #303133;
  line-height: 2;
}
.detail-option {
  padding: 2px 0;
}
.answer-block {
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px dashed #e4e7ed;
}
.answer-label {
  color: #909399;
  font-size: 13px;
  margin-bottom: 8px;
}
.answer-actions {
  display: flex;
  align-items: center;
  gap: 16px;
}
.recommend-item {
  border: 1px solid #ebeef5;
  border-radius: 6px;
  padding: 12px;
  margin-bottom: 12px;
}
.recommend-title {
  font-weight: bold;
  margin-bottom: 6px;
}
.recommend-meta {
  color: #909399;
  font-size: 13px;
  margin-bottom: 6px;
}
.recommend-reason {
  color: #606266;
  font-size: 14px;
  margin-bottom: 10px;
}
</style>
