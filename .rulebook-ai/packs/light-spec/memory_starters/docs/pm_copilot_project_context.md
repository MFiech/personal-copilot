# PM Co-Pilot Project Context

## Project Overview

PM Co-Pilot is an AI-powered assistant designed to supercharge productivity by integrating with personal applications like Gmail and Google Calendar. It uses a sophisticated RAG (Retrieval-Augmented Generation) model to provide context-aware assistance and allows you to take action on your data directly from the chat interface.

## Core Features

- **Conversational AI:** Chat with your data using natural language
- **RAG-based Insights:** Leverages Pinecone vector database for context-aware responses
- **Tooling Integration:** Connects with Gmail and Google Calendar via Composio
- **Interactive UI:** Clean, modern React interface
- **Secure and Private:** Runs locally, user controls all connections

## Tech Stack

### Backend
- **Framework:** Flask with Blueprint pattern
- **AI Integration:** LangChain, OpenAI, Anthropic
- **Vector Database:** Pinecone for RAG operations
- **Document Database:** MongoDB for conversation history
- **Tool Integration:** Composio for Gmail/Google Calendar
- **Containerization:** Docker ("pm-copilot-backend" container)

### Frontend
- **Framework:** React with Material-UI
- **State Management:** React hooks and context
- **API Communication:** RESTful calls to Flask backend

## Key API Endpoints

- `/chat` (POST): Send a query and get an AI response
- `/threads` (GET): Get a list of all conversation threads
- `/chat/<thread_id>` (GET): Get message history for a specific thread
- `/save_insight` (POST): Save a new insight to the vector database

## Database Structure

- **Pinecone vector database** (index: "personal", namespace: "saved_insights")
- **MongoDB** for conversation history and user data
  - **Key collection**: "conversations" - used for debugging and state tracking

## Development Environment

### Prerequisites
- Python 3.10+
- Node.js 16+
- Pinecone API key
- OpenAI API key
- Anthropic API key
- Google API key

### Local Setup
- **Backend**: Flask app with virtual environment
- **Frontend**: React development server
- **Database**: MongoDB (local or containerized)
- **Docker**: docker-compose for orchestration

## Integration Points

### Gmail Integration
- Email search and retrieval
- Draft detection and management
- HTML to markdown conversion
- Metadata extraction

### Google Calendar Integration
- Event creation and management
- Timezone handling
- Attendee management
- Calendar synchronization

### AI/LLM Integration
- OpenAI and Anthropic model calls
- LangChain for tool orchestration
- Pinecone for vector operations
- Context management and RAG

## Known Patterns & Preferences

### Error Handling
- Use try/except blocks consistently
- Validate inputs against model schemas
- Log exceptions with tracebacks
- Maintain graceful degradation

### Development Workflow
- Always use feature branches (never main)
- Run complete test suite before push
- Get user confirmation before pushing
- Update documentation with changes
- Clean up temporary artifacts

### Testing Philosophy
- Never modify app code to match failing tests
- Always fix failing tests, never exclude them
- Use pytest for Python testing
- Test both unit and integration scenarios

### Docker Usage
- Container name: "pm-copilot-backend"
- Never delete containers/volumes unless asked
- Check logs for debugging
- Preserve data integrity

## Security & Safety

### Data Protection
- User data remains local
- Secure API key management
- Input validation and sanitization
- Proper authentication flows

### Development Safety
- Never push to main branch directly
- Always get confirmation before deployment
- Preserve Docker volumes and containers
- Follow testing requirements strictly