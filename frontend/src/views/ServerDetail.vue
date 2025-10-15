<template>
  <div>
    <h1>服务器详情</h1>
    <p>这里将显示 ID 为 {{ id }} 的服务器的详细信息和控制选项。</p>
  </div>
</template>

<script>
export default {
  name: 'ServerDetail',
  props: ['id'],
};
</script>