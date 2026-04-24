<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import api from '@/utils/api'

const router = useRouter()
const userStore = useUserStore()

const nickname = ref(userStore.userInfo?.nickname || '')
const loading = ref(false)
const error = ref('')

const updateProfile = async () => {
  if (!nickname.value) {
    error.value = '请输入昵称'
    return
  }
  
  loading.value = true
  error.value = ''
  
  try {
    await api.put('/user/profile', { nickname: nickname.value })
    await userStore.getUserInfo()
    error.value = '更新成功'
  } catch (e: any) {
    error.value = e.message || '网络错误'
  } finally {
    loading.value = false
  }
}

const logout = () => {
  userStore.logout()
  router.push('/login')
}
</script>

<template>
  <div class="profile-page">
    <div class="profile-card">
      <div class="profile-header">
        <h1>个人中心</h1>
      </div>
      
      <div class="profile-content">
        <div class="user-info">
          <h2>用户信息</h2>
          <div class="info-item">
            <label>用户名</label>
            <div class="info-value">{{ userStore.userInfo?.username }}</div>
          </div>
          <div class="info-item">
            <label>昵称</label>
            <input 
              v-model="nickname" 
              type="text" 
              class="input"
            />
          </div>
          <div class="info-item">
            <label>注册时间</label>
            <div class="info-value">{{ userStore.userInfo?.created_at }}</div>
          </div>
          
          <div v-if="error" class="error-message" :class="{ 'success': error === '更新成功' }">
            {{ error }}
          </div>
          
          <div class="profile-actions">
            <button class="btn btn-primary" @click="updateProfile" :disabled="loading">
              {{ loading ? '更新中...' : '更新信息' }}
            </button>
            <button class="btn btn-secondary" @click="logout">
              退出登录
            </button>
          </div>
        </div>
        
        <div class="history-section">
          <h2>游戏历史</h2>
          <div class="empty-history">
            暂无游戏历史记录
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.profile-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-primary);
  padding: 20px;
}

.profile-card {
  width: 100%;
  max-width: 600px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xl);
  padding: 40px;
  box-shadow: var(--shadow-lg);
  animation: slideUp 0.5s ease-out;
}

.profile-header {
  text-align: center;
  margin-bottom: 30px;
}

.profile-header h1 {
  font-size: 2rem;
  margin-bottom: 8px;
}

.profile-content {
  display: flex;
  flex-direction: column;
  gap: 30px;
}

.user-info h2, .history-section h2 {
  font-size: 1.2rem;
  margin-bottom: 20px;
  color: var(--text-primary);
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 15px;
}

.info-item label {
  font-size: 0.9rem;
  color: var(--text-secondary);
}

.info-value {
  padding: 12px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  color: var(--text-primary);
}

.error-message {
  color: var(--danger-color);
  font-size: 0.9rem;
  text-align: center;
  padding: 10px;
  background: rgba(255, 107, 107, 0.1);
  border-radius: var(--radius-md);
  margin-bottom: 20px;
}

.error-message.success {
  color: var(--success-color);
  background: rgba(78, 204, 163, 0.1);
}

.profile-actions {
  display: flex;
  gap: 15px;
}

.history-section {
  margin-top: 20px;
}

.empty-history {
  text-align: center;
  color: var(--text-secondary);
  padding: 40px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
}

@media (max-width: 768px) {
  .profile-card {
    padding: 20px;
  }
  
  .profile-actions {
    flex-direction: column;
  }
}
</style>