<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useToastStore } from '@/stores/toast'
import { Icon } from '@iconify/vue'
import api from '@/utils/api'
import SkeletonLoader from '@/components/SkeletonLoader.vue'

const router = useRouter()
const userStore = useUserStore()
const toast = useToastStore()

const rooms = ref<any[]>([])
const loading = ref(true)
let pollTimer: any = null

const searchCode = ref('')
const searching = ref(false)
const foundRoom = ref<any>(null)
const notFound = ref(false)

const fetchRooms = async () => {
  try {
    const res = await api.get('/rooms')
    rooms.value = res.data
  } catch (e: any) {
    console.error(e.message)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchRooms()
  pollTimer = setInterval(fetchRooms, 5000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})

const goToRoom = async (roomCode: string) => {
  try {
    await api.post(`/rooms/${roomCode}/join`, { password: '' })
    toast.success('已加入房间')
    router.push(`/room/${roomCode}`)
  } catch (e: any) {
    if (e.response?.status === 403) {
      const password = window.prompt('请输入房间密码：')
      if (password) {
        try {
          await api.post(`/rooms/${roomCode}/join`, { password })
          toast.success('已加入房间')
          router.push(`/room/${roomCode}`)
        } catch (err: any) {
          toast.error(err.response?.data?.detail || '加入房间失败')
        }
      }
    } else if (e.response?.status === 400 && e.response?.data?.detail === 'You are already in this room') {
      router.push(`/room/${roomCode}`)
    } else {
      toast.error(e.response?.data?.detail || '加入房间失败')
    }
  }
}

const goToCreateRoom = () => {
  if (userStore.isLoggedIn) {
    router.push('/create-room')
  } else {
    toast.info('请先登录')
    router.push('/login')
  }
}

const goToLogin = () => {
  router.push('/login')
}

const searchRoom = async () => {
  const code = searchCode.value.trim()
  if (!code) {
    toast.warning('请输入房间号')
    return
  }
  if (code.length !== 6 || !/^\d{6}$/.test(code)) {
    toast.warning('房间号为6位数字')
    return
  }

  searching.value = true
  foundRoom.value = null
  notFound.value = false

  try {
    const res = await api.get(`/rooms/${code}`)
    foundRoom.value = res.data
  } catch (e: any) {
    if (e.response?.status === 404) {
      notFound.value = true
    } else {
      toast.error(e.response?.data?.detail || '查找失败')
    }
  } finally {
    searching.value = false
  }
}

const clearSearch = () => {
  searchCode.value = ''
  foundRoom.value = null
  notFound.value = false
}

const gameTypeIcon = (type: string) => {
  return type === 'add_subtract' ? 'mdi:swap-vertical-bold' : 'mdi:plus-circle'
}

const gameTypeLabel = (type: string) => {
  return type === 'add_subtract' ? '加减分' : '加分'
}
</script>

<template>
  <div class="home">
    <!-- Compact Header -->
    <header class="home-header">
      <div class="header-brand">
        <Icon icon="mdi:scoreboard-outline" :width="28" class="brand-icon" />
        <h1 class="brand-title">计分工具</h1>
      </div>
      <div class="header-actions">
        <template v-if="userStore.isLoggedIn && userStore.userInfo">
          <span class="user-greeting">{{ userStore.userInfo.nickname }}</span>
          <button class="btn btn-xs btn-ghost" @click="router.push('/profile')">
            <Icon icon="mdi:account-circle" :width="16" />
          </button>
          <button class="btn btn-xs btn-ghost" @click="userStore.logout(); router.push('/')">
            <Icon icon="mdi:logout" :width="16" />
          </button>
        </template>
        <template v-else>
          <button class="btn btn-xs btn-ghost" @click="goToLogin">
            <Icon icon="mdi:login" :width="16" />登录
          </button>
          <button class="btn btn-xs btn-primary" @click="router.push('/register')">
            注册
          </button>
        </template>
      </div>
    </header>

    <!-- Hero Banner (compact) -->
    <div class="hero-banner">
      <div class="hero-bg" />
      <div class="hero-content">
        <div class="hero-text">
          <h2 class="hero-title">与朋友一起玩</h2>
          <p class="hero-subtitle">实时计分，轻松管理</p>
        </div>
        <button class="btn btn-primary btn-create" @click="goToCreateRoom">
          <Icon icon="mdi:plus" :width="20" />
          创建房间
        </button>
      </div>
      <div v-if="!userStore.isLoggedIn" class="hero-login-hint">
        <Icon icon="mdi:information" :width="14" />
        <span>登录后可创建和管理房间</span>
      </div>
    </div>

    <!-- Join Room Section -->
    <div class="room-section">
      <div class="section-header">
        <Icon icon="mdi:login" :width="18" />
        <span>加入房间</span>
      </div>
      <div class="join-card">
        <div class="join-input-row">
          <input
            v-model="searchCode"
            type="text"
            class="input join-input"
            placeholder="输入6位房间号"
            maxlength="6"
            @keyup.enter="searchRoom"
          />
          <button
            class="btn btn-primary btn-join"
            :disabled="searching || searchCode.trim().length !== 6"
            @click="searchRoom"
          >
            <Icon :icon="searching ? 'mdi:loading' : 'mdi:magnify'" :width="18" :class="{ spinning: searching }" />
            查找
          </button>
        </div>

        <!-- Search result -->
        <div v-if="searching" class="join-result">
          <SkeletonLoader type="list" :count="1" />
        </div>

        <div v-else-if="foundRoom" class="join-result">
          <div class="found-card" @click="goToRoom(foundRoom.room_code)">
            <div class="room-icon" :class="foundRoom.game_type">
              <Icon :icon="gameTypeIcon(foundRoom.game_type)" :width="22" />
            </div>
            <div class="room-info">
              <div class="room-name">{{ foundRoom.name }}</div>
              <div class="room-meta">
                <span class="room-code-tag">{{ foundRoom.room_code }}</span>
                <span class="room-type">{{ gameTypeLabel(foundRoom.game_type) }}</span>
              </div>
            </div>
            <div class="room-card-right">
              <span v-if="foundRoom.has_password" class="room-lock">
                <Icon icon="mdi:lock" :width="14" />
              </span>
              <span class="room-status-tag" :class="foundRoom.status">
                {{ foundRoom.status === 'open' ? '开放中' : '游戏中' }}
              </span>
              <Icon icon="mdi:chevron-right" :width="18" class="chevron" />
            </div>
          </div>
        </div>

        <div v-else-if="notFound" class="join-result">
          <div class="not-found">
            <Icon icon="mdi:close-circle-outline" :width="28" />
            <span>未找到该房间，请确认房间号后再试</span>
            <button class="btn btn-xs btn-ghost" @click="clearSearch">重新输入</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Room List -->
    <div class="room-section">
      <div class="section-header">
        <Icon icon="mdi:fire" :width="18" />
        <span>热门房间</span>
      </div>

      <div v-if="loading" class="room-list">
        <SkeletonLoader type="card" :count="3" />
      </div>

      <div v-else-if="rooms.length === 0" class="empty-state">
        <Icon icon="mdi:inbox-outline" :width="40" />
        <span>暂无房间，快来创建一个吧！</span>
      </div>

      <div v-else class="room-list">
        <div
          v-for="room in rooms"
          :key="room.id"
          class="room-card"
          @click="goToRoom(room.room_code)"
        >
          <div class="room-card-left">
            <div class="room-icon" :class="room.game_type">
              <Icon :icon="gameTypeIcon(room.game_type)" :width="22" />
            </div>
            <div class="room-info">
              <div class="room-name">{{ room.name }}</div>
              <div class="room-meta">
                <span class="room-code-tag">{{ room.room_code }}</span>
                <span class="room-type">{{ gameTypeLabel(room.game_type) }}</span>
              </div>
            </div>
          </div>
          <div class="room-card-right">
            <span v-if="room.has_password" class="room-lock">
              <Icon icon="mdi:lock" :width="14" />
            </span>
            <span class="room-status-tag" :class="room.status">
              {{ room.status === 'open' ? '开放中' : '游戏中' }}
            </span>
            <Icon icon="mdi:chevron-right" :width="18" class="chevron" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.home {
  min-height: 100vh;
  background: var(--bg-primary);
  padding-bottom: 20px;
}

/* ====== Header ====== */
.home-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: var(--bg-card);
  border-bottom: 1px solid var(--border-color);
  position: sticky;
  top: 0;
  z-index: 10;
}

.header-brand {
  display: flex;
  align-items: center;
  gap: 8px;
}

.brand-icon {
  color: var(--accent-color);
}

.brand-title {
  font-size: 1.25rem;
  font-weight: 700;
  margin: 0;
  background: linear-gradient(135deg, var(--accent-color) 0%, #1a5cd8 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

.user-greeting {
  font-size: 0.78rem;
  color: var(--text-secondary);
  margin-right: 4px;
}

/* ====== Hero Banner ====== */
.hero-banner {
  position: relative;
  margin: 12px 14px;
  padding: 20px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xl);
  overflow: hidden;
}

.hero-bg {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse at 20% 50%, rgba(43, 110, 240, 0.08) 0%, transparent 50%),
    radial-gradient(ellipse at 80% 50%, rgba(14, 199, 130, 0.06) 0%, transparent 50%);
  z-index: 0;
}

.hero-content {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.hero-text {
  flex: 1;
  min-width: 0;
}

.hero-title {
  font-size: 1.3rem;
  font-weight: 700;
  margin-bottom: 4px;
}

.hero-subtitle {
  font-size: 0.82rem;
  color: var(--text-secondary);
}

.btn-create {
  flex-shrink: 0;
  padding: 10px 20px;
  font-size: 0.85rem;
  min-height: 40px;
}

.hero-login-hint {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  margin-top: 12px;
  font-size: 0.72rem;
  color: var(--text-tertiary);
}

/* ====== Join Room ====== */
.join-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 14px 16px;
}

.join-input-row {
  display: flex;
  gap: 8px;
}

.join-input {
  flex: 1;
  font-size: 1.05rem;
  letter-spacing: 2px;
  text-align: center;
  font-weight: 600;
}

.join-input::placeholder {
  letter-spacing: 0;
  font-weight: 400;
  font-size: 0.85rem;
}

.btn-join {
  flex-shrink: 0;
  padding: 10px 18px;
  font-size: 0.85rem;
  min-height: 44px;
}

.join-result {
  margin-top: 10px;
  animation: slideDown 0.25s ease-out;
}

.found-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.found-card:active {
  transform: scale(0.98);
}

.found-card .room-info {
  flex: 1;
  min-width: 0;
}

.found-card .room-name {
  font-size: 0.9rem;
  font-weight: 600;
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.found-card .room-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.72rem;
}

.found-card .room-icon {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.found-card .room-icon.add_subtract {
  background: rgba(43, 110, 240, 0.1);
  color: var(--accent-color);
}

.found-card .room-icon.add_only {
  background: rgba(78, 204, 163, 0.15);
  color: var(--success-color);
}

.found-card .room-code-tag {
  color: var(--info-color);
  background: rgba(0, 217, 255, 0.1);
  padding: 1px 6px;
  border-radius: 4px;
}

.found-card .room-type {
  color: var(--text-tertiary);
}

.found-card .room-card-right {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.found-card .room-lock {
  display: flex;
  align-items: center;
  color: var(--text-tertiary);
  opacity: 0.6;
}

.not-found {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 20px;
  color: var(--text-tertiary);
  font-size: 0.85rem;
  text-align: center;
}

/* ====== Room Section ====== */
.room-section {
  padding: 0 14px;
  margin-top: 14px;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.9rem;
  font-weight: 600;
  margin-bottom: 10px;
  color: var(--text-primary);
}

.room-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.room-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all var(--transition-normal);
}

.room-card:hover {
  border-color: rgba(43, 110, 240, 0.25);
  transform: translateY(-1px);
}

.room-card:active {
  transform: scale(0.98);
}

.room-card-left {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
  flex: 1;
}

.room-icon {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.room-icon.add_subtract {
  background: rgba(43, 110, 240, 0.1);
  color: var(--accent-color);
}

.room-icon.add_only {
  background: rgba(78, 204, 163, 0.15);
  color: var(--success-color);
}

.room-info {
  min-width: 0;
  flex: 1;
}

.room-name {
  font-size: 0.9rem;
  font-weight: 600;
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.room-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.72rem;
}

.room-code-tag {
  color: var(--accent-color);
  background: rgba(43, 110, 240, 0.1);
  padding: 1px 6px;
  border-radius: 4px;
  font-weight: 600;
  letter-spacing: 1px;
}

.room-type {
  color: var(--text-tertiary);
}

.room-card-right {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.room-status-tag {
  font-size: 0.7rem;
  padding: 2px 8px;
  border-radius: 8px;
  font-weight: 500;
}

.room-status-tag.open {
  background: rgba(78, 204, 163, 0.15);
  color: var(--success-color);
}

.room-status-tag.playing {
  background: rgba(43, 110, 240, 0.1);
  color: var(--accent-color);
}

.room-lock {
  display: flex;
  align-items: center;
  color: var(--text-tertiary);
  opacity: 0.6;
}

.chevron {
  color: var(--text-tertiary);
}

/* ====== Empty State ====== */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  color: var(--text-tertiary);
  padding: 40px 20px;
  font-size: 0.85rem;
}

/* ====== Spinning ====== */
.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Mobile optimization */
@media (max-width: 480px) {
  .hero-content {
    flex-direction: column;
    text-align: center;
  }

  .btn-create {
    width: 100%;
  }
}
</style>
