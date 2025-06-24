import requests
import os

class VeyraXService:
    def __init__(self, api_key, base_url="https://api.veyrax.com/v1"):
        """Initialize the VeyraX service client."""
        if not api_key:
            raise ValueError("VeyraX API key is required.")
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        })
        print(f"VeyraXService initialized with base URL: {self.base_url}")

    def check_auth(self):
        """Placeholder for checking VeyraX authentication."""
        # This is a simplified check. A real check might involve a specific endpoint.
        # For now, we'll assume if the key is present, it might be valid.
        # print("Attempting to check VeyraX authentication (placeholder)...")
        # try:
        #     response = self.session.get(f"{self.base_url}/user/profile") # Example endpoint
        #     if response.status_code == 200:
        #         print("VeyraX authentication successful (placeholder check).")
        #         return True
        #     else:
        #         print(f"VeyraX authentication failed (placeholder check). Status: {response.status_code}, Response: {response.text}")
        #         return False
        # except requests.RequestException as e:
        #     print(f"Error during VeyraX authentication check (placeholder): {e}")
        #     return False
        print("VeyraX authentication check is a placeholder. Assuming valid if API key provided.")
        return True # In app.py, it uses this. For now, keep it simple.
    
    def process_query(self, query, thread_history):
        """Placeholder for processing a query via VeyraX."""
        print(f"[VeyraXService] process_query called with query: '{query}'. This is a placeholder.")
        # This would involve calling the actual VeyraX API to get emails, calendar events etc.
        # Based on the query and history.
        # Returning a mock structure for now to allow app.py to function.
        if "email" in query.lower():
            return {
                "source_type": "gmail",
                "data": {
                    "messages": [
                        # {"id": "mock_email_1", "subject": "Mock Email 1", "from_email": {"name": "Mock Sender"}, "date": "2023-01-01T10:00:00Z"}
                    ]
                }
            }
        elif "calendar" in query.lower() or "event" in query.lower():
            return {
                "source_type": "google-calendar",
                "data": {
                    "events": [
                        # {"id": "mock_event_1", "summary": "Mock Event 1", "start": {"dateTime": "2023-01-01T12:00:00Z"}, "end": {"dateTime": "2023-01-01T13:00:00Z"}}
                    ]
                }
            }
        return None

    def delete_email(self, message_id):
        """Delete an email using VeyraX API."""
        print(f"[VeyraXService] Attempting to delete email with ID: {message_id}")
        if not message_id:
            print("[VeyraXService] Error: No message_id provided for email deletion.")
            return {'success': False, 'reason': 'missing_id', 'details': 'No message_id provided'}
        
        try:
            target_url = f"{self.base_url}/emails/{message_id}"
            print(f"[VeyraXService] Calling VeyraX DELETE: {target_url}")
            response = self.session.delete(target_url)
            
            if response.status_code == 200 or response.status_code == 204: # 204 No Content is also success
                print(f"[VeyraXService] Successfully deleted email with ID: {message_id}. Status: {response.status_code}")
                return {'success': True, 'reason': 'deleted', 'details': 'Email successfully deleted'}
            else:
                response_data = {}
                error_detail_text = response.text
                try:
                    response_data = response.json()
                    # Try to get a more specific error message if available
                    error_detail_text = response_data.get('error', response_data.get('message', response.text))
                    if isinstance(response_data.get('data'), dict):
                         error_detail_text = response_data.get('data').get('error', error_detail_text)
                except ValueError: # Not a JSON response
                    pass # error_detail_text remains response.text
                
                reason = 'not_found' if response.status_code == 404 or 'not found' in error_detail_text.lower() else 'api_error'
                
                print(f"[VeyraXService] Failed to delete email {message_id}. Status: {response.status_code}, Reason: {reason}, Detail: {error_detail_text}")
                return {'success': False, 'reason': reason, 'details': error_detail_text}
        except requests.RequestException as e:
            print(f"[VeyraXService] RequestException during email deletion for {message_id}: {e}")
            return {'success': False, 'reason': 'request_exception', 'details': str(e)}
        except Exception as e:
            print(f"[VeyraXService] Unexpected error deleting email {message_id}: {e}")
            return {'success': False, 'reason': 'unknown_exception', 'details': str(e)}

    def delete_calendar_event(self, event_id):
        """Delete a calendar event using VeyraX API."""
        print(f"[VeyraXService] Attempting to delete calendar event with ID: {event_id}")
        if not event_id:
            print("[VeyraXService] Error: No event_id provided for calendar event deletion.")
            return {'success': False, 'reason': 'missing_id', 'details': 'No event_id provided'}

        try:
            target_url = f"{self.base_url}/calendar/events/{event_id}"
            print(f"[VeyraXService] Calling VeyraX DELETE: {target_url}")
            response = self.session.delete(target_url)

            if response.status_code == 200 or response.status_code == 204: 
                print(f"[VeyraXService] Successfully deleted calendar event with ID: {event_id}. Status: {response.status_code}")
                return {'success': True, 'reason': 'deleted', 'details': 'Calendar event successfully deleted'}
            else:
                response_data = {}
                error_detail_text = response.text
                try:
                    response_data = response.json()
                    error_detail_text = response_data.get('error', response_data.get('message', response.text))
                    if isinstance(response_data.get('data'), dict):
                         error_detail_text = response_data.get('data').get('error', error_detail_text)
                except ValueError: 
                    pass
                
                reason = 'not_found' if response.status_code == 404 or 'not found' in error_detail_text.lower() else 'api_error'
                
                print(f"[VeyraXService] Failed to delete calendar event {event_id}. Status: {response.status_code}, Reason: {reason}, Detail: {error_detail_text}")
                return {'success': False, 'reason': reason, 'details': error_detail_text}
        except requests.RequestException as e:
            print(f"[VeyraXService] RequestException during calendar event deletion for {event_id}: {e}")
            return {'success': False, 'reason': 'request_exception', 'details': str(e)}
        except Exception as e:
            print(f"[VeyraXService] Unexpected error deleting calendar event {event_id}: {e}")
            return {'success': False, 'reason': 'unknown_exception', 'details': str(e)}

# Example usage (for testing, not part of the service class itself)
if __name__ == '__main__':
    print("VeyraXService module loaded.")
    # Mock API key for local testing if needed, ensure it's not committed.
    # test_api_key = os.getenv("VEYRAX_API_KEY", "your_mock_api_key_here_if_not_in_env") 
    # if test_api_key == "your_mock_api_key_here_if_not_in_env":
    #     print("Warning: Using a mock API key for VeyraXService testing.")
    
    # try:
    #     service = VeyraXService(api_key=test_api_key)
    #     print("VeyraXService instance created for testing.")
    #     # Test auth check
    #     # service.check_auth()
    #     # Test email deletion (replace with a *non-existent or test* ID if actually running against a live service)
    #     # service.delete_email("test_email_id_123")
    #     # Test event deletion
    #     # service.delete_calendar_event("test_event_id_456")
    # except ValueError as ve:
    #     print(f"Failed to initialize VeyraXService for testing: {ve}")
    # except Exception as ex:
    #     print(f"An error occurred during VeyraXService testing: {ex}") 