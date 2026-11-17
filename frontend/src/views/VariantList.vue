<template>
  <div>
    <el-card>
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span style="font-size: 18px; font-weight: bold">
            {{ problemTitle ? `「${problemTitle}」的变题` : '变题列表' }}
          </span>
          <div>
            <el-button @click="goBack">返回母题</el-button>
            <el-button type="primary" @click="openAdd">新增变题</el-button>
          </div>
        </div>
      </template>

      <el-table :data="variants" stripe style="width: 100%">
        <el-table-column prop="title" label="变题" />
        <el-table-column prop="difficulty" label="难度" width="100" />
        <el-table-column label="来源" width="100">
          <template #default="scope">
            <el-tag :type="scope.row.origin === 'ai' ? 'success' : 'info'">
              {{ scope.row.origin === 'ai' ? 'AI 推荐' : '手动录入' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="reason" label="推荐理由 / 说明" />
        <el-table-column label="链接" width="100">
          <template #default="scope">
            <a v-if="isUrl(scope.row.link)" :href="scope.row.link" target="_blank" rel="noopener">打开</a>
            <span v-else-if="scope.row.link">{{ scope.row.link }}</span>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="230">
          <template #default="scope">
            <el-button type="primary" size="small" @click="showDetailDialog(scope.row)">查看</el-button>
            <el-button size="small" @click="openEdit(scope.row)">编辑</el-button>
            <el-button type="danger" size="small" @click="removeFn(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新增 / 编辑变题 -->
    <el-dialog v-model="showDialog" :title="editingId ? '编辑变题' : '新增变题'" width="720px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="变题标题">
          <el-input v-model="form.title" placeholder="变题标题" />
        </el-form-item>
        <el-form-item label="变题正文">
          <div style="width: 100%">
            <div style="margin-bottom: 6px; display: flex; gap: 8px; align-items: center">
              <span style="color: #909399; font-size: 13px">Markdown 支持 KaTeX 公式和图片</span>
              <el-upload :show-file-list="false" :auto-upload="false" :on-change="insertImage" accept="image/*">
                <el-button size="small" plain>插入图片</el-button>
              </el-upload>
            </div>
            <el-input
              v-model="form.content"
              type="textarea"
              :rows="6"
              placeholder="例如：&#10;求极限 $\lim_{x \to 0} \frac{\tan x}{x}$&#10;&#10;![](uploads/xxx.png)"
            />
          </div>
        </el-form-item>
        <el-form-item label="难度">
          <el-select v-model="form.difficulty" style="width: 100%" clearable>
            <el-option label="简单" value="easy" />
            <el-option label="中等" value="medium" />
            <el-option label="困难" value="hard" />
          </el-select>
        </el-form-item>
        <el-form-item label="链接">
          <el-input v-model="form.link" placeholder="题目链接，可空" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="form.reason" type="textarea" :rows="2" placeholder="推荐理由或补充说明" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" @click="submit">确定</el-button>
      </template>
    </el-dialog>

    <!-- 查看变题详情 -->
    <el-dialog v-model="showDetail" :title="'变题：' + (detailData.title || '')" width="760px">
      <MarkdownViewer v-if="detailData.content" :source="detailData.content" />
      <div v-else style="color: #909399; text-align: center; padding: 20px">暂无正文</div>
      <div style="margin-top: 12px; color: #909399; font-size: 13px">
        难度：{{ detailData.difficulty || '-' }} · 来源：{{ detailData.origin === 'ai' ? 'AI 推荐' : '手动录入' }}
        <a v-if="isUrl(detailData.link)" :href="detailData.link" target="_blank" rel="noopener"> · 打开原题链接</a>
        <span v-else-if="detailData.link"> · 出处：{{ detailData.link }}</span>
        <div v-if="detailData.reason" style="margin-top: 6px">说明：{{ detailData.reason }}</div>
      </div>
      <template #footer>
        <el-button @click="showDetail = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getVariants, getProblem, createVariant, updateVariant, deleteVariant, uploadImage } from '../api'
import MarkdownViewer from '../components/MarkdownViewer.vue'
import { ElMessage, ElMessageBox } from 'element-plus'

// 只有完整 URL 才当链接渲染，否则相对路径会跳到错误页面
const isUrl = (value) => /^https?:\/\/\S+/i.test((value || '').trim())

const route = useRoute()
const router = useRouter()
const variants = ref([])
const problemTitle = ref('')
const knowledgePointId = ref('')
const showDialog = ref(false)
const editingId = ref('')
const form = ref({ title: '', content: '', difficulty: '', link: '', reason: '' })

const showDetail = ref(false)
const detailData = ref({})

onMounted(() => {
  loadVariants()
  loadProblem()
})

const loadProblem = async () => {
  try {
    const res = await getProblem(route.params.problemId)
    problemTitle.value = res.data.title
    knowledgePointId.value = res.data.knowledge_point_id || ''
  } catch (error) {
    problemTitle.value = ''
  }
}

const loadVariants = async () => {
  try {
    const res = await getVariants(route.params.problemId)
    variants.value = res.data
  } catch (error) {
    ElMessage.error('加载变题失败')
  }
}

const openAdd = () => {
  editingId.value = ''
  form.value = { title: '', content: '', difficulty: '', link: '', reason: '' }
  showDialog.value = true
}

const openEdit = (row) => {
  editingId.value = row.id
  form.value = {
    title: row.title,
    content: row.content || '',
    difficulty: row.difficulty || '',
    link: row.link || '',
    reason: row.reason || ''
  }
  showDialog.value = true
}

const showDetailDialog = (row) => {
  detailData.value = {
    title: row.title, content: row.content || '',
    difficulty: row.difficulty, origin: row.origin,
    link: row.link, reason: row.reason
  }
  showDetail.value = true
}

const insertImage = async (uploadFile) => {
  const file = uploadFile.raw
  if (!file) return
  try {
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
    ElMessage.warning('请输入变题标题')
    return
  }
  const payload = {
    problem_id: route.params.problemId,
    title: form.value.title,
    content: form.value.content || null,
    difficulty: form.value.difficulty,
    link: form.value.link,
    reason: form.value.reason
  }
  try {
    if (editingId.value) {
      await updateVariant(editingId.value, payload)
      ElMessage.success('修改成功')
    } else {
      await createVariant(payload)
      ElMessage.success('创建成功')
    }
    showDialog.value = false
    loadVariants()
  } catch (error) {
    ElMessage.error('保存失败')
  }
}

const removeFn = async (row) => {
  try {
    await ElMessageBox.confirm(`确定删除「${row.title}」吗？`, '提示', { type: 'warning' })
    await deleteVariant(row.id)
    ElMessage.success('删除成功')
    loadVariants()
  } catch (error) {
    if (error !== 'cancel') ElMessage.error('删除失败')
  }
}

const goBack = () => {
  router.push(`/knowledge-points/${knowledgePointId.value}`)
}
</script>
