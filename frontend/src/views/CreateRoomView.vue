<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { Icon } from '@iconify/vue'
import api from '@/utils/api'

const router = useRouter()
const userStore = useUserStore()

onMounted(() => {
  if (!userStore.isLoggedIn) {
    router.push('/login')
  }
})

const form = reactive({
  name: '',
  gameType: 'add_subtract',
  password: ''
})

const error = ref('')
const loading = ref(false)

const handleSubmit = async () => {
  if (!form.name) {
    error.value = '请输入房间名称'
    return
  }

  loading.value = true
  error.value = ''

  try {
    const res = await api.post('/rooms', {
      name: form.name,
      game_type: form.gameType,
      password: form.password
    })

    router.push(`/room/${res.data.room_code}`)
  } catch (e: any) {
    error.value = e.response?.data?.detail || '网络错误，请稍后重试'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="create-room-page">
    <div class="create-room-card">
      <div class="create-room-header">
        <div class="header-icon">
          <Icon icon="mdi:plus-circle" :width="36" />
        </div>
        <h1>创建房间</h1>
        <p>设置游戏规则</p>
      </div>

      <form @submit.prevent="handleSubmit" class="create-room-form">
        <div class="form-group">
          <label>
            <Icon icon="mdi:tag-text" :width="14" />
            房间名称
          </label>
          <input
            v-model="form.name"
            type="text"
            class="input"
            placeholder="请输入房间名称"
          />
        </div>

        <div class="form-group">
          <label>
            <Icon icon="mdi:gamepad-variant" :width="14" />
            游戏类型
          </label>
          <select v-model="form.gameType" class="input">
            <option value="add_subtract">
              🀄 加减分（麻将）
            </option>
            <option value="add_only">
              🎲 加分（桌游）
            </option>
          </select>
        </div>

        <div class="form-group">
          <label>
            <Icon icon="mdi:lock" :width="14" />
            房间密码（可选）
          </label>
          <input
            v-model="form.password"
            type="password"
            class="input"
            placeholder="设置房间密码"
          />
        </div>

        <div v-if="error" class="error-message">
          <Icon icon="mdi:alert-circle" :width="16" />
          {{ error }}
        </div>

        <button type="submit" class="btn btn-primary w-full" :disabled="loading">
          <Icon :icon="loading ? 'mdi:loading' : 'mdi:plus'" :width="18" :class="{ spinning: loading }" />
          {{ loading ? '创建中...' : '创建房间' }}
        </button>
      </form>

      <div class="back-link">
        <router-link to="/">
          <Icon icon="mdi:arrow-left" :width="14" />返回首页
        </router-link>
      </div>
    </div>
  </div>
</template>

<style scoped>
.create-room-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-primary);
  padding: 20px;
}

.create-room-card {
  width: 100%;
  max-width: 500px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xl);
  padding: 36px 28px;
  box-shadow: var(--shadow-lg);
  animation: slideUp 0.4s ease-out;
}

.create-room-header {
  text-align: center;
  margin-bottom: 28px;
}

.header-icon {
  display: flex;
  justify-content: center;
  margin-bottom: 16px;
  color: var(--accent-color);
}

.create-room-header h1 {
  font-size: 1.6rem;
  margin-bottom: 6px;
}

.create-room-header p {
  color: var(--text-secondary);
  font-size: 0.9rem;
}

.create-room-form {
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

.back-link {
  margin-top: 16px;
  text-align: center;
  font-size: 0.85rem;
}

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
