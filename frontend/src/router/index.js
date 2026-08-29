import { createRouter, createWebHistory } from 'vue-router'
import Home from '../pages/Home.vue'
import Strategy from '../pages/Strategy.vue'
import Strategies from '../pages/Strategies.vue'
import MyBoards from '../pages/MyBoards.vue'
import SharedBoard from '../pages/SharedBoard.vue'
import SharedThread from '../pages/SharedThread.vue'
import User from '../pages/User.vue'
import Cases from '../pages/Cases.vue'
import Forum from '../pages/Forum.vue'
import Pricing from '../pages/Pricing.vue'
import Admin from '../pages/Admin.vue'
import AdminMaps from '../pages/AdminMaps.vue'
import AdminStrategies from '../pages/AdminStrategies.vue'
import AdminUsers from '../pages/AdminUsers.vue'
import AdminPromo from '../pages/AdminPromo.vue'
import AdminTransactions from '../pages/AdminTransactions.vue'

const routes = [
  { path: '/', name: 'Home', component: Home },
  { path: '/map/:id', name: 'Strategies', component: Strategies },
  { path: '/strategy/:id', name: 'Strategy', component: Strategy },
  // My Strategies now lives inside the profile as a tab, not its own page.
  { path: '/my-strategies', redirect: { path: '/user', query: { tab: 'strategies' } } },
  { path: '/user', name: 'User', component: User },
  { path: '/boards', name: 'MyBoards', component: MyBoards },
  { path: '/shared-board/:token', name: 'SharedBoard', component: SharedBoard },
  { path: '/pricing', name: 'Pricing', component: Pricing },
  { path: '/cases', name: 'Cases', component: Cases },
  { path: '/forum', name: 'Forum', component: Forum },
  { path: '/forum/shared/:token', name: 'SharedThread', component: SharedThread },
  { path: '/admin', name: 'Admin', component: Admin },
  { path: '/admin/maps', name: 'AdminMaps', component: AdminMaps },
  { path: '/admin/strategies', name: 'AdminStrategies', component: AdminStrategies },
  { path: '/admin/users', name: 'AdminUsers', component: AdminUsers },
  { path: '/admin/promo', name: 'AdminPromo', component: AdminPromo },
  { path: '/admin/transactions', name: 'AdminTransactions', component: AdminTransactions },
  { path: '/admin/p2p', redirect: '/admin/transactions' },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) return savedPosition
    if (to.hash) return { el: to.hash, behavior: 'smooth' }
    return { top: 0 }
  },
})
