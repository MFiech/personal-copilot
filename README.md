# PM Co-Pilot

A conversational AI assistant that uses a vector database to provide context-aware responses.

## Overview

PM Co-Pilot is an AI-powered assistant that:
- Stores and retrieves information from a vector database (Pinecone)
- Uses OpenAI embeddings and Anthropic Claude for language processing
- Maintains conversation history and thread context
- Allows saving user insights for future retrieval
- Integrates with Gmail and Google Calendar via VeyraX (optional)

## Setup

### System Requirements

- **macOS**: Xcode Command Line Tools (for MongoDB installation)
- **Python**: 3.11+ (recommended: 3.13)
- **Node.js**: 18+ and npm
- **MongoDB**: 7.0+ (will be installed via Homebrew)

### API Keys Required

- Pinecone account and API key
- OpenAI API key
- Anthropic API key
- VeyraX API key (optional, for Gmail/Calendar integration)

### Environment Variables

Create a `.env` file in the `backend` directory with the following:

```
PINECONE_API_TOKEN=your_pinecone_api_key
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
VEYRAX_API_KEY=your_veyrax_api_key  # Optional, for Gmail/Calendar
```

### Installation

#### 1. Install System Dependencies

**macOS:**
```bash
# Install Xcode Command Line Tools (if not already installed)
xcode-select --install

# Install MongoDB via Homebrew
brew tap mongodb/brew
brew install mongodb-community@7.0

# Start MongoDB service
brew services start mongodb/brew/mongodb-community@7.0
```

#### 2. Setup Python Virtual Environment

```bash
# Create virtual environment
python3 -m venv myenv

# Activate virtual environment
source myenv/bin/activate
```

#### 3. Install Backend Dependencies

```bash
cd backend
pip install -r requirements.txt
```

#### 4. Install Frontend Dependencies

```bash
cd frontend
npm install
```

## Running the Application

### Backend

**Important**: Always activate the virtual environment before running the backend.

```bash
# Activate virtual environment
source myenv/bin/activate

# Navigate to backend directory
cd backend

# Start the Flask server
python3 app.py
```

The server will run on `http://localhost:5001`.

### Frontend

```bash
cd frontend
npm run dev
```

The frontend will run on `http://localhost:3000`.

## Adding Data

You can add data to the vector database in two ways:

### 1. Using the `/save_insight` API Endpoint

Send a POST request to `/save_insight` with a JSON body containing the content:

```json
{
  "content": "Your insight text here"
}
```

This will store the text in the Pinecone database for future retrieval.

### 2. Using the Data Pipeline

1. Create a folder named `data` in the project root
2. Add text files in the format:
   ```
   Text content goes here.
   Multiple paragraphs are allowed.
   
   Metadata: key1=value1, key2=value2, key3=value3
   ```
3. Run the data pipeline script:
   ```
   cd backend/scripts
   python update_data_pipeline.py
   ```

## API Endpoints

- `/chat` (POST): Send a query and get an AI response
- `/threads` (GET): Get a list of all conversation threads
- `/chat/<thread_id>` (GET): Get the message history for a specific thread
- `/save_insight` (POST): Save a new insight to the vector database
- `/veyrax/check` (GET): Check VeyraX configuration status

## Gmail and Google Calendar Integration

For instructions on setting up Gmail and Google Calendar integration via VeyraX, see [README-VEYRAX.md](README-VEYRAX.md).

## Database Structure

The application uses:
- **Pinecone vector database** (index: "personal", namespace: "saved_insights")
- **MongoDB** for conversation history and user data
- **SQLite** (legacy, may be used for some features)

## Troubleshooting

### Common Issues

1. **"ModuleNotFoundError: No module named 'flask'"**
   - Make sure you've activated the virtual environment: `source myenv/bin/activate`
   - Verify you're using the correct Python: `which python3` should point to `myenv/bin/python3`

2. **MongoDB Connection Error**
   - Ensure MongoDB is running: `brew services start mongodb/brew/mongodb-community@7.0`
   - Test connection: `mongosh --eval "db.runCommand('ping')"`

3. **Frontend Build Errors**
   - Clear node_modules and reinstall: `rm -rf node_modules package-lock.json && npm install`

### Development Notes

- The backend uses Python 3.13 with a virtual environment to manage dependencies
- All langchain-related packages are installed without version pinning to avoid conflicts
- MongoDB is required for the application to function properly