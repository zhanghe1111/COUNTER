<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useToastStore } from '@/stores/toast'
import { Icon } from '@iconify/vue'
import api from '@/utils/api'
import SkeletonLoader from '@/components/SkeletonLoader.vue'

const router = useRouter()
const userStore = useUserStore()
const toast = useToastStore()

const nickname = ref(userStore.userInfo?.nickname || '')
const loading = ref(false)
const error = ref('')

const history = ref<any[]>([])
const historyLoading = ref(true)

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
    toast.success('昵称已更新')
    error.value = ''
  } catch (e: any) {
    error.value = e.response?.data?.detail || '网络错误'
  } finally {
    loading.value = false
  }
}

const handleLogout = () => {
  userStore.logout()
  toast.info('已退出登录')
  router.push('/login')
}

const fetchHistory = async () => {
  historyLoading.value = true
  try {
    const res = await api.get('/user/history')
    history.value = res.data
  } catch (e: any) {
    toast.error('获取历史记录失败')
    console.error('获取历史记录失败', e)
  } finally {
    historyLoading.value = false
  }
}

const statusLabel = (status: string) => {
  switch (status) {
    case 'open': return '等待中'
    case 'playing': return '游戏中'
    case 'finished': return '已结束'
    default: return status
  }
}

const statusClass = (status: string) => {
  switch (status) {
    case 'open': return 'tag-info'
    case 'playing': return 'tag-danger'
    case 'finished': return 'tag-success'
    default: return ''
  }
}

const gameTypeIcon = (type: string) => {
  return type === 'add_subtract' ? 'mdi:swap-vertical-bold' : 'mdi:plus-circle'
}

const goToRoom = (roomCode: string) => {
  router.push(`/room/${roomCode}`)
}

onMounted(() => {
  fetchHistory()
})
</script>

<template>
  <div class="profile-page">
    <div class="profile-card">
      <div class="profile-header">
        <button class="btn btn-ghost" @click="router.push('/')">
          <Icon icon="mdi:arrow-left" :width="18" />返回
        </button>
        <div class="header-center">
          <div class="avatar-circle">
            <Icon icon="mdi:account" :width="32" />
          </div>
          <h1>{{ userStore.userInfo?.nickname }}</h1>
          <p class="username">@{{ userStore.userInfo?.username }}</p>
        </div>
      </div>

      <div class="profile-content">
        <div class="info-section">
          <div class="info-item">
            <label>
              <Icon icon="mdi:badge-account" :width="14" />
              昵称
            </label>
            <input
              v-model="nickname"
              type="text"
              class="input"
            />
          </div>
          <div class="info-item">
            <label>
              <Icon icon="mdi:calendar" :width="14" />
              注册时间
            </label>
            <div class="info-value">{{ userStore.userInfo?.created_at }}</div>
          </div>
        </div>

        <div v-if="error" class="error-message" :class="{ 'success': error === '更新成功' }">
          <Icon :icon="error === '更新成功' ? 'mdi:check-circle' : 'mdi:alert-circle'" :width="16" />
          {{ error }}
        </div>

        <div class="profile-actions">
          <button class="btn btn-primary w-full" @click="updateProfile" :disabled="loading">
            <Icon :icon="loading ? 'mdi:loading' : 'mdi:content-save'" :width="18" :class="{ spinning: loading }" />
            {{ loading ? '更新中...' : '保存修改' }}
          </button>
          <button class="btn btn-ghost w-full" @click="handleLogout">
            <Icon icon="mdi:logout" :width="18" />退出登录
          </button>
        </div>

        <div class="history-section">
          <h3>
            <Icon icon="mdi:history" :width="16" />
            游戏历史
            <span v-if="history.length > 0" class="history-count">{{ history.length }}</span>
          </h3>

          <div v-if="historyLoading" class="skeleton-wrap">
            <SkeletonLoader type="list" :count="3" />
          </div>

          <div v-else-if="history.length === 0" class="empty-history">
            <Icon icon="mdi:inbox-outline" :width="28" />
            <span>暂无游戏历史记录</span>
          </div>

          <div v-else class="history-list">
            <div
              v-for="item in history"
              :key="item.room_id"
              class="history-item"
              @click="goToRoom(item.room_code)"
            >
              <div class="history-icon" :class="item.game_type">
                <Icon :icon="gameTypeIcon(item.game_type)" :width="18" />
              </div>
              <div class="history-body">
                <div class="history-name">{{ item.room_name }}</div>
                <div class="history-meta">
                  <span class="tag" :class="statusClass(item.status)">{{ statusLabel(item.status) }}</span>
                  <span class="history-score" :class="{ 'score-pos': (item.current_score || 0) > 0, 'score-neg': (item.current_score || 0) < 0 }">
                    {{ (item.current_score || 0) > 0 ? '+' : '' }}{{ item.current_score || 0 }}
                  </span>
                  <span class="history-rounds">{{ item.round_count }} 轮</span>
                </div>
              </div>
              <Icon icon="mdi:chevron-right" :width="16" class="history-chevron" />
            </div>
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
  align-items: flex-start;
  justify-content: center;
  background: var(--bg-primary);
  padding: 20px;
  padding-top: 40px;
}

.profile-card {
  width: 100%;
  max-width: 500px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xl);
  padding: 28px;
  box-shadow: var(--shadow-lg);
  animation: slideUp 0.4s ease-out;
}

.profile-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 28px;
  position: relative;
}

.profile-header .btn-ghost {
  position: absolute;
  left: 0;
  top: 0;
  padding: 8px 12px;
  font-size: 0.85rem;
  min-height: 36px;
}

.header-center {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.avatar-circle {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: rgba(43, 110, 240, 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--accent-color);
  margin-bottom: 4px;
}

.header-center h1 {
  font-size: 1.3rem;
}

.username {
  font-size: 0.85rem;
  color: var(--text-secondary);
}

.profile-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.info-section {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.info-item label {
  font-size: 0.82rem;
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  gap: 4px;
}

.info-value {
  padding: 12px 16px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  color: var(--text-primary);
  font-size: 0.9rem;
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

.error-message.success {
  color: var(--success-color);
  background: rgba(78, 204, 163, 0.1);
}

.profile-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* ====== History Section ====== */
.history-section {
  padding-top: 16px;
  border-top: 1px solid var(--border-color);
}

.history-section h3 {
  font-size: 0.9rem;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.history-count {
  font-size: 0.65rem;
  padding: 0 7px;
  border-radius: 8px;
  background: rgba(43, 110, 240, 0.1);
  color: var(--accent-color);
  font-weight: 500;
}

.skeleton-wrap {
  padding: 4px 0;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.history-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.history-item:active {
  transform: scale(0.98);
}

.history-icon {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.history-icon.add_subtract {
  background: rgba(240, 72, 72, 0.1);
  color: var(--danger-color);
}

.history-icon.add_only {
  background: rgba(14, 199, 130, 0.1);
  color: var(--success-color);
}

.history-body {
  flex: 1;
  min-width: 0;
}

.history-name {
  font-size: 0.82rem;
  font-weight: 600;
  margin-bottom: 3px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.history-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.7rem;
}

.history-score {
  font-weight: 700;
}

.score-pos {
  color: var(--success-color);
}

.score-neg {
  color: var(--danger-color);
}

.history-rounds {
  color: var(--text-tertiary);
}

.history-chevron {
  color: var(--text-tertiary);
  flex-shrink: 0;
}

.empty-history {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  color: var(--text-tertiary);
  padding: 30px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  font-size: 0.85rem;
}

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

@media (max-width: 768px) {
  .profile-page {
    padding: 12px;
    padding-top: 24px;
  }

  .profile-card {
    padding: 20px;
  }
}
</style>
