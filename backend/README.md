# PM Co-Pilot Backend

Backend for PM Co-Pilot application with VeyraX integration for Gmail and Google Calendar.

## VeyraX Integration

The application uses VeyraX to access Gmail and Google Calendar data when the user requests it. The integration works by:

1. Using LLM-based intent detection to identify when users ask for email or calendar data
2. Requesting user confirmation before accessing their data
3. Using VeyraX API to fetch the requested data
4. Presenting the formatted data to the user

### Setup

To use the VeyraX integration:

1. Get a VeyraX API key from your account
2. Add it to the `.env` file as `VEYRAX_API_KEY=your-key-here`
3. Connect your Gmail and Google Calendar accounts in the VeyraX dashboard
4. Ensure `USE_MOCK_VEYRAX` is set to `False` in `app.py`

### Troubleshooting

If you encounter authentication errors:

1. Run the test script to check your VeyraX connection:
   ```
   python scripts/test_veyrax_status.py
   ```

2. Common issues:
   - **"Invalid authentication"**: Your Gmail or Calendar accounts are not properly connected in VeyraX
   - **"404 Not Found"**: The endpoint or service doesn't exist or is unavailable in your VeyraX plan
   - **"500 Server Error"**: VeyraX encountered an internal error when trying to access your data

3. Resolution steps:
   - Check that your VeyraX API key is correct
   - Log in to VeyraX dashboard
   - Go to Connections/Integrations section
   - Connect or reconnect your Gmail and Google Calendar accounts
   - Make sure you've granted the necessary permissions

### Using Mock Mode

If you're developing without VeyraX access or encounter persistent issues:

1. Set `USE_MOCK_VEYRAX = True` in `app.py` to use mock data
2. The mock service will generate realistic fake email and calendar data for testing
3. This allows you to develop and test the application UI without real data access

## Running the Application

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Start the backend server:
   ```
   python app.py
   ```

3. The server will be available at http://localhost:5001 