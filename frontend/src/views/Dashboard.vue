<template>
  <div>
    <h1>服务器仪表盘</h1>
    <div v-if="error" class="error">
      <p>加载数据失败:</p>
      <pre>{{ error.message }}</pre>
    </div>
    <div v-else-if="!servers.length && !isLoading" class="no-servers">
      <p>还没有添加服务器。</p>
    </div>
    <div v-else class="server-list">
      <div v-for="server in servers" :key="server.id" class="server-card">
        <div class="card-header">
          <h2>{{ server.name }}</h2>
          <span class="server-model">{{ server.model }}</span>
        </div>
        <div class="card-body">
          <div class="info-row">
            <span>IPMI Host:</span>
            <span>{{ server.ipmi_host }}</span>
          </div>
          <div class="status-grid">
            <div class="status-item">
              <span class="status-label">温度</span>
              <span v-if="server.isLoadingStatus" class="status-value loading-text">加载中...</span>
              <span v-else class="status-value">{{ server.temperature ?? 'N/A' }} °C</span>
            </div>
            <div class="status-item">
              <span class="status-label">风扇转速</span>
              <span v-if="server.isLoadingStatus" class="status-value loading-text">加载中...</span>
              <span v-else class="status-value">{{ server.fan_speed ?? 'N/A' }} RPM</span>
            </div>
          </div>
        </div>
        <div class="card-footer">
          <router-link :to="{ name: 'ServerDetail', params: { id: server.id } }" class="details-link">
            管理与详情
          </router-link>
        </div>
      </div>
    </div>
    <div v-if="isLoading && !servers.length" class="loading">
      <p>正在从服务器加载设备列表...</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';

const servers = ref([]);
const isLoading = ref(true);
const error = ref(null);
let pollInterval;

const fetchServerStatus = async (server) => {
  server.isLoadingStatus = true;
  try {
    const [tempRes, fanRes] = await Promise.all([
      fetch(`/api/v1/control/${server.id}/temperature`),
      fetch(`/api/v1/control/${server.id}/fan/speed`),
    ]);

    if (tempRes.ok) {
      const tempData = await tempRes.json();
      server.temperature = tempData.temperature;
    } else {
      server.temperature = 'Error';
    }

    if (fanRes.ok) {
      const fanData = await fanRes.json();
      server.fan_speed = fanData.average_speed_rpm;
    } else {
      server.fan_speed = 'Error';
    }
  } catch (e) {
    console.error(`获取服务器 ${server.name} 状态失败`, e);
    server.temperature = 'Error';
    server.fan_speed = 'Error';
  } finally {
    server.isLoadingStatus = false;
  }
};

const fetchAllServerStatus = () => {
  servers.value.forEach(fetchServerStatus);
};

const fetchServers = async () => {
  isLoading.value = true;
  error.value = null;
  try {
    const response = await fetch('/api/v1/servers');
    if (!response.ok) {
      throw new Error(`HTTP 错误! 状态: ${response.status}`);
    }
    const serverData = await response.json();
    servers.value = serverData.map(s => ({
      ...s,
      temperature: null,
      fan_speed: null,
      isLoadingStatus: true,
    }));
    
    fetchAllServerStatus();
    // 设置定时轮询
    if (pollInterval) clearInterval(pollInterval);
    pollInterval = setInterval(fetchAllServerStatus, 10000); // 每 10 秒轮询一次

  } catch (e) {
    error.value = e;
  } finally {
    isLoading.value = false;
  }
};

onMounted(() => {
  fetchServers();
});

onUnmounted(() => {
  // 组件卸载时清除定时器
  if (pollInterval) {
    clearInterval(pollInterval);
  }
});
</script>

<style scoped>
.server-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 24px;
  padding: 20px;
}

.server-card {
  background: #2d3748;
  color: #f7fafc;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 4px 6px rgba(0,0,0,0.1);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.card-header {
  border-bottom: 1px solid #4a5568;
  padding-bottom: 12px;
  margin-bottom: 12px;
}

.card-header h2 {
  margin: 0;
  font-size: 1.25rem;
}

.server-model {
  font-size: 0.875rem;
  color: #a0aec0;
}

.info-row {
  display: flex;
  justify-content: space-between;
  font-size: 0.9rem;
  margin-bottom: 16px;
}

.status-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.status-item {
  background: #4a5568;
  padding: 12px;
  border-radius: 6px;
  text-align: center;
}

.status-label {
  display: block;
  font-size: 0.8rem;
  color: #a0aec0;
  margin-bottom: 8px;
}

.status-value {
  font-size: 1.2rem;
  font-weight: bold;
}

.loading-text {
  font-size: 0.9rem;
  font-weight: normal;
  color: #cbd5e0;
}

.card-footer {
  margin-top: 20px;
  text-align: right;
}

.details-link {
  background: #4299e1;
  color: white;
  padding: 8px 16px;
  border-radius: 6px;
  text-decoration: none;
  transition: background-color 0.2s;
}

.details-link:hover {
  background: #2b6cb0;
}

.error, .loading, .no-servers {
  color: #a0aec0;
  margin-top: 40px;
}
</style>