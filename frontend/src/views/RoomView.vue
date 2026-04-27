<script setup lang="ts">
import { ref, reactive, onMounted, computed, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import api from '@/utils/api'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const roomCode = route.params.roomCode as string
const roomInfo = ref<any>(null)
const players = ref<any[]>([])
const scores = ref<any[]>([])
const loading = ref(false)
const error = ref('')

const confirmationStatus = ref<any>(null)
const isCurrentPlayerConfirmed = ref(false)

const scoreForm = reactive({
  score: 0,
  round: 1,
  selectedPlayers: [] as number[]
})

const ws = ref<WebSocket | null>(null)

const events = ref<any[]>([])

const filteredEvents = computed(() => {
  if (isPlayingState.value) {
    return events.value.filter(e => e.type !== 'player_joined' && e.type !== 'player_left')
  }
  return events.value
})
const pendingNotifications = ref<any[]>([])

const isPendingScoreEvent = (event: any) => {
  if (event.type !== 'score_collected') return false
  const current = currentPlayer.value
  if (!current) return false
  const batchId = event.content.batch_id
  return pendingNotifications.value.some(n => n.batch_id === batch_id && n.target_player_id === current.id)
}

const roomStatus = ref<any>(null)
const isWaitingState = computed(() => roomInfo.value?.status === 'open')
const isPlayingState = computed(() => roomInfo.value?.status === 'playing')
const allPlayersReady = computed(() => {
  const activeP = players.value.filter(p => p.status === 'active')
  return activeP.length >= 2 && activeP.every(p => p.is_ready)
})
const endGameVotes = ref<any[]>([])
const isEndGameProposed = computed(() => endGameVotes.value.length > 0)
const hasCurrentVotedEnd = computed(() => {
  if (!currentPlayer.value) return false
  return endGameVotes.value.some(v => v.player_id === currentPlayer.value?.id && v.is_approved)
})
const allApprovedEnd = computed(() => {
  if (!isEndGameProposed.value) return false
  return endGameVotes.value.every(v => v.is_approved)
})
const leaveRequests = ref<any[]>([])
const currentLeaveRequest = computed(() => {
  if (!currentPlayer.value) return null
  return leaveRequests.value.find(lr => lr.player_id === currentPlayer.value?.id)
})

const fetchRoomStatus = async () => {
  if (!roomInfo.value) return
  try {
    const res = await api.get(`/rooms/${roomCode}/status`)
    roomStatus.value = res.data
    for (const sp of res.data.players) {
      const localP = players.value.find(p => p.id === sp.id)
      if (localP) localP.is_ready = sp.is_ready
    }
    if (res.data.end_game_proposal?.is_active) {
      endGameVotes.value = res.data.end_game_proposal.votes
    } else {
      endGameVotes.value = []
    }
    leaveRequests.value = res.data.leave_requests || []
  } catch (e) {
    console.error('Failed to fetch room status', e)
  }
}

const toggleReady = async () => {
  try {
    await api.post(`/rooms/${roomCode}/ready`)
  } catch (e: any) {
    error.value = e.response?.data?.detail || '操作失败'
  }
}

const startGame = async () => {
  try {
    await api.post(`/rooms/${roomCode}/start`)
  } catch (e: any) {
    error.value = e.response?.data?.detail || '开始失败'
  }
}

const proposeEndGame = async () => {
  try {
    await api.post(`/rooms/${roomCode}/propose-end`)
  } catch (e: any) {
    error.value = e.response?.data?.detail || '操作失败'
  }
}

const voteEndGame = async () => {
  try {
    const res = await api.post(`/rooms/${roomCode}/vote-end`)
    if (res.data.game_reset) {
      await refreshRoomData()
    }
  } catch (e: any) {
    error.value = e.response?.data?.detail || '操作失败'
  }
}

const requestLeaveRoom = async () => {
  try {
    await api.post(`/rooms/${roomCode}/request-leave`)
  } catch (e: any) {
    error.value = e.response?.data?.detail || '操作失败'
  }
}

const approveLeave = async (requestId: number) => {
  try {
    await api.post(`/rooms/${roomCode}/approve-leave/${requestId}`)
    await refreshRoomData()
  } catch (e: any) {
    error.value = e.response?.data?.detail || '操作失败'
  }
}

const rejectLeave = async (requestId: number) => {
  try {
    await api.post(`/rooms/${roomCode}/reject-leave/${requestId}`)
    leaveRequests.value = leaveRequests.value.filter(lr => lr.id !== requestId)
  } catch (e: any) {
    error.value = e.response?.data?.detail || '操作失败'
  }
}

const fetchEvents = async () => {
  if (!roomInfo.value) return
  try {
    const res = await api.get(`/events/room/${roomInfo.value.id}?limit=100`)
    events.value = res.data
  } catch (e) {
    console.error('Failed to fetch events', e)
  }
}

const fetchPendingNotifications = async () => {
  if (!roomInfo.value || !currentPlayer.value) return
  try {
    const res = await api.get(`/pending-scores/room/${roomInfo.value.id}/player/${currentPlayer.value.id}`)
    pendingNotifications.value = res.data
  } catch (e) {
    console.error('Failed to fetch pending notifications', e)
  }
}

const acceptPendingScore = async (pendingId: number) => {
  try {
    await api.post(`/pending-scores/${pendingId}/accept`)
    pendingNotifications.value = pendingNotifications.value.filter(n => n.id !== pendingId)
  } catch (e: any) {
    console.error('Failed to accept pending score', e)
  }
}

const rejectPendingScore = async (pendingId: number) => {
  try {
    await api.post(`/pending-scores/${pendingId}/reject`)
    await refreshRoomData()
    pendingNotifications.value = pendingNotifications.value.filter(n => n.id !== pendingId)
  } catch (e: any) {
    console.error('Failed to reject pending score', e)
  }
}

const getEventText = (event: any) => {
  const c = event.content
  switch (event.type) {
    case 'player_joined':
      return `${c.player_nickname} 进入了房间`
    case 'player_left':
      return `${c.player_nickname} 离开了房间`
    case 'score_collected':
      const targetNames = c.targets?.map((t: any) => t.nickname).join('、') || ''
      return `${c.source_nickname} 向 ${targetNames} 收取了 ${c.score} 分`
    case 'score_accepted':
      return `${c.target_nickname} 确认了 ${c.source_nickname} 收取的 ${c.score} 分`
    case 'score_rejected':
      const rejectedTargets = c.targets?.map((t: any) => t.nickname).join('、') || ''
      return `${c.rejector_nickname} 拒绝了 ${c.source_nickname} 收取的 ${c.score} 分（影响: ${rejectedTargets}），分数已撤销`
    case 'round_confirmed':
      return `${c.player_nickname} 确认了第 ${c.round} 轮`
    case 'round_advanced':
      return `游戏进入第 ${c.new_round} 轮`
    case 'game_started':
      return `游戏开始了！`
    case 'game_reset':
      return `游戏已重置`
    case 'end_proposed':
      return `${c.player_nickname} 提议结束游戏`
    case 'end_voted':
      return `${c.player_nickname} 投票结束游戏`
    case 'leave_requested':
      return `${c.player_nickname} 请求退出`
    case 'leave_approved':
      return `${c.player_nickname} 的退出请求已批准`
    case 'leave_rejected':
      return `${c.player_nickname} 的退出请求被拒绝`
    default:
      return JSON.stringify(c)
  }
}

const getEventClass = (type: string) => {
  switch (type) {
    case 'player_joined': return 'event-join'
    case 'player_left': return 'event-leave'
    case 'score_collected': return 'event-score'
    case 'score_accepted': return 'event-accept'
    case 'score_rejected': return 'event-reject'
    case 'round_confirmed': return 'event-confirm'
    case 'round_advanced': return 'event-advance'
    case 'game_started': return 'event-start'
    case 'game_reset': return 'event-reset'
    case 'end_proposed': return 'event-end-propose'
    case 'end_voted': return 'event-end-vote'
    case 'leave_requested': return 'event-leave-request'
    case 'leave_approved': return 'event-leave-approve'
    case 'leave_rejected': return 'event-leave-reject'
    default: return ''
  }
}

const currentPlayer = computed(() => {
  return players.value.find(p => p.user_id === userStore.userInfo?.id)
})

const currentRound = computed(() => {
  return roomInfo.value?.current_round || 1
})

const activePlayers = computed(() => {
  return players.value.filter(p => p.status === 'active' && p.id !== currentPlayer.value?.id)
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
    const roomRes = await api.get(`/rooms/${roomCode}`)
    roomInfo.value = roomRes.data

    const playersRes = await api.get(`/players/room/${roomInfo.value.id}`)
    players.value = playersRes.data

    const scoresRes = await api.get(`/scores/room/${roomInfo.value.id}`)
    scores.value = scoresRes.data

    await loadConfirmationStatus()

    await fetchEvents()
    await fetchPendingNotifications()
    await fetchRoomStatus()
  } catch (e: any) {
    error.value = e.message || '加载失败'
  } finally {
    loading.value = false
  }
}

const refreshRoomData = async () => {
  if (!roomInfo.value) return
  error.value = ''
  try {
    const roomRes = await api.get(`/rooms/${roomCode}`)
    roomInfo.value = roomRes.data

    const playersRes = await api.get(`/players/room/${roomInfo.value.id}`)
    players.value = playersRes.data

    const scoresRes = await api.get(`/scores/room/${roomInfo.value.id}`)
    scores.value = scoresRes.data

    await loadConfirmationStatus()
    await fetchEvents()
    await fetchPendingNotifications()
    await fetchRoomStatus()
  } catch (e: any) {
    console.error('刷新数据失败', e)
  }
}

const loadConfirmationStatus = async () => {
  if (!roomInfo.value) return
  try {
    const res = await api.get(`/confirmations/room/${roomInfo.value.id}/status`)
    confirmationStatus.value = res.data
    updateCurrentPlayerConfirmation()
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

let reconnectTimer: any = null;
let reconnectCount = 0;
const MAX_RECONNECT = 5;

const initWebSocket = () => {
  if (!roomInfo.value || !userStore.userInfo) return

  const player = players.value.find(p => p.user_id === userStore.userInfo?.id)
  if (!player) return

  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  // 生产环境可能没有 8000 端口，这里做简单的环境区分
  const wsHost = window.location.hostname === 'localhost' ? 'localhost:8000' : window.location.host;
  const wsUrl = `${wsProtocol}//${wsHost}/api/ws/${roomInfo.value.id}/${player.id}`
  
  ws.value = new WebSocket(wsUrl)

  ws.value.onopen = () => {
    console.log('WebSocket连接成功')
    reconnectCount = 0; // 重置重连次数
  }

  ws.value.onmessage = (event) => {
    const message = JSON.parse(event.data)
    console.log('收到消息:', message)

    if (message.type === 'room_event') {
      error.value = ''
      if (message.event_type === 'score_rejected') {
        refreshRoomData()
      } else if (message.event_type === 'score_accepted') {
        fetchPendingNotifications()
      } else if (['ready_update', 'player_joined', 'player_left', 'game_reset'].includes(message.event_type)) {
        refreshRoomData()
      } else if (message.event_type === 'game_started') {
        refreshRoomData()
      } else if (message.event_type === 'end_proposed') {
        fetchRoomStatus()
      } else if (message.event_type === 'end_voted') {
        fetchRoomStatus()
      } else if (message.event_type === 'leave_requested') {
        fetchRoomStatus()
      } else if (message.event_type === 'leave_approved') {
        refreshRoomData()
      } else if (message.event_type === 'leave_rejected') {
        fetchRoomStatus()
      } else {
        refreshRoomData()
      }
    } else if (message.type === 'confirmation_update') {
      loadConfirmationStatus()
      if (message.round_advanced) {
        roomInfo.value.current_round = message.new_round
        loadConfirmationStatus()
      }
    } else if (message.type === 'round_advanced') {
      roomInfo.value.current_round = message.new_round
      loadConfirmationStatus()
    }
  }

  ws.value.onclose = () => {
    console.log('WebSocket连接关闭')
    if (reconnectCount < MAX_RECONNECT) {
      reconnectCount++
      console.log(`尝试重新连接... (${reconnectCount}/${MAX_RECONNECT})`)
      reconnectTimer = setTimeout(() => {
        initWebSocket()
      }, 3000)
    } else {
      error.value = '实时连接已断开，请刷新页面重试'
    }
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

    await api.post('/scores', scoreData)

    await refreshRoomData()
    scoreForm.score = 0
    scoreForm.selectedPlayers = []
  } catch (e: any) {
    error.value = e.message || '网络错误'
  }
}

const togglePlayer = (playerId: number) => {
  const idx = scoreForm.selectedPlayers.indexOf(playerId)
  if (idx === -1) {
    scoreForm.selectedPlayers.push(playerId)
  } else {
    scoreForm.selectedPlayers.splice(idx, 1)
  }
}

const submitConfirmation = async (confirmed: boolean) => {
  if (!roomInfo.value) return

  try {
    const res = await api.post(`/confirmations/room/${roomInfo.value.id}/confirm`, { confirmed })
    
    const data = res.data
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
  } catch (e: any) {
    error.value = e.message || '网络错误'
  }
}

const advanceToNextRound = async () => {
  if (!roomInfo.value) return

  try {
    const res = await api.post(`/confirmations/room/${roomInfo.value.id}/next-round`)
    
    const data = res.data
    roomInfo.value.current_round = data.new_round
    await loadConfirmationStatus()

    if (ws.value && ws.value.readyState === WebSocket.OPEN) {
      ws.value.send(JSON.stringify({
        type: 'round_advanced',
        new_round: data.new_round
      }))
    }
  } catch (e: any) {
    error.value = e.message || '网络错误'
  }
}

const leaveRoom = async () => {
  if (!roomInfo.value) return

  try {
    await api.delete(`/rooms/${roomCode}/leave`)
    router.push('/')
  } catch (e: any) {
    error.value = e.message || '离开失败'
  }
}

onMounted(async () => {
  if (!userStore.isLoggedIn) {
    router.push('/login')
    return
  }
  await loadRoomInfo()
  initWebSocket()
})

onUnmounted(() => {
  if (reconnectTimer) clearTimeout(reconnectTimer)
  if (ws.value) {
    ws.value.onclose = null // 防止触发重连
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
            <span class="round" :class="{ playing: isPlayingState }">
              {{ isWaitingState ? '等待开始' : `第 ${currentRound} 轮` }}
            </span>
            <span class="room-status-tag" :class="roomInfo.status">
              {{ isPlayingState ? '游戏中' : '等待中' }}
            </span>
            <span v-if="roomInfo.base_score !== 0" class="base-score">
              基础分: {{ roomInfo.base_score }}
            </span>
          </div>
        </div>
        <div class="room-actions">
          <button v-if="!isPlayingState" class="btn btn-secondary" @click="leaveRoom">
            离开房间
          </button>
          <button v-else class="btn btn-secondary" @click="requestLeaveRoom" :disabled="!!currentLeaveRequest">
            {{ currentLeaveRequest ? '已申请退出' : '申请退出' }}
          </button>
        </div>
      </div>

      <div class="room-main">
        <div class="left-section">
          <div v-if="isWaitingState" class="score-input-section">
            <h2>游戏准备</h2>
            <div class="ready-actions">
              <button
                class="btn btn-primary w-full"
                :class="{ ready: currentPlayer?.is_ready }"
                @click="toggleReady"
              >
                {{ currentPlayer?.is_ready ? '✓ 已准备' : '点击准备' }}
              </button>
              <button
                v-if="isRoomCreator"
                class="btn btn-success w-full btn-lg"
                :disabled="!allPlayersReady"
                @click="startGame"
              >
                开始游戏{{ allPlayersReady ? '' : ' (等待所有人准备)' }}
              </button>
            </div>
          </div>

          <div v-if="isPlayingState" class="score-input-section">
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
                <label>选择输家（点击选择，再次点击取消，每个输家扣除相同分数）</label>
                <div class="target-buttons">
                  <button
                    v-for="player in activePlayers"
                    :key="player.id"
                    class="target-btn"
                    :class="{ selected: scoreForm.selectedPlayers.includes(player.id) }"
                    @click="togglePlayer(player.id)"
                  >
                    {{ player.nickname }}
                    <span class="target-score" v-if="scoreForm.score > 0 && scoreForm.selectedPlayers.includes(player.id)">
                      -{{ scoreForm.score }}
                    </span>
                  </button>
                </div>
                <p class="helper-text" v-if="scoreForm.selectedPlayers.length > 0 && scoreForm.score > 0">
                  已选 {{ scoreForm.selectedPlayers.length }} 人，每个输家将扣除 {{ scoreForm.score }} 分，你将获得 {{ scoreForm.score * scoreForm.selectedPlayers.length }} 分
                </p>
              </div>

              <button class="btn btn-primary w-full" @click="submitScore">
                提交分数
              </button>
            </div>
          </div>

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
                    <span v-if="isWaitingState && player.is_ready" class="ready-tag">✓ 已准备</span>
                    <span v-else-if="isWaitingState && !player.is_ready" class="not-ready-tag">未准备</span>
                    <span v-else :class="player.status">
                      {{ player.status === 'active' ? '活跃' : player.status === 'eliminated' ? '淘汰' : '胜利' }}
                    </span>
                    <span v-if="!isWaitingState && confirmationStatus?.players?.find((p: any) => p.player_id === player.id)?.is_confirmed" class="confirmed-tag">
                      ✓ 已确认
                    </span>
                  </div>
                </div>
                <div class="player-score">{{ isWaitingState ? '-' : player.current_score }}</div>
              </div>
            </div>
          </div>

          <div v-if="isPlayingState" class="confirmation-section">
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

          <div v-if="isPlayingState && isRoomCreator" class="confirmation-section">
            <div class="confirmation-info">
              <div class="confirmation-status">
                <span v-if="isEndGameProposed" class="waiting-confirm">
                  已发起结束对局投票 ({{ endGameVotes.filter(v => v.is_approved).length }}/{{ endGameVotes.length }})
                </span>
              </div>
              <div class="confirmation-buttons">
                <button
                  v-if="!isEndGameProposed"
                  class="btn btn-warning w-full"
                  @click="proposeEndGame"
                >
                  结束对局
                </button>
              </div>
            </div>
          </div>

          <div v-if="isPlayingState && !isRoomCreator && currentPlayer" class="confirmation-section">
            <div class="confirmation-info">
              <div class="confirmation-status">
                <span v-if="isEndGameProposed && !hasCurrentVotedEnd" class="waiting-confirm">
                  房主发起了结束对局投票，请投票
                </span>
                <span v-else-if="hasCurrentVotedEnd" class="all-confirmed">
                  你已同意结束对局
                </span>
              </div>
              <div class="confirmation-buttons">
                <button
                  v-if="!currentLeaveRequest"
                  class="btn btn-secondary w-full"
                  @click="requestLeaveRoom"
                >
                  申请退出对局
                </button>
                <button
                  v-if="isEndGameProposed && !hasCurrentVotedEnd"
                  class="btn btn-success w-full"
                  @click="voteEndGame"
                >
                  同意结束
                </button>
              </div>
            </div>
          </div>
        </div>

        <div class="center-section">
          <div v-if="isPlayingState && isRoomCreator && leaveRequests.length > 0" class="notification-panel" style="border-color: var(--info-color);">
            <h3 style="color: var(--info-color);">
              退出申请
              <span class="notification-count">({{ leaveRequests.length }})</span>
            </h3>
            <div v-for="lr in leaveRequests" :key="lr.id" class="notification-item">
              <div class="notification-info">
                <strong>{{ lr.player_nickname }}</strong> 申请退出对局
              </div>
              <div class="notification-actions">
                <button class="btn btn-success btn-sm" @click="approveLeave(lr.id)">
                  同意
                </button>
                <button class="btn btn-danger btn-sm" @click="rejectLeave(lr.id)">
                  拒绝
                </button>
              </div>
            </div>
          </div>

          <div class="activity-section">
            <h2>房间动态</h2>
            <div class="activity-feed">
              <div v-if="filteredEvents.length === 0" class="activity-empty">
                暂无动态
              </div>
              <div
                v-for="event in filteredEvents"
                :key="event.id"
                class="activity-item"
                :class="getEventClass(event.type)"
              >
                <div class="activity-icon">
                  <span v-if="event.type === 'player_joined'">➡️</span>
                  <span v-else-if="event.type === 'player_left'">⬅️</span>
                  <span v-else-if="event.type === 'score_collected'">💰</span>
                  <span v-else-if="event.type === 'score_accepted'">✅</span>
                  <span v-else-if="event.type === 'score_rejected'">⛔</span>
                  <span v-else-if="event.type === 'round_confirmed'">✔️</span>
                  <span v-else-if="event.type === 'round_advanced'">▶️</span>
                  <span v-else>●</span>
                </div>
                <div class="activity-content">
                  <div class="activity-text">{{ getEventText(event) }}</div>
                  <div v-if="isPendingScoreEvent(event)" class="activity-actions">
                    <button
                      class="btn btn-success btn-sm"
                      @click="acceptPendingScore(pendingNotifications.find(n => n.batch_id === event.content.batch_id)?.id)"
                    >
                      接受
                    </button>
                    <button
                      class="btn btn-danger btn-sm"
                      @click="rejectPendingScore(pendingNotifications.find(n => n.batch_id === event.content.batch_id)?.id)"
                    >
                      拒绝
                    </button>
                  </div>
                </div>
              </div>
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

.room-actions {
  display: flex;
  gap: 10px;
  flex-shrink: 0;
}

.room-status-tag {
  padding: 4px 12px;
  border-radius: var(--radius-sm);
  font-size: 0.85rem;
  font-weight: 500;
}

.room-status-tag.open {
  background: rgba(78, 204, 163, 0.2);
  color: var(--success-color);
}

.room-status-tag.playing {
  background: rgba(233, 69, 96, 0.2);
  color: var(--accent-color);
}

.ready-tag {
  color: var(--success-color);
  font-weight: 600;
}

.not-ready-tag {
  color: var(--text-secondary);
}

.ready-actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.ready-actions .btn.ready {
  background: var(--success-color);
}

.ready-actions .btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn:disabled:hover {
  transform: none;
}

.btn-secondary {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
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

.round.playing {
  background: rgba(233, 69, 96, 0.2);
  color: var(--accent-color);
}

.base-score {
  background: rgba(78, 204, 163, 0.2);
  color: var(--success-color);
}

.room-main {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  align-items: start;
}

.left-section, .center-section {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.players-section, .score-input-section, .confirmation-section, .activity-section {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 20px;
  box-shadow: var(--shadow-md);
}

.players-section h2, .score-input-section h2, .confirmation-section h2, .activity-section h2 {
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

.target-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.target-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 12px 20px;
  background: var(--bg-secondary);
  border: 2px solid var(--border-color);
  border-radius: var(--radius-md);
  color: var(--text-primary);
  font-size: 0.95rem;
  cursor: pointer;
  transition: all var(--transition-normal);
  min-width: 80px;
}

.target-btn:hover {
  border-color: var(--accent-color);
  transform: translateY(-2px);
}

.target-btn.selected {
  border-color: var(--accent-color);
  background: rgba(233, 69, 96, 0.15);
  box-shadow: 0 0 12px rgba(233, 69, 96, 0.3);
}

.target-score {
  font-size: 0.8rem;
  color: var(--accent-color);
  font-weight: 600;
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

.notification-panel {
  background: var(--bg-card);
  border: 2px solid var(--warning-color);
  border-radius: var(--radius-lg);
  padding: 16px 20px;
  margin-bottom: 20px;
  box-shadow: 0 4px 20px rgba(255, 193, 7, 0.3);
  animation: slideDown 0.3s ease-out;
}

.notification-panel h3 {
  font-size: 1.1rem;
  margin-bottom: 12px;
  color: var(--warning-color);
  display: flex;
  align-items: center;
  gap: 8px;
}

.notification-count {
  font-size: 0.9rem;
  color: var(--text-secondary);
}

.notification-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  margin-bottom: 8px;
  transition: all var(--transition-normal);
}

.notification-item:last-child {
  margin-bottom: 0;
}

.notification-item:hover {
  border-color: var(--warning-color);
}

.notification-info {
  flex: 1;
  font-size: 0.95rem;
  line-height: 1.5;
}

.notification-info strong {
  color: var(--accent-color);
}

.notification-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.activity-feed {
  display: flex;
  flex-direction: column;
  gap: 2px;
  max-height: 500px;
  overflow-y: auto;
}

.activity-empty {
  color: var(--text-secondary);
  text-align: center;
  padding: 30px;
  font-size: 0.95rem;
}

.activity-item {
  display: flex;
  gap: 12px;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  transition: background var(--transition-normal);
  border-left: 3px solid transparent;
}

.activity-item:hover {
  background: var(--bg-secondary);
}

.activity-item.event-join {
  border-left-color: var(--success-color);
}

.activity-item.event-leave {
  border-left-color: var(--text-secondary);
  opacity: 0.7;
}

.activity-item.event-score {
  border-left-color: var(--accent-color);
  background: rgba(233, 69, 96, 0.05);
}

.activity-item.event-accept {
  border-left-color: var(--success-color);
}

.activity-item.event-reject {
  border-left-color: var(--danger-color);
  background: rgba(255, 107, 107, 0.05);
}

.activity-item.event-confirm {
  border-left-color: var(--info-color);
}

.activity-item.event-advance {
  border-left-color: var(--warning-color);
  background: rgba(255, 193, 7, 0.05);
}

.activity-item.event-start {
  border-left-color: var(--success-color);
  background: rgba(78, 204, 163, 0.1);
}

.activity-item.event-reset {
  border-left-color: var(--warning-color);
  background: rgba(255, 193, 7, 0.08);
}

.activity-item.event-end-propose {
  border-left-color: var(--warning-color);
}

.activity-item.event-end-vote {
  border-left-color: var(--success-color);
}

.activity-item.event-leave-request {
  border-left-color: var(--info-color);
}

.activity-item.event-leave-approve {
  border-left-color: var(--success-color);
}

.activity-item.event-leave-reject {
  border-left-color: var(--danger-color);
}

.activity-icon {
  font-size: 1.1rem;
  flex-shrink: 0;
  width: 24px;
  text-align: center;
  line-height: 1.5;
}

.activity-content {
  flex: 1;
  min-width: 0;
}

.activity-text {
  font-size: 0.9rem;
  line-height: 1.5;
  color: var(--text-primary);
}

.activity-actions {
  display: flex;
  gap: 6px;
  margin-top: 6px;
}

.btn-danger {
  background: var(--danger-color);
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-normal);
}

.btn-danger:hover {
  background: #e55555;
  transform: translateY(-2px);
}

.btn-sm {
  padding: 6px 16px;
  font-size: 0.85rem;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
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