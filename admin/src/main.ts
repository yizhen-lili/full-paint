import { createApp } from 'vue'

import App from './App.vue'
import { pinia } from './app/pinia'
import { VueQueryPlugin, vueQueryPluginOptions } from './app/query'
import { router } from './app/router'
import './style.css'

const app = createApp(App)

app.use(pinia)
app.use(router)
app.use(VueQueryPlugin, vueQueryPluginOptions)

app.mount('#app')
