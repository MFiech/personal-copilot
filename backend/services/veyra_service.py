    def delete_email(self, message_id):
        """Delete an email using VeyraX API"""
        try:
            if not message_id:
                print("Error: No message_id provided")
                return False
            
            print(f"Calling VeyraX API to delete email with ID: {message_id}")
            response = self.session.delete(f"{self.base_url}/emails/{message_id}")
            
            if response.status_code == 200:
                print(f"Successfully deleted email with ID: {message_id}")
                return True
            else:
                print(f"Failed to delete email. Status code: {response.status_code}")
                print(f"Response: {response.text}")
                return False
            
        except Exception as e:
            print(f"Error deleting email: {e}")
            return False 