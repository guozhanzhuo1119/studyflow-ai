import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'
import router from './router'
import App from './App.vue'
import './style.css'

// 启用 Element Plus 暗色主题（柔和深空灰 + 薄荷青，详见 style.css）
document.documentElement.classList.add('dark')

// 开发辅助：支持 ?__token__=xxx 注入登录态（仅本地调试用）
const __t = new URLSearchParams(location.search).get('__token__')
if (__t) {
  localStorage.setItem('token', __t)
  history.replaceState({}, '', location.pathname)
}

const app = createApp(App)
app.use(ElementPlus)
app.use(router)
app.mount('#app')
