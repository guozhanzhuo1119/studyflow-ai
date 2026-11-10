<template>
  <div>
    <el-card>
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span style="font-size: 18px; font-weight: bold">科目列表</span>
          <div>
            <el-button @click="router.push('/errors')">错因统计</el-button>
            <el-button type="primary" @click="openAdd">新建科目</el-button>
          </div>
        </div>
      </template>

      <el-table :data="subjects" stripe style="width: 100%">
        <el-table-column prop="name" label="科目" />
        <el-table-column prop="description" label="描述" />
        <el-table-column prop="chapter_count" label="章节数" width="100" />
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column label="操作" width="260">
          <template #default="scope">
            <el-button type="primary" size="small" @click="goToChapters(scope.row)">查看章节</el-button>
            <el-button size="small" @click="openEdit(scope.row)">编辑</el-button>
            <el-button type="danger" size="small" @click="removeFn(scope.row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="showDialog" :title="editingId ? '编辑科目' : '新建科目'" width="460px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="科目名">
          <el-input v-model="form.name" placeholder="例如：高等数学" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" placeholder="例如：考研数学一" />
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
import { useRouter } from 'vue-router'
import { getSubjects, createSubject, updateSubject, deleteSubject } from '../api'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()
const subjects = ref([])
const showDialog = ref(false)
const editingId = ref('')
const form = ref({ name: '', description: '' })

onMounted(() => {
  loadSubjects()
})

const loadSubjects = async () => {
  try {
    const res = await getSubjects()
    subjects.value = res.data
  } catch (error) {
    ElMessage.error('加载科目失败')
  }
}

const openAdd = () => {
  editingId.value = ''
  form.value = { name: '', description: '' }
  showDialog.value = true
}

const openEdit = (row) => {
  editingId.value = row.id
  form.value = { name: row.name, description: row.description || '' }
  showDialog.value = true
}

const submit = async () => {
  if (!form.value.name) {
    ElMessage.warning('请输入科目名')
    return
  }
  try {
    if (editingId.value) {
      await updateSubject(editingId.value, form.value)
      ElMessage.success('修改成功')
    } else {
      await createSubject(form.value)
      ElMessage.success('创建成功')
    }
    showDialog.value = false
    loadSubjects()
  } catch (error) {
    ElMessage.error('保存失败')
  }
}

const removeFn = async (row) => {
  try {
    await ElMessageBox.confirm(`删除「${row.name}」会同时删掉它的章节、知识点、母题和变题，确定吗？`, '提示', {
      type: 'warning'
    })
    const res = await deleteSubject(row.id)
    ElMessage.success(`删除成功，同时清理了 ${res.data.deletedProblems} 道母题`)
    loadSubjects()
  } catch (error) {
    if (error !== 'cancel') ElMessage.error('删除失败')
  }
}

const goToChapters = (row) => {
  router.push(`/subjects/${row.id}`)
}
</script>
