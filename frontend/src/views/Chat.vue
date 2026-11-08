<template>
  <div style="max-width: 800px; margin: 0 auto">
    <el-card>
      <template #header>
        <div style="display: flex; justify-content: space-between; align-items: center">
          <span style="font-size: 18px; font-weight: bold">AI 学习助手</span>
          <el-button size="small" @click="resetSession">开启新对话</el-button>
        </div>
      </template>

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
import { ref, nextTick } from 'vue'
import { chat } from '../api'
import { ElMessage } from 'element-plus'

const messages = ref([])
const inputMessage = ref('')
const loading = ref(false)
// 会话 id 存本地，刷新页面后还能接着之前的话题聊（历史在后端数据库里）
const sessionId = ref(localStorage.getItem('chatSessionId'))
const chatContainer = ref(null)

const sendMessage = async () => {
  if (!inputMessage.value.trim()) return

  const userMsg = inputMessage.value
  messages.value.push({ role: 'user', content: userMsg })
  inputMessage.value = ''
  loading.value = true

  try {
    const res = await chat(userMsg, sessionId.value)
    messages.value.push({ role: 'assistant', content: res.data.reply })
    sessionId.value = res.data.session_id
    localStorage.setItem('chatSessionId', res.data.session_id)
  } catch (error) {
    ElMessage.error('发送失败')
  } finally {
    loading.value = false
    await nextTick()
    chatContainer.value.scrollTop = chatContainer.value.scrollHeight
  }
}

const resetSession = () => {
  localStorage.removeItem('chatSessionId')
  sessionId.value = null
  messages.value = []
}
</script>
