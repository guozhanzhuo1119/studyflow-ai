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

// 科目
export const getSubjects = () => api.get('/subjects')
export const getSubject = (id) => api.get(`/subjects/${id}`)
export const createSubject = (data) => api.post('/subjects', data)
export const updateSubject = (id, data) => api.put(`/subjects/${id}`, data)
export const deleteSubject = (id) => api.delete(`/subjects/${id}`)

// 章节
export const getChapters = (subjectId) => api.get('/chapters', { params: { subject_id: subjectId } })
export const getChapter = (id) => api.get(`/chapters/${id}`)
export const createChapter = (data) => api.post('/chapters', data)
export const updateChapter = (id, data) => api.put(`/chapters/${id}`, data)
export const deleteChapter = (id) => api.delete(`/chapters/${id}`)

// 知识点
export const getKnowledgePoints = (chapterId) =>
  api.get('/knowledge-points', { params: { chapter_id: chapterId } })
export const getKnowledgePoint = (id) => api.get(`/knowledge-points/${id}`)
export const createKnowledgePoint = (data) => api.post('/knowledge-points', data)
export const updateKnowledgePoint = (id, data) => api.put(`/knowledge-points/${id}`, data)
export const deleteKnowledgePoint = (id) => api.delete(`/knowledge-points/${id}`)

// 题目（母题）
export const getProblems = (knowledgePointId) =>
  api.get('/problems', { params: { knowledge_point_id: knowledgePointId } })
export const getProblem = (id) => api.get(`/problems/${id}`)
export const createProblem = (data) => api.post('/problems', data)
export const updateProblem = (id, data) => api.put(`/problems/${id}`, data)
export const deleteProblem = (id) => api.delete(`/problems/${id}`)
export const searchProblems = (query, topK = 5) => api.post('/problems/search', { query, top_k: topK })
export const importProblems = (knowledgePointId, items) =>
  api.post('/problems/import', { knowledge_point_id: knowledgePointId, items })

// 变题
export const getVariants = (problemId) => api.get('/variants', { params: { problem_id: problemId } })
export const createVariant = (data) => api.post('/variants', data)
export const saveVariantsFromRecommendation = (problemId, recommendations) =>
  api.post('/variants/from-recommendation', { problem_id: problemId, recommendations })
export const updateVariant = (id, data) => api.put(`/variants/${id}`, data)
export const deleteVariant = (id) => api.delete(`/variants/${id}`)

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
