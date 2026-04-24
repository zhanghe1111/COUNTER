<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

const rooms = ref<any[]>([])
const loading = ref(false)

const fetchRooms = async () => {
  loading.value = true
  try {
    const res = await fetch('/api/rooms')
    rooms.value = await res.json()
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

const goToRoom = (roomCode: string) => {
  router.push(`/room/${roomCode}`)
}

const goToCreateRoom = () => {
  router.push('/create-room')
}

const goToLogin = () => {
  router.push('/login')
}

onMounted(() => {
  fetchRooms()
})
</script>

<template>
  <div class="home">
    <div class="hero">
      <div class="hero-content">
        <h1 class="title">麻将/桌游算分器</h1>
        <p class="subtitle">与朋友一起享受游戏的乐趣</p>
        <div class="hero-buttons">
          <button class="btn btn-primary btn-lg" @click="goToCreateRoom">
            创建房间
          </button>
          <button v-if="!userStore.isLoggedIn" class="btn btn-secondary btn-lg" @click="goToLogin">
            登录
          </button>
        </div>
      </div>
      <div class="hero-bg"></div>
    </div>

    <div class="rooms-section">
      <h2>热门房间</h2>
      <div v-if="loading" class="loading">加载中...</div>
      <div v-else-if="rooms.length === 0" class="empty">
        暂无房间，快来创建一个吧！
      </div>
      <div v-else class="rooms-grid">
        <div
          v-for="room in rooms"
          :key="room.id"
          class="room-card"
          @click="goToRoom(room.room_code)"
        >
          <div class="room-icon">
            {{ room.game_type === 'add_subtract' ? '🎯' : '⭐' }}
          </div>
          <div class="room-info">
            <h3>{{ room.name }}</h3>
            <p>房间码: {{ room.room_code }}</p>
            <p>游戏类型: {{ room.game_type === 'add_subtract' ? '加减分' : '加分' }}</p>
          </div>
          <div class="room-status" :class="room.status">
            {{ room.status === 'open' ? '开放中' : '游戏中' }}
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
}

.hero {
  position: relative;
  height: 60vh;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.hero-bg {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: 
    radial-gradient(ellipse at top, #1a1a2e 0%, transparent 50%),
    radial-gradient(ellipse at bottom right, rgba(233, 69, 96, 0.15) 0%, transparent 50%),
    radial-gradient(ellipse at bottom left, rgba(78, 204, 163, 0.1) 0%, transparent 50%);
  z-index: 0;
}

.hero-content {
  position: relative;
  z-index: 1;
  text-align: center;
  animation: slideUp 0.8s ease-out;
}

.title {
  font-size: 4rem;
  font-weight: 700;
  background: linear-gradient(135deg, #fff 0%, var(--accent-color) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin-bottom: 16px;
}

.subtitle {
  font-size: 1.5rem;
  color: var(--text-secondary);
  margin-bottom: 40px;
}

.hero-buttons {
  display: flex;
  gap: 20px;
  justify-content: center;
}

.btn-lg {
  padding: 16px 40px;
  font-size: 18px;
}

.rooms-section {
  max-width: 1200px;
  margin: 0 auto;
  padding: 40px 20px;
}

.rooms-section h2 {
  text-align: center;
  margin-bottom: 30px;
  font-size: 2rem;
}

.rooms-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}

.room-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 20px;
  cursor: pointer;
  transition: all var(--transition-normal);
  display: flex;
  align-items: center;
  gap: 16px;
}

.room-card:hover {
  transform: translateY(-4px);
  border-color: var(--accent-color);
  box-shadow: var(--shadow-glow);
}

.room-icon {
  font-size: 3rem;
}

.room-info {
  flex: 1;
}

.room-info h3 {
  font-size: 1.25rem;
  margin-bottom: 8px;
}

.room-info p {
  color: var(--text-secondary);
  font-size: 0.9rem;
}

.room-status {
  padding: 4px 12px;
  border-radius: var(--radius-sm);
  font-size: 0.85rem;
}

.room-status.open {
  background: rgba(78, 204, 163, 0.2);
  color: var(--success-color);
}

.room-status.playing {
  background: rgba(233, 69, 96, 0.2);
  color: var(--accent-color);
}

.loading, .empty {
  text-align: center;
  color: var(--text-secondary);
  padding: 40px;
}
</style>