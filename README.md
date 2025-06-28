# PM Co-Pilot

PM Co-Pilot is an AI-powered assistant designed to supercharge your productivity by integrating with your personal applications like Gmail and Google Calendar. It uses a sophisticated RAG (Retrieval-Augmented Generation) model to provide context-aware assistance and allows you to take action on your data directly from the chat interface.

## Features

- **Conversational AI:** Chat with your data using natural language.
- **RAG-based Insights:** The application leverages a Pinecone vector database to provide answers based on your saved insights and conversation history.
- **Tooling Integration:** Connects with Gmail and Google Calendar via Composio to fetch, display, and manage your emails and events.
- **Interactive UI:** A clean, modern interface built with React that allows you to interact with your data in real-time.
- **Secure and Private:** Your data is your own. The application runs locally, and you control all connections to your personal apps.

## Tech Stack

- **Backend:** Flask, LangChain, OpenAI, Anthropic, Pinecone, MongoDB
- **Frontend:** React, Material-UI
- **Integrations:** Composio (for Gmail, Google Calendar)

## Setup and Installation

### Prerequisites

- Python 3.10+
- Node.js 16+
- Pinecone API key
- OpenAI API key
- Anthropic API key
- Google API key (for certain LLM features)

### Backend Setup

1.  Navigate to the `backend` directory: `cd backend`
2.  Create a virtual environment: `python -m venv myenv`
3.  Activate the environment: `source myenv/bin/activate` (macOS/Linux) or `myenv\Scripts\activate` (Windows)
4.  Install dependencies: `pip install -r requirements.txt`
5.  Create a `.env` file in the `backend` directory and add your API keys:

    ```
    PINECONE_API_TOKEN=your_pinecone_api_key
    OPENAI_API_KEY=your_openai_api_key
    ANTHROPIC_API_KEY=your_anthropic_api_key
    GOOGLE_API_KEY=your_google_api_key
    ```
6.  To connect to your tools, you will need to set up Composio. Follow their documentation to get your GMail and Google Calendar connected.
7.  Run the backend server: `python app.py`

### Frontend Setup

1.  Navigate to the `frontend` directory: `cd frontend`
2.  Install dependencies: `npm install`
3.  Run the frontend development server: `npm start`

The application should now be running on `http://localhost:3000`.

## Project Structure

(Details about the project structure can be added here)

## Contributing

(Details on how to contribute can be added here)

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