<template>
  <div class="chat-overlay" @click.self="closeChat">
    <div class="chat-window glass-card">
      <div class="chat-head">
        <img :src="xinyuehu" class="bot-avatar" style="width: 36px; height: 36px" alt="心月狐" />
        <div class="chat-head-text">
          <div class="chat-name">心月狐</div>
          <div class="chat-role">情感陪伴 · 学习陪练</div>
        </div>
        <span class="chat-online"><i></i>在线</span>
        <button class="chat-close" title="收起" @click="closeChat">×</button>
      </div>

      <div class="chat-select">
        <el-select v-model="currentSubject" size="small" style="width: 100%" placeholder="选择科目">
          <el-option label="通用" :value="GENERAL" />
          <el-option v-for="s in subjects" :key="s.id" :label="s.name" :value="s.id" />
        </el-select>
      </div>

      <!-- 从题目详情带进来的题目上下文 -->
      <el-alert
        v-if="questionId"
        type="info"
        show-icon
        closable
        style="margin: 0 14px 8px"
        @close="clearQuestion"
      >
        <template #title>正在围绕题目提问：{{ questionTitle || questionId }}</template>
      </el-alert>

      <!-- 聊天消息列表 -->
      <div ref="chatContainer" class="chat-scroll" style="flex: 1; overflow-y: auto; padding: 16px">
        <div v-for="(msg, index) in messages" :key="index" style="margin-bottom: 14px">
          <div v-if="msg.role === 'user'" style="display: flex; justify-content: flex-end">
            <div class="bubble-user">
              {{ msg.content }}
            </div>
          </div>
          <div v-else style="display: flex; justify-content: flex-start; gap: 10px; align-items: flex-start">
            <img :src="xinyuehu" class="bot-avatar" alt="心月狐" />
            <div class="bubble-bot">
              {{ msg.content }}
            </div>
          </div>
        </div>
        <div v-if="loading" style="text-align: center; color: var(--sf-mint)">心月狐正在思考…</div>
      </div>

      <!-- 快捷问题 -->
      <div class="chat-quick">
        <button class="quick-chip" @click="inputMessage = '我好焦虑，做不出来…'; sendMessage()">我好焦虑</button>
        <button class="quick-chip" @click="inputMessage = '给我一点鼓励吧'; sendMessage()">给我鼓励</button>
        <button class="quick-chip" @click="inputMessage = '这道题讲讲思路'; sendMessage()">讲讲思路</button>
      </div>

      <!-- 输入框 -->
      <div class="chat-input-row">
        <el-input
          v-model="inputMessage"
          type="textarea"
          :rows="2"
          placeholder="和心月狐说说…"
          @keyup.enter.ctrl="sendMessage"
        />
        <el-button type="primary" @click="sendMessage" :loading="loading">发送</el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { chat, getSubjects, getSessionMessages } from '../api'
import { ElMessage } from 'element-plus'
import xinyuehu from '../assets/xinyuehu.png'

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

// 聊天窗是悬浮形态，收起即返回工作台
const closeChat = () => {
  router.push('/')
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

<style scoped>
.chat-overlay {
  position: fixed;
  inset: 0;
  background: rgba(10, 12, 16, 0.45);
  z-index: 1500;
}

.chat-window {
  position: fixed;
  right: 26px;
  bottom: 96px;
  width: 380px;
  height: 560px;
  display: flex;
  flex-direction: column;
  z-index: 1600;
  padding: 0;
}

.chat-head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px 10px;
  border-bottom: 1px solid var(--sf-line);
}

.chat-head-text { flex: 1; }

.chat-name {
  font-size: 15px;
  font-weight: 700;
  color: var(--sf-text);
}

.chat-role {
  font-size: 11.5px;
  color: var(--sf-text-muted);
  margin-top: 2px;
}

.chat-online {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 11.5px;
  color: var(--sf-mint);
}

.chat-online i {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--sf-mint);
  box-shadow: 0 0 6px rgba(90, 227, 208, 0.7);
  animation: blink 2.4s ease-in-out infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.chat-close {
  width: 26px;
  height: 26px;
  border-radius: 7px;
  border: 1px solid var(--sf-line);
  background: transparent;
  color: var(--sf-text-muted);
  font-size: 16px;
  cursor: pointer;
  line-height: 1;
}

.chat-close:hover { color: var(--sf-text); border-color: var(--sf-mint-line); }

.chat-select { padding: 10px 14px 0; }

.chat-quick {
  display: flex;
  gap: 8px;
  padding: 10px 14px 0;
}

.quick-chip {
  padding: 5px 12px;
  border-radius: 99px;
  border: 1px solid var(--sf-mint-line);
  background: var(--sf-mint-soft);
  color: var(--sf-mint);
  font-size: 12px;
  cursor: pointer;
  transition: 0.16s;
}

.quick-chip:hover {
  background: rgba(90, 227, 208, 0.24);
  box-shadow: var(--sf-mint-glow);
}

.chat-input-row {
  display: flex;
  gap: 10px;
  align-items: flex-end;
  padding: 10px 14px 14px;
}
</style>
