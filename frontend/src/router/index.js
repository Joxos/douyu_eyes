import { createRouter, createWebHistory } from 'vue-router'
import StatsView from '../views/StatsView.vue'
import SearchView from '../views/SearchView.vue'
import RandomView from '../views/RandomView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      redirect: '/stats'
    },
    {
      path: '/stats',
      name: 'stats',
      component: StatsView
    },
    {
      path: '/search',
      name: 'search',
      component: SearchView
    },
    {
      path: '/random',
      name: 'random',
      component: RandomView
    }
  ]
})

export default router
