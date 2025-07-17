// AI Chat Assistant JavaScript
class ChatAssistant {
    constructor(config) {
        this.config = config;
        this.isLoading = false;
        this.messageHistory = [];
        
        this.initializeElements();
        this.bindEvents();
        this.loadChatHistory();
    }
    
    initializeElements() {
        // Chat elements
        this.chatForm = document.getElementById('chat-form');
        this.messageInput = document.getElementById('message-input');
        this.sendButton = document.getElementById('send-button');
        this.chatMessages = document.getElementById('chat-messages');
        this.chatHistory = document.getElementById('chat-history');
        this.charCount = document.getElementById('char-count');
        
        // FAQ elements
        this.faqForm = document.getElementById('faq-search-form');
        this.faqQuery = document.getElementById('faq-query');
        this.faqCategory = document.getElementById('faq-category');
        this.faqResults = document.getElementById('faq-results');
        
        // Loading modal
        this.loadingModal = new bootstrap.Modal(document.getElementById('loadingModal'));
    }
    
    bindEvents() {
        // Chat form submission
        this.chatForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.sendMessage();
        });
        
        // Enter key handling for message input
        this.messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        // Character count
        this.messageInput.addEventListener('input', () => {
            this.updateCharCount();
        });
        
        // FAQ search
        this.faqForm.addEventListener('submit', (e) => {
            e.preventDefault();
            this.searchFAQ();
        });
        
        // FAQ real-time search
        this.faqQuery.addEventListener('input', () => {
            this.debounce(() => this.searchFAQ(), 500);
        });
        
        this.faqCategory.addEventListener('change', () => {
            this.searchFAQ();
        });
    }
    
    updateCharCount() {
        const count = this.messageInput.value.length;
        this.charCount.textContent = count;
        
        if (count > 900) {
            this.charCount.style.color = '#dc3545';
        } else if (count > 800) {
            this.charCount.style.color = '#fd7e14';
        } else {
            this.charCount.style.color = '#6c757d';
        }
    }
    
    async sendMessage() {
        const message = this.messageInput.value.trim();
        
        if (!message || this.isLoading) {
            return;
        }
        
        if (message.length > 1000) {
            this.showError('Message too long (max 1000 characters)');
            return;
        }
        
        // Add user message to chat
        this.addMessage('user', message);
        
        // Clear input
        this.messageInput.value = '';
        this.updateCharCount();
        
        // Show loading state
        this.setLoading(true);
        this.showTypingIndicator();
        
        try {
            const response = await fetch(this.config.apiUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    session_id: this.config.sessionId
                })
            });
            
            const data = await response.json();
            
            // Remove typing indicator
            this.removeTypingIndicator();
            
            if (data.success) {
                this.addMessage('assistant', data.message, {
                    responseTime: data.response_time,
                    sessionId: data.session_id
                });
            } else {
                this.showError(data.error || 'Failed to get response');
            }
            
        } catch (error) {
            this.removeTypingIndicator();
            this.showError('Network error. Please try again.');
            console.error('Chat error:', error);
        } finally {
            this.setLoading(false);
        }
    }
    
    addMessage(type, content, metadata = {}) {
        const messageContainer = document.createElement('div');
        messageContainer.className = `message ${type}-message`;
        
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.innerHTML = type === 'user' ? '<i class="fas fa-user"></i>' : '<i class="fas fa-robot"></i>';
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        
        const messageBubble = document.createElement('div');
        messageBubble.className = 'message-bubble';
        messageBubble.innerHTML = this.formatMessage(content);
        
        const messageTime = document.createElement('div');
        messageTime.className = 'message-time';
        messageTime.innerHTML = `<small class="text-muted">${this.formatTime(new Date())}</small>`;
        
        messageContent.appendChild(messageBubble);
        messageContent.appendChild(messageTime);
        
        // Add metadata for assistant messages
        if (type === 'assistant' && metadata.responseTime) {
            const messageMeta = document.createElement('div');
            messageMeta.className = 'message-meta';
            messageMeta.innerHTML = `<small>Response time: ${metadata.responseTime.toFixed(2)}s</small>`;
            messageContent.appendChild(messageMeta);
        }
        
        messageContainer.appendChild(avatar);
        messageContainer.appendChild(messageContent);
        
        this.chatHistory.appendChild(messageContainer);
        this.scrollToBottom();
        
        // Store in history
        this.messageHistory.push({
            type,
            content,
            timestamp: new Date(),
            metadata
        });
    }
    
    formatMessage(content) {
        // Basic formatting for message content
        return content
            .replace(/\n/g, '<br>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code>$1</code>');
    }
    
    formatTime(date) {
        return date.toLocaleTimeString([], { 
            hour: '2-digit', 
            minute: '2-digit' 
        });
    }
    
    showTypingIndicator() {
        const typingContainer = document.createElement('div');
        typingContainer.className = 'message assistant-message';
        typingContainer.id = 'typing-indicator';
        
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.innerHTML = '<i class="fas fa-robot"></i>';
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        
        const typingIndicator = document.createElement('div');
        typingIndicator.className = 'typing-indicator';
        typingIndicator.innerHTML = '<div class="dot"></div><div class="dot"></div><div class="dot"></div>';
        
        messageContent.appendChild(typingIndicator);
        typingContainer.appendChild(avatar);
        typingContainer.appendChild(messageContent);
        
        this.chatHistory.appendChild(typingContainer);
        this.scrollToBottom();
    }
    
    removeTypingIndicator() {
        const typingIndicator = document.getElementById('typing-indicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }
    
    async searchFAQ() {
        const query = this.faqQuery.value.trim();
        const category = this.faqCategory.value;
        
        if (!query && !category) {
            this.faqResults.innerHTML = `
                <div class="p-3 text-muted text-center">
                    <i class="fas fa-info-circle"></i>
                    <p>Search the knowledge base for quick answers</p>
                </div>
            `;
            return;
        }
        
        try {
            const params = new URLSearchParams();
            if (query) params.append('query', query);
            if (category) params.append('category', category);
            
            const response = await fetch(`${this.config.faqUrl}?${params}`);
            const data = await response.json();
            
            if (data.success) {
                this.displayFAQResults(data.entries);
            } else {
                this.showError('Failed to search FAQ');
            }
            
        } catch (error) {
            this.showError('Network error during FAQ search');
            console.error('FAQ search error:', error);
        }
    }
    
    displayFAQResults(entries) {
        if (entries.length === 0) {
            this.faqResults.innerHTML = `
                <div class="p-3 text-muted text-center">
                    <i class="fas fa-search"></i>
                    <p>No FAQ entries found</p>
                </div>
            `;
            return;
        }
        
        const resultsHTML = entries.map(entry => `
            <div class="faq-item" onclick="chatAssistant.useFAQAnswer('${entry.answer.replace(/'/g, "\\'")}')">
                <div class="faq-question">${this.escapeHtml(entry.question)}</div>
                <div class="faq-answer">${this.escapeHtml(entry.answer.substring(0, 100))}${entry.answer.length > 100 ? '...' : ''}</div>
                <div class="faq-category">${entry.category}</div>
            </div>
        `).join('');
        
        this.faqResults.innerHTML = resultsHTML;
    }
    
    useFAQAnswer(answer) {
        this.messageInput.value = `Can you explain: ${answer}`;
        this.messageInput.focus();
        this.updateCharCount();
    }
    
    async loadChatHistory() {
        try {
            const response = await fetch(`${this.config.historyUrl}?session_id=${this.config.sessionId}`);
            const data = await response.json();
            
            if (data.success && data.messages.length > 0) {
                // Clear existing history except welcome message
                this.chatHistory.innerHTML = '';
                
                // Add messages from history
                data.messages.forEach(msg => {
                    if (msg.type !== 'system') {
                        this.addMessage(msg.type, msg.content, {
                            responseTime: msg.response_time,
                            tokensUsed: msg.tokens_used
                        });
                    }
                });
            }
            
        } catch (error) {
            console.error('Failed to load chat history:', error);
        }
    }
    
    setLoading(loading) {
        this.isLoading = loading;
        this.sendButton.disabled = loading;
        this.messageInput.disabled = loading;
        
        if (loading) {
            this.sendButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Sending...';
        } else {
            this.sendButton.innerHTML = '<i class="fas fa-paper-plane"></i> Send';
        }
    }
    
    scrollToBottom() {
        this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
    }
    
    showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.innerHTML = `<i class="fas fa-exclamation-triangle"></i> ${message}`;
        
        this.chatHistory.appendChild(errorDiv);
        this.scrollToBottom();
        
        // Remove error after 5 seconds
        setTimeout(() => {
            errorDiv.remove();
        }, 5000);
    }
    
    escapeHtml(unsafe) {
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
    
    debounce(func, wait) {
        clearTimeout(this.debounceTimer);
        this.debounceTimer = setTimeout(func, wait);
    }
}

// Global chat assistant instance
let chatAssistant;

// Initialize chat assistant
function initializeChat(config) {
    chatAssistant = new ChatAssistant(config);
}

// Mobile menu toggle (for responsive design)
function toggleMobileMenu() {
    const sidebar = document.querySelector('.sidebar');
    sidebar.classList.toggle('show');
}

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    // Ctrl/Cmd + K to focus search
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        document.getElementById('faq-query').focus();
    }
    
    // Escape to close mobile menu
    if (e.key === 'Escape') {
        const sidebar = document.querySelector('.sidebar');
        sidebar.classList.remove('show');
    }
});

// Handle visibility change (pause/resume when tab is hidden/visible)
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        // Pause any ongoing operations
        if (chatAssistant) {
            chatAssistant.isLoading = false;
        }
    }
});
