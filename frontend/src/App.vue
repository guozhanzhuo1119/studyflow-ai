<template>
  <el-container style="height: 100vh">
    <el-header v-if="!isQuiz" class="sf-header">
      <div class="sf-brand">
        <span class="sf-brand-dot"></span>
        <span class="sf-brand-name">心流学习</span>
        <span class="sf-brand-sub">AI 学习工作台</span>
      </div>
      <el-menu mode="horizontal" :ellipsis="false" class="sf-menu" router>
        <el-menu-item index="/">题库</el-menu-item>
        <el-menu-item index="/materials">导入的教材</el-menu-item>
        <el-menu-item index="/errors">学习报告</el-menu-item>
        <el-menu-item index="/wrong-book">错题记录</el-menu-item>
      </el-menu>
      <div class="sf-header-right">
        <span v-if="username" class="sf-welcome">欢迎，{{ username }}</span>
        <span class="sf-avatar">{{ (username || '学')[0] }}</span>
        <el-button v-if="username" class="sf-logout" size="small" @click="logout">退出</el-button>
      </div>
    </el-header>
    <el-main class="sf-main" :class="{ 'sf-main-quiz': isQuiz }">
      <router-view />
    </el-main>
    <div v-if="!isQuiz" class="sf-status">
      <span class="sf-status-left"><i class="sf-dot"></i>学习服务已连接</span>
      <span class="sf-status-right">本地进度已同步</span>
    </div>

    <!-- 心月狐悬浮球：点击进入 AI 陪练 -->
    <button v-if="!isQuiz" class="ai-fab" title="问心月狐" @click="router.push('/chat')">
      <img :src="xinyuehu" alt="心月狐" />
    </button>
  </el-container>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import xinyuehu from './assets/xinyuehu.png'

const route = useRoute()
const router = useRouter()
const username = ref(localStorage.getItem('username') || '')
// 做题页是全屏专注模式，隐藏顶栏、状态栏和悬浮球
const isQuiz = computed(() => route.path === '/quiz')

onMounted(() => {
  // 监听 storage 变化
  window.addEventListener('storage', () => {
    username.value = localStorage.getItem('username') || ''
  })
})

const logout = () => {
  localStorage.removeItem('token')
  localStorage.removeItem('userId')
  localStorage.removeItem('username')
  username.value = ''
  router.push('/login')
}
</script>

<style scoped>
.sf-header {
  display: flex;
  align-items: center;
  gap: 18px;
  background: rgba(21, 24, 31, 0.88);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  border-bottom: 1px solid rgba(90, 227, 208, 0.18);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}

.sf-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: none;
}

.sf-brand-dot {
  width: 14px;
  height: 14px;
  border-radius: 4px;
  background: var(--sf-mint);
  box-shadow: 0 0 10px rgba(90, 227, 208, 0.6);
}

.sf-brand-name {
  font-size: 18px;
  font-weight: 700;
  color: var(--sf-text);
  letter-spacing: 1px;
}

.sf-brand-sub {
  font-size: 12px;
  color: var(--sf-text-muted);
  padding-left: 10px;
  border-left: 1px solid var(--sf-line);
}

.sf-menu {
  background: transparent;
  border-bottom: none;
  flex: none;
}

.sf-menu .el-menu-item {
  color: var(--sf-text-dim);
  border-bottom: 2px solid transparent;
  font-size: 14px;
}

.sf-menu .el-menu-item:hover {
  background: rgba(90, 227, 208, 0.08);
  color: var(--sf-mint);
}

.sf-menu .el-menu-item.is-active {
  color: var(--sf-mint);
  border-bottom: 2px solid var(--sf-mint);
  background: transparent;
}

.sf-header-right {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 12px;
}

.sf-welcome {
  color: var(--sf-text-muted);
  font-size: 13px;
}

.sf-avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: var(--sf-mint-soft);
  border: 1px solid var(--sf-mint-line);
  color: var(--sf-mint);
  font-weight: 700;
}

.sf-logout {
  background: transparent;
  border: 1px solid var(--sf-line);
  color: var(--sf-text-muted);
}

.sf-logout:hover {
  border-color: rgba(240, 106, 106, 0.5);
  color: var(--sf-danger);
  background: rgba(240, 106, 106, 0.08);
}

.sf-main {
  padding: 0;
  overflow: hidden;
}

.sf-main-quiz {
  padding: 0;
}

.sf-status {
  flex: none;
  height: 26px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  background: rgba(17, 20, 26, 0.92);
  border-top: 1px solid var(--sf-line);
  font-size: 12px;
  color: var(--sf-text-muted);
}

.sf-status-left {
  display: flex;
  align-items: center;
  gap: 6px;
}

.sf-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--sf-mint);
  box-shadow: 0 0 6px rgba(90, 227, 208, 0.7);
}
</style>
