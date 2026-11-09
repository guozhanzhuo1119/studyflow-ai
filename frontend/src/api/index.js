import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000
})

// 请求拦截器：自动带上 token
api.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截器：处理 401
api.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('userId')
      localStorage.removeItem('username')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// 知识点
export const getCategories = () => api.get('/categories')
export const createCategory = (data) => api.post('/categories', data)

// 题目
export const getProblems = (categoryId) => api.get('/problems', { params: { category_id: categoryId } })
export const createProblem = (data) => api.post('/problems', data)
export const updateProblem = (id, data) => api.put(`/problems/${id}`, data)
export const deleteProblem = (id) => api.delete(`/problems/${id}`)
export const searchProblems = (query, topK = 5) => api.post('/problems/search', { query, top_k: topK })

// AI 推荐
export const recommend = (problemId, count = 5) => api.post('/recommend', { problem_id: problemId, count })

// 错因分类
export const getErrorMeta = (topic) => api.get('/errors/meta', { params: { topic } })
export const decideErrorType = (answers, specificBehavior) =>
  api.post('/errors/decide', { answers, specific_behavior: specificBehavior })
export const getErrors = (params = {}) => api.get('/errors', { params })
export const createError = (data) => api.post('/errors', data)
export const updateError = (id, data) => api.put(`/errors/${id}`, data)
export const deleteError = (id) => api.delete(`/errors/${id}`)
export const getErrorStatistics = (practiceMode = true) =>
  api.get('/errors/statistics', { params: { practice_mode: practiceMode } })

// AI 对话
export const chat = (message, sessionId = null) => api.post('/chat', { message, session_id: sessionId })
export const getSessions = () => api.get('/chat/sessions')
export const deleteSession = (sessionId) => api.delete(`/chat/sessions/${sessionId}`)

// 认证
export const register = (data) => api.post('/auth/register', data)
export const login = (data) => api.post('/auth/login', data)
export const getCurrentUser = (token) => api.get('/auth/me', { params: { token } })

export default api
