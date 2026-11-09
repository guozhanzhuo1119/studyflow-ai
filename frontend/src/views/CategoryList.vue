<template>
  <div>
    <el-card>
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span style="font-size: 18px; font-weight: bold">知识点列表</span>
          <div>
            <el-button @click="router.push('/errors')">错因统计</el-button>
            <el-button type="primary" @click="showAddDialog = true">新建知识点</el-button>
          </div>
        </div>
      </template>

      <el-table :data="categories" stripe style="width: 100%">
        <el-table-column prop="name" label="名称" />
        <el-table-column prop="source" label="来源" />
        <el-table-column prop="created_at" label="创建时间" width="180" />
        <el-table-column label="操作" width="150">
          <template #default="scope">
            <el-button type="primary" size="small" @click="goToProblems(scope.row)">查看题目</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新建知识点对话框 -->
    <el-dialog v-model="showAddDialog" title="新建知识点" width="400px">
      <el-form :model="newCategory" label-width="80px">
        <el-form-item label="名称">
          <el-input v-model="newCategory.name" placeholder="例如：线性代数" />
        </el-form-item>
        <el-form-item label="来源">
          <el-input v-model="newCategory.source" placeholder="例如：考研数学" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="addCategory">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getCategories, createCategory } from '../api'
import { ElMessage } from 'element-plus'

const router = useRouter()
const categories = ref([])
const showAddDialog = ref(false)
const newCategory = ref({ name: '', source: '' })

onMounted(() => {
  loadCategories()
})

const loadCategories = async () => {
  try {
    const res = await getCategories()
    categories.value = res.data
  } catch (error) {
    ElMessage.error('加载知识点失败')
  }
}

const addCategory = async () => {
  if (!newCategory.value.name) {
    ElMessage.warning('请输入名称')
    return
  }
  try {
    await createCategory(newCategory.value)
    ElMessage.success('创建成功')
    showAddDialog.value = false
    newCategory.value = { name: '', source: '' }
    loadCategories()
  } catch (error) {
    ElMessage.error('创建失败')
  }
}

const goToProblems = (category) => {
  router.push(`/categories/${category.id}`)
}
</script>
