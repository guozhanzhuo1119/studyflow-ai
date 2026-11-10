import { createRouter, createWebHistory } from 'vue-router'
import Login from '../views/Login.vue'
import SubjectList from '../views/SubjectList.vue'
import ChapterList from '../views/ChapterList.vue'
import KnowledgePointList from '../views/KnowledgePointList.vue'
import ProblemList from '../views/ProblemList.vue'
import VariantList from '../views/VariantList.vue'
import Chat from '../views/Chat.vue'
import ErrorAnalysis from '../views/ErrorAnalysis.vue'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: Login
  },
  {
    path: '/',
    name: 'Subjects',
    component: SubjectList,
    meta: { requiresAuth: true }
  },
  {
    path: '/subjects/:subjectId',
    name: 'Chapters',
    component: ChapterList,
    meta: { requiresAuth: true }
  },
  {
    path: '/chapters/:chapterId',
    name: 'KnowledgePoints',
    component: KnowledgePointList,
    meta: { requiresAuth: true }
  },
  {
    path: '/knowledge-points/:kpId',
    name: 'Problems',
    component: ProblemList,
    meta: { requiresAuth: true }
  },
  {
    path: '/problems/:problemId/variants',
    name: 'Variants',
    component: VariantList,
    meta: { requiresAuth: true }
  },
  {
    path: '/chat',
    name: 'Chat',
    component: Chat,
    meta: { requiresAuth: true }
  },
  {
    path: '/errors',
    name: 'Errors',
    component: ErrorAnalysis,
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
