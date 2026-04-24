<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

const username = ref('')
const password = ref('')
const nickname = ref('')
const error = ref('')
const loading = ref(false)

const handleRegister = async () => {
  if (!username.value || !password.value || !nickname.value) {
    error.value = '请填写所有字段'
    return
  }
  
  loading.value = true
  error.value = ''
  
  try {
    await userStore.register(username.value, password.value, nickname.value)
    // 注册成功后自动登录
    await userStore.login(username.value, password.value)
    router.push('/')
  } catch (e: any) {
    error.value = e.response?.data?.detail || '注册失败'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="register-page">
    <div class="register-card">
      <div class="register-header">
        <h1>注册</h1>
        <p>创建你的账号</p>
      </div>
      
      <form @submit.prevent="handleRegister" class="register-form">
        <div class="form-group">
          <label>用户名</label>
          <input 
            v-model="username" 
            type="text" 
            class="input"
            placeholder="请输入用户名"
          />
        </div>
        
        <div class="form-group">
          <label>昵称</label>
          <input 
            v-model="nickname" 
            type="text" 
            class="input"
            placeholder="请输入昵称"
          />
        </div>
        
        <div class="form-group">
          <label>密码</label>
          <input 
            v-model="password" 
            type="password" 
            class="input"
            placeholder="请输入密码"
          />
        </div>
        
        <div v-if="error" class="error-message">
          {{ error }}
        </div>
        
        <button type="submit" class="btn btn-primary w-full" :disabled="loading">
          {{ loading ? '注册中...' : '注册' }}
        </button>
      </form>
      
      <div class="register-footer">
        <p>已有账号？<router-link to="/login">立即登录</router-link></p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.register-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-primary);
  padding: 20px;
}

.register-card {
  width: 100%;
  max-width: 400px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xl);
  padding: 40px;
  box-shadow: var(--shadow-lg);
  animation: slideUp 0.5s ease-out;
}

.register-header {
  text-align: center;
  margin-bottom: 30px;
}

.register-header h1 {
  font-size: 2rem;
  margin-bottom: 8px;
}

.register-header p {
  color: var(--text-secondary);
}

.register-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-group label {
  font-size: 0.9rem;
  color: var(--text-secondary);
}

.error-message {
  color: var(--danger-color);
  font-size: 0.9rem;
  text-align: center;
  padding: 10px;
  background: rgba(255, 107, 107, 0.1);
  border-radius: var(--radius-md);
}

.register-footer {
  margin-top: 20px;
  text-align: center;
  color: var(--text-secondary);
}
</style>