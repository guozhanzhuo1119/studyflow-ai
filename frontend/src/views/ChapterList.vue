<template>
  <div>
    <el-card>
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span style="font-size: 18px; font-weight: bold">
            {{ subjectName || '章节' }} · 章节列表
          </span>
          <div>
            <el-button @click="router.push('/')">返回科目</el-button>
            <el-button type="primary" @click="openAdd">新建章节</el-button>
          </div>
        </div>
      </template>

      <el-table :data="chapters" stripe style="width: 100%">
        <el-table-column prop="name" label="章节/模块" />
        <el-table-column prop="order_num" label="排序" width="80" />
        <el-table-column prop="knowledge_point_count" label="知识点数" width="110" />
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column label="操作" width="260">
          <template #default="scope">
            <el-button type="primary" size="small" @click="goToKnowledgePoints(scope.row)">查看知识点</el-button>
            <el-button size="small" @click="openEdit(scope.row)">编辑</el-button>
            <el-button type="danger" size="small" @click="removeFn(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="showDialog" :title="editingId ? '编辑章节' : '新建章节'" width="460px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="章节名">
          <el-input v-model="form.name" placeholder="例如：极限" />
        </el-form-item>
        <el-form-item label="排序">
          <el-input-number v-model="form.order_num" :min="0" />
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
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getChapters, getSubject, createChapter, updateChapter, deleteChapter } from '../api'
import { ElMessage, ElMessageBox } from 'element-plus'

const route = useRoute()
const router = useRouter()
const chapters = ref([])
const subjectName = ref('')
const showDialog = ref(false)
const editingId = ref('')
const form = ref({ name: '', order_num: 0 })

onMounted(() => {
  loadChapters()
  loadSubjectName()
})

const loadSubjectName = async () => {
  try {
    const res = await getSubject(route.params.subjectId)
    subjectName.value = res.data.name
  } catch (error) {
    subjectName.value = ''
  }
}

const loadChapters = async () => {
  try {
    const res = await getChapters(route.params.subjectId)
    chapters.value = res.data
  } catch (error) {
    ElMessage.error('加载章节失败')
  }
}

const openAdd = () => {
  editingId.value = ''
  form.value = { name: '', order_num: chapters.value.length }
  showDialog.value = true
}

const openEdit = (row) => {
  editingId.value = row.id
  form.value = { name: row.name, order_num: row.order_num || 0 }
  showDialog.value = true
}

const submit = async () => {
  if (!form.value.name) {
    ElMessage.warning('请输入章节名')
    return
  }
  const payload = {
    subject_id: route.params.subjectId,
    name: form.value.name,
    order_num: form.value.order_num || 0
  }
  try {
    if (editingId.value) {
      await updateChapter(editingId.value, payload)
      ElMessage.success('修改成功')
    } else {
      await createChapter(payload)
      ElMessage.success('创建成功')
    }
    showDialog.value = false
    loadChapters()
  } catch (error) {
    ElMessage.error('保存失败')
  }
}

const removeFn = async (row) => {
  try {
    await ElMessageBox.confirm(`删除「${row.name}」会同时删掉它下面的知识点、母题和变题，确定吗？`, '提示', {
      type: 'warning'
    })
    const res = await deleteChapter(row.id)
    ElMessage.success(`删除成功，同时清理了 ${res.data.deletedProblems} 道母题`)
    loadChapters()
  } catch (error) {
    if (error !== 'cancel') ElMessage.error('删除失败')
  }
}

const goToKnowledgePoints = (row) => {
  router.push(`/chapters/${row.id}`)
}
</script>
