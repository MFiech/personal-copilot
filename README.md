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

### Requirements

- Python 3.8+
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

1. Install backend dependencies:
   ```
   cd backend
   pip install -r requirements.txt
   ```

2. Install frontend dependencies:
   ```
   cd frontend
   npm install
   ```

## Running the Application

### Backend

Start the Flask server:

```
cd backend
python app.py
```

The server will run on `http://localhost:5001`.

### Frontend

Start the frontend development server:

```
cd frontend
npm run dev
```

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
- Pinecone vector database (index: "personal", namespace: "saved_insights")
- SQLite database for conversation history