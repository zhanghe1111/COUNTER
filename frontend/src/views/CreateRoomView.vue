<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import api from '@/utils/api'

const router = useRouter()
const userStore = useUserStore()

// 页面加载时检查登录状态
onMounted(() => {
  if (!userStore.isLoggedIn) {
    router.push('/login')
  }
})

const form = reactive({
  name: '',
  gameType: 'add_subtract',
  baseScore: 0,
  eliminationScore: null as number | null,
  winningScore: null as number | null,
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
      base_score: form.baseScore,
      elimination_score: form.eliminationScore,
      winning_score: form.winningScore,
      password: form.password
    })
    
    router.push(`/room/${res.data.room_code}`)
  } catch (e: any) {
    error.value = e.message || '网络错误，请稍后重试'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="create-room-page">
    <div class="create-room-card">
      <div class="create-room-header">
        <h1>创建房间</h1>
        <p>设置游戏规则</p>
      </div>
      
      <form @submit.prevent="handleSubmit" class="create-room-form">
        <div class="form-group">
          <label>房间名称</label>
          <input 
            v-model="form.name" 
            type="text" 
            class="input"
            placeholder="请输入房间名称"
          />
        </div>
        
        <div class="form-group">
          <label>游戏类型</label>
          <select v-model="form.gameType" class="input">
            <option value="add_subtract">加减分（麻将）</option>
            <option value="add_only">加分（桌游）</option>
          </select>
        </div>
        
        <div class="form-group">
          <label>基础分数</label>
          <input 
            v-model.number="form.baseScore" 
            type="number" 
            class="input"
            placeholder="默认为0"
          />
        </div>
        
        <div class="form-group">
          <label>淘汰分数</label>
          <input 
            v-model.number="form.eliminationScore" 
            type="number" 
            class="input"
            placeholder="不设置为无下限"
          />
        </div>
        
        <div class="form-group">
          <label>胜利分数</label>
          <input 
            v-model.number="form.winningScore" 
            type="number" 
            class="input"
            placeholder="不设置为无上限"
          />
        </div>
        
        <div class="form-group">
          <label>房间密码（可选）</label>
          <input 
            v-model="form.password" 
            type="password" 
            class="input"
            placeholder="设置房间密码"
          />
        </div>
        
        <div v-if="error" class="error-message">
          {{ error }}
        </div>
        
        <button type="submit" class="btn btn-primary w-full" :disabled="loading">
          {{ loading ? '创建中...' : '创建房间' }}
        </button>
      </form>
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
  padding: 40px;
  box-shadow: var(--shadow-lg);
  animation: slideUp 0.5s ease-out;
}

.create-room-header {
  text-align: center;
  margin-bottom: 30px;
}

.create-room-header h1 {
  font-size: 2rem;
  margin-bottom: 8px;
}

.create-room-header p {
  color: var(--text-secondary);
}

.create-room-form {
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
</style>