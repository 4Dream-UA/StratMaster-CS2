import { createRouter, createWebHistory } from 'vue-router'
import Home from '../pages/Home.vue'

// Home is the landing route for essentially every session, so it stays in
// the main bundle. Everything else is split out: the admin pages alone are
// a large slice of the app that no ordinary player ever loads, and on a
// phone over mobile data the whole thing arriving up front is the single
// biggest thing standing between tapping the bot and seeing the app.
const Strategy = () => import('../pages/Strategy.vue')
const Strategies = () => import('../pages/Strategies.vue')
const SharedBoard = () => import('../pages/SharedBoard.vue')
const SharedThread = () => import('../pages/SharedThread.vue')
const User = () => import('../pages/User.vue')
const Forum = () => import('../pages/Forum.vue')
const Pricing = () => import('../pages/Pricing.vue')
const Admin = () => import('../pages/Admin.vue')
const AdminMaps = () => import('../pages/AdminMaps.vue')
const AdminStrategies = () => import('../pages/AdminStrategies.vue')
const AdminUsers = () => import('../pages/AdminUsers.vue')
const AdminPromo = () => import('../pages/AdminPromo.vue')
const AdminTransactions = () => import('../pages/AdminTransactions.vue')
const Legal = () => import('../pages/Legal.vue')

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
