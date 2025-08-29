# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

PM Co-Pilot is an AI-powered assistant that integrates with personal applications (Gmail, Google Calendar) using a sophisticated RAG model. It provides conversational AI for data interaction, tooling integration through Composio, and runs locally with user-controlled data.

**Tech Stack:**
- **Backend:** Flask, LangChain, OpenAI, Anthropic, Pinecone, MongoDB
- **Frontend:** React with Material-UI and TailwindCSS
- **Integrations:** Composio for Gmail/Google Calendar access
- **AI Models:** Claude 3.7 Sonnet (primary), Gemini 2.0 Flash Lite (summarization)

## Development Commands

### Backend (Flask API Server)
```bash
# Navigate to backend directory
cd backend

# Activate Python virtual environment (required)
source myenv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run development server
python app.py
# Server runs on http://localhost:5001
```

### Frontend (React App)
```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Run development server
npm start
# Runs on http://localhost:3000

# Build for production
npm run build

# Run tests
npm test
```

### Docker Development
```bash
# Build and run backend in Docker
docker-compose up pm-copilot-backend

# View backend logs
docker logs pm-copilot-backend

# Access running container for debugging
docker exec -it pm-copilot-backend bash
```

### Database Operations
```bash
# Start MongoDB (if running locally)
brew services start mongodb/brew/mongodb-community@7.0

# Test MongoDB connection
mongosh --eval "db.runCommand('ping')"

# Initialize MongoDB schema
cd backend/scripts
python init_mongo.py
```

### Testing
```bash
# Backend tests
cd backend
python test_contact_system.py
python test_draft_system.py
python test_email_content.py

# Frontend tests
cd frontend
npm test
```

### Data Pipeline
```bash
# Add data to vector database via pipeline
# 1. Create 'data' folder in project root
mkdir data

# 2. Add .txt files with content and metadata
# 3. Run pipeline script
cd backend/scripts
python update_data_pipeline.py
```

## Architecture Overview

### High-Level Structure
```
PM Co-Pilot/
├── backend/          # Flask API server
│   ├── app.py        # Main application entry
│   ├── models/       # MongoDB data models
│   ├── services/     # Business logic services
│   ├── config/       # Database configuration
│   └── utils/        # Helper utilities
├── frontend/         # React application
│   └── src/
│       ├── components/  # React components
│       └── utils/      # Frontend utilities
├── database/         # SQLite files (legacy)
└── docker-compose.yml
```

### Backend Architecture

**Core Components:**
- **Flask App (`app.py`)**: Main API server with CORS setup for frontend communication
- **Models**: MongoDB-backed data models for conversations, emails, insights, drafts, contacts
- **Services**: Business logic for Composio integration, contact management, draft handling
- **Config**: MongoDB schema definitions and collection initialization

**Key Services:**
- **ComposioService**: Handles Gmail/Calendar integration with MCP support
- **ContactSyncService**: Manages contact synchronization 
- **DraftService**: Handles email draft creation and management

**Data Flow:**
1. User query → Flask API endpoint
2. Query classification (Gemini LLM or keyword-based)
3. Tool execution (Composio for emails/calendar, Pinecone for RAG)
4. LLM processing (Claude) with retrieved context
5. Response with tool results stored in MongoDB

**Database Architecture:**
- **MongoDB Collections**: conversations, emails, insights, drafts, contacts
- **Pinecone Vector Store**: RAG embeddings in "personal" index, "saved_insights" namespace
- **SQLite**: Legacy chat history (database/chat_history.db)

### Frontend Architecture

**Components:**
- **Chat.tsx**: Main chat interface
- **ToolResults.js**: Displays email/calendar results
- **EmailSidebar.js**: Email management interface
- **SelectionControlPanel**: Multi-selection controls

**State Management:**
- React state for chat messages and tool results
- Axios for backend API communication
- Material-UI components with custom styling

## Environment Setup

### Required API Keys (.env in backend/)
```
PINECONE_API_TOKEN=your_pinecone_api_key
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
GOOGLE_API_KEY=your_google_api_key
COMPOSIO_API_KEY=your_composio_api_key
```

### Composio Configuration
- User ID: `michal.fiech@gmail.com`
- MCP Config ID: `a06cbb3a-cc69-4ee6-8bb3-be7bb30a6cb3`
- Gmail Auth Config: `ac_iAjd2trEsUx4`
- Calendar Auth Config: `ac_RojXkl42zm7s`

## Important Patterns & Guidelines

### Prompt Engineering (from .cursor/rules)
- Use appropriate prompting strategies: classification (few-shot), extraction (structured JSON), instruction-following (zero-shot)
- Gather missing context proactively with follow-up questions
- Include relevant context and role definitions
- Enforce strict output format with JSON schemas
- Leverage available tools effectively (Composio, Pinecone)

### Development Workflow (from .cursor/rules)
- Work on feature branches, not main
- Pull latest main before creating new features
- Stage all changes before committing
- Write descriptive commit messages covering all branch changes
- Push to remote: `git@github.com:MFiech/pm-copilot.git`

### Debugging Guidelines
- Backend container: `pm-copilot-backend`
- Check MongoDB "conversations" collection for recent document saves
- Use explicit logging for complex data flows
- Frontend logs require explicit requests if not extractable

### Code Quality Standards
- Python virtual environment is required (`myenv/bin/activate`)
- All langchain packages installed without version pinning
- MongoDB required for proper application function
- Maintain backward compatibility with existing APIs

## API Endpoints

**Core Endpoints:**
- `POST /chat` - Send query and get AI response
- `GET /threads` - List all conversation threads  
- `GET /chat/<thread_id>` - Get thread message history
- `POST /save_insight` - Save insight to vector database

**Composio Endpoints:**
- Email search and retrieval
- Calendar event management
- Contact synchronization

## Troubleshooting

**Common Issues:**
- Virtual environment not activated → `source myenv/bin/activate`
- MongoDB connection errors → `brew services start mongodb/brew/mongodb-community@7.0`
- Frontend build errors → `rm -rf node_modules package-lock.json && npm install`

**Database Debugging:**
- Check conversations collection in MongoDB for recent saves
- Verify Pinecone index "personal" namespace "saved_insights"
- Test connections with ping commands

