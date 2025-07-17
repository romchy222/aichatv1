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
        
        if (data.success && data.results.length > 0) {
            displayFAQResults(data.results);
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

// Initialize theme on page load
document.addEventListener('DOMContentLoaded', function() {
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
});