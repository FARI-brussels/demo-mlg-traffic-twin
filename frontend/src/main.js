import { createApp } from 'vue'
import { createRouter, createWebHashHistory } from 'vue-router'
import App from './App.vue'
import GenerateSimulation from './views/GenerateSimulation.vue'
import ResultView from './views/ResultView.vue'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/', component: GenerateSimulation },
    { path: '/results', component: ResultView }
  ]
})

createApp(App).use(router).mount('#app') 