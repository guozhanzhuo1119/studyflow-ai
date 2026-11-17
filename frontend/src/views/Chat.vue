<template>
  <div style="max-width: 800px; margin: 0 auto">
    <el-card>
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <div style="display: flex; align-items: center; gap: 10px">
            <span style="font-size: 18px; font-weight: bold">AI 学习助手</span>
            <el-select v-model="currentSubject" size="small" style="width: 150px" placeholder="选择科目">
              <el-option label="通用" :value="GENERAL" />
              <el-option v-for="s in subjects" :key="s.id" :label="s.name" :value="s.id" />
            </el-select>
          </div>
          <el-button size="small" @click="resetSession">开启新对话</el-button>
        </div>
      </template>

      <!-- 从题目详情带进来的题目上下文 -->
      <el-alert
        v-if="questionId"
        type="info"
        show-icon
        closable
        style="margin-bottom: 10px"
        @close="clearQuestion"
      >
        <template #title>正在围绕题目提问：{{ questionTitle || questionId }}</template>
      </el-alert>

      <!-- 聊天消息列表 -->
      <div ref="chatContainer" style="height: 500px; overflow-y: auto; padding: 20px; background: #f5f5f5">
        <div v-for="(msg, index) in messages" :key="index" style="margin-bottom: 15px">
          <div v-if="msg.role === 'user'" style="display: flex; justify-content: flex-end">
            <div style="background: #409eff; color: white; padding: 10px 15px; border-radius: 10px; max-width: 70%">
              {{ msg.content }}
            </div>
          </div>
          <div v-else style="display: flex; justify-content: flex-start">
            <div style="background: white; padding: 10px 15px; border-radius: 10px; max-width: 70%; white-space: pre-wrap">
              {{ msg.content }}
            </div>
          </div>
        </div>
        <div v-if="loading" style="text-align: center; color: #999">AI 正在思考...</div>
      </div>

      <!-- 输入框 -->
      <div style="display: flex; gap: 10px; margin-top: 15px">
        <el-input
          v-model="inputMessage"
          type="textarea"
          :rows="3"
          placeholder="输入你的问题，例如：帮我分析线性代数的弱项"
          @keyup.enter.ctrl="sendMessage"
        />
        <el-button type="primary" @click="sendMessage" :loading="loading" style="height: 80px">发送</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { chat, getSubjects, getSessionMessages } from '../api'
import { ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()
const questionId = ref(route.query.question_id || '')
const questionTitle = ref(route.query.question_title || '')

const GENERAL = '__general__'
const messages = ref([])
const inputMessage = ref('')
const loading = ref(false)
const chatContainer = ref(null)
const subjects = ref([])
// 记住上次选的科目，刷新页面后自动回到那个科目的对话
const currentSubject = ref(localStorage.getItem('chatSubject') || GENERAL)
const sessionId = ref(null)

// 每个科目各存一份会话 id，切换科目时互不覆盖
const storageKey = (subject) => `chatSessionId:${subject}`

const scrollToBottom = async () => {
  await nextTick()
  if (chatContainer.value) {
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight
  }
}

const loadSession = async (subject) => {
  messages.value = []
  sessionId.value = localStorage.getItem(storageKey(subject))
  if (!sessionId.value) return
  try {
    const res = await getSessionMessages(sessionId.value)
    messages.value = res.data.messages
      .filter((msg) => msg.role !== 'system')
      .map((msg) => ({ role: msg.role, content: msg.content }))
    await scrollToBottom()
  } catch (error) {
    // 会话已被删除或不存在，清掉本地残留的 id
    localStorage.removeItem(storageKey(subject))
    sessionId.value = null
  }
}

onMounted(async () => {
  try {
    const res = await getSubjects()
    subjects.value = res.data || []
  } catch (error) {
    subjects.value = []
  }
  await loadSession(currentSubject.value)
})

// 切换科目就切换会话，并恢复该科目上一次的聊天记录
watch(currentSubject, async (value) => {
  localStorage.setItem('chatSubject', value)
  await loadSession(value)
})

watch(() => route.query.question_id, (value) => {
  questionId.value = value || ''
  questionTitle.value = route.query.question_title || ''
})

const clearQuestion = () => {
  questionId.value = ''
  questionTitle.value = ''
  router.replace({ path: '/chat' })
}

const sendMessage = async () => {
  if (!inputMessage.value.trim()) return

  const subject = currentSubject.value
  // 通用对话不限定科目，选了科目则把 id 带给后端，让工具只在该科目内检索统计
  const subjectId = subject === GENERAL ? null : subject
  const userMsg = inputMessage.value
  messages.value.push({ role: 'user', content: userMsg })
  inputMessage.value = ''
  loading.value = true

  try {
    const res = await chat(userMsg, sessionId.value, subjectId, questionId.value || null)
    messages.value.push({ role: 'assistant', content: res.data.reply })
    sessionId.value = res.data.session_id
    localStorage.setItem(storageKey(subject), res.data.session_id)
  } catch (error) {
    ElMessage.error('发送失败')
  } finally {
    loading.value = false
    await scrollToBottom()
  }
}

const resetSession = () => {
  localStorage.removeItem(storageKey(currentSubject.value))
  sessionId.value = null
  messages.value = []
}
</script>
