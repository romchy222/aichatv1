# AI Agent Chat Assistant - System Architecture

## Overview

This is a Django-based AI chat assistant application that provides an interactive chat interface with FAQ search capabilities. The system integrates with Together.ai API for AI-powered responses and maintains a knowledge base of frequently asked questions. The application is designed for educational institutions to help students and staff get quick answers to common queries.

## User Preferences

Preferred communication style: Simple, everyday language.

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