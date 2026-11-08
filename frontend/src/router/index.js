import { createRouter, createWebHistory } from 'vue-router'
import Login from '../views/Login.vue'
import CategoryList from '../views/CategoryList.vue'
import ProblemList from '../views/ProblemList.vue'
import Chat from '../views/Chat.vue'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: Login
  },
  {
    path: '/',
    name: 'Categories',
    component: CategoryList,
    meta: { requiresAuth: true }
  },
  {
    path: '/categories/:id',
    name: 'Problems',
    component: ProblemList,
    props: true,
    meta: { requiresAuth: true }
  },
  {
    path: '/chat',
    name: 'Chat',
    component: Chat,
    meta: { requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  if (to.meta.requiresAuth && !token) {
    next('/login')
  } else {
    next()
  }
})

export default router
