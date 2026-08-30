import { createRouter, createWebHistory } from 'vue-router'
import Home from '../pages/Home.vue'
import Strategy from '../pages/Strategy.vue'
import Strategies from '../pages/Strategies.vue'
import SharedBoard from '../pages/SharedBoard.vue'
import SharedThread from '../pages/SharedThread.vue'
import User from '../pages/User.vue'
import Forum from '../pages/Forum.vue'
import Pricing from '../pages/Pricing.vue'
import Admin from '../pages/Admin.vue'
import AdminMaps from '../pages/AdminMaps.vue'
import AdminStrategies from '../pages/AdminStrategies.vue'
import AdminUsers from '../pages/AdminUsers.vue'
import AdminPromo from '../pages/AdminPromo.vue'
import AdminTransactions from '../pages/AdminTransactions.vue'
import Legal from '../pages/Legal.vue'

const routes = [
  { path: '/', name: 'Home', component: Home },
  { path: '/map/:id', name: 'Strategies', component: Strategies },
  { path: '/strategy/:id', name: 'Strategy', component: Strategy },
  // My Strategies / My Board / Cases now live inside the profile as tabs,
  // not their own pages — old links redirect straight to the right tab
  // (Cases also forwards a `sub` query so e.g. an offer notification can
  // deep-link into the Offers sub-view).
  { path: '/my-strategies', redirect: { path: '/user', query: { tab: 'strategies' } } },
  { path: '/boards', redirect: { path: '/user', query: { tab: 'board' } } },
  { path: '/cases', redirect: (to) => ({ path: '/user', query: { tab: 'cases', sub: to.query.tab } }) },
  { path: '/user', name: 'User', component: User },
  { path: '/shared-board/:token', name: 'SharedBoard', component: SharedBoard },
  { path: '/pricing', name: 'Pricing', component: Pricing },
  { path: '/forum', name: 'Forum', component: Forum },
  { path: '/forum/shared/:token', name: 'SharedThread', component: SharedThread },
  { path: '/admin', name: 'Admin', component: Admin },
  { path: '/admin/maps', name: 'AdminMaps', component: AdminMaps },
  { path: '/admin/strategies', name: 'AdminStrategies', component: AdminStrategies },
  { path: '/admin/users', name: 'AdminUsers', component: AdminUsers },
  { path: '/admin/promo', name: 'AdminPromo', component: AdminPromo },
  { path: '/admin/transactions', name: 'AdminTransactions', component: AdminTransactions },
  { path: '/admin/p2p', redirect: '/admin/transactions' },
  { path: '/terms', name: 'Terms', component: Legal },
  { path: '/privacy', name: 'Privacy', component: Legal },
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
