<template>
  <div class="model-uploader">
    <div class="uploader-container">
      <div class="upload-header">
        <h3>海洋平台模型上传</h3>
        <p class="upload-description">
          上传STEP格式(.step, .stp)的3D模型文件，系统将自动解析并可视化
        </p>
      </div>
      
      <div class="upload-area" 
           :class="{ 'drag-over': isDragging, 'has-file': selectedFile }"
           @dragover.prevent="onDragOver"
           @dragleave.prevent="onDragLeave"
           @drop.prevent="onFileDrop">
        
        <div class="upload-icon">
          <i class="fas fa-cloud-upload-alt" v-if="!uploading"></i>
          <i class="fas fa-spinner fa-spin" v-else></i>
        </div>
        
        <div class="upload-text" v-if="!selectedFile">
          <p>拖放文件到此处或</p>
          <label for="file-input" class="upload-button">选择文件</label>
          <input 
            type="file" 
            id="file-input" 
            accept=".step,.stp" 
            @change="onFileSelected" 
            style="display: none"
          />
        </div>
        
        <div class="file-info" v-else>
          <p class="file-name">{{ selectedFile.name }}</p>
          <p class="file-size">{{ formatFileSize(selectedFile.size) }}</p>
          <div class="file-actions">
            <button class="upload-action-btn" @click="uploadFile" :disabled="uploading">
              {{ uploading ? '上传中...' : '上传' }}
            </button>
            <button class="cancel-action-btn" @click="cancelUpload" :disabled="uploading">
              取消
            </button>
          </div>
        </div>
      </div>
      
      <div class="upload-status" v-if="uploadStatus">
        <div class="status-icon" :class="uploadStatus.type">
          <i :class="uploadStatus.icon"></i>
        </div>
        <div class="status-message">{{ uploadStatus.message }}</div>
      </div>
      
      <div class="upload-progress" v-if="uploading">
        <div class="progress-bar">
          <div class="progress-fill" :style="{ width: uploadProgress + '%' }"></div>
        </div>
        <div class="progress-text">{{ uploadProgress }}%</div>
      </div>
      
      <div class="file-requirements">
        <h4>文件要求</h4>
        <ul>
          <li>支持的格式: STEP文件 (.step, .stp)</li>
          <li>最大文件大小: 100MB</li>
          <li>推荐使用标准CAD软件导出的STEP格式</li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, reactive } from 'vue';
import modelService from '@/services/modelService';

export default {
  name: 'ModelUploader',
  
  emits: ['model-uploaded'],
  
  setup(props, { emit }) {
    const selectedFile = ref(null);
    const isDragging = ref(false);
    const uploading = ref(false);
    const uploadProgress = ref(0);
    const uploadStatus = ref(null);
    
    // 处理文件拖拽
    const onDragOver = () => {
      isDragging.value = true;
    };
    
    const onDragLeave = () => {
      isDragging.value = false;
    };
    
    const onFileDrop = (event) => {
      isDragging.value = false;
      const files = event.dataTransfer.files;
      if (files.length > 0) {
        handleFile(files[0]);
      }
    };
    
    // 处理文件选择
    const onFileSelected = (event) => {
      const files = event.target.files;
      if (files.length > 0) {
        handleFile(files[0]);
      }
    };
    
    // 验证并处理文件
    const handleFile = (file) => {
      // 检查文件类型
      const validExtensions = ['.step', '.stp'];
      const fileExt = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
      
      if (!validExtensions.includes(fileExt)) {
        uploadStatus.value = {
          type: 'error',
          icon: 'fas fa-exclamation-circle',
          message: '不支持的文件格式，请上传STEP文件(.step, .stp)'
        };
        return;
      }
      
      // 检查文件大小 (100MB限制)
      const maxSize = 100 * 1024 * 1024;
      if (file.size > maxSize) {
        uploadStatus.value = {
          type: 'error',
          icon: 'fas fa-exclamation-circle',
          message: '文件过大，请上传小于100MB的文件'
        };
        return;
      }
      
      selectedFile.value = file;
      uploadStatus.value = null;
    };
    
    // 上传文件
    const uploadFile = async () => {
      if (!selectedFile.value) return;
      
      uploading.value = true;
      uploadProgress.value = 0;
      uploadStatus.value = null;
      
      try {
        // 创建FormData对象
        const formData = new FormData();
        formData.append('model_file', selectedFile.value);
        
        // 模拟上传进度
        const progressInterval = setInterval(() => {
          if (uploadProgress.value < 90) {
            uploadProgress.value += Math.floor(Math.random() * 10) + 1;
          }
        }, 300);
        
        // 调用上传API
        const response = await modelService.uploadModel(selectedFile.value);
        
        // 清除进度模拟
        clearInterval(progressInterval);
        uploadProgress.value = 100;
        
        // 处理上传成功
        uploadStatus.value = {
          type: 'success',
          icon: 'fas fa-check-circle',
          message: '模型上传成功！'
        };
        
        // 通知父组件
        emit('model-uploaded', response);
        
        // 延迟重置上传状态
        setTimeout(() => {
          uploading.value = false;
          selectedFile.value = null;
        }, 2000);
        
      } catch (error) {
        console.error('上传失败:', error);
        
        uploadStatus.value = {
          type: 'error',
          icon: 'fas fa-exclamation-circle',
          message: `上传失败: ${error.message || '未知错误'}`
        };
        
        uploading.value = false;
      }
    };
    
    // 取消上传
    const cancelUpload = () => {
      selectedFile.value = null;
      uploadStatus.value = null;
    };
    
    // 格式化文件大小
    const formatFileSize = (bytes) => {
      if (bytes === 0) return '0 Bytes';
      
      const k = 1024;
      const sizes = ['Bytes', 'KB', 'MB', 'GB'];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    };
    
    return {
      selectedFile,
      isDragging,
      uploading,
      uploadProgress,
      uploadStatus,
      onDragOver,
      onDragLeave,
      onFileDrop,
      onFileSelected,
      uploadFile,
      cancelUpload,
      formatFileSize
    };
  }
};
</script>

<style scoped>
.model-uploader {
  width: 100%;
  padding: 1rem;
  background-color: #f8f9fa;
  border-radius: 8px;
}

.uploader-container {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.upload-header {
  text-align: center;
  margin-bottom: 1rem;
}

.upload-header h3 {
  font-size: 1.5rem;
  color: #2c3e50;
  margin-bottom: 0.5rem;
}

.upload-description {
  color: #6c757d;
  font-size: 0.9rem;
}

.upload-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2rem;
  border: 2px dashed #ced4da;
  border-radius: 8px;
  background-color: #fff;
  transition: all 0.3s ease;
  min-height: 200px;
}

.upload-area.drag-over {
  border-color: #0077ff;
  background-color: rgba(0, 119, 255, 0.05);
}

.upload-area.has-file {
  border-color: #28a745;
}

.upload-icon {
  font-size: 3rem;
  color: #6c757d;
  margin-bottom: 1rem;
}

.upload-text {
  text-align: center;
}

.upload-button {
  display: inline-block;
  padding: 0.5rem 1rem;
  background-color: #0077ff;
  color: white;
  border-radius: 4px;
  cursor: pointer;
  margin-top: 0.5rem;
  transition: background-color 0.3s;
}

.upload-button:hover {
  background-color: #0056b3;
}

.file-info {
  text-align: center;
  width: 100%;
}

.file-name {
  font-weight: bold;
  margin-bottom: 0.25rem;
  word-break: break-all;
}

.file-size {
  color: #6c757d;
  font-size: 0.9rem;
  margin-bottom: 1rem;
}

.file-actions {
  display: flex;
  justify-content: center;
  gap: 1rem;
}

.upload-action-btn, .cancel-action-btn {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.upload-action-btn {
  background-color: #28a745;
  color: white;
}

.upload-action-btn:hover {
  background-color: #218838;
}

.upload-action-btn:disabled {
  background-color: #6c757d;
  cursor: not-allowed;
}

.cancel-action-btn {
  background-color: #dc3545;
  color: white;
}

.cancel-action-btn:hover {
  background-color: #c82333;
}

.cancel-action-btn:disabled {
  background-color: #6c757d;
  cursor: not-allowed;
}

.upload-status {
  display: flex;
  align-items: center;
  padding: 0.75rem;
  border-radius: 4px;
  background-color: #f8f9fa;
}

.status-icon {
  margin-right: 0.75rem;
  font-size: 1.25rem;
}

.status-icon.success {
  color: #28a745;
}

.status-icon.error {
  color: #dc3545;
}

.upload-progress {
  width: 100%;
  margin-top: 0.5rem;
}

.progress-bar {
  height: 8px;
  background-color: #e9ecef;
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background-color: #0077ff;
  transition: width 0.3s ease;
}

.progress-text {
  text-align: right;
  font-size: 0.8rem;
  color: #6c757d;
  margin-top: 0.25rem;
}

.file-requirements {
  margin-top: 1rem;
  padding: 1rem;
  background-color: #fff;
  border-radius: 4px;
  border-left: 4px solid #0077ff;
}

.file-requirements h4 {
  margin-bottom: 0.5rem;
  color: #2c3e50;
}

.file-requirements ul {
  padding-left: 1.5rem;
  margin: 0;
}

.file-requirements li {
  margin-bottom: 0.25rem;
  color: #6c757d;
}
</style>
