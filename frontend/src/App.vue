<template>
  <el-container style="height: 100vh">
    <el-header style="background: #409eff; color: white; display: flex; align-items: center; justify-content: space-between">
      <div style="font-size: 20px; font-weight: bold">StudyFlow AI</div>
      <div style="display: flex; align-items: center; gap: 15px">
        <span v-if="username" style="color: white">欢迎，{{ username }}</span>
        <el-button v-if="username" type="danger" size="small" @click="logout">退出登录</el-button>
        <el-menu mode="horizontal" :ellipsis="false" style="background: transparent; border: none" router>
          <el-menu-item index="/">知识点</el-menu-item>
          <el-menu-item index="/chat">AI 助手</el-menu-item>
        </el-menu>
      </div>
    </el-header>
    <el-main>
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const username = ref(localStorage.getItem('username') || '')

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

<style>
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}
</style>
