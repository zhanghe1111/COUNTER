import axios from 'axios'

const api = axios.create({
  baseURL: '/api'
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  response => response,
  error => {
    if (!error.response) {
      return Promise.reject(new Error('网络连接失败，请检查网络或联系管理员'))
    }

    return Promise.reject(error)
  }
)

export default api
