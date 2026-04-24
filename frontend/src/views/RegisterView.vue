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
const passwordStrength = ref('')
const passwordStrengthClass = ref('')

// 检查密码强度
const checkPasswordStrength = (pwd: string) => {
  let strength = 0
  
  // 长度检查
  if (pwd.length >= 6) strength += 1
  if (pwd.length >= 8) strength += 1
  
  // 包含数字
  if (/\d/.test(pwd)) strength += 1
  
  // 包含小写字母
  if (/[a-z]/.test(pwd)) strength += 1
  
  // 包含大写字母
  if (/[A-Z]/.test(pwd)) strength += 1
  
  // 包含特殊字符
  if (/[!@#$%^&*(),.?":{}|<>]/.test(pwd)) strength += 1
  
  // 设置强度等级
  if (strength < 3) {
    passwordStrength.value = '弱'
    passwordStrengthClass.value = 'weak'
  } else if (strength < 5) {
    passwordStrength.value = '中'
    passwordStrengthClass.value = 'medium'
  } else {
    passwordStrength.value = '强'
    passwordStrengthClass.value = 'strong'
  }
}

const handleRegister = async () => {
  // 表单验证
  if (!username.value) {
    error.value = '请输入用户名'
    return
  }
  
  if (!password.value) {
    error.value = '请输入密码'
    return
  }
  
  if (!nickname.value) {
    error.value = '请输入昵称'
    return
  }
  
  // 用户名格式验证
  if (username.value.length < 3 || username.value.length > 20) {
    error.value = '用户名长度应在3-20个字符之间'
    return
  }
  
  // 昵称格式验证
  if (nickname.value.length < 2 || nickname.value.length > 20) {
    error.value = '昵称长度应在2-20个字符之间'
    return
  }
  
  // 密码格式验证
  if (password.value.length < 6) {
    error.value = '密码长度至少为6个字符'
    return
  }
  
  // 密码长度上限验证（后端bcrypt限制72字节）
  const passwordBytes = new TextEncoder().encode(password.value)
  if (passwordBytes.length > 72) {
    error.value = `密码长度不能超过72字节（当前：${passwordBytes.length}字节）`
    return
  }
  
  loading.value = true
  error.value = ''
  
  try {
    await userStore.register(username.value, password.value, nickname.value)
    // 注册成功后自动登录
    await userStore.login(username.value, password.value)
    // 检查是否有重定向地址
    const redirectPath = new URLSearchParams(window.location.search).get('redirect')
    router.push(redirectPath || '/')
  } catch (e: any) {
    error.value = e.message || '注册失败'
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
            @input="checkPasswordStrength(password)"
          />
          <div v-if="password" class="password-strength">
            <span class="strength-label">密码强度：</span>
            <span :class="['strength-indicator', passwordStrengthClass]">{{ passwordStrength }}</span>
          </div>
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

.password-strength {
  margin-top: 8px;
  font-size: 0.85rem;
  display: flex;
  align-items: center;
  gap: 8px;
}

.strength-label {
  color: var(--text-secondary);
}

.strength-indicator {
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  font-weight: 500;
}

.strength-indicator.weak {
  background: rgba(255, 107, 107, 0.2);
  color: var(--danger-color);
}

.strength-indicator.medium {
  background: rgba(255, 193, 7, 0.2);
  color: #ffc107;
}

.strength-indicator.strong {
  background: rgba(78, 204, 163, 0.2);
  color: var(--success-color);
}

.register-footer {
  margin-top: 20px;
  text-align: center;
  color: var(--text-secondary);
}
</style>