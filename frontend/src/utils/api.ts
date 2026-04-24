import axios from 'axios'
import { useUserStore } from '@/stores/user'

const api = axios.create({
  baseURL: '/api'
})

// 请求拦截器：自动附加 Token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截器：统一处理错误
api.interceptors.response.use(
  response => response,
  error => {
    if (!error.response) {
      return Promise.reject(new Error('网络连接失败，请检查网络或联系管理员'))
    }
    
    // 401 处理，如果非登录相关接口报错 401，则自动跳转登录或清除状态
    if (error.response.status === 401) {
      const userStore = useUserStore()
      userStore.removeToken()
      // 可以选择跳转到登录页： window.location.href = '/login'
    }

    if (error.response.data && error.response.data.detail) {
      return Promise.reject(new Error(error.response.data.detail))
    }
    
    return Promise.reject(new Error(`请求失败 (${error.response.status})`))
  }
)

export default api
