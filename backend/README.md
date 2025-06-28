# Backend

Backend for PM Co-Pilot application with Composio integration for Gmail and Google Calendar.

## Features

- Flask server to handle API requests
- LangChain for LLM interactions (Anthropic Claude & Google Gemini)
- Pinecone for vector storage and retrieval (RAG)
- MongoDB for storing conversation history and insights
- Composio for connecting to external tools like Gmail and Google Calendar

## Setup

1.  **Activate Virtual Environment**:
    Make sure you have activated the Python virtual environment created in the root setup.
    ```bash
    source myenv/bin/activate
    ```

2.  **Environment Variables**:
    Create a `.env` file in this directory and add your API keys:
    ```
    PINECONE_API_TOKEN=your_pinecone_api_key
    OPENAI_API_KEY=your_openai_api_key
    ANTHROPIC_API_KEY=your_anthropic_api_key
    GOOGLE_API_KEY=your_google_api_key # For Gemini summarization
    ```

3.  **Run the Server**:
    ```bash
    python app.py
    ```
    The server will start on `http://localhost:5001`.

## Composio Integration

The application uses Composio to access Gmail and Google Calendar data when the user requests it. The integration works by:

1.  Initializing the `ComposioService`.
2.  Using the service to process natural language queries related to emails or calendar events.
3.  The service calls the appropriate Composio tools (e.g., `GMAIL_SEARCH_EMAILS`, `GOOGLECALENDAR_GET_EVENTS`).
4.  The results are then formatted and passed to the LLM to generate a response.

To use the Composio integration, ensure you have connected your GMail and Google Calendar accounts in the Composio dashboard and have the server IDs correctly configured in `composio_service.py`.

## Mock Service

For development without live tool access, you can adapt the `ComposioService` to return mock data. This can be done by modifying the methods in `composio_service.py` to return static JSON responses instead of making live API calls. 