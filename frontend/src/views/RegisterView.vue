<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useToastStore } from '@/stores/toast'
import { Icon } from '@iconify/vue'

const router = useRouter()
const userStore = useUserStore()
const toast = useToastStore()

const username = ref('')
const password = ref('')
const confirmPassword = ref('')
const nickname = ref('')
const error = ref('')
const loading = ref(false)

const passwordStrength = computed(() => {
  const pwd = password.value
  if (!pwd) return { level: 0, label: '', color: '' }
  let strength = 0
  if (pwd.length >= 8) strength++
  if (/[A-Z]/.test(pwd)) strength++
  if (/[a-z]/.test(pwd)) strength++
  if (/[0-9]/.test(pwd)) strength++
  if (/[^A-Za-z0-9]/.test(pwd)) strength++
  if (pwd.length >= 12) strength++

  if (strength <= 1) return { level: 1, label: '弱', color: 'var(--accent-color)' }
  if (strength <= 3) return { level: 2, label: '中', color: 'var(--warning-color)' }
  return { level: 3, label: '强', color: 'var(--success-color)' }
})

const handleRegister = async () => {
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
  if (username.value.length < 3 || username.value.length > 20) {
    error.value = '用户名长度应在3-20个字符之间'
    return
  }
  if (password.value.length < 6) {
    error.value = '密码长度至少为6个字符'
    return
  }
  if (password.value !== confirmPassword.value) {
    error.value = '两次密码输入不一致'
    return
  }

  loading.value = true
  error.value = ''

  try {
    await userStore.register(username.value, password.value, nickname.value)
    toast.success('注册成功，欢迎！')
    router.push('/')
  } catch (e: any) {
    error.value = e.response?.data?.detail || e.message || '注册失败'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="register-page">
    <div class="register-card">
      <div class="register-header">
        <div class="register-logo">
          <Icon icon="mdi:account-plus" :width="36" />
        </div>
        <h1>创建账号</h1>
        <p>加入游戏社区</p>
      </div>

      <form @submit.prevent="handleRegister" class="register-form">
        <div class="form-group">
          <label>
            <Icon icon="mdi:account" :width="14" />
            用户名
          </label>
          <input
            v-model="username"
            type="text"
            class="input"
            placeholder="3-20个字符"
            autocomplete="username"
          />
        </div>

        <div class="form-group">
          <label>
            <Icon icon="mdi:badge-account" :width="14" />
            昵称
          </label>
          <input
            v-model="nickname"
            type="text"
            class="input"
            placeholder="显示在游戏中的名称"
          />
        </div>

        <div class="form-group">
          <label>
            <Icon icon="mdi:lock" :width="14" />
            密码
          </label>
          <input
            v-model="password"
            type="password"
            class="input"
            placeholder="至少6个字符"
            autocomplete="new-password"
          />
          <div v-if="password" class="password-strength">
            <div class="strength-bar">
              <div
                class="strength-fill"
                :style="{ width: (passwordStrength.level / 3) * 100 + '%', background: passwordStrength.color }"
              />
            </div>
            <span class="strength-label" :style="{ color: passwordStrength.color }">
              {{ passwordStrength.label }}
            </span>
          </div>
        </div>

        <div class="form-group">
          <label>
            <Icon icon="mdi:lock-check" :width="14" />
            确认密码
          </label>
          <input
            v-model="confirmPassword"
            type="password"
            class="input"
            placeholder="再次输入密码"
            autocomplete="new-password"
          />
        </div>

        <div v-if="error" class="error-message">
          <Icon icon="mdi:alert-circle" :width="16" />
          {{ error }}
        </div>

        <button type="submit" class="btn btn-primary w-full" :disabled="loading">
          <Icon :icon="loading ? 'mdi:loading' : 'mdi:account-plus'" :width="18" :class="{ spinning: loading }" />
          {{ loading ? '注册中...' : '注册' }}
        </button>
      </form>

      <div class="register-footer">
        <p>已有账号？<router-link to="/login">立即登录</router-link></p>
        <router-link to="/" class="back-link">
          <Icon icon="mdi:arrow-left" :width="14" />返回首页
        </router-link>
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
  max-width: 420px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xl);
  padding: 36px 28px;
  box-shadow: var(--shadow-lg);
  animation: slideUp 0.4s ease-out;
}

.register-header {
  text-align: center;
  margin-bottom: 28px;
}

.register-logo {
  display: flex;
  justify-content: center;
  margin-bottom: 16px;
  color: var(--accent-color);
}

.register-header h1 {
  font-size: 1.6rem;
  margin-bottom: 6px;
}

.register-header p {
  color: var(--text-secondary);
  font-size: 0.9rem;
}

.register-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group label {
  font-size: 0.82rem;
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  gap: 4px;
}

.password-strength {
  display: flex;
  align-items: center;
  gap: 8px;
}

.strength-bar {
  flex: 1;
  height: 4px;
  background: var(--border-color);
  border-radius: 2px;
  overflow: hidden;
}

.strength-fill {
  height: 100%;
  border-radius: 2px;
  transition: all var(--transition-normal);
}

.strength-label {
  font-size: 0.72rem;
  font-weight: 600;
  min-width: 20px;
  text-align: right;
}

.error-message {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--danger-color);
  font-size: 0.82rem;
  padding: 10px;
  background: rgba(255, 107, 107, 0.1);
  border-radius: var(--radius-md);
}

.register-footer {
  margin-top: 20px;
  text-align: center;
  color: var(--text-secondary);
  font-size: 0.85rem;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.back-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 0.8rem;
}

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
