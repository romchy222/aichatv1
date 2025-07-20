# AI Agent Chat Assistant - System Architecture

## Overview

This is a Django-based AI chat assistant application that provides an interactive chat interface with FAQ search capabilities. The system integrates with Together.ai API for AI-powered responses and maintains a knowledge base of frequently asked questions. The application is designed for educational institutions to help students and staff get quick answers to common queries.

## User Preferences

Preferred communication style: Simple, everyday language.

## Recent Changes

- **July 20, 2025**: Made enhanced interface the default main page
  - Updated ChatView to always use enhanced-chat.html template
  - Replaced /enhanced/ route with /classic/ for fallback to old interface
  - Enhanced interface now accessible at root URL (/) with all modern features
  - Fixed ChatManager.generate_response method for voice message processing
  - Resolved JavaScript conflicts and UI error handling
- **July 19, 2025**: Added comprehensive file upload and processing system
  - Created FileUpload model for tracking uploaded files and processing status
  - Built FileProcessorManager with support for multiple file types:
    - Images (JPG, PNG, GIF) with basic analysis and OCR placeholder
    - Documents (DOCX, TXT, PDF) with full text extraction
    - Spreadsheets (XLSX, CSV) with data parsing and table extraction
  - Added file upload API endpoints (/api/files/) with 10MB size limit
  - Integrated drag-and-drop file upload interface in chat
  - Added file processing status tracking and error handling
  - Created admin interface for managing uploaded files
  - Files are processed automatically and content is extracted for AI analysis
- **July 19, 2025**: Implemented comprehensive content moderation system for AI and FAQ
  - Added ContentFilter model for managing banned words, phrases, and regex patterns
  - Added ModerationLog model for tracking all moderation actions
  - Created ContentModerator class with filtering logic for different content types
  - Integrated moderation into ChatManager for AI responses and user input
  - Added moderation to FAQ search results
  - Created admin interface for managing content filters
  - Added default filters for common inappropriate content in Russian and English
  - Support for three severity levels: low (warning), medium (censorship), high (blocking)
  - Language-specific filtering with auto-detection
- **July 17, 2025**: Complete Russian interface with light/dark themes and ChatGPT-style design
  - Fully russified interface with proper Russian translations
  - Added comprehensive light/dark theme system with CSS variables
  - Implemented ChatGPT-style modern interface with clean design
  - Added theme toggle button with persistent localStorage settings
  - Created responsive mobile-first design with sidebar navigation
  - Enhanced message styling with proper avatars and gradients
  - Added smooth animations and transitions throughout the interface
  - Implemented proper Russian date/time formatting
  - Added mobile menu functionality for tablet and phone screens
- **July 17, 2025**: Enhanced super admin interface with configuration management
  - Added AIModelConfig model for AI model selection and parameters
  - Added SystemPrompt model for dynamic prompt management
  - Added APIKeyConfig model for API key and provider management
  - Created custom admin dashboard with real-time status monitoring
  - Implemented system status API endpoint for live configuration display
  - Added multiple AI model presets (Mistral 7B, Llama 3, Mixtral)
  - Added multiple system prompt templates (University, Friendly, Professional, Russian)
- **July 17, 2025**: Updated color scheme to modern AI-focused palette
  - Primary: #0D1B2A (dark navy)
  - Accent: #00AEEF (bright blue)
  - Secondary: #F0F0F0 (light gray)
  - Text: #222222 (near black)
  - Highlight: #A3D900 (lime green)
- **July 17, 2025**: Implemented ChatGPT/GigaChat-style modern interface
  - Glassmorphism effects with backdrop blur
  - Gradient buttons and avatars
  - Enhanced message bubbles with better spacing
  - Improved typography and animations

## System Architecture

### Backend Architecture
- **Framework**: Django 4.x with Python
- **Database**: SQLite (default Django database for development)
- **API Integration**: Together.ai API for AI chat responses using Mistral-7B-Instruct model
- **Session Management**: Django sessions for chat continuity
- **Admin Interface**: Django admin for content management

### Frontend Architecture
- **Templates**: Django template system with Bootstrap 5 for responsive UI
- **JavaScript**: Vanilla JavaScript for real-time chat interactions
- **CSS Framework**: Bootstrap 5 with custom styling
- **Icons**: Font Awesome for UI elements

### Key Components

1. **Chat System**
   - Real-time messaging interface
   - Session-based conversation tracking
   - AI response generation through Together.ai API
   - Message history persistence

2. **Knowledge Base**
   - FAQ entry management with categories
   - Search functionality with keyword matching
   - Admin interface for content management
   - Category-based organization (schedules, documents, scholarships, exams, administration, general)

3. **User Management**
   - Optional user authentication
   - Session-based tracking for anonymous users
   - User activity logging

4. **Analytics & Logging**
   - API request logging with response times
   - Token usage tracking
   - Success/failure rate monitoring

## Key Components

### Models
- **FAQEntry**: Stores knowledge base questions and answers with categories and keywords
- **ChatSession**: Manages user chat sessions with unique session IDs
- **ChatMessage**: Stores individual chat messages with timestamps and types
- **RequestLog**: Tracks API requests, response times, and token usage

### Views
- **ChatView**: Main chat interface with form handling
- **ChatAPIView**: API endpoint for sending/receiving chat messages
- **FAQView**: API endpoint for FAQ search functionality
- **ChatHistoryView**: API endpoint for retrieving chat history
- **AnalyticsView**: API endpoint for system analytics

### Utilities
- **TogetherAIClient**: Wrapper for Together.ai API integration
- **ChatManager**: Handles chat session management and message processing
- **KnowledgeBaseManager**: Manages FAQ search and retrieval

## Data Flow

1. **User Input**: User submits message through chat interface
2. **Session Management**: System creates/retrieves chat session
3. **Knowledge Base Search**: System searches FAQ entries for relevant answers
4. **AI Processing**: If no FAQ match, message is sent to Together.ai API
5. **Response Generation**: AI generates response using Mistral-7B-Instruct model
6. **Data Storage**: Messages and API logs are stored in database
7. **Response Display**: Answer is displayed in chat interface

## External Dependencies

### Required Python Packages
- Django 4.x
- requests (for API calls)
- django-cors-headers (for CORS handling)

### External APIs
- **Together.ai API**: Primary AI service for chat responses
  - Model: mistralai/Mistral-7B-Instruct-v0.1
  - Requires API key configuration
  - Supports streaming and non-streaming responses

### Frontend Dependencies
- Bootstrap 5 (via CDN)
- Font Awesome 6 (via CDN)
- Vanilla JavaScript (no additional frameworks)

## Deployment Strategy

### Development Setup
- Uses Django's built-in development server
- SQLite database for local development
- Debug mode enabled
- CORS headers configured for local development

### Configuration Requirements
- `TOGETHER_API_KEY`: API key for Together.ai service
- `TOGETHER_API_URL`: Together.ai API endpoint
- `SECRET_KEY`: Django secret key (needs to be changed for production)
- `DEBUG`: Should be False in production
- `ALLOWED_HOSTS`: Configure for production domains

### Production Considerations
- Database migration to PostgreSQL recommended
- Static file serving configuration needed
- Environment variable management for sensitive settings
- HTTPS configuration required
- Rate limiting implementation recommended
- Monitoring and logging setup for production use

### Security Features
- CSRF protection enabled
- XFrame protection
- Session security middleware
- Input validation and sanitization
- SQL injection protection through Django ORM

The application follows Django best practices with a clear separation of concerns between models, views, and templates. The modular design allows for easy extension and maintenance.