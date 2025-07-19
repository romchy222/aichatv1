// Russian AI Chat Assistant - Enhanced JavaScript with Theme Support
let currentSessionId = null;
let messageHistory = [];
let isTyping = false;
let currentTheme = 'light';

// Initialize chat application
document.addEventListener('DOMContentLoaded', function() {
    initializeChat();
    setupEventListeners();
    loadChatHistory();
});

// Initialize chat functionality
function initializeChat() {
    currentSessionId = localStorage.getItem('sessionId');
    if (!currentSessionId) {
        currentSessionId = generateSessionId();
        localStorage.setItem('sessionId', currentSessionId);
    }
    
    // Set up theme
    currentTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', currentTheme);
    
    // Clear welcome message if there are existing messages
    const welcomeMessage = document.getElementById('welcome-message');
    if (messageHistory.length > 0 && welcomeMessage) {
        welcomeMessage.style.display = 'none';
    }
}

// Setup event listeners
function setupEventListeners() {
    // Chat form submission
    const chatForm = document.getElementById('chat-form');
    chatForm.addEventListener('submit', handleChatSubmit);
    
    // FAQ search
    const faqSearch = document.getElementById('faq-search');
    faqSearch.addEventListener('input', debounce(handleFAQSearch, 300));
    
    // Message input auto-resize
    const messageInput = document.getElementById('message-input');
    messageInput.addEventListener('input', autoResizeTextarea);
    
    // Enter key handling
    messageInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            chatForm.dispatchEvent(new Event('submit'));
        }
    });
}

// Generate unique session ID
function generateSessionId() {
    return 'session_' + Math.random().toString(36).substr(2, 9) + '_' + Date.now();
}

// Handle chat form submission
async function handleChatSubmit(e) {
    e.preventDefault();
    
    const messageInput = document.getElementById('message-input');
    const message = messageInput.value.trim();
    
    if (!message) {
        showError(window.translations.empty_message);
        return;
    }
    
    if (message.length > 2000) {
        showError(window.translations.message_too_long);
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
    
    // Disable send button and show typing indicator
    toggleSendButton(false);
    showTypingIndicator();
    
    try {
        const response = await fetch('/api/chat/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                message: message,
                session_id: currentSessionId
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Remove typing indicator
            hideTypingIndicator();
            
            // Add assistant response to UI
            addMessageToUI(data.message, 'assistant');
            
            // Update message history
            messageHistory.push({
                message: message,
                response: data.message,
                timestamp: new Date().toISOString()
            });
            
        } else {
            hideTypingIndicator();
            showError(data.error || window.translations.error_occurred);
        }
        
    } catch (error) {
        hideTypingIndicator();
        showError(window.translations.connection_error);
        console.error('Chat error:', error);
    }
    
    // Re-enable send button
    toggleSendButton(true);
}

// Add message to UI
function addMessageToUI(message, type, timestamp = null) {
    const messagesContainer = document.getElementById('messages-container');
    const messageElement = createMessageElement(message, type, timestamp);
    messagesContainer.appendChild(messageElement);
    scrollToBottom();
}

// Create message element
function createMessageElement(message, type, timestamp = null) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;
    
    const time = timestamp ? new Date(timestamp) : new Date();
    const timeString = time.toLocaleTimeString('ru-RU', {
        hour: '2-digit',
        minute: '2-digit'
    });
    
    // Create avatar
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = type === 'user' ? 'В' : 'AI';
    
    // Create content
    const content = document.createElement('div');
    content.className = 'message-content';
    content.innerHTML = formatMessage(message);
    
    // Create time
    const timeDiv = document.createElement('div');
    timeDiv.className = 'message-time';
    timeDiv.textContent = timeString;
    
    // Create actions
    const actions = document.createElement('div');
    actions.className = 'message-actions';
    
    if (type === 'assistant') {
        const copyBtn = document.createElement('button');
        copyBtn.className = 'message-action';
        copyBtn.innerHTML = '<i class="fas fa-copy"></i> ' + window.translations.copy;
        copyBtn.onclick = () => copyMessage(message);
        actions.appendChild(copyBtn);
        
        const regenerateBtn = document.createElement('button');
        regenerateBtn.className = 'message-action';
        regenerateBtn.innerHTML = '<i class="fas fa-redo"></i> ' + window.translations.regenerate;
        regenerateBtn.onclick = () => regenerateMessage(messageDiv);
        actions.appendChild(regenerateBtn);
    }
    
    // Assemble message
    messageDiv.appendChild(avatar);
    const contentWrapper = document.createElement('div');
    contentWrapper.appendChild(content);
    contentWrapper.appendChild(timeDiv);
    contentWrapper.appendChild(actions);
    messageDiv.appendChild(contentWrapper);
    
    return messageDiv;
}

// Format message content
function formatMessage(message) {
    // Convert URLs to links
    const urlRegex = /(https?:\/\/[^\s]+)/g;
    message = message.replace(urlRegex, '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>');
    
    // Convert line breaks to HTML
    message = message.replace(/\n/g, '<br>');
    
    // Convert **bold** to <strong>
    message = message.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // Convert *italic* to <em>
    message = message.replace(/\*(.*?)\*/g, '<em>$1</em>');
    
    return message;
}

// Show typing indicator
function showTypingIndicator() {
    if (isTyping) return;
    
    isTyping = true;
    const messagesContainer = document.getElementById('messages-container');
    
    const typingDiv = document.createElement('div');
    typingDiv.className = 'message assistant';
    typingDiv.id = 'typing-indicator';
    
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.textContent = 'AI';
    
    const typingContent = document.createElement('div');
    typingContent.className = 'typing-indicator';
    typingContent.innerHTML = `
        <div class="typing-dots">
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
        </div>
        <span>${window.translations.typing}</span>
    `;
    
    typingDiv.appendChild(avatar);
    typingDiv.appendChild(typingContent);
    messagesContainer.appendChild(typingDiv);
    scrollToBottom();
}

// Hide typing indicator
function hideTypingIndicator() {
    isTyping = false;
    const typingIndicator = document.getElementById('typing-indicator');
    if (typingIndicator) {
        typingIndicator.remove();
    }
}

// Handle FAQ search
async function handleFAQSearch(e) {
    const query = e.target.value.trim();
    const resultsContainer = document.getElementById('faq-results');
    
    if (query.length < 2) {
        resultsContainer.innerHTML = '<div class="welcome-message"><p>Введите вопрос для поиска в базе знаний</p></div>';
        return;
    }
    
    try {
        const response = await fetch(`/api/faq/?q=${encodeURIComponent(query)}`);
        const data = await response.json();
        
        if (data.success && data.entries.length > 0) {
            displayFAQResults(data.entries);
        } else {
            resultsContainer.innerHTML = `<div class="welcome-message"><p>${window.translations.no_results}</p></div>`;
        }
    } catch (error) {
        console.error('FAQ search error:', error);
        resultsContainer.innerHTML = `<div class="error-message"><i class="fas fa-exclamation-triangle"></i> ${window.translations.error_occurred}</div>`;
    }
}

// Display FAQ results
function displayFAQResults(results) {
    const resultsContainer = document.getElementById('faq-results');
    resultsContainer.innerHTML = '';
    
    results.forEach(result => {
        const faqItem = document.createElement('div');
        faqItem.className = 'faq-item';
        faqItem.onclick = () => insertFAQResponse(result);
        
        const category = document.createElement('div');
        category.className = 'faq-category';
        category.textContent = window.translations.categories[result.category] || result.category;
        
        const question = document.createElement('div');
        question.className = 'faq-question';
        question.textContent = result.question;
        
        const answer = document.createElement('div');
        answer.className = 'faq-answer';
        answer.textContent = result.answer;
        
        faqItem.appendChild(category);
        faqItem.appendChild(question);
        faqItem.appendChild(answer);
        
        resultsContainer.appendChild(faqItem);
    });
}

// Insert FAQ response as message
function insertFAQResponse(faqItem) {
    const messageInput = document.getElementById('message-input');
    messageInput.value = faqItem.question;
    messageInput.focus();
    
    // Auto-resize textarea
    messageInput.style.height = 'auto';
    messageInput.style.height = messageInput.scrollHeight + 'px';
}

// Load chat history
async function loadChatHistory() {
    try {
        const response = await fetch(`/api/history/?session_id=${currentSessionId}`);
        const data = await response.json();
        
        if (data.success && data.messages.length > 0) {
            // Hide welcome message
            const welcomeMessage = document.getElementById('welcome-message');
            if (welcomeMessage) {
                welcomeMessage.style.display = 'none';
            }
            
            // Display messages
            data.messages.forEach(msg => {
                addMessageToUI(msg.message, msg.message_type, msg.timestamp);
            });
        }
    } catch (error) {
        console.error('Failed to load chat history:', error);
    }
}

// Utility functions
function toggleSendButton(enabled) {
    const sendButton = document.getElementById('send-button');
    sendButton.disabled = !enabled;
}

function scrollToBottom() {
    const messagesContainer = document.getElementById('messages-container');
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function autoResizeTextarea() {
    const textarea = document.getElementById('message-input');
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
}

function showError(message) {
    const messagesContainer = document.getElementById('messages-container');
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.innerHTML = `<i class="fas fa-exclamation-triangle"></i> ${message}`;
    messagesContainer.appendChild(errorDiv);
    
    // Auto-remove error after 5 seconds
    setTimeout(() => {
        errorDiv.remove();
    }, 5000);
    
    scrollToBottom();
}

function copyMessage(message) {
    navigator.clipboard.writeText(message).then(() => {
        // Show temporary success message
        const notification = document.createElement('div');
        notification.className = 'copy-notification';
        notification.textContent = window.translations.copied;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: var(--bg-button);
            color: var(--text-inverse);
            padding: 10px 20px;
            border-radius: 8px;
            z-index: 1000;
            font-size: 14px;
            font-weight: 600;
        `;
        
        document.body.appendChild(notification);
        setTimeout(() => notification.remove(), 2000);
    });
}

function regenerateMessage(messageElement) {
    // Find the previous user message
    const userMessage = messageElement.previousElementSibling;
    if (userMessage && userMessage.classList.contains('user')) {
        const userText = userMessage.querySelector('.message-content').textContent;
        
        // Remove the assistant message
        messageElement.remove();
        
        // Resend the user message
        document.getElementById('message-input').value = userText;
        document.getElementById('chat-form').dispatchEvent(new Event('submit'));
    }
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

// Handle suggestion buttons
function sendSuggestion(message) {
    const messageInput = document.getElementById('message-input');
    messageInput.value = message;
    messageInput.focus();
    document.getElementById('chat-form').dispatchEvent(new Event('submit'));
}

// Add mobile-specific functionality
if (window.innerWidth <= 768) {
    // Add mobile menu button
    const chatHeader = document.querySelector('.chat-header');
    const mobileMenuBtn = document.createElement('button');
    mobileMenuBtn.className = 'mobile-menu-btn';
    mobileMenuBtn.innerHTML = '<i class="fas fa-bars"></i>';
    mobileMenuBtn.style.cssText = `
        background: none;
        border: none;
        color: var(--text-primary);
        font-size: 18px;
        padding: 8px;
        cursor: pointer;
        border-radius: 8px;
        transition: var(--transition);
    `;
    
    mobileMenuBtn.onclick = function() {
        const sidebar = document.getElementById('sidebar');
        sidebar.classList.toggle('open');
    };
    
    chatHeader.insertBefore(mobileMenuBtn, chatHeader.firstChild);
    
    // Close sidebar when clicking outside
    document.addEventListener('click', function(e) {
        const sidebar = document.getElementById('sidebar');
        const mobileMenuBtn = document.querySelector('.mobile-menu-btn');
        
        if (!sidebar.contains(e.target) && !mobileMenuBtn.contains(e.target)) {
            sidebar.classList.remove('open');
        }
    });
}

// File upload functionality
let uploadedFiles = [];

function initializeFileUpload() {
    const attachBtn = document.getElementById('attach-btn');
    const fileUploadArea = document.getElementById('fileUploadArea');
    const fileInput = document.getElementById('fileInput');
    const uploadedFilesDiv = document.getElementById('uploadedFiles');
    
    if (!attachBtn || !fileUploadArea || !fileInput) return;
    
    // Toggle file upload area
    attachBtn.addEventListener('click', function() {
        fileUploadArea.style.display = fileUploadArea.style.display === 'none' ? 'block' : 'none';
    });
    
    // Handle file input change
    fileInput.addEventListener('change', function(e) {
        handleFileUpload(e.target.files);
    });
    
    // Drag and drop functionality
    const uploadZone = document.querySelector('.upload-zone');
    if (uploadZone) {
        uploadZone.addEventListener('dragover', function(e) {
            e.preventDefault();
            e.stopPropagation();
            this.style.background = 'var(--bg-hover)';
        });
        
        uploadZone.addEventListener('dragleave', function(e) {
            e.preventDefault();
            e.stopPropagation();
            this.style.background = '';
        });
        
        uploadZone.addEventListener('drop', function(e) {
            e.preventDefault();
            e.stopPropagation();
            this.style.background = '';
            handleFileUpload(e.dataTransfer.files);
        });
    }
}

function handleFileUpload(files) {
    const uploadedFilesDiv = document.getElementById('uploadedFiles');
    
    Array.from(files).forEach(file => {
        // Check file size (10MB limit)
        if (file.size > 10 * 1024 * 1024) {
            showNotification(`Файл ${file.name} слишком большой (максимум 10MB)`, 'error');
            return;
        }
        
        // Create file item
        const fileItem = createFileItem(file);
        uploadedFilesDiv.appendChild(fileItem);
        
        // Upload file
        uploadFile(file, fileItem);
    });
    
    // Hide upload area after files are selected
    document.getElementById('fileUploadArea').style.display = 'none';
}

function createFileItem(file) {
    const fileItem = document.createElement('div');
    fileItem.className = 'file-item';
    fileItem.innerHTML = `
        <div class="file-icon">
            <i class="${getFileIcon(file.name)}"></i>
        </div>
        <div class="file-info">
            <div class="file-name">${file.name}</div>
            <div class="file-status">Загружается...</div>
        </div>
        <div class="file-actions">
            <button class="btn btn-sm btn-outline-danger" onclick="removeFileItem(this)">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `;
    return fileItem;
}

function getFileIcon(filename) {
    const extension = filename.split('.').pop().toLowerCase();
    const iconMap = {
        'pdf': 'fas fa-file-pdf',
        'doc': 'fas fa-file-word',
        'docx': 'fas fa-file-word',
        'xls': 'fas fa-file-excel',
        'xlsx': 'fas fa-file-excel',
        'csv': 'fas fa-file-csv',
        'txt': 'fas fa-file-alt',
        'jpg': 'fas fa-file-image',
        'jpeg': 'fas fa-file-image',
        'png': 'fas fa-file-image',
        'gif': 'fas fa-file-image'
    };
    return iconMap[extension] || 'fas fa-file';
}

function uploadFile(file, fileItem) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('session_id', sessionId);
    
    const statusDiv = fileItem.querySelector('.file-status');
    
    fetch('/api/files/', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            statusDiv.textContent = 'Обработан';
            statusDiv.style.color = 'green';
            
            // Add to uploaded files list
            uploadedFiles.push({
                id: data.file_id,
                filename: data.filename,
                summary: data.summary,
                extracted_text: data.extracted_text
            });
            
            // Show success message
            showNotification(`Файл ${data.filename} успешно обработан`, 'success');
            
            // Add file info to message if text was extracted
            if (data.extracted_text && data.extracted_text.length > 0) {
                const messageInput = document.getElementById('message-input');
                const currentText = messageInput.value;
                const fileInfo = `[Файл: ${data.filename}] ${data.summary}\n\n`;
                messageInput.value = fileInfo + currentText;
            }
        } else {
            statusDiv.textContent = 'Ошибка';
            statusDiv.style.color = 'red';
            showNotification(`Ошибка обработки файла: ${data.error}`, 'error');
        }
    })
    .catch(error => {
        statusDiv.textContent = 'Ошибка';
        statusDiv.style.color = 'red';
        showNotification(`Ошибка загрузки файла: ${error.message}`, 'error');
    });
}

function removeFileItem(button) {
    const fileItem = button.closest('.file-item');
    fileItem.remove();
}

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type === 'error' ? 'danger' : type === 'success' ? 'success' : 'info'}`;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        z-index: 1000;
        min-width: 300px;
        animation: slideIn 0.3s ease;
        padding: 12px;
        border-radius: 8px;
        background: ${type === 'error' ? '#ff6b6b' : type === 'success' ? '#51cf66' : '#339af0'};
        color: white;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    `;
    notification.innerHTML = `
        <i class="fas fa-${type === 'error' ? 'exclamation-circle' : type === 'success' ? 'check-circle' : 'info-circle'}"></i>
        ${message}
        <button type="button" onclick="this.parentElement.remove()" style="float: right; background: none; border: none; color: white; font-size: 18px; cursor: pointer;">&times;</button>
    `;
    document.body.appendChild(notification);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (notification.parentElement) {
            notification.remove();
        }
    }, 5000);
}

// Make functions global for onclick handlers
window.removeFileItem = removeFileItem;

// Initialize theme on page load
document.addEventListener('DOMContentLoaded', function() {
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
    initializeFileUpload();
});