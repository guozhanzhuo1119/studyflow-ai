<template>
  <div>
    <el-card>
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span style="font-size: 18px; font-weight: bold">
            {{ pathText }} · 知识点列表
          </span>
          <div>
            <el-button @click="goBack">返回章节</el-button>
            <el-button type="primary" @click="openAdd">新建知识点</el-button>
          </div>
        </div>
      </template>

      <el-table :data="knowledgePoints" stripe style="width: 100%">
        <el-table-column prop="name" label="知识点" />
        <el-table-column prop="problem_count" label="母题数" width="100" />
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column label="操作" width="260">
          <template #default="scope">
            <el-button type="primary" size="small" @click="goToProblems(scope.row)">查看母题</el-button>
            <el-button size="small" @click="openEdit(scope.row)">编辑</el-button>
            <el-button type="danger" size="small" @click="removeFn(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="showDialog" :title="editingId ? '编辑知识点' : '新建知识点'" width="460px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="知识点名">
          <el-input v-model="form.name" placeholder="例如：洛必达法则" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" @click="submit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getKnowledgePoints, getChapter, createKnowledgePoint, updateKnowledgePoint, deleteKnowledgePoint } from '../api'
import { ElMessage, ElMessageBox } from 'element-plus'

const route = useRoute()
const router = useRouter()
const knowledgePoints = ref([])
const chapterName = ref('')
const subjectName = ref('')
const subjectId = ref('')
const showDialog = ref(false)
const editingId = ref('')
const form = ref({ name: '' })

const pathText = computed(() => [subjectName.value, chapterName.value].filter(Boolean).join(' / '))

onMounted(() => {
  loadKnowledgePoints()
  loadChapter()
})

const loadChapter = async () => {
  try {
    const res = await getChapter(route.params.chapterId)
    chapterName.value = res.data.name
    subjectName.value = res.data.subject_name || ''
    subjectId.value = res.data.subject_id || ''
  } catch (error) {
    chapterName.value = ''
  }
}

const loadKnowledgePoints = async () => {
  try {
    const res = await getKnowledgePoints(route.params.chapterId)
    knowledgePoints.value = res.data
  } catch (error) {
    ElMessage.error('加载知识点失败')
  }
}

const openAdd = () => {
  editingId.value = ''
  form.value = { name: '' }
  showDialog.value = true
}

const openEdit = (row) => {
  editingId.value = row.id
  form.value = { name: row.name }
  showDialog.value = true
}

const submit = async () => {
  if (!form.value.name) {
    ElMessage.warning('请输入知识点名')
    return
  }
  const payload = { chapter_id: route.params.chapterId, name: form.value.name }
  try {
    if (editingId.value) {
      await updateKnowledgePoint(editingId.value, payload)
      ElMessage.success('修改成功')
    } else {
      await createKnowledgePoint(payload)
      ElMessage.success('创建成功')
    }
    showDialog.value = false
    loadKnowledgePoints()
  } catch (error) {
    ElMessage.error('保存失败')
  }
}

const removeFn = async (row) => {
  try {
    await ElMessageBox.confirm(`删除「${row.name}」会同时删掉它下面的母题和变题，确定吗？`, '提示', {
      type: 'warning'
    })
    const res = await deleteKnowledgePoint(row.id)
    ElMessage.success(`删除成功，同时清理了 ${res.data.deletedProblems} 道母题`)
    loadKnowledgePoints()
  } catch (error) {
    if (error !== 'cancel') ElMessage.error('删除失败')
  }
}

const goToProblems = (row) => {
  router.push(`/knowledge-points/${row.id}`)
}

const goBack = () => {
  router.push(`/subjects/${subjectId.value}`)
}
</script>
