<template>
  <div class="dashboard">
    <!-- 顶部标题栏 -->
    <div class="header-bar">
      <h1 class="page-title">服务器仪表盘</h1>
      <div class="header-actions">
        <button @click="refreshData" class="refresh-btn">
          <span class="refresh-icon">🔄</span>
          刷新
        </button>
        <button @click="showAddServerDialog" class="add-server-btn">
          <span class="btn-icon">➕</span>
          添加服务器
        </button>
      </div>
    </div>

    <!-- 错误提示 -->
    <div v-if="error" class="error-banner">
      <span class="error-icon">⚠️</span>
      <span>{{ error.message }}</span>
      <button @click="error = null" class="close-error">✕</button>
    </div>

    <!-- 无服务器提示 -->
    <div v-else-if="!servers.length && !isLoading" class="empty-state">
      <div class="empty-icon">📋</div>
      <h3>还没有添加服务器</h3>
      <p>点击右上角的管理按钮添加您的第一台服务器</p>
    </div>

    <!-- 服务器列表 -->
    <div v-else class="server-grid">
      <div v-for="server in servers" :key="server.id" class="server-card">
        <div class="card-header">
          <div class="server-info">
            <h2 class="server-name">{{ server.name }}</h2>
            <span class="model-badge">{{ server.model }}</span>
          </div>
          <div class="connection-status">
            <span class="status-indicator" :class="server.connectionStatus"></span>
          </div>
        </div>

        <div class="card-body">
          <div class="metrics-grid">
            <div class="metric-item">
              <div class="metric-icon">🌡️</div>
              <div class="metric-content">
                <div class="metric-label">CPU温度</div>
                <div v-if="server.isLoadingStatus" class="metric-value loading">加载中...</div>
                <div v-else class="metric-value">{{ server.temperature ?? 'N/A' }}°C</div>
              </div>
            </div>
            
            <div class="metric-item">
              <div class="metric-icon">🌀</div>
              <div class="metric-content">
                <div class="metric-label">风扇转速</div>
                <div v-if="server.isLoadingStatus" class="metric-value loading">加载中...</div>
                <div v-else class="metric-value">{{ server.fan_speed ?? 'N/A' }} RPM</div>
              </div>
            </div>
          </div>

          <div class="server-details">
            <div class="detail-row">
              <span class="detail-label">IPMI主机:</span>
              <span class="detail-value">{{ server.ipmi_host }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">控制模式:</span>
              <span class="detail-value">{{ server.control_mode === 'manual' ? '手动' : '自动' }}</span>
            </div>
          </div>
        </div>

        <div class="card-footer">
          <div class="card-actions">
            <router-link :to="{ name: 'ServerDetail', params: { id: server.id } }" class="detail-btn">
              <span class="btn-icon">⚙️</span>
              管理详情
            </router-link>
            <button @click="showEditServerDialog(server)" class="edit-btn">
              <span class="btn-icon">✏️</span>
              编辑
            </button>
            <button @click="deleteServer(server)" class="delete-btn">
              <span class="btn-icon">🗑️</span>
              删除
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="isLoading && !servers.length" class="loading-state">
      <div class="loading-spinner"></div>
      <p>正在加载服务器列表...</p>
    </div>
  </div>

  <!-- 添加/编辑服务器对话框 -->
  <div v-if="showDialog" class="dialog-overlay" @click="closeDialog">
    <div class="dialog-content" @click.stop>
      <div class="dialog-header">
        <h3>{{ isEditing ? '编辑服务器' : '添加服务器' }}</h3>
        <button @click="closeDialog" class="close-dialog">✕</button>
      </div>
      
      <form @submit.prevent="saveServer" class="dialog-form">
        <div class="form-group">
          <label for="serverName">服务器名称</label>
          <input
            id="serverName"
            v-model="serverForm.name"
            type="text"
            required
            placeholder="例如: R730-服务器1"
            class="form-input"
          >
        </div>
        
        <div class="form-group">
          <label for="serverModel">服务器型号</label>
          <select
            id="serverModel"
            v-model="serverForm.model"
            required
            class="form-input"
          >
            <option value="">请选择型号</option>
            <option value="r730">Dell PowerEdge R730</option>
            <option value="r4900g3">H3C R4900 G3</option>
          </select>
        </div>
        
        <div class="form-group">
          <label for="ipmiHost">IPMI主机地址</label>
          <input
            id="ipmiHost"
            v-model="serverForm.ipmi_host"
            type="text"
            required
            placeholder="例如: 192.168.1.100"
            class="form-input"
          >
        </div>
        
        <div class="form-group">
          <label for="ipmiUser">IPMI用户名</label>
          <input
            id="ipmiUser"
            v-model="serverForm.ipmi_user"
            type="text"
            required
            placeholder="例如: admin"
            class="form-input"
          >
        </div>
        
        <div class="form-group">
          <label for="ipmiPass">IPMI密码</label>
          <input
            id="ipmiPass"
            v-model="serverForm.ipmi_password"
            type="password"
            required
            placeholder="请输入密码"
            class="form-input"
          >
        </div>
        
        <div class="dialog-actions">
          <button type="button" @click="closeDialog" class="cancel-btn">
            取消
          </button>
          <button type="submit" class="save-btn" :disabled="isSaving">
            {{ isSaving ? '保存中...' : (isEditing ? '更新' : '添加') }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import { ElNotification } from 'element-plus';

const servers = ref([]);
const isLoading = ref(true);
const error = ref(null);
const showDialog = ref(false);
const isEditing = ref(false);
const isSaving = ref(false);
const editingServer = ref(null);

const serverForm = ref({
  name: '',
  model: '',
  ipmi_host: '',
  ipmi_user: '',
  ipmi_password: ''
});

let pollInterval;

const showNotification = (message, type = 'success', title = '') => {
  const icons = {
    success: '✅',
    warning: '⚠️',
    error: '❌',
    info: 'ℹ️'
  };
  
  ElNotification({
    title: title || (type === 'success' ? '成功' : type === 'error' ? '错误' : '提示'),
    message: message,
    type: type,
    icon: icons[type],
    duration: 3000,
    position: 'top-right'
  });
};

const refreshData = () => {
  fetchServers();
};

const showAddServerDialog = () => {
  isEditing.value = false;
  editingServer.value = null;
  serverForm.value = {
    name: '',
    model: '',
    ipmi_host: '',
    ipmi_user: '',
    ipmi_password: ''
  };
  showDialog.value = true;
};

const showEditServerDialog = (server) => {
  isEditing.value = true;
  editingServer.value = server;
  serverForm.value = {
    name: server.name,
    model: server.model,
    ipmi_host: server.ipmi_host,
    ipmi_user: server.ipmi_user,
    ipmi_password: '' // 密码不显示，需要重新输入
  };
  showDialog.value = true;
};

const closeDialog = () => {
  showDialog.value = false;
  isEditing.value = false;
  editingServer.value = null;
};

const saveServer = async () => {
  isSaving.value = true;
  try {
    const url = isEditing.value
      ? `/api/v1/servers/${editingServer.value.id}`
      : '/api/v1/servers';
    
    const method = isEditing.value ? 'PUT' : 'POST';
    
    const response = await fetch(url, {
      method: method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(serverForm.value)
    });
    
    if (response.ok) {
      showNotification(
        isEditing.value ? '服务器信息已更新' : '服务器添加成功',
        'success'
      );
      closeDialog();
      await fetchServers();
    } else {
      const errorData = await response.json();
      throw new Error(errorData.detail || '操作失败');
    }
  } catch (e) {
    showNotification(e.message, 'error');
  } finally {
    isSaving.value = false;
  }
};

const deleteServer = async (server) => {
  if (!confirm(`确定要删除服务器 "${server.name}" 吗？此操作不可恢复。`)) {
    return;
  }
  
  try {
    const response = await fetch(`/api/v1/servers/${server.id}`, {
      method: 'DELETE'
    });
    
    if (response.ok) {
      showNotification('服务器已删除', 'success');
      await fetchServers();
    } else {
      throw new Error('删除失败');
    }
  } catch (e) {
    showNotification(e.message, 'error');
  }
};

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
      server.connectionStatus = 'connected';
    } else {
      server.temperature = 'Error';
      server.connectionStatus = 'disconnected';
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
    server.connectionStatus = 'disconnected';
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
      connectionStatus: 'disconnected',
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
.dashboard {
  height: 100vh;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
  color: #ffffff;
  padding: 20px;
  box-sizing: border-box;
  overflow: hidden;
}

/* 顶部标题栏 */
.header-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(10px);
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 20px;
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.page-title {
  margin: 0;
  font-size: 1.8em;
  color: #ffffff;
}

.header-actions {
  display: flex;
  gap: 15px;
}

.refresh-btn {
  background: rgba(233, 69, 96, 0.2);
  color: #e94560;
  border: 1px solid #e94560;
  padding: 8px 16px;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
}

.refresh-icon {
  font-size: 1.2em;
}

/* 错误横幅 */
.error-banner {
  background: rgba(255, 0, 0, 0.2);
  color: #ff6b6b;
  padding: 15px;
  border-radius: 8px;
  margin-bottom: 20px;
  display: flex;
  align-items: center;
  gap: 10px;
  border: 1px solid rgba(255, 0, 0, 0.3);
}

.close-error {
  background: none;
  border: none;
  color: #ff6b6b;
  font-size: 1.2em;
  cursor: pointer;
  margin-left: auto;
}

/* 空状态 */
.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #a0aec0;
}

.empty-icon {
  font-size: 4em;
  margin-bottom: 20px;
  opacity: 0.6;
}

.empty-state h3 {
  color: #ffffff;
  margin-bottom: 10px;
  font-size: 1.5em;
}

/* 服务器网格 */
.server-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 20px;
  max-height: calc(100vh - 120px);
  overflow-y: auto;
  padding-right: 4px;
  align-content: start;
}

/* 服务器卡片 */
.server-card {
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(10px);
  border-radius: 12px;
  padding: 20px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  display: flex;
  flex-direction: column;
  gap: 15px;
  transition: transform 0.2s, box-shadow 0.2s;
  min-height: 280px;
  max-height: 320px;
}

.server-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 5px;
}

.server-info {
  flex: 1;
}

.server-name {
  margin: 0;
  font-size: 1.3em;
  color: #ffffff;
  margin-bottom: 5px;
}

.model-badge {
  background: linear-gradient(45deg, #e94560, #ff6b6b);
  color: white;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 0.8em;
  font-weight: 500;
}

.connection-status {
  display: flex;
  align-items: center;
}

.status-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #ef4444;
}

.status-indicator.connected {
  background: #4ade80;
}

/* 指标网格 */
.metrics-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 15px;
  margin-bottom: 15px;
}

.metric-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.05);
  border-radius: 8px;
}

.metric-icon {
  font-size: 1.5em;
  opacity: 0.8;
}

.metric-content {
  flex: 1;
}

.metric-label {
  font-size: 0.8em;
  color: #a0aec0;
  margin-bottom: 2px;
}

.metric-value {
  font-size: 1.1em;
  font-weight: bold;
  color: #4ade80;
}

.metric-value.loading {
  color: #cbd5e0;
  font-size: 0.9em;
}

/* 服务器详情 */
.server-details {
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  padding-top: 15px;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  font-size: 0.9em;
}

.detail-label {
  color: #a0aec0;
}

.detail-value {
  color: #ffffff;
  font-weight: 500;
}

/* 卡片底部 */
.card-footer {
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  padding-top: 15px;
  text-align: right;
}

.detail-btn {
  background: linear-gradient(45deg, #4299e1, #60a5fa);
  color: white;
  padding: 8px 16px;
  border-radius: 8px;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
  transition: all 0.2s;
}

.detail-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(66, 153, 225, 0.3);
}

.btn-icon {
  font-size: 1.1em;
}

/* 加载状态 */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: calc(100vh - 120px);
  color: #a0aec0;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid rgba(255, 255, 255, 0.1);
  border-top: 3px solid #e94560;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 20px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* 添加服务器按钮 */
.add-server-btn {
  background: linear-gradient(45deg, #38a169, #4ade80);
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
  transition: all 0.2s;
}

.add-server-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(56, 161, 105, 0.3);
}

/* 卡片操作按钮 */
.card-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.edit-btn, .delete-btn {
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  color: #ffffff;
  padding: 6px 12px;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.9em;
  transition: all 0.2s;
}

.edit-btn:hover {
  background: rgba(66, 153, 225, 0.3);
  border-color: #4299e1;
}

.delete-btn:hover {
  background: rgba(239, 68, 68, 0.3);
  border-color: #ef4444;
}

/* 对话框样式 */
.dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(5px);
}

.dialog-content {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
  border-radius: 12px;
  padding: 0;
  border: 1px solid rgba(255, 255, 255, 0.2);
  width: 90%;
  max-width: 500px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5);
}

.dialog-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.dialog-header h3 {
  margin: 0;
  color: #ffffff;
  font-size: 1.3em;
}

.close-dialog {
  background: none;
  border: none;
  color: #a0aec0;
  font-size: 1.5em;
  cursor: pointer;
  padding: 0;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: all 0.2s;
}

.close-dialog:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #ffffff;
}

.dialog-form {
  padding: 20px;
}

.form-group {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
  gap: 15px;
}

.form-group label {
  flex-shrink: 0;
  width: 100px; /* 控制左边长度 */
  text-align: right;
  color: #cbd5e0; /* 调亮字体颜色 */
  font-weight: 500;
  font-size: 0.9em;
}

.form-input {
  width: 100%;
  padding: 12px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  color: #ffffff;
  font-size: 1em;
  transition: all 0.2s;
}

.form-input:focus {
  outline: none;
  border-color: #e94560;
  background: rgba(255, 255, 255, 0.08);
}

.form-input::placeholder {
  color: #a0aec0; /* 调整占位符颜色 */
  opacity: 0.8;
}

select.form-input {
  cursor: pointer;
}

select.form-input option {
  background: #16213e; /* 为下拉选项添加深色背景 */
  color: #ffffff;
}

.dialog-actions {
  display: flex;
  gap: 15px;
  justify-content: flex-end;
  margin-top: 30px;
}

.cancel-btn, .save-btn {
  padding: 12px 24px;
  border-radius: 8px;
  border: none;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.2s;
}

.cancel-btn {
  background: rgba(255, 255, 255, 0.1);
  color: #a0aec0;
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.cancel-btn:hover {
  background: rgba(255, 255, 255, 0.15);
  color: #ffffff;
}

.save-btn {
  background: linear-gradient(45deg, #38a169, #4ade80);
  color: white;
}

.save-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(56, 161, 105, 0.3);
}

.save-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 滚动条样式 - iOS风格 */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 3px;
  border: none;
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.3);
}

::-webkit-scrollbar-corner {
  background: transparent;
}

.server-grid {
  scrollbar-width: thin;
  scrollbar-color: rgba(255, 255, 255, 0.2) transparent;
}

.server-grid::-webkit-scrollbar {
  width: 4px;
}

.server-grid::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.15);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .server-grid {
    grid-template-columns: 1fr;
    gap: 15px;
  }
  
  .metrics-grid {
    grid-template-columns: 1fr;
  }
  
  .header-bar {
    flex-direction: column;
    gap: 15px;
  }
  
  .card-actions {
    flex-direction: column;
  }
  
  .dialog-content {
    width: 95%;
    margin: 20px;
  }
}
</style>