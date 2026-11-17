<template>
  <div class="knowledge-base">
    <el-card shadow="never" class="upload-card">
      <template #header>
        <div class="card-head">
          <span>上传教材 / 文档</span>
          <span class="hint">支持 PDF、TXT、Markdown，单文件 ≤ 500MB</span>
        </div>
      </template>
      <el-form :inline="true" @submit.prevent>
        <el-form-item label="标题">
          <el-input v-model="title" placeholder="留空则用文件名" clearable style="width: 220px" />
        </el-form-item>
        <el-form-item label="科目">
          <el-select v-model="subjectId" placeholder="可选，仅做归档" clearable style="width: 180px">
            <el-option v-for="s in subjects" :key="s.id" :label="s.name" :value="s.id" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-upload
            :show-file-list="false"
            :http-request="doUpload"
            :disabled="uploading"
            accept=".pdf,.txt,.md,.markdown"
          >
            <el-button type="primary" :loading="uploading">选择文件并导入</el-button>
          </el-upload>
        </el-form-item>
        <el-form-item>
          <el-button @click="pasteDialog = true">粘贴文字导入</el-button>
        </el-form-item>
      </el-form>
      <el-alert
        v-if="warning"
        :title="warning"
        type="warning"
        show-icon
        :closable="false"
        style="margin-top: 4px"
      />
    </el-card>

    <el-card shadow="never" style="margin-top: 16px">
      <template #header>
        <div class="card-head">
          <span>知识库（{{ materials.length }} 份）</span>
          <el-button text @click="load">刷新</el-button>
        </div>
      </template>

      <el-table :data="materials" v-loading="loading" empty-text="还没有导入任何文档">
        <el-table-column prop="title" label="标题" min-width="180" />
        <el-table-column prop="file_type" label="格式" width="80" />
        <el-table-column prop="page_count" label="页数" width="80" />
        <el-table-column prop="char_count" label="字符数" width="100" />
        <el-table-column label="抽取质量" width="110">
          <template #default="{ row }">
            <el-tag :type="row.quality === 'ok' ? 'success' : 'danger'" size="small">
              {{ row.quality === 'ok' ? '可检索' : '扫描版' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="230">
          <template #default="{ row }">
            <el-button text size="small" @click="preview(row)">预览原文</el-button>
            <el-button text size="small" type="primary" @click="parseOutline(row)">解析章节</el-button>
            <el-button text size="small" type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-drawer v-model="drawer" :title="current?.title" size="60%">
      <div v-loading="chunkLoading">
        <p class="hint" style="margin-bottom: 12px">
          共 {{ current?.page_count }} 页 / {{ current?.char_count }} 字符。下面显示前 30 段，每段标注所在页码。
        </p>
        <el-card v-for="chunk in chunks" :key="chunk.page_no + '-' + chunk.seq" shadow="never" class="chunk-card">
          <template #header>
            <span class="chunk-page">第 {{ chunk.page_no }} 页 · 段 {{ chunk.seq + 1 }}</span>
          </template>
          <pre class="chunk-text">{{ chunk.content }}</pre>
        </el-card>
      </div>
    </el-drawer>

    <el-dialog v-model="pasteDialog" title="粘贴文字导入" width="720px">
      <el-form label-width="80px">
        <el-form-item label="标题" required>
          <el-input v-model="pasteForm.title" placeholder="例如：数据结构教材 第1章" maxlength="200" />
        </el-form-item>
        <el-form-item label="科目">
          <el-select v-model="pasteForm.subject_id" placeholder="可选，仅做归档" clearable style="width: 220px">
            <el-option v-for="s in subjects" :key="s.id" :label="s.name" :value="s.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="正文" required>
          <el-input
            v-model="pasteForm.content"
            type="textarea"
            :rows="14"
            placeholder="把教材文字粘贴进来，建议保留「第X章 / 第X节」等标题行"
          />
          <span class="hint">当前 {{ pasteForm.content.trim().length }} 字符，至少 50 字</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="pasteDialog = false">取消</el-button>
        <el-button type="primary" :loading="pasteSaving" @click="submitPaste">导入</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="outlineDrawer" :title="`解析章节 · ${outlineMaterial?.title || ''}`" size="65%">
      <div v-loading="outlineLoading">
        <el-alert
          v-for="(item, index) in outlineWarnings"
          :key="index"
          :title="item"
          type="warning"
          show-icon
          :closable="false"
          style="margin-bottom: 8px"
        />

        <div class="outline-bar">
          <span class="hint">写入科目：</span>
          <el-select v-model="outlineSubjectId" placeholder="留空则新建科目（使用教材标题）" clearable style="width: 280px">
            <el-option v-for="s in subjects" :key="s.id" :label="s.name" :value="s.id" />
          </el-select>
          <span class="hint">共 {{ selectedCount }} / {{ outline.length }} 章将被写入</span>
        </div>

        <el-table :data="outline" size="small" empty-text="没有生成章节草案" style="margin-top: 8px">
          <el-table-column width="52">
            <template #default="{ row }">
              <el-checkbox v-model="row.selected" />
            </template>
          </el-table-column>
          <el-table-column label="章节名" min-width="240">
            <template #default="{ row }">
              <el-input v-model="row.name" size="small" maxlength="100" />
            </template>
          </el-table-column>
          <el-table-column label="起始页" width="110">
            <template #default="{ row }">
              <el-input-number v-model="row.start_page" :min="0" :controls="false" size="small" style="width: 80px" />
            </template>
          </el-table-column>
          <el-table-column label="结束页" width="110">
            <template #default="{ row }">
              <el-input-number v-model="row.end_page" :min="0" :controls="false" size="small" style="width: 80px" />
            </template>
          </el-table-column>
          <el-table-column label="操作" width="110">
            <template #default="{ $index }">
              <el-button text size="small" :disabled="$index >= outline.length - 1" @click="mergeNext($index)">
                并入下一章
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
      <template #footer>
        <el-button @click="outlineDrawer = false">取消</el-button>
        <el-button type="primary" :loading="outlineSaving" @click="confirmOutline">确认写入章节</el-button>
      </template>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  confirmMaterialOutline,
  deleteMaterial,
  getMaterialChunks,
  getMaterialOutline,
  getMaterials,
  getSubjects,
  importMaterialText,
  uploadMaterial
} from '../api'

const materials = ref([])
const subjects = ref([])
const chunks = ref([])
const title = ref('')
const subjectId = ref('')
const uploading = ref(false)
const loading = ref(false)
const chunkLoading = ref(false)
const warning = ref('')
const drawer = ref(false)
const current = ref(null)

// 教材 -> 章节草案
const outline = ref([])
const outlineMaterial = ref(null)
const outlineWarnings = ref([])
const outlineSubjectId = ref('')
const outlineDrawer = ref(false)
const outlineLoading = ref(false)
const outlineSaving = ref(false)
const selectedCount = computed(() => outline.value.filter(item => item.selected && item.name.trim()).length)

// 粘贴文字导入
const pasteDialog = ref(false)
const pasteSaving = ref(false)
const pasteForm = ref({ title: '', subject_id: '', content: '' })

const load = async () => {
  loading.value = true
  try {
    const res = await getMaterials()
    materials.value = res.data
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '加载知识库失败')
  } finally {
    loading.value = false
  }
}

const loadSubjects = async () => {
  try {
    const res = await getSubjects()
    subjects.value = res.data
  } catch (e) {
    // 科目只用于归档，失败不影响上传
  }
}

const doUpload = async ({ file }) => {
  const ext = file.name.split('.').pop().toLowerCase()
  if (!['pdf', 'txt', 'md', 'markdown'].includes(ext)) {
    ElMessage.error('仅支持 PDF、TXT、Markdown')
    return
  }
  uploading.value = true
  warning.value = ''
  try {
    const res = await uploadMaterial(file, title.value, subjectId.value)
    warning.value = res.data.warning || ''
    ElMessage.success(
      res.data.warning
        ? `「${res.data.title}」已导入，但未检测到文字层`
        : `「${res.data.title}」导入成功：${res.data.page_count} 页，${res.data.char_count} 字符`
    )
    title.value = ''
    await load()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '上传失败')
  } finally {
    uploading.value = false
  }
}

const preview = async row => {
  current.value = row
  drawer.value = true
  chunkLoading.value = true
  chunks.value = []
  try {
    const res = await getMaterialChunks(row.id, { limit: 30 })
    chunks.value = res.data.chunks
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '读取原文失败')
  } finally {
    chunkLoading.value = false
  }
}

const remove = async row => {
  try {
    await ElMessageBox.confirm(`删除「${row.title}」及其分块？磁盘上的原文件会保留。`, '确认删除', {
      type: 'warning'
    })
  } catch (e) {
    return
  }
  try {
    await deleteMaterial(row.id)
    ElMessage.success('已删除')
    await load()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '删除失败')
  }
}

const parseOutline = async row => {
  outlineMaterial.value = row
  outlineSubjectId.value = row.subject_id || ''
  outline.value = []
  outlineWarnings.value = []
  outlineDrawer.value = true
  outlineLoading.value = true
  try {
    const res = await getMaterialOutline(row.id)
    outlineWarnings.value = res.data.warnings || []
    outline.value = (res.data.chapters || []).map(item => ({
      selected: true,
      name: item.name,
      start_page: item.start_page,
      end_page: item.end_page
    }))
    if (!outline.value.length) {
      ElMessage.warning('没有识别到章节，可改用「粘贴文字导入」后重试')
    }
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '解析章节失败')
  } finally {
    outlineLoading.value = false
  }
}

const mergeNext = index => {
  if (index < 0 || index >= outline.value.length - 1) return
  const current = outline.value[index]
  const next = outline.value[index + 1]
  current.end_page = Math.max(current.end_page, next.end_page)
  if (current.start_page > current.end_page) {
    current.start_page = next.start_page
  }
  outline.value.splice(index + 1, 1)
}

const confirmOutline = async () => {
  const picked = outline.value.filter(item => item.selected && item.name.trim())
  if (!picked.length) {
    ElMessage.warning('至少勾选一个有章节名的章节')
    return
  }
  outlineSaving.value = true
  try {
    const res = await confirmMaterialOutline(outlineMaterial.value.id, {
      subject_id: outlineSubjectId.value || null,
      chapters: picked.map(item => ({
        name: item.name.trim(),
        start_page: item.start_page,
        end_page: item.end_page
      }))
    })
    const created = res.data.created?.length || 0
    const skipped = res.data.skipped?.length || 0
    ElMessage.success(
      `已写入 ${created} 个章节${skipped ? `，跳过 ${skipped} 个同名章节` : ''}`
    )
    outlineDrawer.value = false
    await load()
    await loadSubjects()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '写入章节失败')
  } finally {
    outlineSaving.value = false
  }
}

const submitPaste = async () => {
  const name = pasteForm.value.title.trim()
  if (!name) {
    ElMessage.warning('请填写标题')
    return
  }
  if (pasteForm.value.content.trim().length < 50) {
    ElMessage.warning('正文至少 50 字')
    return
  }
  pasteSaving.value = true
  try {
    const res = await importMaterialText({
      title: name,
      content: pasteForm.value.content,
      subject_id: pasteForm.value.subject_id || null
    })
    ElMessage.success(`「${res.data.title}」已导入：${res.data.char_count} 字符`)
    pasteDialog.value = false
    pasteForm.value = { title: '', subject_id: '', content: '' }
    await load()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '导入失败')
  } finally {
    pasteSaving.value = false
  }
}

onMounted(() => {
  load()
  loadSubjects()
})
</script>

<style scoped>
.knowledge-base {
  padding: 16px;
}
.card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.hint {
  color: #909399;
  font-size: 12px;
}
.chunk-card {
  margin-bottom: 12px;
}
.chunk-page {
  font-size: 12px;
  color: #606266;
}
.chunk-text {
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
}
.outline-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
</style>
