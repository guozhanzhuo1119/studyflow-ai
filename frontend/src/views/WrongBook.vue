<template>
  <el-card>
    <template #header>
      <div class="header-row">
        <span class="title">错题本（未掌握 {{ unmastered }} / 共 {{ total }}）</span>
        <div class="header-actions">
          <el-radio-group v-model="filter" size="small" @change="load">
            <el-radio-button label="unmastered">未掌握</el-radio-button>
            <el-radio-button label="mastered">已掌握</el-radio-button>
            <el-radio-button label="all">全部</el-radio-button>
          </el-radio-group>
          <el-button size="small" @click="load">刷新</el-button>
        </div>
      </div>
    </template>

    <el-table v-loading="loading" :data="items" stripe style="width: 100%">
      <el-table-column label="题目" min-width="260">
        <template #default="scope">
          <div>{{ scope.row.title }}</div>
          <div class="path">{{ pathText(scope.row) }}</div>
        </template>
      </el-table-column>
      <el-table-column label="类型" width="80">
        <template #default="scope">{{ scope.row.target_type === 'variant' ? '变题' : '母题' }}</template>
      </el-table-column>
      <el-table-column prop="wrong_count" label="答错次数" width="90" />
      <el-table-column label="最近答错" width="160">
        <template #default="scope">{{ formatTime(scope.row.last_wrong_at) }}</template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="scope">
          <el-tag :type="scope.row.mastered ? 'success' : 'danger'" size="small">
            {{ scope.row.mastered ? '已掌握' : '未掌握' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="100">
        <template #default="scope">
          <el-button size="small" type="primary" :disabled="!scope.row.knowledge_point_id" @click="goPractice(scope.row)">
            去练习
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <div v-if="!loading && !items.length" class="empty">还没有错题，去题目详情里做题试试</div>
  </el-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getWrongBook } from '../api'
import { ElMessage } from 'element-plus'

const router = useRouter()
const loading = ref(false)
const filter = ref('unmastered')
const items = ref([])
const total = ref(0)
const unmastered = ref(0)

const load = async () => {
  loading.value = true
  try {
    const params = filter.value === 'all' ? {} : { mastered: filter.value === 'mastered' }
    const res = await getWrongBook(params)
    items.value = res.data.items || []
    total.value = res.data.total || 0
    unmastered.value = res.data.unmastered || 0
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '错题本加载失败')
  } finally {
    loading.value = false
  }
}

const pathText = (row) => {
  const parts = [row.subject_name, row.chapter_name, row.knowledge_point_name].filter(Boolean)
  return parts.length ? parts.join(' / ') : '题目可能已被删除'
}

const formatTime = (value) => (value ? String(value).replace('T', ' ').slice(0, 16) : '-')

const goPractice = (row) => {
  if (row.knowledge_point_id) {
    router.push(`/knowledge-points/${row.knowledge_point_id}`)
  }
}

onMounted(load)
</script>

<style scoped>
.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.title {
  font-weight: bold;
}
.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}
.path {
  margin-top: 4px;
  color: #909399;
  font-size: 12px;
}
.empty {
  padding: 30px;
  text-align: center;
  color: #909399;
}
</style>
