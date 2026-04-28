<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useToastStore } from '@/stores/toast'
import { Icon } from '@iconify/vue'

const router = useRouter()
const userStore = useUserStore()
const toast = useToastStore()

const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

const handleLogin = async () => {
  if (!username.value) {
    error.value = '请输入用户名'
    return
  }

  if (!password.value) {
    error.value = '请输入密码'
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

  loading.value = true
  error.value = ''

  try {
    const success = await userStore.login(username.value, password.value)
    if (success) {
      toast.success('登录成功')
      const redirectPath = new URLSearchParams(window.location.search).get('redirect')
      router.push(redirectPath || '/')
    } else {
      error.value = '用户名或密码错误'
    }
  } catch (e: any) {
    error.value = e.response?.data?.detail || '登录失败'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-header">
        <div class="login-logo">
          <Icon icon="mdi:scoreboard-outline" :width="36" />
        </div>
        <h1>欢迎回来</h1>
        <p>登录继续游戏</p>
      </div>

      <form @submit.prevent="handleLogin" class="login-form">
        <div class="form-group">
          <label>
            <Icon icon="mdi:account" :width="14" />
            用户名
          </label>
          <input
            v-model="username"
            type="text"
            class="input"
            placeholder="请输入用户名"
            autocomplete="username"
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
            placeholder="请输入密码"
            autocomplete="current-password"
          />
        </div>

        <div v-if="error" class="error-message">
          <Icon icon="mdi:alert-circle" :width="16" />
          {{ error }}
        </div>

        <button type="submit" class="btn btn-primary w-full" :disabled="loading">
          <Icon :icon="loading ? 'mdi:loading' : 'mdi:login'" :width="18" :class="{ spinning: loading }" />
          {{ loading ? '登录中...' : '登录' }}
        </button>
      </form>

      <div class="login-footer">
        <p>还没有账号？<router-link to="/register">立即注册</router-link></p>
        <router-link to="/" class="back-link">
          <Icon icon="mdi:arrow-left" :width="14" />返回首页
        </router-link>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-primary);
  padding: 20px;
}

.login-card {
  width: 100%;
  max-width: 400px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xl);
  padding: 36px 28px;
  box-shadow: var(--shadow-lg);
  animation: slideUp 0.4s ease-out;
}

.login-header {
  text-align: center;
  margin-bottom: 28px;
}

.login-logo {
  display: flex;
  justify-content: center;
  margin-bottom: 16px;
  color: var(--accent-color);
}

.login-header h1 {
  font-size: 1.6rem;
  margin-bottom: 6px;
}

.login-header p {
  color: var(--text-secondary);
  font-size: 0.9rem;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 18px;
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

.login-footer {
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
