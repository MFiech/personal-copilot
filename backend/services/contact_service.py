import time
import logging
from composio import ComposioToolSet, Action
from models.contact import Contact
from models.contact_sync_log import ContactSyncLog

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ContactSyncService:
    def __init__(self):
        self.composio_toolset = ComposioToolSet()
        
    def sync_gmail_contacts(self, full_sync=True):
        """
        Sync contacts from Gmail using Composio and manages them in our database.
        
        Args:
            full_sync (bool): If True, performs full sync. If False, incremental sync.
            
        Returns:
            dict: Sync results with statistics
        """
        sync_log = ContactSyncLog(sync_type="gmail_contacts")
        sync_log.start_sync()
        
        try:
            logger.info("Starting Gmail contacts sync...")
            
            # Get Gmail contacts via Composio
            # Note: Using generic Action name - needs to be updated with actual Composio action
            contacts_data = self._fetch_gmail_contacts_from_composio()
            
            sync_stats = {
                'total_fetched': len(contacts_data),
                'total_processed': 0,
                'new_contacts': 0,
                'updated_contacts': 0,
                'errors': []
            }
            
            # Process each contact
            skipped_no_email = 0
            for contact_data in contacts_data:
                try:
                    result = self._process_contact_data(contact_data)
                    sync_stats['total_processed'] += 1
                    
                    if result['action'] == 'created':
                        sync_stats['new_contacts'] += 1
                    elif result['action'] == 'updated':
                        sync_stats['updated_contacts'] += 1
                        
                except Exception as e:
                    error_msg = str(e)
                    if "has no email addresses - skipping" in error_msg:
                        # This is expected - contacts without emails
                        skipped_no_email += 1
                        logger.debug(error_msg)
                    else:
                        # This is a real error
                        logger.error(f"Error processing contact: {error_msg}")
                        sync_log.add_error(error_msg, contact_data)
                        sync_stats['errors'].append(error_msg)
            
            # Add skipped count to stats
            sync_stats['skipped_no_email'] = skipped_no_email
            
            # Complete sync
            sync_log.complete_sync(sync_stats)
            logger.info(f"Contacts sync completed: {sync_stats}")
            
            return {
                'success': True,
                'sync_id': sync_log.sync_id,
                'stats': sync_stats
            }
            
        except Exception as e:
            error_msg = f"Critical error during sync: {str(e)}"
            logger.error(error_msg)
            sync_log.fail_sync(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'sync_id': sync_log.sync_id
            }
    
    def _fetch_gmail_contacts_from_composio(self):
        """
        Fetch ALL contacts from Gmail using Composio GMAIL_GET_CONTACTS action with pagination
        """
        all_connections = []
        page_token = None
        page_number = 1
        max_pages = 50  # Safety limit to prevent infinite loops (1135 contacts / 100 per page = ~12 pages needed)
        
        try:
            logger.info("Fetching ALL contacts from Gmail via Composio with pagination...")
            
            while page_number <= max_pages:
                logger.info(f"Fetching page {page_number}" + (f" (token: {page_token[:20]}...)" if page_token else " (first page)"))
                
                # Use the correct Composio action for getting Gmail contacts
                result = self.composio_toolset.execute_action(
                    action=Action.GMAIL_GET_CONTACTS,
                    params={
                        "resource_name": "people/me",
                        "person_fields": "names,emailAddresses,phoneNumbers,metadata",
                        "page_token": page_token
                    }
                )
                
                # Check if the action was successful
                if not result.get('successful', False):
                    error_msg = result.get('error', 'Unknown error from Composio')
                    logger.error(f"Composio action failed on page {page_number}: {error_msg}")
                    break
                
                # Extract data from successful response - handle nested structure
                data = result.get('data', {})
                
                # Try both possible structures based on your example
                connections = []
                next_page_token = None
                total_items = 0
                
                if 'response_data' in data:
                    # Structure: data.response_data.connections
                    response_data = data.get('response_data', {})
                    connections = response_data.get('connections', [])
                    next_page_token = response_data.get('nextPageToken')
                    total_items = response_data.get('totalItems', 0)
                    if page_number == 1:
                        logger.info(f"Found response_data structure with {total_items} total items across all pages")
                else:
                    # Fallback: data.connections
                    connections = data.get('connections', [])
                    next_page_token = data.get('nextPageToken')
                    if page_number == 1:
                        logger.info(f"Using direct data.connections structure")
                
                # Add this page's connections to our collection
                all_connections.extend(connections)
                logger.info(f"Page {page_number}: fetched {len(connections)} contacts (total so far: {len(all_connections)})")
                
                # Check if there are more pages
                if not next_page_token:
                    logger.info(f"No more pages. Completed pagination at page {page_number}")
                    break
                
                # Prepare for next page
                page_token = next_page_token
                page_number += 1
            
            if page_number > max_pages:
                logger.warning(f"Reached maximum page limit ({max_pages}). There might be more contacts.")
            
            logger.info(f"Successfully fetched {len(all_connections)} total contacts from Gmail across {page_number-1} pages")
            return all_connections
                
        except Exception as e:
            logger.error(f"Error fetching contacts from Composio: {str(e)}")
            # Return what we have so far
            return all_connections
    
    def _process_contact_data(self, contact_data):
        """
        Process a single contact from Google People API data
        
        Args:
            contact_data (dict): Contact data from Google People API
            
        Returns:
            dict: Processing result with action taken
        """
        try:
            # Extract email addresses
            email_addresses = contact_data.get('emailAddresses', [])
            if not email_addresses:
                # Skip contacts without email addresses
                contact_name = "Unknown"
                names = contact_data.get('names', [])
                if names:
                    contact_name = names[0].get('displayName', 'Unknown')
                logger.debug(f"Skipping contact '{contact_name}' - no email addresses")
                raise ValueError(f"Contact '{contact_name}' has no email addresses - skipping")
            
            # Process all emails into our format
            processed_emails = []
            primary_email = None
            
            for email_data in email_addresses:
                email_obj = {
                    "email": email_data['value'],
                    "is_primary": email_data.get('metadata', {}).get('primary', False),
                    "is_obsolete": None,  # We'll set this based on Google's format if available
                    "metadata": email_data.get('metadata', {})
                }
                
                # Check if this email is marked as obsolete in Google Contacts
                if email_data.get('metadata', {}).get('verified', True) == False:
                    email_obj["is_obsolete"] = True
                
                processed_emails.append(email_obj)
                
                # Track primary email
                if email_obj["is_primary"]:
                    primary_email = email_obj["email"]
            
            # If no primary was found, make the first one primary
            if not primary_email and processed_emails:
                processed_emails[0]["is_primary"] = True
                primary_email = processed_emails[0]["email"]
            
            # Extract name
            names = contact_data.get('names', [])
            if not names:
                raise ValueError("Contact has no names")
            
            # Use primary name or first name
            primary_name = None
            for name in names:
                if name.get('metadata', {}).get('primary', False):
                    primary_name = name.get('displayName') or f"{name.get('givenName', '')} {name.get('familyName', '')}".strip()
                    break
            
            if not primary_name:
                first_name = names[0]
                primary_name = first_name.get('displayName') or f"{first_name.get('givenName', '')} {first_name.get('familyName', '')}".strip()
            
            # Extract phone numbers
            phone_numbers = contact_data.get('phoneNumbers', [])
            primary_phone = None
            if phone_numbers:
                for phone in phone_numbers:
                    if phone.get('metadata', {}).get('primary', False):
                        primary_phone = phone['value']
                        break
                if not primary_phone:
                    primary_phone = phone_numbers[0]['value']
            
            # Create metadata
            metadata = {
                'resourceName': contact_data.get('resourceName'),
                'etag': contact_data.get('etag'),
                'sources': contact_data.get('metadata', {}).get('sources', [])
            }
            
            # Create or update contact
            contact = Contact(
                emails=processed_emails,
                name=primary_name,
                phone=primary_phone,
                source="gmail_contacts",
                metadata=metadata
            )
            
            contact_id = contact.save()
            
            # Determine if this was a creation or update
            existing_contact = Contact.get_by_email(primary_email)
            action = 'updated' if existing_contact else 'created'
            
            return {
                'action': action,
                'contact_id': contact_id,
                'primary_email': primary_email,
                'emails': processed_emails
            }
            
        except Exception as e:
            raise Exception(f"Failed to process contact data: {str(e)}")
    
    def get_sync_status(self, sync_id=None):
        """
        Get status of a specific sync or the latest sync
        
        Args:
            sync_id (str, optional): Specific sync ID to check
            
        Returns:
            dict: Sync status information
        """
        if sync_id:
            sync_log = ContactSyncLog.get_by_sync_id(sync_id)
        else:
            sync_log = ContactSyncLog.get_latest_sync("gmail_contacts")
        
        if not sync_log:
            return {"error": "No sync found"}
        
        return sync_log
    
    def get_sync_history(self, limit=10):
        """
        Get history of contact syncs
        
        Args:
            limit (int): Number of sync records to return
            
        Returns:
            list: List of sync records
        """
        return ContactSyncLog.get_sync_history(limit=limit, sync_type="gmail_contacts")
    
    def cleanup_old_sync_logs(self, days_to_keep=30):
        """
        Clean up old sync logs
        
        Args:
            days_to_keep (int): Number of days of logs to keep
            
        Returns:
            int: Number of records deleted
        """
        return ContactSyncLog.cleanup_old_logs(days_to_keep)
    
    def get_contact_stats(self):
        """
        Get contact statistics
        
        Returns:
            dict: Contact statistics
        """
        return Contact.get_stats()
    
    def search_contacts(self, query, limit=20):
        """
        Search contacts by name or email using both local database and Gmail search
        
        Args:
            query (str): Search query
            limit (int): Maximum number of results
            
        Returns:
            list: List of matching contacts
        """
        # First search local database
        local_results = Contact.search_by_name(query, limit)
        
        # If we have enough results from local DB, return them
        if len(local_results) >= limit:
            return local_results
        
        # Otherwise, try searching Gmail directly for fresh results
        try:
            gmail_results = self._search_gmail_contacts(query, limit)
            
            # Combine and deduplicate results (prioritize local DB results)
            combined_results = local_results.copy()
            local_emails = {contact['primary_email'] for contact in local_results}
            
            for contact in gmail_results:
                if contact['primary_email'] not in local_emails:
                    combined_results.append(contact)
                    if len(combined_results) >= limit:
                        break
            
            return combined_results[:limit]
            
        except Exception as e:
            logger.error(f"Error searching Gmail contacts: {str(e)}")
            return local_results
    
    def _search_gmail_contacts(self, query, limit=20):
        """
        Search Gmail contacts using Composio GMAIL_SEARCH_PEOPLE action
        
        Args:
            query (str): Search query
            limit (int): Maximum number of results (capped at 30 by API)
            
        Returns:
            list: List of matching contacts from Gmail
        """
        try:
            logger.info(f"Searching Gmail contacts for query: '{query}'")
            
            # Use the correct Composio action for searching Gmail contacts
            result = self.composio_toolset.execute_action(
                action=Action.GMAIL_SEARCH_PEOPLE,
                params={
                    "query": query,
                    "pageSize": min(limit, 30),  # API caps at 30
                    "person_fields": "names,emailAddresses,phoneNumbers",
                    "other_contacts": True  # Include "Other Contacts" (auto-created from emails)
                }
            )
            
            logger.info(f"Gmail search response: {result}")
            
            # Check if the action was successful
            if not result.get('successful', False):
                error_msg = result.get('error', 'Unknown error from Composio')
                logger.error(f"Gmail search failed: {error_msg}")
                return []
            
            # Extract data from successful response
            data = result.get('data', {})
            people = data.get('people', [])
            
            logger.info(f"Found {len(people)} contacts in Gmail search")
            
            # Process the search results into our contact format
            processed_contacts = []
            for person_data in people:
                try:
                    contact_dict = self._process_contact_data_to_dict(person_data)
                    processed_contacts.append(contact_dict)
                except Exception as e:
                    logger.error(f"Error processing search result: {str(e)}")
                    continue
            
            return processed_contacts
                
        except Exception as e:
            logger.error(f"Error searching Gmail contacts: {str(e)}")
            return []
    
    def _process_contact_data_to_dict(self, contact_data):
        """
        Process contact data from Gmail API into a dictionary format
        (without saving to database)
        
        Args:
            contact_data (dict): Contact data from Google People API
            
        Returns:
            dict: Contact data in our standard format
        """
        # Extract email addresses
        email_addresses = contact_data.get('emailAddresses', [])
        if not email_addresses:
            raise ValueError("Contact has no email addresses")
        
        # Use primary email or first email
        primary_email = None
        for email in email_addresses:
            if email.get('metadata', {}).get('primary', False):
                primary_email = email['value']
                break
        
        if not primary_email:
            primary_email = email_addresses[0]['value']
        
        # Extract name
        names = contact_data.get('names', [])
        if not names:
            raise ValueError("Contact has no names")
        
        # Use primary name or first name
        primary_name = None
        for name in names:
            if name.get('metadata', {}).get('primary', False):
                primary_name = name.get('displayName') or f"{name.get('givenName', '')} {name.get('familyName', '')}".strip()
                break
        
        if not primary_name:
            first_name = names[0]
            primary_name = first_name.get('displayName') or f"{first_name.get('givenName', '')} {first_name.get('familyName', '')}".strip()
        
        # Extract phone numbers
        phone_numbers = contact_data.get('phoneNumbers', [])
        primary_phone = None
        if phone_numbers:
            for phone in phone_numbers:
                if phone.get('metadata', {}).get('primary', False):
                    primary_phone = phone['value']
                    break
            if not primary_phone:
                primary_phone = phone_numbers[0]['value']
        
        # Create metadata
        metadata = {
            'resourceName': contact_data.get('resourceName'),
            'etag': contact_data.get('etag'),
            'sources': contact_data.get('metadata', {}).get('sources', [])
        }
        
        return {
            'primary_email': primary_email,
            'emails': [{'email': primary_email, 'is_primary': True, 'is_obsolete': None, 'metadata': None}],
            'name': primary_name,
            'phone': primary_phone,
            'source': "gmail_search",
            'metadata': metadata
        }
    
    def get_all_contacts(self, limit=100, offset=0):
        """
        Get all contacts with pagination
        
        Args:
            limit (int): Number of contacts per page
            offset (int): Offset for pagination
            
        Returns:
            list: List of contacts
        """
        return Contact.get_all(limit, offset)
    
    def delete_all_contacts(self):
        """
        Delete all contacts - for testing purposes only
        
        Returns:
            int: Number of contacts deleted
        """
        logger.warning("Deleting all contacts!")
        return Contact.delete_all() 