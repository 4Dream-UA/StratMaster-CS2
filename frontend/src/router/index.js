import { createRouter, createWebHistory } from 'vue-router'
import Home from '../pages/Home.vue'
import Strategy from '../pages/Strategy.vue'
import Strategies from '../pages/Strategies.vue'
import User from '../pages/User.vue'
import Pricing from '../pages/Pricing.vue'
import Admin from '../pages/Admin.vue'
import AdminSection from '../pages/AdminSection.vue'
import AdminMaps from '../pages/AdminMaps.vue'
import AdminStrategies from '../pages/AdminStrategies.vue'
import AdminUsers from '../pages/AdminUsers.vue'
import AdminPromo from '../pages/AdminPromo.vue'

const routes = [
  { path: '/', name: 'Home', component: Home },
  { path: '/map/:id', name: 'Strategies', component: Strategies },
  { path: '/strategy/:id', name: 'Strategy', component: Strategy },
  { path: '/user', name: 'User', component: User },
  { path: '/pricing', name: 'Pricing', component: Pricing },
  { path: '/admin', name: 'Admin', component: Admin },
  { path: '/admin/maps', name: 'AdminMaps', component: AdminMaps },
  { path: '/admin/strategies', name: 'AdminStrategies', component: AdminStrategies },
  { path: '/admin/users', name: 'AdminUsers', component: AdminUsers },
  { path: '/admin/promo', name: 'AdminPromo', component: AdminPromo },
  { path: '/admin/p2p', name: 'AdminP2P', component: AdminSection, meta: { sectionKey: 'p2p' } },
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
