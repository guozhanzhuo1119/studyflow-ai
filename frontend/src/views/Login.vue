<template>
  <div style="display: flex; justify-content: center; align-items: center; height: 100vh; background: #f5f5f5">
    <el-card style="width: 400px">
      <template #header>
        <h2 style="text-align: center; margin: 0">{{ isLogin ? '登录' : '注册' }}</h2>
      </template>

      <el-form :model="form" label-width="80px">
        <el-form-item label="用户名">
          <el-input v-model="form.username" placeholder="请输入用户名" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" placeholder="请输入密码" show-password />
        </el-form-item>
        <el-form-item v-if="!isLogin" label="邮箱">
          <el-input v-model="form.email" placeholder="请输入邮箱（可选）" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" style="width: 100%" @click="submit" :loading="loading">
            {{ isLogin ? '登录' : '注册' }}
          </el-button>
        </el-form-item>
        <div style="text-align: center">
          <el-link type="primary" @click="isLogin = !isLogin">
            {{ isLogin ? '没有账号？去注册' : '已有账号？去登录' }}
          </el-link>
        </div>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { login, register } from '../api'
import { ElMessage } from 'element-plus'

const router = useRouter()
const isLogin = ref(true)
const loading = ref(false)
const form = ref({
  username: '',
  password: '',
  email: ''
})

const submit = async () => {
  if (!form.value.username || !form.value.password) {
    ElMessage.warning('请填写用户名和密码')
    return
  }

  loading.value = true
  try {
    let res
    if (isLogin.value) {
      res = await login(form.value)
    } else {
      res = await register(form.value)
    }

    // 保存 token
    localStorage.setItem('token', res.data.access_token)
    localStorage.setItem('userId', res.data.user_id)
    localStorage.setItem('username', res.data.username)

    ElMessage.success(isLogin.value ? '登录成功' : '注册成功')
    router.push('/')
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '操作失败')
  } finally {
    loading.value = false
  }
}
</script>
