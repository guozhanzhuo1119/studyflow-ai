<template>
  <div>
    <el-card>
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span style="font-size: 18px; font-weight: bold">题目列表</span>
          <div>
            <el-button @click="goBack">返回</el-button>
            <el-button type="primary" @click="showAddDialog = true">新建题目</el-button>
          </div>
        </div>
      </template>

      <!-- 语义搜题：向量相似度检索，不是关键词匹配 -->
      <div style="display: flex; gap: 10px; margin-bottom: 15px">
        <el-input
          v-model="searchQuery"
          placeholder="语义搜题，例如：求极限常用的思路、和矩阵有关的题"
          @keyup.enter="searchFn"
          clearable
        />
        <el-button type="primary" :loading="searching" @click="searchFn">语义搜索</el-button>
        <el-button v-if="searchMode" @click="clearSearch">返回全部</el-button>
      </div>
      <el-alert
        v-if="searchMode"
        :title="`语义检索结果：${problems.length} 道相似题（按相似度排序）`"
        type="success"
        :closable="false"
        style="margin-bottom: 15px"
      />

      <el-table :data="problems" stripe style="width: 100%">
        <el-table-column prop="title" label="标题" />
        <el-table-column v-if="searchMode" prop="score" label="相似度" width="100" />
        <el-table-column prop="source" label="来源" width="120" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="scope">
            <el-tag :type="scope.row.status === 'done' ? 'success' : 'info'">{{ scope.row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="300">
          <template #default="scope">
            <el-button type="success" size="small" @click="recommendFn(scope.row)">AI 推荐</el-button>
            <el-button type="warning" size="small" @click="goErrorAnalysis(scope.row)">错因归因</el-button>
            <el-button type="danger" size="small" @click="deleteProblemFn(scope.row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新建题目对话框 -->
    <el-dialog v-model="showAddDialog" title="新建题目" width="500px">
      <el-form :model="newProblem" label-width="80px">
        <el-form-item label="标题">
          <el-input v-model="newProblem.title" placeholder="题目名称" />
        </el-form-item>
        <el-form-item label="来源">
          <el-input v-model="newProblem.source" placeholder="例如：考研真题" />
        </el-form-item>
        <el-form-item label="标签">
          <el-input v-model="newProblem.tags" placeholder="用逗号分隔" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="addProblem">确定</el-button>
      </template>
    </el-dialog>

    <!-- AI 推荐结果对话框 -->
    <el-dialog v-model="showRecommendDialog" title="AI 推荐变体题" width="700px">
      <div v-if="recommendations.length > 1">
        <el-card v-for="(item, index) in recommendations.slice(1)" :key="index" style="margin-bottom: 15px">
          <template #header>
            <div style="display: flex; justify-content: space-between">
              <span style="font-weight: bold">{{ index + 1 }}. {{ item.title }}</span>
              <el-tag :type="getDifficultyType(item.difficulty)">{{ item.difficulty }}</el-tag>
            </div>
          </template>
          <div v-if="item.link" style="color: #409eff; margin-bottom: 10px">来源：{{ item.link }}</div>
          <div style="color: #666">{{ item.reason }}</div>
        </el-card>
      </div>
      <el-empty v-else description="暂无推荐" />
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getProblems, createProblem, deleteProblem as apiDeleteProblem, recommend as apiRecommend, searchProblems } from '../api'
import { ElMessage, ElMessageBox } from 'element-plus'

const route = useRoute()
const router = useRouter()
const problems = ref([])
const searchQuery = ref('')
const searching = ref(false)
const searchMode = ref(false)
const showAddDialog = ref(false)
const showRecommendDialog = ref(false)
const recommendations = ref([])
const newProblem = ref({
  title: '',
  source: '',
  tags: '',
  category_id: route.params.id
})

onMounted(() => {
  loadProblems()
})

const loadProblems = async () => {
  try {
    const res = await getProblems(route.params.id)
    problems.value = res.data
  } catch (error) {
    ElMessage.error('加载题目失败')
  }
}

const searchFn = async () => {
  if (!searchQuery.value.trim()) {
    ElMessage.warning('请输入搜索内容')
    return
  }
  searching.value = true
  try {
    const res = await searchProblems(searchQuery.value, 10)
    problems.value = res.data.results
    searchMode.value = true
    if (!problems.value.length) ElMessage.info('没有找到语义相似的题目')
  } catch (error) {
    ElMessage.error('搜索失败')
  } finally {
    searching.value = false
  }
}

const clearSearch = () => {
  searchQuery.value = ''
  searchMode.value = false
  loadProblems()
}

const goErrorAnalysis = (problem) => {
  router.push({ path: '/errors', query: { problem_id: problem.id } })
}

const addProblem = async () => {
  if (!newProblem.value.title) {
    ElMessage.warning('请输入标题')
    return
  }
  try {
    await createProblem(newProblem.value)
    ElMessage.success('创建成功')
    showAddDialog.value = false
    newProblem.value = { title: '', source: '', tags: '', category_id: route.params.id }
    loadProblems()
  } catch (error) {
    ElMessage.error('创建失败')
  }
}

const deleteProblemFn = async (id) => {
  try {
    await ElMessageBox.confirm('确定删除这道题吗？', '提示', { type: 'warning' })
    await apiDeleteProblem(id)
    ElMessage.success('删除成功')
    loadProblems()
  } catch (error) {
    if (error !== 'cancel') ElMessage.error('删除失败')
  }
}

const recommendFn = async (problem) => {
  try {
    ElMessage.info('AI 正在生成推荐...')
    const res = await apiRecommend(problem.id, 3)
    recommendations.value = res.data.recommendations
    showRecommendDialog.value = true
  } catch (error) {
    ElMessage.error('推荐失败')
  }
}

const getDifficultyType = (difficulty) => {
  const map = { easy: 'success', medium: 'warning', hard: 'danger' }
  return map[difficulty] || 'info'
}

const goBack = () => {
  router.push('/')
}
</script>
