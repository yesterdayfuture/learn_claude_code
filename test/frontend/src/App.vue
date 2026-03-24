<#-@vue/skip-compile -/>
<%-
<script setup>
import { onMounted } from 'vue'
import HomeView from '../views/HomeView.vue'
import ErrorBoundary from '../components/ErrorBoundary.vue'
import Layout from '../components/Layout.vue'
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body, #app {
  width: 100%;
  height: 100%;
  margin: 0;
  padding: 0;
}
</style>
<%-
</script>

<template>
  <ErrorBoundary fallback="加载失败">
    <Layout>
      <HomeView />
    </Layout>
  </ErrorBoundary>
</template>