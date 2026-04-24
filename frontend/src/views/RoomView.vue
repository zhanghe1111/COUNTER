<script setup lang="ts">
import { ref, reactive, onMounted, computed, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  DatasetComponent,
  TransformComponent,
  DataZoomComponent
} from 'echarts/components'
import { LabelLayout, UniversalTransition } from 'echarts/features'
import { CanvasRenderer } from 'echarts/renderers'

use([
  LineChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  DatasetComponent,
  TransformComponent,
  DataZoomComponent,
  LabelLayout,
  UniversalTransition,
  CanvasRenderer
])

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const roomCode = route.params.roomCode as string
const roomInfo = ref<any>(null)
const players = ref<any[]>([])
const scores = ref<any[]>([])
const chartData = ref<any>(null)
const loading = ref(false)
const error = ref('')

const confirmationStatus = ref<any>(null)
const isCurrentPlayerConfirmed = ref(false)

const scoreForm = reactive({
  score: 0,
  round: 1,
  selectedPlayers: [] as number[]
})

const selectedRoundForChart = ref<number | null>(null)

const ws = ref<WebSocket | null>(null)
const currentPlayer = computed(() => {
  return players.value.find(p => p.user_id === userStore.userInfo?.id)
})

const currentRound = computed(() => {
  return roomInfo.value?.current_round || 1
})

const playerRanking = computed(() => {
  return [...players.value].sort((a, b) => b.current_score - a.current_score)
})

const activePlayers = computed(() => {
  return players.value.filter(p => p.status === 'active')
})

const allActivePlayersConfirmed = computed(() => {
  return confirmationStatus.value?.all_confirmed || false
})

const isRoomCreator = computed(() => {
  return roomInfo.value?.created_by === userStore.userInfo?.id
})

const loadRoomInfo = async () => {
  loading.value = true
  try {
    const roomRes = await fetch(`/api/rooms/${roomCode}`)
    if (roomRes.ok) {
      roomInfo.value = await roomRes.json()
      selectedRoundForChart.value = roomInfo.value.current_round
    } else {
      throw new Error('房间不存在')
    }

    const playersRes = await fetch(`/api/players/room/${roomInfo.value.id}`)
    if (playersRes.ok) {
      players.value = await playersRes.json()
    }

    const scoresRes = await fetch(`/api/scores/room/${roomInfo.value.id}`)
    if (scoresRes.ok) {
      scores.value = await scoresRes.json()
    }

    await loadConfirmationStatus()

    await loadChartData(selectedRoundForChart.value)

    initWebSocket()
  } catch (e: any) {
    error.value = e.message || '加载失败'
  } finally {
    loading.value = false
  }
}

const loadConfirmationStatus = async () => {
  if (!roomInfo.value) return
  try {
    const res = await fetch(`/api/confirmations/room/${roomInfo.value.id}/status`)
    if (res.ok) {
      confirmationStatus.value = await res.json()
      updateCurrentPlayerConfirmation()
    }
  } catch (e) {
    console.error('Failed to load confirmation status', e)
  }
}

const updateCurrentPlayerConfirmation = () => {
  if (!currentPlayer.value || !confirmationStatus.value) {
    isCurrentPlayerConfirmed.value = false
    return
  }
  const playerStatus = confirmationStatus.value.players.find(
    (p: any) => p.player_id === currentPlayer.value?.id
  )
  isCurrentPlayerConfirmed.value = playerStatus?.is_confirmed || false
}

const loadChartData = async (round: number | null) => {
  if (!roomInfo.value) return
  try {
    let url = `/api/charts/room/${roomInfo.value.id}`
    if (round !== null) {
      url = `/api/charts/room/${roomInfo.value.id}/round/${round}`
    }
    const res = await fetch(url)
    if (res.ok) {
      chartData.value = await res.json()
    }
  } catch (e) {
    console.error('Failed to load chart data', e)
  }
}

const initWebSocket = () => {
  if (!roomInfo.value || !userStore.userInfo) return

  const player = players.value.find(p => p.user_id === userStore.userInfo.id)
  if (!player) return

  const wsUrl = `ws://localhost:8000/api/ws/${roomInfo.value.id}/${player.id}`
  ws.value = new WebSocket(wsUrl)

  ws.value.onopen = () => {
    console.log('WebSocket连接成功')
  }

  ws.value.onmessage = (event) => {
    const message = JSON.parse(event.data)
    console.log('收到消息:', message)

    if (message.type === 'player_joined' || message.type === 'player_left') {
      loadRoomInfo()
    } else if (message.type === 'score_update' || message.type === 'status_update') {
      loadRoomInfo()
    } else if (message.type === 'confirmation_update') {
      loadConfirmationStatus()
      if (message.round_advanced) {
        roomInfo.value.current_round = message.new_round
        selectedRoundForChart.value = message.new_round
        loadChartData(selectedRoundForChart.value)
      }
    } else if (message.type === 'round_advanced') {
      roomInfo.value.current_round = message.new_round
      selectedRoundForChart.value = message.new_round
      loadChartData(selectedRoundForChart.value)
      loadConfirmationStatus()
    }
  }

  ws.value.onclose = () => {
    console.log('WebSocket连接关闭')
  }
}

const submitScore = async () => {
  if (!roomInfo.value) return

  const playerId = players.value.find(p => p.user_id === userStore.userInfo?.id)?.id
  if (!playerId) return

  try {
    const scoreData: any = {
      room_id: roomInfo.value.id,
      player_id: playerId,
      round: currentRound.value,
      score: scoreForm.score,
      details: {
        type: roomInfo.value.game_type
      }
    }

    if (roomInfo.value.game_type === 'add_subtract') {
      scoreData.details.targets = scoreForm.selectedPlayers
    }

    const res = await fetch('/api/scores', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${userStore.token}`
      },
      body: JSON.stringify(scoreData)
    })

    if (res.ok) {
      await loadRoomInfo()
      scoreForm.score = 0
      scoreForm.selectedPlayers = []
      if (ws.value && ws.value.readyState === WebSocket.OPEN) {
        ws.value.send(JSON.stringify({
          type: 'score_update',
          score: scoreForm.score,
          round: currentRound.value
        }))
      }
    } else {
      const data = await res.json()
      error.value = data.detail || '提交失败'
    }
  } catch (e) {
    error.value = '网络错误'
  }
}

const submitConfirmation = async (confirmed: boolean) => {
  if (!roomInfo.value) return

  try {
    const res = await fetch(`/api/confirmations/room/${roomInfo.value.id}/confirm`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${userStore.token}`
      },
      body: JSON.stringify({ confirmed })
    })

    if (res.ok) {
      const data = await res.json()
      isCurrentPlayerConfirmed.value = confirmed
      await loadConfirmationStatus()

      if (ws.value && ws.value.readyState === WebSocket.OPEN) {
        ws.value.send(JSON.stringify({
          type: 'confirmation_update',
          is_confirmed: confirmed,
          all_confirmed: data.all_confirmed,
          can_advance_round: data.can_advance_round
        }))
      }
    } else {
      const data = await res.json()
      error.value = data.detail || '确认失败'
    }
  } catch (e) {
    error.value = '网络错误'
  }
}

const advanceToNextRound = async () => {
  if (!roomInfo.value) return

  try {
    const res = await fetch(`/api/confirmations/room/${roomInfo.value.id}/next-round`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${userStore.token}`
      }
    })

    if (res.ok) {
      const data = await res.json()
      roomInfo.value.current_round = data.new_round
      selectedRoundForChart.value = data.new_round
      await loadChartData(selectedRoundForChart.value)
      await loadConfirmationStatus()

      if (ws.value && ws.value.readyState === WebSocket.OPEN) {
        ws.value.send(JSON.stringify({
          type: 'round_advanced',
          new_round: data.new_round
        }))
      }
    } else {
      const data = await res.json()
      error.value = data.detail || '进入下一轮失败'
    }
  } catch (e) {
    error.value = '网络错误'
  }
}

const leaveRoom = async () => {
  if (!roomInfo.value) return

  try {
    const res = await fetch(`/api/rooms/${roomCode}/leave`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${userStore.token}`
      }
    })

    if (res.ok) {
      router.push('/')
    }
  } catch (e) {
    error.value = '离开失败'
  }
}

const onRoundChange = async () => {
  await loadChartData(selectedRoundForChart.value)
}

const chartOption = computed(() => {
  if (!chartData.value) return {}

  return {
    title: {
      text: selectedRoundForChart.value
        ? `第 ${selectedRoundForChart.value} 轮分数曲线`
        : '分数变化曲线',
      textStyle: {
        color: '#fff'
      }
    },
    tooltip: {
      trigger: 'axis'
    },
    legend: {
      data: chartData.value.players?.map((p: any) => p.name) || [],
      textStyle: {
        color: '#fff'
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '15%',
      containLabel: true
    },
    dataZoom: [
      {
        type: 'inside',
        start: 0,
        end: 100
      },
      {
        type: 'slider',
        start: 0,
        end: 100,
        textStyle: {
          color: '#fff'
        }
      }
    ],
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: chartData.value.rounds || [],
      axisLabel: {
        color: '#fff'
      },
      axisLine: {
        lineStyle: {
          color: '#4a5568'
        }
      }
    },
    yAxis: {
      type: 'value',
      axisLabel: {
        color: '#fff'
      },
      axisLine: {
        lineStyle: {
          color: '#4a5568'
        }
      },
      splitLine: {
        lineStyle: {
          color: '#2d3748'
        }
      }
    },
    series: (chartData.value.players || []).map((player: any, index: number) => {
      const colors = ['#e94560', '#4ecca3', '#00d9ff', '#ffc107', '#ff6b6b']
      return {
        name: player.name,
        type: 'line',
        areaStyle: {
          opacity: 0.2
        },
        emphasis: {
          focus: 'series'
        },
        lineStyle: {
          width: 3
        },
        itemStyle: {
          color: colors[index % colors.length]
        },
        data: player.scores || player.score_changes || []
      }
    })
  }
})

onMounted(() => {
  if (!userStore.isLoggedIn) {
    router.push('/login')
    return
  }
  loadRoomInfo()
})

onUnmounted(() => {
  if (ws.value) {
    ws.value.close()
  }
})
</script>

<template>
  <div class="room-page">
    <div v-if="loading" class="loading">加载中...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else-if="roomInfo" class="room-content">
      <div class="room-header">
        <div class="room-info">
          <h1>{{ roomInfo.name }}</h1>
          <div class="room-details">
            <span class="room-code">房间码: {{ roomInfo.room_code }}</span>
            <span class="game-type" :class="roomInfo.game_type">
              {{ roomInfo.game_type === 'add_subtract' ? '加减分' : '加分' }}
            </span>
            <span class="round">当前轮次: {{ currentRound }}</span>
            <span v-if="roomInfo.base_score !== 0" class="base-score">
              基础分: {{ roomInfo.base_score }}
            </span>
          </div>
        </div>
        <button class="btn btn-secondary" @click="leaveRoom">
          离开房间
        </button>
      </div>

      <div class="room-main">
        <div class="left-section">
          <div class="players-section">
            <h2>玩家列表</h2>
            <div class="players-list">
              <div
                v-for="player in players"
                :key="player.id"
                class="player-item"
                :class="[player.status, { confirmed: confirmationStatus?.players?.find((p: any) => p.player_id === player.id)?.is_confirmed }]"
              >
                <div class="player-info">
                  <div class="player-nickname">
                    {{ player.nickname }}
                    <span v-if="player.id === currentPlayer?.id" class="you-tag">(你)</span>
                    <span v-if="roomInfo.created_by === player.user_id" class="host-tag">房主</span>
                  </div>
                  <div class="player-status">
                    <span :class="player.status">
                      {{ player.status === 'active' ? '活跃' : player.status === 'eliminated' ? '淘汰' : '胜利' }}
                    </span>
                    <span v-if="confirmationStatus?.players?.find((p: any) => p.player_id === player.id)?.is_confirmed" class="confirmed-tag">
                      ✓ 已确认
                    </span>
                  </div>
                </div>
                <div class="player-score">{{ player.current_score }}</div>
              </div>
            </div>
          </div>

          <div class="score-input-section">
            <h2>分数输入 - 第 {{ currentRound }} 轮</h2>
            <div class="score-form">
              <div class="form-group">
                <label>{{ roomInfo.game_type === 'add_subtract' ? '分数（赢家获得）' : '分数' }}</label>
                <input
                  v-model.number="scoreForm.score"
                  type="number"
                  class="input"
                  placeholder="输入分数"
                />
              </div>

              <div v-if="roomInfo.game_type === 'add_subtract'" class="form-group">
                <label>选择输家（每个输家都需要交出相同分数）</label>
                <div class="checkbox-group">
                  <label v-for="player in activePlayers" :key="player.id" class="checkbox-item">
                    <input
                      type="checkbox"
                      :value="player.id"
                      v-model="scoreForm.selectedPlayers"
                    />
                    {{ player.nickname }}
                  </label>
                </div>
                <p class="helper-text" v-if="scoreForm.selectedPlayers.length > 0 && scoreForm.score > 0">
                  每个输家将扣除 {{ scoreForm.score }} 分
                </p>
              </div>

              <button class="btn btn-primary w-full" @click="submitScore">
                提交分数
              </button>
            </div>
          </div>

          <div class="confirmation-section">
            <h2>确认状态</h2>
            <div class="confirmation-info">
              <div class="confirmation-status">
                <span v-if="allActivePlayersConfirmed" class="all-confirmed">
                  所有活跃玩家已确认
                </span>
                <span v-else class="waiting-confirm">
                  等待确认... ({{ activePlayers.filter(p => confirmationStatus?.players?.find((cp: any) => cp.player_id === p.id)?.is_confirmed).length }}/{{ activePlayers.length }})
                </span>
              </div>
              <div class="confirmation-buttons">
                <button
                  v-if="!isCurrentPlayerConfirmed && currentPlayer?.status === 'active'"
                  class="btn btn-success"
                  @click="submitConfirmation(true)"
                >
                  确认本轮
                </button>
                <button
                  v-if="isCurrentPlayerConfirmed"
                  class="btn btn-warning"
                  @click="submitConfirmation(false)"
                >
                  取消确认
                </button>
                <button
                  v-if="allActivePlayersConfirmed && isRoomCreator"
                  class="btn btn-primary btn-lg"
                  @click="advanceToNextRound"
                >
                  进入下一轮
                </button>
              </div>
            </div>
          </div>
        </div>

        <div class="right-section">
          <div class="ranking-section">
            <h2>排行榜</h2>
            <div class="ranking-list">
              <div
                v-for="(player, index) in playerRanking"
                :key="player.id"
                class="ranking-item"
                :class="player.status"
              >
                <div class="rank">{{ index + 1 }}</div>
                <div class="player-info">
                  <div class="player-nickname">{{ player.nickname }}</div>
                  <div class="player-status">
                    <span :class="player.status">
                      {{ player.status === 'active' ? '活跃' : player.status === 'eliminated' ? '淘汰' : '胜利' }}
                    </span>
                  </div>
                </div>
                <div class="player-score">{{ player.current_score }}</div>
              </div>
            </div>
          </div>

          <div class="chart-section">
            <h2>分数曲线</h2>
            <div class="round-selector">
              <label>选择轮次:</label>
              <select v-model="selectedRoundForChart" @change="onRoundChange" class="input">
                <option :value="null">全部轮次</option>
                <option v-for="r in roomInfo.current_round" :key="r" :value="r">
                  第 {{ r }} 轮
                </option>
              </select>
            </div>
            <div class="chart-container">
              <v-chart
                class="chart"
                :option="chartOption"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.room-page {
  min-height: 100vh;
  background: var(--bg-primary);
  padding: 20px;
}

.loading, .error {
  min-height: 80vh;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
  font-size: 1.2rem;
}

.room-content {
  max-width: 1400px;
  margin: 0 auto;
  animation: slideUp 0.5s ease-out;
}

.room-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: var(--shadow-md);
}

.room-info h1 {
  font-size: 1.8rem;
  margin-bottom: 10px;
}

.room-details {
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
}

.room-code, .game-type, .round, .base-score {
  padding: 4px 12px;
  border-radius: var(--radius-sm);
  font-size: 0.9rem;
}

.room-code {
  background: rgba(0, 217, 255, 0.2);
  color: var(--info-color);
}

.game-type.add_subtract {
  background: rgba(233, 69, 96, 0.2);
  color: var(--accent-color);
}

.game-type.add_only {
  background: rgba(78, 204, 163, 0.2);
  color: var(--success-color);
}

.round {
  background: rgba(255, 193, 7, 0.2);
  color: var(--warning-color);
}

.base-score {
  background: rgba(78, 204, 163, 0.2);
  color: var(--success-color);
}

.room-main {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.left-section, .right-section {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.players-section, .score-input-section, .ranking-section, .chart-section, .confirmation-section {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 20px;
  box-shadow: var(--shadow-md);
}

.players-section h2, .score-input-section h2, .ranking-section h2, .chart-section h2, .confirmation-section h2 {
  font-size: 1.2rem;
  margin-bottom: 15px;
  color: var(--text-primary);
}

.players-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 300px;
  overflow-y: auto;
}

.player-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  transition: all var(--transition-normal);
  border-left: 4px solid var(--success-color);
}

.player-item:hover {
  border-color: var(--accent-color);
  transform: translateY(-2px);
}

.player-item.active {
  border-left-color: var(--success-color);
}

.player-item.eliminated {
  opacity: 0.6;
  border-left-color: var(--danger-color);
}

.player-item.won {
  border-left-color: var(--warning-color);
  background: rgba(255, 193, 7, 0.1);
}

.player-item.confirmed {
  background: rgba(78, 204, 163, 0.1);
  border-color: var(--success-color);
}

.player-info {
  flex: 1;
}

.player-nickname {
  font-weight: 500;
  margin-bottom: 4px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.you-tag {
  font-size: 0.75rem;
  background: var(--accent-color);
  color: white;
  padding: 2px 6px;
  border-radius: 4px;
}

.host-tag {
  font-size: 0.75rem;
  background: var(--warning-color);
  color: white;
  padding: 2px 6px;
  border-radius: 4px;
}

.player-status {
  font-size: 0.8rem;
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  gap: 8px;
}

.player-status .active {
  color: var(--success-color);
}

.player-status .eliminated {
  color: var(--danger-color);
}

.player-status .won {
  color: var(--warning-color);
}

.confirmed-tag {
  color: var(--success-color);
  font-weight: 600;
}

.player-score {
  font-size: 1.2rem;
  font-weight: 600;
  color: var(--text-primary);
}

.score-form {
  display: flex;
  flex-direction: column;
  gap: 15px;
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

.helper-text {
  font-size: 0.8rem;
  color: var(--text-secondary);
  font-style: italic;
}

.checkbox-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.checkbox-item {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.checkbox-item input[type="checkbox"] {
  width: 16px;
  height: 16px;
  accent-color: var(--accent-color);
}

.ranking-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 300px;
  overflow-y: auto;
}

.ranking-item {
  display: flex;
  align-items: center;
  padding: 12px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
}

.ranking-item.eliminated {
  opacity: 0.6;
}

.ranking-item.won {
  background: rgba(255, 193, 7, 0.1);
}

.rank {
  width: 30px;
  font-size: 1.2rem;
  font-weight: 700;
  color: var(--accent-color);
  text-align: center;
  margin-right: 15px;
}

.ranking-item .player-info {
  flex: 1;
}

.round-selector {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 15px;
}

.round-selector label {
  font-size: 0.9rem;
  color: var(--text-secondary);
}

.round-selector select {
  flex: 1;
  max-width: 200px;
}

.chart-container {
  height: 350px;
  width: 100%;
}

.chart {
  width: 100%;
  height: 100%;
}

.confirmation-section {
  background: var(--bg-card);
}

.confirmation-info {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.confirmation-status {
  font-size: 1rem;
}

.all-confirmed {
  color: var(--success-color);
  font-weight: 600;
}

.waiting-confirm {
  color: var(--warning-color);
}

.confirmation-buttons {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.btn-lg {
  padding: 12px 30px;
  font-size: 1rem;
}

.btn-success {
  background: var(--success-color);
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-normal);
}

.btn-success:hover {
  background: #3da87d;
  transform: translateY(-2px);
}

.btn-warning {
  background: var(--warning-color);
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-normal);
}

.btn-warning:hover {
  background: #d39e00;
  transform: translateY(-2px);
}

@media (max-width: 768px) {
  .room-main {
    grid-template-columns: 1fr;
  }

  .room-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }

  .room-details {
    gap: 10px;
  }
}
</style>