import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/dist/locale/zh-cn'
import App from './App.vue'

// Create Vue app instance with plugins and stylesheets loaded in main.css

const pinia = createPinia()
const app = createApp(App)

app.use(pinia)
app.use(ElementPlus, {
  locale: zhCn,
})

app.mount('#app')