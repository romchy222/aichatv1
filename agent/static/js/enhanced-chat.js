// Enhanced AI Chat Assistant with Multimodal Support
let currentSessionId = null;
let currentProject = null;
let messageHistory = [];
let isTyping = false;
let currentTheme = 'light';
let mediaRecorder = null;
let recordingChunks = [];
let isRecording = false;

// Initialize enhanced chat application
document.addEventListener('DOMContentLoaded', function() {
    initializeEnhancedChat();
    setupEnhancedEventListeners();
    loadProjects();
    loadChatHistory();
});

// Initialize enhanced chat functionality
function initializeEnhancedChat() {
    currentSessionId = localStorage.getItem('sessionId');
    if (!currentSessionId) {
        currentSessionId = generateSessionId();
        localStorage.setItem('sessionId', currentSessionId);
    }
    
    currentProject = localStorage.getItem('currentProject');
    currentTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', currentTheme);
    
    // Initialize voice recording capabilities
    initializeVoiceRecording();
    
    // Initialize drag and drop for files
    initializeDragAndDrop();
}

// Setup enhanced event listeners
function setupEnhancedEventListeners() {
    // Existing chat form and FAQ search
    const chatForm = document.getElementById('chat-form');
    chatForm.addEventListener('submit', handleEnhancedChatSubmit);
    
    const faqSearch = document.getElementById('faq-search');
    faqSearch.addEventListener('input', debounce(handleFAQSearch, 300));
    
    // Voice recording button
    const voiceButton = document.getElementById('voice-record-btn');
    if (voiceButton) {
        voiceButton.addEventListener('click', toggleVoiceRecording);
    }
    
    // File attachment button
    const fileButton = document.getElementById('file-attach-btn');
    const fileInput = document.getElementById('file-input');
    if (fileButton && fileInput) {
        fileButton.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', handleFileAttachment);
    }
    
    // Project selector
    const projectSelector = document.getElementById('project-selector');
    if (projectSelector) {
        projectSelector.addEventListener('change', handleProjectChange);
    }
    
    // New project button
    const newProjectBtn = document.getElementById('new-project-btn');
    if (newProjectBtn) {
        newProjectBtn.addEventListener('click', showNewProjectModal);
    }
    
    // Export chat button
    const exportBtn = document.getElementById('export-chat-btn');
    if (exportBtn) {
        exportBtn.addEventListener('click', showExportModal);
    }
    
    // Search history button
    const searchBtn = document.getElementById('search-history-btn');
    if (searchBtn) {
        searchBtn.addEventListener('click', showSearchModal);
    }
}

// Voice Recording Functions
function initializeVoiceRecording() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        console.warn('Voice recording not supported in this browser');
        const voiceButton = document.getElementById('voice-record-btn');
        if (voiceButton) {
            voiceButton.style.display = 'none';
        }
        return;
    }
}

async function toggleVoiceRecording() {
    if (!isRecording) {
        await startVoiceRecording();
    } else {
        await stopVoiceRecording();
    }
}

async function startVoiceRecording() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ 
            audio: { 
                echoCancellation: true,
                noiseSuppression: true,
                sampleRate: 44100
            } 
        });
        
        mediaRecorder = new MediaRecorder(stream, { 
            mimeType: 'audio/webm;codecs=opus' 
        });
        
        recordingChunks = [];
        
        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                recordingChunks.push(event.data);
            }
        };
        
        mediaRecorder.onstop = async () => {
            const audioBlob = new Blob(recordingChunks, { type: 'audio/webm' });
            await processVoiceMessage(audioBlob);
            
            // Stop all tracks
            stream.getTracks().forEach(track => track.stop());
        };
        
        mediaRecorder.start(100); // Collect data every 100ms
        isRecording = true;
        
        updateVoiceButton(true);
        showVoiceRecordingIndicator();
        
    } catch (error) {
        console.error('Error starting voice recording:', error);
        showError('Не удалось начать запись голоса. Проверьте разрешения микрофона.');
    }
}

async function stopVoiceRecording() {
    if (mediaRecorder && isRecording) {
        mediaRecorder.stop();
        isRecording = false;
        updateVoiceButton(false);
        hideVoiceRecordingIndicator();
    }
}

function updateVoiceButton(recording) {
    const voiceButton = document.getElementById('voice-record-btn');
    if (voiceButton) {
        if (recording) {
            voiceButton.innerHTML = '<i class="fas fa-stop"></i>';
            voiceButton.classList.add('recording');
            voiceButton.title = 'Остановить запись';
        } else {
            voiceButton.innerHTML = '<i class="fas fa-microphone"></i>';
            voiceButton.classList.remove('recording');
            voiceButton.title = 'Начать голосовую запись';
        }
    }
}

function showVoiceRecordingIndicator() {
    const indicator = document.createElement('div');
    indicator.id = 'voice-indicator';
    indicator.className = 'voice-recording-indicator';
    indicator.innerHTML = `
        <div class="pulse-animation"></div>
        <span>Идёт запись голоса...</span>
    `;
    
    const chatContainer = document.querySelector('.chat-container');
    if (chatContainer) {
        chatContainer.appendChild(indicator);
    }
}

function hideVoiceRecordingIndicator() {
    const indicator = document.getElementById('voice-indicator');
    if (indicator) {
        indicator.remove();
    }
}

async function processVoiceMessage(audioBlob) {
    try {
        showTypingIndicator('Обрабатываю голосовое сообщение...');
        
        // Create FormData for file upload
        const formData = new FormData();
        formData.append('audio', audioBlob, 'voice-message.webm');
        formData.append('session_id', currentSessionId);
        formData.append('project_id', currentProject || '');
        
        const response = await fetch('/api/voice/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: formData
        });
        
        const data = await response.json();
        
        hideTypingIndicator();
        
        if (data.success) {
            // Add voice message to UI
            addVoiceMessageToUI(audioBlob, data.transcription);
            
            // Add AI response if provided
            if (data.ai_response) {
                addMessageToUI(data.ai_response, 'assistant');
            }
        } else {
            showError('Ошибка обработки голосового сообщения: ' + (data.error || 'Неизвестная ошибка'));
        }
        
    } catch (error) {
        hideTypingIndicator();
        console.error('Voice processing error:', error);
        showError('Не удалось обработать голосовое сообщение');
    }
}

function addVoiceMessageToUI(audioBlob, transcription) {
    const audioUrl = URL.createObjectURL(audioBlob);
    const messageContainer = document.getElementById('messages-container');
    
    const messageElement = document.createElement('div');
    messageElement.className = 'message user-message voice-message';
    
    messageElement.innerHTML = `
        <div class="message-avatar">
            <i class="fas fa-user"></i>
        </div>
        <div class="message-content">
            <div class="voice-player">
                <audio controls>
                    <source src="${audioUrl}" type="audio/webm">
                    Ваш браузер не поддерживает воспроизведение аудио.
                </audio>
                <div class="voice-duration">
                    <i class="fas fa-microphone"></i>
                    Голосовое сообщение
                </div>
            </div>
            ${transcription ? `<div class="transcription">📝 ${transcription}</div>` : ''}
            <div class="message-time">${formatTime(new Date())}</div>
        </div>
    `;
    
    messageContainer.appendChild(messageElement);
    scrollToBottom();
}

// File Attachment Functions
function initializeDragAndDrop() {
    const chatContainer = document.querySelector('.chat-container');
    
    if (!chatContainer) return;
    
    // Prevent default drag behaviors
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        chatContainer.addEventListener(eventName, preventDefaults, false);
    });
    
    // Highlight drop area
    ['dragenter', 'dragover'].forEach(eventName => {
        chatContainer.addEventListener(eventName, highlight, false);
    });
    
    ['dragleave', 'drop'].forEach(eventName => {
        chatContainer.addEventListener(eventName, unhighlight, false);
    });
    
    // Handle dropped files
    chatContainer.addEventListener('drop', handleDrop, false);
    
    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    function highlight() {
        chatContainer.classList.add('drag-over');
    }
    
    function unhighlight() {
        chatContainer.classList.remove('drag-over');
    }
    
    function handleDrop(e) {
        const files = e.dataTransfer.files;
        handleFiles(files);
    }
}

function handleFileAttachment(event) {
    const files = event.target.files;
    handleFiles(files);
    event.target.value = ''; // Reset input
}

function handleFiles(files) {
    Array.from(files).forEach(file => {
        if (validateFile(file)) {
            uploadFile(file);
        }
    });
}

function validateFile(file) {
    const maxSize = 10 * 1024 * 1024; // 10MB
    const allowedTypes = [
        'image/jpeg', 'image/png', 'image/gif', 'image/webp',
        'application/pdf', 'text/plain',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    ];
    
    if (file.size > maxSize) {
        showError(`Файл "${file.name}" слишком большой. Максимальный размер: 10MB`);
        return false;
    }
    
    if (!allowedTypes.includes(file.type)) {
        showError(`Тип файла "${file.type}" не поддерживается`);
        return false;
    }
    
    return true;
}

async function uploadFile(file) {
    try {
        showTypingIndicator(`Загружаю файл "${file.name}"...`);
        
        const formData = new FormData();
        formData.append('file', file);
        formData.append('session_id', currentSessionId);
        formData.append('project_id', currentProject || '');
        
        const response = await fetch('/api/upload/', {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: formData
        });
        
        const data = await response.json();
        
        hideTypingIndicator();
        
        if (data.success) {
            addFileMessageToUI(file, data);
            showSuccess(`Файл "${file.name}" успешно загружен и обработан`);
        } else {
            showError(`Ошибка загрузки файла: ${data.error || 'Неизвестная ошибка'}`);
        }
        
    } catch (error) {
        hideTypingIndicator();
        console.error('File upload error:', error);
        showError('Не удалось загрузить файл');
    }
}

function addFileMessageToUI(file, data) {
    const messageContainer = document.getElementById('messages-container');
    
    const messageElement = document.createElement('div');
    messageElement.className = 'message user-message file-message';
    
    let filePreview = '';
    if (file.type.startsWith('image/')) {
        const imageUrl = URL.createObjectURL(file);
        filePreview = `
            <div class="file-preview image-preview">
                <img src="${imageUrl}" alt="${file.name}" onclick="openImageModal('${imageUrl}')">
            </div>
        `;
    } else {
        const fileIcon = getFileIcon(file.type);
        filePreview = `
            <div class="file-preview document-preview">
                <i class="${fileIcon}"></i>
                <span>${file.name}</span>
                <small>${formatFileSize(file.size)}</small>
            </div>
        `;
    }
    
    messageElement.innerHTML = `
        <div class="message-avatar">
            <i class="fas fa-user"></i>
        </div>
        <div class="message-content">
            ${filePreview}
            ${data.analysis ? `<div class="file-analysis">${data.analysis}</div>` : ''}
            <div class="message-time">${formatTime(new Date())}</div>
        </div>
    `;
    
    messageContainer.appendChild(messageElement);
    scrollToBottom();
}

// Project Management Functions
async function loadProjects() {
    try {
        const response = await fetch('/api/projects/', {
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            updateProjectSelector(data.projects);
            
            // Set current project if exists
            if (currentProject) {
                const selector = document.getElementById('project-selector');
                if (selector) {
                    selector.value = currentProject;
                }
            }
        }
        
    } catch (error) {
        console.error('Error loading projects:', error);
    }
}

function updateProjectSelector(projects) {
    const selector = document.getElementById('project-selector');
    if (!selector) return;
    
    selector.innerHTML = '<option value="">Общий чат</option>';
    
    projects.forEach(project => {
        const option = document.createElement('option');
        option.value = project.id;
        option.textContent = `${project.icon} ${project.name}`;
        selector.appendChild(option);
    });
}

function handleProjectChange(event) {
    const projectId = event.target.value;
    currentProject = projectId;
    
    if (projectId) {
        localStorage.setItem('currentProject', projectId);
    } else {
        localStorage.removeItem('currentProject');
    }
    
    // Load project-specific chat history
    loadChatHistory();
    
    // Update UI theme based on project
    updateProjectTheme(projectId);
}

function updateProjectTheme(projectId) {
    if (!projectId) return;
    
    // This could fetch project-specific styling
    // For now, just add a class to indicate active project
    document.body.classList.toggle('has-active-project', !!projectId);
}

// Enhanced chat submission with multimodal support
async function handleEnhancedChatSubmit(e) {
    e.preventDefault();
    
    const messageInput = document.getElementById('message-input');
    const message = messageInput.value.trim();
    
    if (!message) {
        showError('Пожалуйста, введите сообщение');
        return;
    }
    
    if (message.length > 2000) {
        showError('Сообщение слишком длинное (максимум 2000 символов)');
        return;
    }
    
    // Hide welcome message
    const welcomeMessage = document.getElementById('welcome-message');
    if (welcomeMessage) {
        welcomeMessage.style.display = 'none';
    }
    
    // Add user message to UI
    addMessageToUI(message, 'user');
    
    // Clear input
    messageInput.value = '';
    messageInput.style.height = 'auto';
    
    // Show typing indicator
    showTypingIndicator();
    
    try {
        const requestData = {
            message: message,
            session_id: currentSessionId,
            project_id: currentProject || null
        };
        
        const response = await fetch('/api/chat/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify(requestData)
        });
        
        const data = await response.json();
        
        hideTypingIndicator();
        
        if (data.success) {
            addMessageToUI(data.message, 'assistant');
            
            // Update message history
            messageHistory.push({
                message: message,
                response: data.message,
                timestamp: new Date().toISOString(),
                project_id: currentProject
            });
            
            // Show mood detection if available
            if (data.detected_mood) {
                showMoodDetection(data.detected_mood);
            }
            
        } else {
            showError(data.error || 'Произошла ошибка при отправке сообщения');
        }
        
    } catch (error) {
        hideTypingIndicator();
        console.error('Chat submission error:', error);
        showError('Не удалось отправить сообщение. Проверьте подключение к интернету.');
    }
}

// Utility Functions
function generateSessionId() {
    return 'session_' + Math.random().toString(36).substr(2, 9) + '_' + Date.now();
}

function formatTime(date) {
    return date.toLocaleTimeString('ru-RU', { 
        hour: '2-digit', 
        minute: '2-digit' 
    });
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function getFileIcon(mimeType) {
    if (mimeType.startsWith('image/')) return 'fas fa-image';
    if (mimeType.includes('pdf')) return 'fas fa-file-pdf';
    if (mimeType.includes('word') || mimeType.includes('document')) return 'fas fa-file-word';
    if (mimeType.includes('sheet') || mimeType.includes('excel')) return 'fas fa-file-excel';
    return 'fas fa-file';
}

function showSuccess(message) {
    showNotification(message, 'success');
}

function showError(message) {
    showNotification(message, 'error');
}

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        notification.remove();
    }, 5000);
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Enhanced UI functions (to be implemented)
function showNewProjectModal() {
    // Implementation for creating new project
    console.log('Show new project modal');
}

function showExportModal() {
    // Implementation for exporting chat
    console.log('Show export modal');
}

function showSearchModal() {
    // Implementation for searching chat history
    console.log('Show search modal');
}

function showMoodDetection(mood) {
    // Implementation for showing detected mood
    console.log('Detected mood:', mood);
}

function openImageModal(imageUrl) {
    // Implementation for image preview modal
    console.log('Open image modal:', imageUrl);
}

// Legacy functions for compatibility
function addMessageToUI(message, type) {
    // Implementation from original chat.js
    console.log('Add message:', message, type);
}

function showTypingIndicator(customMessage = null) {
    // Implementation from original chat.js
    console.log('Show typing indicator:', customMessage);
}

function hideTypingIndicator() {
    // Implementation from original chat.js
    console.log('Hide typing indicator');
}

function scrollToBottom() {
    // Implementation from original chat.js
    const messagesContainer = document.getElementById('messages-container');
    if (messagesContainer) {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
}

function handleFAQSearch() {
    // Implementation from original chat.js
    console.log('FAQ search');
}

function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

function loadChatHistory() {
    // Implementation from original chat.js
    console.log('Load chat history');
}