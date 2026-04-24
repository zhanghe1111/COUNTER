import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'

const api = axios.create({
  baseURL: '/api'
})

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('token') || '')
  const userInfo = ref<any>(null)
  const isLoggedIn = computed(() => !!token.value)

  // 设置token
  const setToken = (newToken: string) => {
    token.value = newToken
    localStorage.setItem('token', newToken)
    api.defaults.headers.common['Authorization'] = `Bearer ${newToken}`
  }

  // 移除token
  const removeToken = () => {
    token.value = ''
    localStorage.removeItem('token')
    delete api.defaults.headers.common['Authorization']
  }

  // 登录
  const login = async (username: string, password: string) => {
    const res = await api.post('/auth/login', { username, password })
    if (res.data.access_token) {
      setToken(res.data.access_token)
      await getUserInfo()
      return true
    }
    return false
  }

  // 注册
  const register = async (username: string, password: string, nickname: string) => {
    const res = await api.post('/auth/register', { username, password, nickname })
    return res.data
  }

  // 获取用户信息
  const getUserInfo = async () => {
    if (!token.value) return
    api.defaults.headers.common['Authorization'] = `Bearer ${token.value}`
    const res = await api.get('/user/profile')
    userInfo.value = res.data
  }

  // 登出
  const logout = () => {
    removeToken()
    userInfo.value = null
  }

  // 初始化
  if (token.value) {
    getUserInfo()
  }

  return {
    token,
    userInfo,
    isLoggedIn,
    setToken,
    removeToken,
    login,
    register,
    getUserInfo,
    logout
  }
})