import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('@/views/HomeView.vue')
    },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue')
    },
    {
      path: '/register',
      name: 'register',
      component: () => import('@/views/RegisterView.vue')
    },
    {
      path: '/room/:roomCode',
      name: 'room',
      component: () => import('@/views/RoomView.vue')
    },
    {
      path: '/create-room',
      name: 'create-room',
      component: () => import('@/views/CreateRoomView.vue'),
      meta: { requiresAuth: true }
    },
    {
      path: '/profile',
      name: 'profile',
      component: () => import('@/views/ProfileView.vue'),
      meta: { requiresAuth: true }
    }
  ]
})

// 导航守卫
router.beforeEach((to, _from, next) => {
  const userStore = useUserStore()
  
  // 检查页面是否需要认证
  if (to.matched.some(record => record.meta.requiresAuth)) {
    // 检查用户是否登录
    if (!userStore.isLoggedIn) {
      // 未登录，重定向到登录页
      next({
        path: '/login',
        query: { redirect: to.fullPath }
      })
    } else {
      // 已登录，继续访问
      next()
    }
  } else {
    // 不需要认证的页面，直接访问
    next()
  }
})

export default router