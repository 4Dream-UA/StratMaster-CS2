import { createRouter, createWebHistory } from 'vue-router'
import Home from '../pages/Home.vue'
import Strategy from '../pages/Strategy.vue'
import Strategies from '../pages/Strategies.vue'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: Home
  },
  {
    path: '/map/:id',
    name: 'Strategies',
    component: Strategies
  },
  {
    path: '/strategy/:id',
    name: 'Strategy',
    component: Strategy
  }
]

export const router = createRouter({
  history: createWebHistory(),
  routes
})