import React, { useState, useEffect } from 'react';
import { 
  Card, 
  Typography, 
  Box, 
  IconButton, 
  Menu, 
  MenuItem,
  Grid,
  Paper,
  Button,
  List,
  ListItem,
  ListItemText,
  Checkbox
} from '@mui/material';
import MoreVertIcon from '@mui/icons-material/MoreVert';
import ClearAllIcon from '@mui/icons-material/ClearAll';
import DeleteIcon from '@mui/icons-material/Delete';
import NotesIcon from '@mui/icons-material/Notes';
import VisibilityIcon from '@mui/icons-material/Visibility';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import DoneAllIcon from '@mui/icons-material/DoneAll';
import CircularProgress from '@mui/material/CircularProgress';
import './VeyraResults.css';

const VeyraResults = ({ results, currentThreadId, message_id, onNewMessageReceived, showSnackbar }) => {
  const [anchorEl, setAnchorEl] = useState(null);
  const [selectedItem, setSelectedItem] = useState(null);
  const [deletedEmails, setDeletedEmails] = useState(new Set());
  const [deletedEvents, setDeletedEvents] = useState(new Set());
  const [clickedElement, setClickedElement] = useState(null);
  const [selectedTiles, setSelectedTiles] = useState({});
  const [isBulkDeleting, setIsBulkDeleting] = useState(false);
  const [isSummarizingEmail, setIsSummarizingEmail] = useState(false);

  // States for email pagination
  const [displayedEmails, setDisplayedEmails] = useState([]);
  const [currentEmailOffset, setCurrentEmailOffset] = useState(0);
  const [limitPerPage, setLimitPerPage] = useState(0); // Will be set from initial results
  const [totalEmailsAvailable, setTotalEmailsAvailable] = useState(0);
  const [canLoadMoreEmails, setCanLoadMoreEmails] = useState(false);
  const [isLoadingMoreEmails, setIsLoadingMoreEmails] = useState(false);

  useEffect(() => {
    if (results) {
        // Ensure we have a valid array of emails, even if empty
        const emails = results.veyra_results?.emails || [];
        setDisplayedEmails(emails);
        
        const initialOffset = results.veyra_current_offset || 0;
        const initialLimit = results.veyra_limit_per_page || 10;
        const initialTotal = results.veyra_total_emails_available || 0;

        setCurrentEmailOffset(initialOffset);
        setLimitPerPage(initialLimit);
        setTotalEmailsAvailable(initialTotal);

        let canCurrentlyLoadMore;
        if (typeof results.veyra_has_more === 'boolean') {
            canCurrentlyLoadMore = results.veyra_has_more;
            console.log('[VeyraResults useEffect] Using veyra_has_more from props:', canCurrentlyLoadMore);
        } else {
            canCurrentlyLoadMore = (initialOffset + initialLimit) < initialTotal;
            console.log('[VeyraResults useEffect] Calculated canLoadMoreEmails:', canCurrentlyLoadMore, 
                        {offset: initialOffset, limit: initialLimit, total: initialTotal});
        }
        setCanLoadMoreEmails(canCurrentlyLoadMore);

        console.log('[VeyraResults useEffect] Initial pagination state set:', {
            offset: initialOffset,
            limit: initialLimit,
            total: initialTotal,
            hasMoreSource: typeof results.veyra_has_more === 'boolean' ? 'prop' : 'calculated',
            canLoadMore: canCurrentlyLoadMore,
            displayedEmailsCount: emails.length,
            resultsProp: results
        });
    } else {
        // Reset state if results are not available
        setDisplayedEmails([]);
        setCurrentEmailOffset(0);
        setLimitPerPage(10);
        setTotalEmailsAvailable(0);
        setCanLoadMoreEmails(false);
        console.log('[VeyraResults useEffect] No results, resetting pagination state.');
    }
}, [results]);

  console.log('[VeyraResults] Props received (full assistant message object):', { results, currentThreadId, message_id });
  console.log('[VeyraResults] Current selectedTiles:', selectedTiles);

  const formatEventDateTime = (dateTime) => {
    try {
      if (!dateTime) return 'No date';
      const date = new Date(dateTime);
      if (isNaN(date.getTime())) {
        console.error('Invalid date:', dateTime);
        return 'Invalid date';
      }
      
      return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: 'numeric',
        hour12: true
      });
    } catch (e) {
      console.error('Error formatting date:', e);
      return 'Invalid date';
    }
  };

  const handleMenuClick = (event, item) => {
    setAnchorEl(event.currentTarget);
    setSelectedItem(item);
    // Save the nearest Card element that has a data attribute
    const cardElement = event.currentTarget.closest('[data-email-id], [data-event-id]');
    setClickedElement(cardElement);
    console.log('[VeyraResults] Menu clicked for item:', item, 'Card element:', cardElement);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
    setSelectedItem(null);
    setClickedElement(null);
  };

  const handleAction = async (action, item) => {
    console.log(`[VeyraResults] Action: ${action} for item:`, item);
    if (action === 'delete') {
      // Check if this is a calendar event or an email
      if (item.start) { // This is a calendar event
        try {
          // Get the event ID from the data attribute on the card element
          let currentEventId = item.id;
          
          // If we have a clicked element with data-event-id, use that instead
          if (clickedElement && clickedElement.dataset.eventId) {
            currentEventId = clickedElement.dataset.eventId;
          }
          
          if (!currentEventId || !currentThreadId || !message_id) {
            console.error('Missing required IDs:', { 
              id: currentEventId, 
              thread_id: currentThreadId,
              message_id: message_id 
            });
            showSnackbar('Could not find required IDs for deletion. Please try again.', 'error');
            return;
          }
          
          const payload = {
            message_id: message_id,
            event_id: currentEventId,
            thread_id: currentThreadId
          };
          
          console.log('Sending delete event request with payload:', payload);
          
          const response = await fetch('http://localhost:5001/delete_calendar_event', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify(payload)
          });
          
          const data = await response.json();
          console.log('Delete event response:', data);
          
          // Update UI regardless of API response to ensure events disappear
          setDeletedEvents(prev => {
            const newSet = new Set(prev);
            newSet.add(item.id);
            console.log('[VeyraResults] Updated deletedEvents (optimistic):', newSet);
            return newSet;
          });
          
          if (data.success) {
            console.log('Event successfully deleted');
          } else {
            console.error('Failed to delete event:', data.message);
          }
        } catch (error) {
          console.error('Error deleting event:', error);
          // Even if there's an error, mark the event as deleted in the UI
          setDeletedEvents(prev => {
            const newSet = new Set(prev);
            newSet.add(item.id);
            console.log('[VeyraResults] Updated deletedEvents (error catch):', newSet);
            return newSet;
          });
        } finally {
          handleMenuClose();
          
          // After a delay, remove the event from the deletedEvents set
          setTimeout(() => {
            setDeletedEvents(prev => {
              const newSet = new Set(prev);
              newSet.delete(item.id);
              return newSet;
            });
          }, 2000);
        }
      } else { // This is an email
        try {
          // Get the email ID from the data attribute on the card element
          // This ensures we use the exact same ID that's displayed in the UI
          let currentEmailId = item.id;
          
          // If we have a clicked element with data-email-id, use that instead
          if (clickedElement && clickedElement.dataset.emailId) {
            currentEmailId = clickedElement.dataset.emailId;
            console.log('Using email ID from data attribute:', currentEmailId);
          } else if (!currentEmailId) {
            // Try to extract ID directly from the email object structure
            console.log('No email ID found in element or direct property, examining full email object...');
            const keys = Object.keys(item);
            console.log('Available email object keys:', keys);
            
            // Look for any property that might be an ID (id, message_id, email_id, etc.)
            const potentialIdProps = ['id', 'message_id', 'email_id', 'messageId', 'emailId'];
            for (const prop of potentialIdProps) {
              if (item[prop]) {
                currentEmailId = item[prop];
                console.log(`Found ID in property "${prop}":`, currentEmailId);
                break;
              }
            }
          }
          
          console.log('Email object structure:', {
            id: currentEmailId,
            message_id: message_id,
            thread_id: currentThreadId,
            full_email: item
          });
          
          if (!currentEmailId || !message_id) {
            console.error('Missing required IDs:', { id: currentEmailId, message_id });
            showSnackbar('Could not find email ID for deletion. Please try again.', 'error');
            return;
          }
          
          const payload = {
            message_id: message_id,
            email_id: currentEmailId,
            thread_id: currentThreadId
          };
          
          console.log('Sending delete request with payload:', payload);
          
          const response = await fetch('http://localhost:5001/delete_email', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify(payload)
          });
          
          const data = await response.json();
          console.log('Delete response:', data);
          
          // Update UI regardless of API response to ensure emails disappear
          // This improves UX even if there are backend issues
          setDeletedEmails(prev => {
            const newSet = new Set(prev);
            newSet.add(item.id);
            console.log('[VeyraResults] Updated deletedEmails (optimistic):', newSet);
            return newSet;
          });
          
          if (data.success) {
            console.log('Email successfully deleted');
            // Email was successfully deleted, we can leave it marked as deleted
          } else {
            console.error('Failed to delete email:', data.message);
            // Optionally, show an error message to the user
            // but keep the email marked as deleted in the UI for better UX
          }
        } catch (error) {
          console.error('Error deleting email:', error);
          // Even if there's an error, mark the email as deleted in the UI
          // This improves UX when there are network issues
          setDeletedEmails(prev => {
            const newSet = new Set(prev);
            newSet.add(item.id);
            console.log('[VeyraResults] Updated deletedEmails (error catch):', newSet);
            return newSet;
          });
        } finally {
          handleMenuClose();
          
          // After a delay, remove the email from the deletedEmails set
          // This allows the animation to complete
          setTimeout(() => {
            setDeletedEmails(prev => {
              const newSet = new Set(prev);
              newSet.delete(item.id);
              return newSet;
            });
          }, 2000);
        }
      }
    } else if (action === 'open' && item.htmlLink) {
      // Open calendar event in Google Calendar
      window.open(item.htmlLink, '_blank');
      handleMenuClose();
    }
  };

  if (!results || (!results.veyra_results?.emails?.length && !results.calendar_events?.length)) {
    console.log('[VeyraResults] No results to display');
    return null;
  }

  // --- Methods for tile selection ---
  const makeTileKey = (itemType, itemId) => {
    // Using message_id from props to ensure it's the assistant's message ID
    // Changed delimiter from '-' to '|' for robustness with itemIDs containing hyphens
    return `${message_id}|${itemType}|${itemId}`;
  };

  const handleTileSelect = (itemType, itemId) => {
    const key = makeTileKey(itemType, itemId);
    setSelectedTiles(prev => {
      const newSelected = { ...prev };
      // Toggle selection
      if (newSelected[key]) {
        delete newSelected[key];
      } else {
        newSelected[key] = true;
      }
      console.log('[VeyraResults] Tile selection changed. Key:', key, 'New selectedTiles:', newSelected);
      return newSelected;
    });
  };
  
  const handleSelectAllTiles = () => {
    const newSelected = { ...selectedTiles };
    // Select all displayed emails
    (displayedEmails || []).forEach(email => {
      if (email && email.email_id) { // Ensure email and email.email_id exist
        const key = makeTileKey('email', email.email_id);
        newSelected[key] = true;
      }
    });
    // Select all displayed calendar events
    (results?.calendar_events || []).forEach(event => {
      if (event && event.id) { // Ensure event and event.id exist
        const key = makeTileKey('event', event.id);
        newSelected[key] = true;
      }
    });
    setSelectedTiles(newSelected);
    console.log('[VeyraResults] All visible tiles selected:', newSelected);
  };

  const getSelectedCount = () => {
    return Object.values(selectedTiles).filter(isSelected => isSelected).length;
  };

  const handleBulkDelete = async () => {
    const itemsToDelete = [];
    for (const key in selectedTiles) {
      if (selectedTiles[key]) { // Ensure it's truly selected
        const keyParts = key.split('|'); // Use new delimiter '|'

        if (keyParts.length === 3) {
          // keyParts[0] is message_id (from the VeyraResults block)
          // keyParts[1] is itemType ('email' or 'event')
          // keyParts[2] is itemId
          const itemTypeFromKey = keyParts[1];
          const itemIdFromKey = keyParts[2];
          
          itemsToDelete.push({
            item_id: itemIdFromKey,
            item_type: itemTypeFromKey, // This should now correctly be 'email' or 'event'
          });
        } else {
          console.error('[VeyraResults] Error parsing tile key for bulk delete. Key:', key, 'Expected 3 parts, got:', keyParts.length);
          // Optionally, alert the user or skip this item
        }
      }
    }

    if (itemsToDelete.length === 0) {
      showSnackbar('No items selected for deletion.', 'error');
      console.log('[VeyraResults] Bulk delete attempted with no items selected.');
      return;
    }

    setIsBulkDeleting(true);
    console.log('[VeyraResults] Starting bulk delete for items:', itemsToDelete);

    // `message_id` prop is the assistant's message ID
    // `currentThreadId` prop is the chat thread ID
    const payload = {
      message_id: message_id, 
      thread_id: currentThreadId, 
      items: itemsToDelete
    };

    console.log('[VeyraResults] Sending bulk delete request with payload:', payload);

    try {
      const response = await fetch('http://localhost:5001/bulk_delete_items', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      const data = await response.json();
      console.log('[VeyraResults] Bulk delete response received:', data);

      if (data.success && data.results) {
        const successfullyDeletedEmailIds = new Set();
        const successfullyDeletedEventIds = new Set();
        let successfulDeletes = 0;
        let failedDeletes = 0;

        data.results.forEach(result => {
          if (result.deleted) {
            successfulDeletes++;
            if (result.item_type === 'email') {
              successfullyDeletedEmailIds.add(result.item_id);
            } else if (result.item_type === 'event') {
              successfullyDeletedEventIds.add(result.item_id);
            }
          } else {
            failedDeletes++;
            console.warn(`[VeyraResults] Failed to delete ${result.item_type} with ID ${result.item_id}: ${result.error || 'Unknown reason'}`);
          }
        });

        setDeletedEmails(prev => {
          const newSet = new Set([...prev, ...successfullyDeletedEmailIds]);
          console.log('[VeyraResults] Updated deletedEmails after bulk delete:', newSet);
          return newSet;
        });
        setDeletedEvents(prev => {
          const newSet = new Set([...prev, ...successfullyDeletedEventIds]);
          console.log('[VeyraResults] Updated deletedEvents after bulk delete:', newSet);
          return newSet;
        });

        setSelectedTiles({}); // Clear selection
        console.log('[VeyraResults] Cleared selectedTiles after bulk delete.');
        showSnackbar(`${successfulDeletes} item(s) processed for deletion. ${failedDeletes > 0 ? `${failedDeletes} item(s) failed.` : ''} Check console for details.`, failedDeletes > 0 ? 'error' : 'success');
      
      } else {
        console.error('[VeyraResults] Bulk delete API call failed or returned unexpected data:', data.error || data);
        showSnackbar(`Bulk delete request failed: ${data.error || 'Server error. Check console.'}`, 'error');
      }
    } catch (error) {
      console.error('[VeyraResults] Error during bulk delete fetch operation:', error);
      showSnackbar(`Error during bulk delete: ${error.message}. Check console.`, 'error');
    } finally {
      setIsBulkDeleting(false);
      console.log('[VeyraResults] Bulk delete operation finished.');
    }
  };
  // --- End of methods for tile selection ---

  const selectedCount = getSelectedCount();

  // Helper to get selected email items
  const getSelectedEmailItems = () => {
    // displayedEmails is now the source of truth for what's rendered
    if (!displayedEmails) return [];
    return displayedEmails.filter(email => {
      const key = makeTileKey('email', email.email_id);
      return !!selectedTiles[key];
    });
  };

  // Email action handler
  const handleEmailAction = async (action, email) => {
    console.log(`[INFO] Handling email action: ${action} for email:`, email);
    
    if (action === 'summarize') {
        try {
            // Show loading state
            setIsSummarizingEmail(true);
            
            // Get all selected emails
            const emailsToSummarize = getSelectedEmailItems();
            let successCount = 0;
            let failedCount = 0;
            const failedEmails = [];
            
            // Process each email sequentially
            for (const emailToSummarize of emailsToSummarize) {
                console.log(`[INFO] Processing email for summarization: ${emailToSummarize.email_id}`);
                
                try {
                    // Step 1: Get email content (this will fetch and save to DB if not already there)
                    const contentResponse = await fetch('http://localhost:5001/get_email_content', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            email_id: emailToSummarize.email_id
                        }),
                    });

                    if (!contentResponse.ok) {
                        const errorData = await contentResponse.json().catch(() => ({ error: 'Unknown error' }));
                        console.error('[ERROR] Failed to get email content:', errorData.error);
                        failedCount++;
                        failedEmails.push(emailToSummarize.subject || 'Unknown email');
                        continue; // Continue with next email even if one fails
                    }

                    const contentData = await contentResponse.json();
                    console.log('[INFO] Retrieved email content successfully');

                    // Step 2: Now call the summarize endpoint with the content
                    const summarizeResponse = await fetch('http://localhost:5001/summarize_single_email', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            email_id: emailToSummarize.email_id,
                            thread_id: currentThreadId,
                            assistant_message_id: message_id,
                            email_content_full: contentData.content.html || contentData.content.text,
                            email_content_truncated: contentData.content.text || contentData.content.html
                        }),
                    });

                    const summarizeData = await summarizeResponse.json();
                    
                    if (!summarizeResponse.ok) {
                        console.error('[ERROR] Failed to summarize email:', summarizeData.error);
                        failedCount++;
                        failedEmails.push(emailToSummarize.subject || 'Unknown email');
                        continue; // Continue with next email even if one fails
                    }

                    console.log('[INFO] Received summary:', summarizeData.response);
                    successCount++;

                    // The summary is already saved in the database with the correct role
                    // Just trigger a refresh of the conversation to show the new message
                    if (typeof onNewMessageReceived === 'function') {
                        onNewMessageReceived(summarizeData);
                    }
                } catch (emailError) {
                    console.error(`[ERROR] Error processing email ${emailToSummarize.email_id}:`, emailError);
                    failedCount++;
                    failedEmails.push(emailToSummarize.subject || 'Unknown email');
                }
            }
            
            // Show summary to user
            if (successCount > 0 && failedCount === 0) {
                console.log(`[SUCCESS] Successfully summarized ${successCount} email(s)`);
            } else if (successCount > 0 && failedCount > 0) {
                showSnackbar(`Summarization completed: ${successCount} successful, ${failedCount} failed.\n\nFailed emails: ${failedEmails.join(', ')}`, failedCount > 0 ? 'error' : 'success');
            } else {
                showSnackbar('Failed to summarize any emails. All emails failed to process.', 'error');
            }
            
        } catch (error) {
            console.error('[ERROR] Error summarizing emails:', error);
            showSnackbar('An unexpected error occurred while summarizing emails.', 'error');
        } finally {
            setIsSummarizingEmail(false);
            // Clear selection after processing all emails
            setSelectedTiles({});
        }
    } else if (action === 'display') {
        showSnackbar(`Display action for: ${email.subject}`, 'info');
    } else if (action === 'view_gmail') {
        const webLink = email.webLink || email.alternateLink;
        if (webLink) {
            window.open(webLink, '_blank');
        } else {
            showSnackbar('No direct link available for this email.', 'error');
        }
    }
  };

  const selectedEmailItems = getSelectedEmailItems();

  const handleLoadMoreEmails = async () => {
    if (!canLoadMoreEmails || isLoadingMoreEmails) return;

    setIsLoadingMoreEmails(true);
    console.log(`[VeyraResults] Loading more emails for message_id: ${message_id}, thread_id: ${currentThreadId}`);
    try {
        const response = await fetch('http://localhost:5001/load_more_emails', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                thread_id: currentThreadId,
                assistant_message_id: message_id 
            }),
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ error: 'Failed to parse error response' }));
            console.error('[VeyraResults] Error loading more emails:', response.status, errorData);
            throw new Error(`HTTP error! status: ${response.status} - ${errorData.error || 'Unknown error'}`);
        }
        const data = await response.json();
        console.log('[VeyraResults] Received more emails:', data);

        if (data.new_emails && data.new_emails.length > 0) {
            setDisplayedEmails(prevEmails => [...prevEmails, ...data.new_emails]);
        }
        setCurrentEmailOffset(data.current_offset);
        setLimitPerPage(data.limit_per_page); 
        setTotalEmailsAvailable(data.total_emails_available);
        setCanLoadMoreEmails(data.has_more);

    } catch (error) {
        console.error("[VeyraResults] Catch block error loading more emails:", error);
        setCanLoadMoreEmails(false); // Stop trying if there was an error
        showSnackbar(`Error loading more emails: ${error.message}`, 'error');
    } finally {
        setIsLoadingMoreEmails(false);
    }
  };

  return (
    <Grid container spacing={2} sx={{ bgcolor: 'rgba(0, 0, 0, 0.02)', p: 1 }}>
      {/* Filter Information */}
      {results.filter_applied && (
        <Grid item xs={12}>
          <Typography 
            variant="caption" 
            sx={{ 
              display: 'block',
              color: 'text.secondary',
              mb: 1,
              fontStyle: 'italic'
            }}
          >
            {results.source_type === 'mail' ? 'Showing unread emails only' : 'Showing events from primary calendar only'}
          </Typography>
        </Grid>
      )}

      {/* Selection Control Panel - Email actions as icons */}
      {selectedEmailItems.length > 0 && (
        <Grid item xs={12}>
          <Paper 
            elevation={2} 
            sx={{ 
              p: 1, 
              mb: 2, 
              display: 'flex', 
              justifyContent: 'space-between', 
              alignItems: 'center',
              backgroundColor: 'rgba(25, 118, 210, 0.05)'
            }}
          >
            <Typography variant="body2" sx={{ color: 'primary.main', ml: 1 }}>
              {selectedEmailItems.length} email(s) selected
            </Typography>
            <Box>
              <IconButton 
                onClick={handleSelectAllTiles}
                size="small"
                title="Select All Visible"
                sx={{ mr: 0.5 }}
                disabled={isBulkDeleting || (displayedEmails.length === 0 && (!results?.calendar_events || results.calendar_events.length === 0) )}
              >
                <DoneAllIcon />
              </IconButton>
              <IconButton 
                onClick={() => setSelectedTiles({})} 
                size="small"
                title="Deselect All"
                sx={{ mr: 0.5 }}
              >
                <ClearAllIcon />
              </IconButton>
              <IconButton
                title="Summarize selected email(s)"
                size="small"
                onClick={(e) => handleEmailAction('summarize', selectedEmailItems[0])}
                disabled={selectedEmailItems.length === 0 || isBulkDeleting || isSummarizingEmail}
                sx={{ mr: 0.5 }}
              >
                {isSummarizingEmail ? <CircularProgress size={20} /> : <NotesIcon />}
              </IconButton>
              <IconButton
                title="Display selected email"
                size="small"
                onClick={(e) => handleEmailAction('display', selectedEmailItems[0])}
                disabled={selectedEmailItems.length !== 1 || isBulkDeleting}
                sx={{ mr: 0.5 }}
              >
                <VisibilityIcon />
              </IconButton>
              <IconButton
                title="View selected email in GMail"
                size="small"
                onClick={(e) => handleEmailAction('view_gmail', selectedEmailItems[0])}
                disabled={selectedEmailItems.length !== 1 || isBulkDeleting}
                sx={{ mr: 0.5 }}
              >
                <OpenInNewIcon />
              </IconButton>
              <IconButton 
                onClick={handleBulkDelete} 
                color="error" 
                size="small"
                title="Delete Selected Email(s)"
                disabled={isBulkDeleting || selectedEmailItems.length === 0}
              >
                {isBulkDeleting ? <CircularProgress size={20} color="inherit" /> : <DeleteIcon />}
              </IconButton>
            </Box>
          </Paper>
        </Grid>
      )}

      {/* Email List */}
      {Array.isArray(displayedEmails) && displayedEmails.length > 0 && (
        <Grid item xs={12}>
          <List disablePadding sx={{ bgcolor: 'background.paper', border: '1px solid rgba(0,0,0,0.08)', borderRadius: '4px' }}>
            {displayedEmails.map((email, index) => {
              if (!email || !email.email_id) return null;
              
              const tileKey = makeTileKey('email', email.email_id);
              const isSelected = !!selectedTiles[tileKey];
              if (deletedEmails.has(email.email_id)) {
                return (
                  <ListItem key={`email-${email.email_id}-deleted`} sx={{ p: 2, justifyContent: 'center', alignItems: 'center', opacity: 0.5 }}>
                    <Typography>🙌 Email deleted</Typography>
                  </ListItem>
                );
              }
              return (
                <ListItem
                  key={`email-${email.email_id}`}
                  button
                  selected={isSelected}
                  onClick={() => handleTileSelect('email', email.email_id)}
                  divider={index < displayedEmails.length - 1}
                  sx={{
                    padding: '10px 12px',
                    '&.Mui-selected': {
                      backgroundColor: 'action.selected',
                    },
                    '&.Mui-selected:hover': {
                      backgroundColor: 'action.selected',
                    },
                    '&:hover': {
                       backgroundColor: !isSelected ? 'action.hover' : undefined,
                    },
                  }}
                >
                  <Checkbox
                    checked={isSelected}
                    onClick={(e) => {
                      e.stopPropagation();
                      handleTileSelect('email', email.email_id);
                    }}
                    edge="start"
                    sx={{ mr: 1, p: 0.5 }}
                    size="small"
                  />
                  <Box sx={{ display: 'flex', alignItems: 'center', width: '180px', mr: 2, flexShrink: 0 }}>
                    <Typography 
                      variant="body2" 
                      noWrap
                      sx={{ 
                        fontWeight: 500,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                      }}
                    >
                      {email.from_email?.name || email.from_email?.email || 'Unknown Sender'}
                    </Typography>
                  </Box>
                  <ListItemText
                    primary={
                      <Typography 
                        variant="body2" 
                        noWrap
                        sx={{
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                        }}
                      >
                        {email.subject?.length > 100 ? `${email.subject.substring(0, 100)}...` : email.subject || 'No Subject'}
                      </Typography>
                    }
                    sx={{ flexGrow: 1, mr: 2, my: 0 }}
                  />
                  <Typography 
                    variant="caption" 
                    sx={{ 
                      color: 'text.secondary', 
                      whiteSpace: 'nowrap',
                      ml: 'auto',
                      minWidth: '90px',
                      textAlign: 'right'
                    }}
                  >
                    {formatEventDateTime(email.date)}
                  </Typography>
                </ListItem>
              );
            })}
          </List>
          {canLoadMoreEmails && (
            <Box sx={{ display: 'flex', justifyContent: 'center', mt: 2, mb: 1 }}>
              <Button 
                variant="outlined"
                onClick={handleLoadMoreEmails} 
                disabled={isLoadingMoreEmails}
              >
                {isLoadingMoreEmails ? <CircularProgress size={24} /> : 'Load More Emails'}
              </Button>
            </Box>
          )}
        </Grid>
      )}

      {/* Calendar Event Tiles */}
      {results.calendar_events && Array.isArray(results.calendar_events) && results.calendar_events.length > 0 && results.calendar_events.map((event, index) => {
        const tileKey = makeTileKey('event', event.id);
        const isSelected = !!selectedTiles[tileKey];

        if (deletedEvents.has(event.id)) {
          return (
            <Grid item xs={12} sm={6} md={3} key={`event-${index}`}>
              <Card sx={{ 
                height: '100%', 
                p: 2, 
                boxShadow: 'none',
                border: '1px solid rgba(0, 0, 0, 0.08)',
                bgcolor: 'white',
                animation: 'fadeOut 2s ease-in-out',
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center',
                '@keyframes fadeOut': {
                  '0%': { opacity: 1 },
                  '70%': { opacity: 1 },
                  '100%': { opacity: 0 }
                }
              }}>
                <Typography>🙌 Successfully deleted</Typography>
              </Card>
            </Grid>
          );
        }
        return (
          <Grid item xs={12} sm={6} md={3} key={`event-${index}`}>
            <Card 
              className="calendar-event-card"
              sx={{ 
                height: '100%', 
                p: 2, 
                boxShadow: 'none',
                border: isSelected ? '2px solid #1976d2' : '1px solid rgba(0, 0, 0, 0.08)',
                bgcolor: isSelected ? '#e3f2fd' : 'white',
                cursor: 'pointer',
                '&:hover': {
                  border: isSelected ? '2px solid #1565c0' : '1px solid rgba(0, 0, 0, 0.12)',
                  transform: 'translateY(-2px)',
                  boxShadow: '0 4px 8px rgba(0, 0, 0, 0.1) !important'
                },
                transition: 'all 0.2s ease-in-out'
              }}
              data-event-id={event.id}
              onClick={() => handleTileSelect('event', event.id)}
            >
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <Box sx={{ flex: 1, mr: 1 }}>
                  <Typography 
                    variant="h6" 
                    sx={{ 
                      fontSize: '0.875rem', 
                      fontWeight: 'bold',
                      wordBreak: 'break-word',
                      mb: 1
                    }}
                  >
                    {event.summary || 'Untitled Event'}
                  </Typography>
                  
                  <Typography 
                    variant="body2" 
                    sx={{ 
                      fontSize: '0.75rem',
                      color: 'text.secondary',
                      mb: 0.5
                    }}
                  >
                    Since: {formatEventDateTime(event.start)}
                  </Typography>
                  
                  <Typography 
                    variant="body2" 
                    sx={{ 
                      fontSize: '0.75rem',
                      color: 'text.secondary',
                      mb: 0.5
                    }}
                  >
                    Until: {formatEventDateTime(event.end)}
                  </Typography>
                  
                  <Typography 
                    variant="body2" 
                    sx={{ 
                      fontSize: '0.75rem',
                      color: 'text.secondary'
                    }}
                  >
                    Status: {event.status}
                  </Typography>
                </Box>
                <IconButton 
                  size="small"
                  onClick={(e) => handleMenuClick(e, event)}
                  sx={{ ml: 1 }}
                >
                  <MoreVertIcon />
                </IconButton>
              </Box>
            </Card>
          </Grid>
        );
      })}

      {/* Context Menu */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
      >
        {selectedItem && selectedItem.start ? (
          // Calendar event options
          <>
            <MenuItem onClick={() => handleAction('display', selectedItem)}>
              Display
            </MenuItem>
            <MenuItem onClick={() => handleAction('modify', selectedItem)}>
              Modify the event
            </MenuItem>
            {selectedItem.htmlLink && (
              <MenuItem onClick={() => handleAction('open', selectedItem)}>
                Open in Calendar
              </MenuItem>
            )}
            <MenuItem onClick={() => handleAction('delete', selectedItem)}>
              Delete Event
            </MenuItem>
          </>
        ) : (
          // Email options
          <>
            <MenuItem onClick={() => handleAction('summarize', selectedItem)}>
              Summarize
            </MenuItem>
            <MenuItem onClick={() => handleAction('display', selectedItem)}>
              Display
            </MenuItem>
            <MenuItem onClick={() => handleAction('view_gmail', selectedItem)}>
              View in GMail
            </MenuItem>
            <MenuItem onClick={() => handleAction('delete', selectedItem)}>
              Delete Email
            </MenuItem>
          </>
        )}
      </Menu>
    </Grid>
  );
};

export default VeyraResults; 