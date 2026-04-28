<script setup lang="ts">
import { ref, reactive, onMounted, computed, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useToastStore } from '@/stores/toast'
import { Icon } from '@iconify/vue'
import api from '@/utils/api'
import CollapsibleSection from '@/components/CollapsibleSection.vue'
import SkeletonLoader from '@/components/SkeletonLoader.vue'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const toast = useToastStore()

const roomCode = route.params.roomCode as string
const roomInfo = ref<any>(null)
const players = ref<any[]>([])
const scores = ref<any[]>([])
const loading = ref(true)
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
  const list = isPlayingState.value
    ? events.value.filter(e => e.type !== 'player_joined' && e.type !== 'player_left')
    : events.value
  return [...list].reverse()
})

const pendingNotifications = ref<any[]>([])

const getPendingForEvent = (event: any) => {
  if (event.type !== 'score_collected') return null
  const current = currentPlayer.value
  if (!current) return null
  return pendingNotifications.value.find(n => n.batch_id === event.content.batch_id) || null
}

const roomStatus = ref<any>(null)
const isWaitingState = computed(() => roomInfo.value?.status === 'open')
const isPlayingState = computed(() => roomInfo.value?.status === 'playing')
const isFinishedState = computed(() => roomInfo.value?.status === 'finished')

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
    toast.error(e.response?.data?.detail || '操作失败')
  }
}

const startGame = async () => {
  try {
    await api.post(`/rooms/${roomCode}/start`)
  } catch (e: any) {
    toast.error(e.response?.data?.detail || '开始失败')
  }
}

const proposeEndGame = async () => {
  try {
    await api.post(`/rooms/${roomCode}/propose-end`)
    toast.info('已发起结束提议，等待其他玩家投票')
  } catch (e: any) {
    toast.error(e.response?.data?.detail || '操作失败')
  }
}

const voteEndGame = async () => {
  try {
    const res = await api.post(`/rooms/${roomCode}/vote-end`)
    if (res.data.game_reset) {
      toast.success('游戏已结束')
      await refreshRoomData()
    } else {
      toast.success('已投票')
    }
  } catch (e: any) {
    toast.error(e.response?.data?.detail || '操作失败')
  }
}

const requestLeaveRoom = async () => {
  try {
    await api.post(`/rooms/${roomCode}/request-leave`)
    toast.info('已发起退出申请，等待房主批准')
  } catch (e: any) {
    toast.error(e.response?.data?.detail || '操作失败')
  }
}

const approveLeave = async (requestId: number) => {
  try {
    await api.post(`/rooms/${roomCode}/approve-leave/${requestId}`)
    toast.success('已批准退出')
    await refreshRoomData()
  } catch (e: any) {
    toast.error(e.response?.data?.detail || '操作失败')
  }
}

const rejectLeave = async (requestId: number) => {
  try {
    await api.post(`/rooms/${roomCode}/reject-leave/${requestId}`)
    toast.info('已拒绝退出申请')
    leaveRequests.value = leaveRequests.value.filter(lr => lr.id !== requestId)
  } catch (e: any) {
    toast.error(e.response?.data?.detail || '操作失败')
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
    toast.success('已确认分数')
    pendingNotifications.value = pendingNotifications.value.filter(n => n.id !== pendingId)
    await refreshRoomData()
  } catch (e: any) {
    toast.error('确认失败')
  }
}

const rejectPendingScore = async (pendingId: number) => {
  try {
    await api.post(`/pending-scores/${pendingId}/reject`)
    toast.info('已拒绝分数')
    await refreshRoomData()
    pendingNotifications.value = pendingNotifications.value.filter(n => n.id !== pendingId)
  } catch (e: any) {
    toast.error('拒绝失败')
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

const getEventIcon = (type: string) => {
  switch (type) {
    case 'player_joined': return 'mdi:account-plus'
    case 'player_left': return 'mdi:account-minus'
    case 'score_collected': return 'mdi:cash'
    case 'score_accepted': return 'mdi:check-circle-outline'
    case 'score_rejected': return 'mdi:close-circle-outline'
    case 'round_confirmed': return 'mdi:check-all'
    case 'round_advanced': return 'mdi:skip-next'
    case 'game_started': return 'mdi:play-circle'
    case 'game_reset': return 'mdi:restart'
    case 'end_proposed': return 'mdi:hand-wave'
    case 'end_voted': return 'mdi:ballot'
    case 'leave_requested': return 'mdi:exit-run'
    case 'leave_approved': return 'mdi:door-open'
    case 'leave_rejected': return 'mdi:door-closed'
    default: return 'mdi:circle-small'
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
    if (e.response?.status === 404) {
      error.value = '房间不存在或已被删除'
    } else if (e.response?.status === 403) {
      error.value = '您没有权限进入此房间'
    } else if (e.response?.status === 401) {
      error.value = '请先登录后再进入房间'
    } else if (e.code === 'ERR_NETWORK') {
      error.value = '网络连接失败，请检查网络后重试'
    } else {
      error.value = e.response?.data?.detail || '加载房间信息失败'
    }
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

let reconnectTimer: any = null
let reconnectCount = 0
const MAX_RECONNECT = 5

const initWebSocket = () => {
  if (!roomInfo.value || !userStore.userInfo) return

  const player = players.value.find(p => p.user_id === userStore.userInfo?.id)
  if (!player) return

  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsHost = window.location.hostname === 'localhost' ? 'localhost:8000' : window.location.host
  const wsUrl = `${wsProtocol}//${wsHost}/api/ws/${roomInfo.value.id}/${player.id}`

  ws.value = new WebSocket(wsUrl)

  ws.value.onopen = () => {
    console.log('WebSocket连接成功')
    reconnectCount = 0
  }

  ws.value.onmessage = async (event) => {
    const message = JSON.parse(event.data)
    console.log('收到消息:', message)

    if (message.type === 'room_event') {
      error.value = ''
      if (message.event_type === 'score_collected') {
        await refreshRoomData()
      } else if (message.event_type === 'score_rejected') {
        await refreshRoomData()
      } else if (message.event_type === 'score_accepted') {
        await fetchPendingNotifications()
      } else if (['ready_update', 'player_joined', 'player_left', 'game_reset'].includes(message.event_type)) {
        await refreshRoomData()
      } else if (message.event_type === 'game_started') {
        await refreshRoomData()
      } else if (message.event_type === 'end_proposed') {
        await fetchRoomStatus()
      } else if (message.event_type === 'end_voted') {
        await fetchRoomStatus()
      } else if (message.event_type === 'leave_requested') {
        await fetchRoomStatus()
      } else if (message.event_type === 'leave_approved') {
        await refreshRoomData()
      } else if (message.event_type === 'leave_rejected') {
        await fetchRoomStatus()
      } else {
        await refreshRoomData()
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
      toast.error('实时连接已断开，请刷新页面重试')
    }
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

const resetForm = () => {
  scoreForm.score = 0
  scoreForm.selectedPlayers = []
}

const submitScore = async () => {
  if (!roomInfo.value || scoreForm.score <= 0) {
    toast.warning('请选择分数')
    return
  }

  if (roomInfo.value.game_type === 'add_subtract' && scoreForm.selectedPlayers.length === 0) {
    toast.warning('请选择目标玩家')
    return
  }

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

    toast.success('分数已提交')
    await refreshRoomData()
    scoreForm.score = 0
    scoreForm.selectedPlayers = []
  } catch (e: any) {
    toast.error(e.response?.data?.detail || '提交失败')
  }
}

const submitConfirmation = async (confirmed: boolean) => {
  if (!roomInfo.value) return

  try {
    const res = await api.post(`/confirmations/room/${roomInfo.value.id}/confirm`, { confirmed })

    const data = res.data
    isCurrentPlayerConfirmed.value = confirmed
    await loadConfirmationStatus()

    if (confirmed) {
      toast.success('已确认本轮')
    }

    if (ws.value && ws.value.readyState === WebSocket.OPEN) {
      ws.value.send(JSON.stringify({
        type: 'confirmation_update',
        is_confirmed: confirmed,
        all_confirmed: data.all_confirmed,
        can_advance_round: data.can_advance_round
      }))
    }
  } catch (e: any) {
    toast.error(e.response?.data?.detail || '操作失败')
  }
}

const advanceToNextRound = async () => {
  if (!roomInfo.value) return
  if (pendingNotifications.value.length > 0) {
    toast.warning('有待确认的分数，请先处理')
    return
  }

  try {
    const res = await api.post(`/confirmations/room/${roomInfo.value.id}/next-round`)

    const data = res.data
    roomInfo.value.current_round = data.new_round
    await loadConfirmationStatus()
    toast.success(`进入第 ${data.new_round} 轮`)

    if (ws.value && ws.value.readyState === WebSocket.OPEN) {
      ws.value.send(JSON.stringify({
        type: 'round_advanced',
        new_round: data.new_round
      }))
    }
  } catch (e: any) {
    toast.error(e.response?.data?.detail || '操作失败')
  }
}

const leaveRoom = async () => {
  if (!roomInfo.value) return
  try {
    await api.delete(`/rooms/${roomCode}/leave`)
    toast.info('已离开房间')
    router.push('/')
  } catch (e: any) {
    toast.error(e.response?.data?.detail || '离开失败')
  }
}

const goBack = () => {
  router.push('/')
}

// Avatar color helper
const avatarColors = ['#2b6ef0', '#0ec782', '#0bc5ea', '#f5a623', '#f04848', '#a855f7', '#f97316', '#06b6d4']
const getAvatarColor = (id: number) => avatarColors[id % avatarColors.length]
const getInitial = (name: string) => name.charAt(0).toUpperCase()

const scorePopKey = ref(0)

onMounted(async () => {
  if (!userStore.isLoggedIn) {
    toast.info('请先登录后再进入房间')
    router.push('/login?redirect=' + encodeURIComponent(route.fullPath))
    return
  }
  await loadRoomInfo()
  initWebSocket()
})

onUnmounted(() => {
  if (reconnectTimer) clearTimeout(reconnectTimer)
  if (ws.value) {
    ws.value.onclose = null
    ws.value.close()
  }
})
</script>

<template>
  <div class="room-page">
    <!-- Loading state -->
    <div v-if="loading" class="room-page">
      <div class="room-header-skeleton">
        <div class="skeleton-bar w-60" />
        <div class="skeleton-bar w-40" />
      </div>
      <div class="room-main">
        <SkeletonLoader type="card" :count="4" />
      </div>
    </div>

    <!-- Error state -->
    <div v-else-if="error" class="error-state">
      <div class="error-card">
        <Icon icon="mdi:link-variant-off" :width="48" class="error-icon" />
        <h2 class="error-title">无法进入房间</h2>
        <p class="error-desc">{{ error }}</p>
        <p class="error-hint">房间链接可能已失效，或您未被邀请进入此房间</p>
        <button class="btn btn-primary" @click="goBack">
          <Icon icon="mdi:home" :width="18" />返回首页
        </button>
      </div>
    </div>

    <!-- Main content -->
    <div v-else-if="roomInfo" class="room-content">
      <!-- Fixed Header -->
      <header class="room-header">
        <div class="header-top">
          <button class="btn-icon" @click="goBack">
            <Icon icon="mdi:arrow-left" :width="22" />
          </button>
          <div class="header-title-area">
            <h1 class="room-name">{{ roomInfo.name }}</h1>
          </div>
          <div class="header-actions">
            <button v-if="!isPlayingState" class="btn btn-xs btn-ghost" @click="leaveRoom">
              <Icon icon="mdi:exit-to-app" :width="14" />离开
            </button>
            <button v-else class="btn btn-xs btn-ghost" @click="requestLeaveRoom" :disabled="!!currentLeaveRequest">
              <Icon icon="mdi:exit-run" :width="14" />{{ currentLeaveRequest ? '已申请' : '退出' }}
            </button>
          </div>
        </div>
        <div class="header-tags">
          <span class="tag tag-info">{{ roomInfo.room_code }}</span>
          <span class="tag" :class="roomInfo.game_type === 'add_subtract' ? 'tag-danger' : 'tag-success'">
            <Icon :icon="roomInfo.game_type === 'add_subtract' ? 'mdi:swap-vertical-bold' : 'mdi:plus-circle'" :width="12" />
            {{ roomInfo.game_type === 'add_subtract' ? '加减分' : '加分' }}
          </span>
          <span class="tag" :class="isPlayingState ? 'tag-danger' : isFinishedState ? 'tag-success' : 'tag-success'">
            <Icon :icon="isPlayingState ? 'mdi:play-circle' : isFinishedState ? 'mdi:check-circle' : 'mdi:pause-circle'" :width="12" />
            {{ isPlayingState ? `第 ${currentRound} 轮` : isFinishedState ? '已结束' : '等待中' }}
          </span>
        </div>
      </header>

      <!-- Scrollable Content -->
      <template v-if="isFinishedState">
        <div class="room-main">
          <div class="finished-card">
            <Icon icon="mdi:trophy" :width="48" class="finished-icon" />
            <h2 class="finished-title">游戏已结束</h2>
            <div class="finished-scores">
              <div
                v-for="player in players"
                :key="player.id"
                class="finished-player"
              >
                <div class="fp-avatar" :style="{ background: getAvatarColor(player.id) }">
                  {{ getInitial(player.nickname) }}
                </div>
                <div class="fp-info">
                  <span class="fp-name">{{ player.nickname }}</span>
                  <span class="fp-score" :class="{ 'score-positive': (player.current_score || 0) > 0, 'score-negative': (player.current_score || 0) < 0 }">
                    {{ (player.current_score || 0) > 0 ? '+' : '' }}{{ player.current_score || 0 }}
                  </span>
                </div>
              </div>
            </div>
            <button class="btn btn-primary" @click="goBack">
              <Icon icon="mdi:home" :width="18" />返回首页
            </button>
          </div>
        </div>
      </template>
      <template v-else>
        <div class="room-main">
        <!-- Player List Section (always visible, default open) -->
        <CollapsibleSection
          title="玩家列表"
          icon="mdi:account-group"
          :badge="isPlayingState ? `${players.filter(p => p.status === 'active').length}人 · 第${currentRound}轮` : players.filter(p => p.status === 'active').length"
          :badge-type="isPlayingState ? 'danger' : 'info'"
          :default-open="true"
        >
          <div class="players-list">
            <div
              v-for="player in players"
              :key="player.id"
              class="player-card"
              :class="{
                'is-self': player.id === currentPlayer?.id,
                'is-eliminated': player.status !== 'active',
                'is-confirmed': confirmationStatus?.players?.find((p: any) => p.player_id === player.id)?.is_confirmed,
                'is-target': isPlayingState && roomInfo.game_type === 'add_subtract' && player.id !== currentPlayer?.id && scoreForm.selectedPlayers.includes(player.id),
                'clickable': isPlayingState && roomInfo.game_type === 'add_subtract' && player.id !== currentPlayer?.id
              }"
              @click="isPlayingState && roomInfo.game_type === 'add_subtract' && player.id !== currentPlayer?.id && togglePlayer(player.id)"
            >
              <div
                class="player-avatar"
                :style="{ background: getAvatarColor(player.id) }"
              >
                {{ getInitial(player.nickname) }}
              </div>
              <div class="player-body">
                <div class="player-name-row">
                  <span class="player-name">{{ player.nickname }}</span>
                  <span v-if="player.id === currentPlayer?.id" class="player-tag tag tag-danger">你</span>
                  <span v-if="roomInfo.created_by === player.user_id" class="player-tag tag tag-warning">
                    <Icon icon="mdi:crown" :width="10" />房主
                  </span>
                  <span v-if="isPlayingState && roomInfo.game_type === 'add_subtract' && player.id !== currentPlayer?.id && scoreForm.selectedPlayers.includes(player.id)" class="player-tag tag tag-danger">
                    输家 -{{ scoreForm.score || '?' }}
                  </span>
                </div>
                <div class="player-meta">
                  <template v-if="isWaitingState">
                    <span v-if="player.is_ready" class="status-ready">
                      <Icon icon="mdi:check-circle" :width="12" />已准备
                    </span>
                    <span v-else class="status-not-ready">未准备</span>
                  </template>
                  <template v-else>
                    <span v-if="player.status === 'active'" class="status-active">
                      <Icon icon="mdi:circle" :width="8" />游戏中
                    </span>
                    <span v-else class="status-eliminated">{{ player.status }}</span>
                    <span
                      v-if="confirmationStatus?.players?.find((p: any) => p.player_id === player.id)?.is_confirmed"
                      class="status-confirmed"
                    >
                      <Icon icon="mdi:check-circle" :width="12" />已确认
                    </span>
                  </template>
                </div>
              </div>
              <div class="player-score-area">
                <div
                  v-if="!isWaitingState"
                  class="player-score"
                  :class="{
                    'score-positive': (player.current_score || 0) > 0,
                    'score-negative': (player.current_score || 0) < 0,
                    'score-zero': (player.current_score || 0) === 0
                  }"
                  :key="scorePopKey"
                >
                  <Icon
                    v-if="(player.current_score || 0) > 0"
                    icon="mdi:trending-up"
                    :width="14"
                  />
                  <Icon
                    v-else-if="(player.current_score || 0) < 0"
                    icon="mdi:trending-down"
                    :width="14"
                  />
                  {{ player.current_score || 0 }}
                </div>
                <div v-else class="player-score score-zero">-</div>
              </div>
            </div>
          </div>

          <!-- Score input integrated (only in playing state) -->
          <template v-if="isPlayingState">
            <div class="score-divider" />
            <div class="score-input-area">
              <div class="stepper">
                <button class="stepper-btn" @click="scoreForm.score = Math.max(0, scoreForm.score - 1)">
                  <Icon icon="mdi:minus" :width="22" />
                </button>
                <div class="stepper-value">{{ scoreForm.score }}</div>
                <button class="stepper-btn" @click="scoreForm.score = Math.min(999, scoreForm.score + 1)">
                  <Icon icon="mdi:plus" :width="22" />
                </button>
              </div>
              <div class="submit-area">
                <div v-if="scoreForm.score > 0" class="score-preview">
                  你<Icon icon="mdi:arrow-right" :width="16" />
                  <span class="preview-gain">+{{ roomInfo.game_type === 'add_subtract' ? scoreForm.score * (scoreForm.selectedPlayers.length || 1) : scoreForm.score }}</span>
                  <span v-if="roomInfo.game_type === 'add_subtract' && scoreForm.selectedPlayers.length > 0" class="preview-loss">
                    每人 -{{ scoreForm.score }}
                  </span>
                </div>
                <div class="submit-row">
                  <button class="btn btn-ghost btn-reset" @click="resetForm">
                    <Icon icon="mdi:restart" :width="16" />重置
                  </button>
                  <button
                    class="btn btn-primary btn-submit"
                    :disabled="scoreForm.score <= 0"
                    @click="submitScore"
                  >
                    <Icon icon="mdi:send" :width="18" />
                    提交分数
                  </button>
                </div>
              </div>
            </div>
          </template>
        </CollapsibleSection>

        <!-- Waiting Area (pre-game) -->
        <template v-if="isWaitingState">
          <CollapsibleSection
            title="游戏准备"
            icon="mdi:gamepad-variant"
            :default-open="true"
          >
            <div class="ready-area">
              <button
                class="btn w-full"
                :class="currentPlayer?.is_ready ? 'btn-success' : 'btn-primary'"
                @click="toggleReady"
              >
                <Icon :icon="currentPlayer?.is_ready ? 'mdi:check-circle' : 'mdi:hand-peace'" :width="18" />
                {{ currentPlayer?.is_ready ? '已准备' : '点击准备' }}
              </button>
              <button
                v-if="isRoomCreator"
                class="btn w-full"
                :class="allPlayersReady ? 'btn-success' : 'btn-secondary'"
                :disabled="!allPlayersReady"
                @click="startGame"
              >
                <Icon icon="mdi:play" :width="18" />
                开始游戏{{ allPlayersReady ? '' : ' (等待全员准备)' }}
              </button>
              <p v-if="!allPlayersReady && isRoomCreator" class="ready-hint">
                至少需要2名玩家且全部准备才能开始
              </p>
            </div>
          </CollapsibleSection>
        </template>

        <!-- Playing Area (in-game) -->
        <template v-if="isPlayingState">
          <!-- Confirmation Section -->
          <CollapsibleSection
            title="轮次确认"
            icon="mdi:clipboard-check"
            :badge="`${activePlayers.filter(p => confirmationStatus?.players?.find((cp: any) => cp.player_id === p.id)?.is_confirmed).length}/${activePlayers.length}`"
            :badge-type="allActivePlayersConfirmed ? 'success' : 'warning'"
            :default-open="true"
          >
            <div class="confirm-area">
              <div class="confirm-status-bar">
                <Icon
                  :icon="allActivePlayersConfirmed ? 'mdi:check-decagram' : 'mdi:clock-outline'"
                  :width="20"
                  :style="{ color: allActivePlayersConfirmed ? 'var(--success-color)' : 'var(--warning-color)' }"
                />
                <span :class="allActivePlayersConfirmed ? 'text-success' : 'text-warning'">
                  {{ allActivePlayersConfirmed ? '全员已确认' : '等待确认' }}
                </span>
              </div>
              <div class="confirm-actions">
                <button
                  v-if="!isCurrentPlayerConfirmed && currentPlayer?.status === 'active'"
                  class="btn btn-success w-full"
                  @click="submitConfirmation(true)"
                >
                  <Icon icon="mdi:check" :width="18" />确认本轮
                </button>
                <button
                  v-if="isCurrentPlayerConfirmed"
                  class="btn btn-ghost w-full"
                  @click="submitConfirmation(false)"
                >
                  <Icon icon="mdi:close" :width="18" />取消确认
                </button>
                <button
                  v-if="allActivePlayersConfirmed && isRoomCreator"
                  class="btn btn-primary w-full"
                  :disabled="pendingNotifications.length > 0"
                  @click="advanceToNextRound"
                >
                  <Icon icon="mdi:skip-next" :width="18" />{{ pendingNotifications.length > 0 ? '等待分数确认' : '下一轮' }}
                </button>
              </div>

              <!-- Game end controls -->
              <div class="game-end-controls">
                <button
                  v-if="isRoomCreator && !isEndGameProposed"
                  class="btn btn-warning w-full"
                  @click="proposeEndGame"
                >
                  <Icon icon="mdi:hand-wave" :width="18" />结束对局
                </button>
                <button
                  v-if="!isRoomCreator && !currentLeaveRequest"
                  class="btn btn-ghost w-full"
                  @click="requestLeaveRoom"
                >
                  <Icon icon="mdi:exit-run" :width="18" />申请退出
                </button>
                <template v-if="isEndGameProposed">
                  <div class="end-proposal-banner">
                    <Icon icon="mdi:bullhorn" :width="18" />
                    房主提议结束游戏
                  </div>
                  <button
                    v-if="!hasCurrentVotedEnd && !isRoomCreator"
                    class="btn btn-success w-full"
                    @click="voteEndGame"
                  >
                    <Icon icon="mdi:check" :width="18" />同意结束
                  </button>
                  <div v-if="hasCurrentVotedEnd" class="voted-banner">
                    <Icon icon="mdi:check-decagram" :width="18" />
                    你已同意结束
                  </div>
                  <div v-if="isRoomCreator" class="vote-count">
                    投票进度: {{ endGameVotes.filter(v => v.is_approved).length }}/{{ endGameVotes.length }}
                  </div>
                </template>
              </div>
            </div>
          </CollapsibleSection>
        </template>

        <!-- Activity Feed (always visible) -->
        <div class="feed-section">
          <div class="feed-header">
            <Icon icon="mdi:animation" :width="16" />
            <span>房间动态</span>
            <span v-if="filteredEvents.length > 0" class="feed-count">{{ filteredEvents.length }}</span>
          </div>
          <div class="activity-feed">
            <div v-if="filteredEvents.length === 0" class="activity-empty">
              <Icon icon="mdi:inbox-outline" :width="24" />
              <span>暂无动态</span>
            </div>
            <div
              v-for="event in filteredEvents"
              :key="event.id"
              class="activity-item"
              :class="getEventClass(event.type)"
            >
              <Icon :icon="getEventIcon(event.type)" :width="14" class="activity-icon" />
              <div class="activity-text">{{ getEventText(event) }}</div>
              <div v-if="getPendingForEvent(event)" class="activity-actions">
                <button class="btn btn-xs btn-success" @click="acceptPendingScore(getPendingForEvent(event)!.id)">
                  <Icon icon="mdi:check" :width="11" />
                </button>
                <button class="btn btn-xs btn-danger" @click="rejectPendingScore(getPendingForEvent(event)!.id)">
                  <Icon icon="mdi:close" :width="11" />
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Leave Requests (only for room creator when there are requests) -->
        <template v-if="isPlayingState && isRoomCreator && leaveRequests.length > 0">
          <CollapsibleSection
            title="退出申请"
            icon="mdi:door-open"
            :badge="leaveRequests.length"
            badge-type="warning"
            :default-open="true"
          >
            <div v-for="lr in leaveRequests" :key="lr.id" class="leave-request-item">
              <div class="leave-request-info">
                <div class="leave-request-avatar" :style="{ background: getAvatarColor(lr.player_id) }">
                  {{ getInitial(lr.player_nickname || '?') }}
                </div>
                <span><strong>{{ lr.player_nickname }}</strong> 申请退出</span>
              </div>
              <div class="leave-request-actions">
                <button class="btn btn-xs btn-success" @click="approveLeave(lr.id)">
                  <Icon icon="mdi:check" :width="12" />同意
                </button>
                <button class="btn btn-xs btn-danger" @click="rejectLeave(lr.id)">
                  <Icon icon="mdi:close" :width="12" />拒绝
                </button>
              </div>
            </div>
          </CollapsibleSection>
        </template>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.room-page {
  height: 100vh;
  background: var(--bg-primary);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* ====== Header ====== */
.room-header {
  flex-shrink: 0;
  background: var(--bg-card);
  border-bottom: 1px solid var(--border-color);
  padding: 10px 14px 8px;
  position: sticky;
  top: 0;
  z-index: 10;
}

.header-top {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.btn-icon {
  background: none;
  border: none;
  color: var(--text-primary);
  cursor: pointer;
  padding: 4px;
  display: flex;
  align-items: center;
  border-radius: 8px;
  transition: background var(--transition-fast);
  flex-shrink: 0;
}

.btn-icon:hover {
  background: var(--bg-hover);
}

.btn-icon:active {
  transform: scale(0.92);
}

.header-title-area {
  flex: 1;
  min-width: 0;
}

.room-name {
  font-size: 1rem;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin: 0;
}

.header-actions {
  flex-shrink: 0;
  display: flex;
  gap: 4px;
}

.header-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

/* ====== Main Scrollable Area ====== */
.room-main {
  flex: 1;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding-bottom: 24px;
}

/* ====== Skeleton ====== */
.room-header-skeleton {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.skeleton-bar {
  height: 18px;
  background: var(--border-color);
  border-radius: 4px;
  animation: skeleton-pulse 1.5s ease-in-out infinite;
}

.skeleton-bar.w-60 { width: 60%; }
.skeleton-bar.w-40 { width: 40%; }

@keyframes skeleton-pulse {
  0%, 100% { opacity: 0.6; }
  50% { opacity: 0.3; }
}

/* ====== Error State ====== */
.error-state {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.error-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  text-align: center;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xl);
  padding: 36px 28px;
  max-width: 360px;
  width: 100%;
  box-shadow: var(--shadow-md);
  animation: slideUp 0.4s ease-out;
}

.error-icon {
  opacity: 0.6;
  color: var(--text-tertiary);
}

.error-title {
  font-size: 1.2rem;
  margin: 0;
}

.error-desc {
  font-size: 0.85rem;
  color: var(--text-secondary);
  margin: 0;
}

.error-hint {
  font-size: 0.75rem;
  color: var(--text-tertiary);
  margin: 0 0 4px;
}

/* ====== Player List ====== */
.players-list {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
}

/* ====== Finished State ====== */
.finished-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 14px;
  text-align: center;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-xl);
  padding: 32px 24px;
  box-shadow: var(--shadow-md);
  animation: slideUp 0.4s ease-out;
}

.finished-icon {
  color: var(--warning-color);
  opacity: 0.8;
}

.finished-title {
  font-size: 1.3rem;
  margin: 0;
}

.finished-scores {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin: 4px 0;
}

.finished-player {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
}

.fp-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.78rem;
  font-weight: 700;
  color: white;
  flex-shrink: 0;
}

.fp-info {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-width: 0;
}

.fp-name {
  font-size: 0.85rem;
  font-weight: 600;
}

.fp-score {
  font-size: 1.05rem;
  font-weight: 700;
}

.player-card {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  transition: all var(--transition-normal);
}

.player-card.is-self {
  border-color: rgba(43, 110, 240, 0.3);
  background: rgba(43, 110, 240, 0.05);
}

.player-card.is-confirmed {
  border-color: rgba(14, 199, 130, 0.3);
  background: rgba(14, 199, 130, 0.05);
}

.player-card.is-target {
  border-color: rgba(240, 72, 72, 0.5);
  background: rgba(240, 72, 72, 0.08);
  box-shadow: 0 0 12px rgba(240, 72, 72, 0.15);
}

.player-card.clickable {
  cursor: pointer;
}

.player-card.clickable:active {
  transform: scale(0.97);
}

.player-card.is-eliminated {
  opacity: 0.5;
}

.player-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.78rem;
  font-weight: 700;
  color: white;
  flex-shrink: 0;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.3);
}

.player-body {
  flex: 1;
  min-width: 0;
}

.player-name-row {
  display: flex;
  align-items: center;
  gap: 3px;
  margin-bottom: 1px;
}

.player-name {
  font-size: 0.78rem;
  font-weight: 600;
}

.player-tag {
  font-size: 0.55rem !important;
  padding: 0 5px !important;
  line-height: 1.5 !important;
}

.player-meta {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 0.65rem;
}

.status-ready {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  color: var(--success-color);
}

.status-not-ready {
  color: var(--text-tertiary);
}

.status-active {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  color: var(--success-color);
}

.status-eliminated {
  color: var(--text-tertiary);
}

.status-confirmed {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  color: var(--success-color);
}

.player-score-area {
  flex-shrink: 0;
  margin-left: 4px;
}

.player-score {
  font-size: 0.85rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  gap: 2px;
  animation: numberPop 0.3s ease-out;
}

.score-positive {
  color: var(--success-color);
}

.score-negative {
  color: var(--accent-color);
}

.score-zero {
  color: var(--text-tertiary);
}

/* ====== Ready Area ====== */
.ready-area {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.ready-hint {
  text-align: center;
  font-size: 0.75rem;
  color: var(--text-tertiary);
}

/* ====== Score Input ====== */
.score-input-area {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 8px;
}

.score-divider {
  height: 1px;
  background: var(--border-color);
  margin: 12px 0 4px;
}

.stepper {
  display: flex;
  align-items: center;
  gap: 0;
  background: var(--bg-secondary);
  border: 1.5px solid var(--border-color);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.stepper-btn {
  flex: 0 0 52px;
  height: 52px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: none;
  color: var(--text-primary);
  cursor: pointer;
  transition: all var(--transition-fast);
  -webkit-tap-highlight-color: transparent;
}

.stepper-btn:active {
  background: rgba(43, 110, 240, 0.1);
  color: var(--accent-color);
}

.stepper-value {
  flex: 1;
  text-align: center;
  font-size: 1.6rem;
  font-weight: 700;
  color: var(--text-primary);
  padding: 8px 0;
  border-left: 1px solid var(--border-color);
  border-right: 1px solid var(--border-color);
  user-select: none;
}

.submit-area {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.score-preview {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font-size: 0.82rem;
  color: var(--text-secondary);
  padding: 8px;
  background: var(--bg-secondary);
  border-radius: var(--radius-sm);
}

.preview-gain {
  color: var(--success-color);
  font-weight: 700;
  font-size: 0.95rem;
}

.preview-loss {
  color: var(--accent-color);
  font-weight: 500;
}

.submit-row {
  display: flex;
  gap: 8px;
}

.btn-reset {
  flex: 0 0 auto;
  padding: 8px 14px;
  font-size: 0.82rem;
  min-height: 44px;
}

.btn-submit {
  flex: 1;
  font-size: 1rem;
  padding: 14px;
}

/* ====== Confirmation Area ====== */
.confirm-area {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.confirm-status-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font-size: 0.9rem;
  font-weight: 600;
  padding: 8px;
  background: var(--bg-secondary);
  border-radius: var(--radius-md);
}

.confirm-actions {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.text-success { color: var(--success-color); }
.text-warning { color: var(--warning-color); }

.game-end-controls {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding-top: 8px;
  border-top: 1px solid var(--border-color);
}

.end-proposal-banner {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 8px;
  background: rgba(255, 193, 7, 0.1);
  border: 1px solid rgba(255, 193, 7, 0.3);
  border-radius: var(--radius-sm);
  font-size: 0.82rem;
  color: var(--warning-color);
}

.voted-banner {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 8px;
  background: rgba(78, 204, 163, 0.1);
  border: 1px solid rgba(78, 204, 163, 0.3);
  border-radius: var(--radius-sm);
  font-size: 0.82rem;
  color: var(--success-color);
}

.vote-count {
  text-align: center;
  font-size: 0.78rem;
  color: var(--text-secondary);
}

/* ====== Activity Feed ====== */
.feed-section {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.feed-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 12px 14px 8px;
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--text-secondary);
}

.feed-count {
  font-size: 0.65rem;
  padding: 0 6px;
  border-radius: 8px;
  background: rgba(0, 217, 255, 0.15);
  color: var(--info-color);
  font-weight: 500;
}

.activity-feed {
  display: flex;
  flex-direction: column;
  max-height: 200px;
  overflow-y: auto;
  padding: 0 14px 10px;
}

.activity-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  color: var(--text-tertiary);
  padding: 20px;
  font-size: 0.82rem;
}

.activity-item {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding: 5px 6px;
  border-radius: var(--radius-sm);
  border-left: 3px solid transparent;
}

.activity-icon {
  flex-shrink: 0;
  margin-top: 2px;
  opacity: 0.7;
}

.activity-text {
  flex: 1;
  min-width: 0;
  font-size: 0.75rem;
  line-height: 1.4;
  color: var(--text-primary);
  word-break: break-word;
}

.activity-actions {
  flex-shrink: 0;
  display: flex;
  gap: 3px;
  margin-left: auto;
  align-self: center;
}

.activity-actions .btn-xs {
  padding: 3px 8px;
  min-height: 26px;
  font-size: 0.68rem;
}

.event-join { border-left-color: var(--success-color); }
.event-leave { border-left-color: var(--text-secondary); opacity: 0.7; }
.event-score { border-left-color: var(--accent-color); }
.event-accept { border-left-color: var(--success-color); }
.event-reject { border-left-color: var(--danger-color); }
.event-confirm { border-left-color: var(--info-color); }
.event-advance { border-left-color: var(--warning-color); }
.event-start { border-left-color: var(--success-color); }
.event-reset { border-left-color: var(--warning-color); }
.event-end-propose { border-left-color: var(--warning-color); }
.event-end-vote { border-left-color: var(--success-color); }
.event-leave-request { border-left-color: var(--info-color); }
.event-leave-approve { border-left-color: var(--success-color); }
.event-leave-reject { border-left-color: var(--danger-color); }

/* ====== Leave Requests ====== */
.leave-request-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 10px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  margin-bottom: 6px;
}

.leave-request-item:last-child {
  margin-bottom: 0;
}

.leave-request-info {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.82rem;
  min-width: 0;
  flex: 1;
}

.leave-request-info strong {
  color: var(--accent-color);
}

.leave-request-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.7rem;
  font-weight: 700;
  color: white;
  flex-shrink: 0;
}

.leave-request-actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}
</style>
