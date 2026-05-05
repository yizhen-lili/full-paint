import { createApp } from 'vue'
import { VueQueryPlugin } from '@tanstack/vue-query'
import App from './App.vue'
import { router } from './app/router'
import { pinia } from './app/pinia'
import { queryClient } from './app/query'
import { useAuthStore } from './features/auth/store'
import './style.css'

const app = createApp(App)
app.use(pinia)
app.use(VueQueryPlugin, { queryClient })
app.use(router)
app.mount('#app')

// Fire-and-forget auth bootstrap. Guards observe useAuthStore().bootstrapped.
// 401 (visitor) is treated as success; other failures logged but do not block UI.
const auth = useAuthStore()
auth.fetchMe()
