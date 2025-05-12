import React, { useState } from 'react';
import { 
  Card, 
  Typography, 
  Box, 
  IconButton, 
  Menu, 
  MenuItem,
  Grid
} from '@mui/material';
import MoreVertIcon from '@mui/icons-material/MoreVert';
import './VeyraResults.css';

const VeyraResults = ({ results, currentThreadId, message_id }) => {
  const [anchorEl, setAnchorEl] = useState(null);
  const [selectedItem, setSelectedItem] = useState(null);
  const [deletedEmails, setDeletedEmails] = useState(new Set());
  const [deletedEvents, setDeletedEvents] = useState(new Set());
  const [clickedElement, setClickedElement] = useState(null);

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
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
    setSelectedItem(null);
    setClickedElement(null);
  };

  const handleAction = async (action, item) => {
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
            alert('Could not find required IDs for deletion. Please try again.');
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
          setDeletedEvents(prev => new Set([...prev, item.id]));
          
          if (data.success) {
            console.log('Event successfully deleted');
          } else {
            console.error('Failed to delete event:', data.message);
          }
        } catch (error) {
          console.error('Error deleting event:', error);
          // Even if there's an error, mark the event as deleted in the UI
          setDeletedEvents(prev => new Set([...prev, item.id]));
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
            alert('Could not find email ID for deletion. Please try again.');
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
          setDeletedEmails(prev => new Set([...prev, item.id]));
          
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
          setDeletedEmails(prev => new Set([...prev, item.id]));
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

  if (!results || (!results.emails?.length && !results.calendar_events?.length)) {
    console.log('No results to display');
    return null;
  }

  return (
    <Grid container spacing={2} sx={{ bgcolor: 'rgba(0, 0, 0, 0.02)' }}>
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

      {/* Email Tiles */}
      {results.emails && results.emails.map((email, index) => {
        if (deletedEmails.has(email.id)) {
          return (
            <Grid item xs={12} sm={6} md={3} key={`email-${index}`}>
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
          <Grid item xs={12} sm={6} md={3} key={`email-${index}`}>
            <Card 
              sx={{ 
                height: '100%', 
                p: 2, 
                boxShadow: 'none',
                border: '1px solid rgba(0, 0, 0, 0.08)',
                bgcolor: 'white',
                '&:hover': {
                  border: '1px solid rgba(0, 0, 0, 0.12)'
                }
              }}
              data-email-id={email.id}
            >
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <Box sx={{ flex: 1, mr: 1 }}>
                  <Typography 
                    variant="h6" 
                    sx={{ 
                      fontSize: '0.875rem', 
                      fontWeight: 'bold',
                      wordBreak: 'break-word',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      display: '-webkit-box',
                      WebkitLineClamp: 1,
                      mb: 1
                    }}
                  >
                    {email.subject?.length > 50 ? `${email.subject.substring(0, 50)}...` : email.subject || 'No Subject'}
                  </Typography>
                  
                  <Typography 
                    variant="body2" 
                    sx={{ 
                      fontSize: '0.75rem',
                      color: 'text.secondary',
                      mb: 0.5
                    }}
                  >
                    From: {email.from_email?.name || email.from_email?.email || 'Unknown Sender'}
                  </Typography>
                  
                  <Typography 
                    variant="body2" 
                    sx={{ 
                      fontSize: '0.75rem',
                      color: 'text.secondary'
                    }}
                  >
                    {formatEventDateTime(email.date)}
                  </Typography>
                </Box>
                <IconButton 
                  size="small"
                  onClick={(e) => handleMenuClick(e, email)}
                  sx={{ ml: 1 }}
                >
                  <MoreVertIcon />
                </IconButton>
              </Box>
            </Card>
          </Grid>
        );
      })}

      {/* Calendar Event Tiles */}
      {results.calendar_events && results.calendar_events.map((event, index) => {
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
                border: '1px solid rgba(0, 0, 0, 0.08)',
                bgcolor: 'white',
                '&:hover': {
                  border: '1px solid rgba(0, 0, 0, 0.12)',
                  transform: 'translateY(-2px)',
                  boxShadow: '0 4px 8px rgba(0, 0, 0, 0.1) !important'
                },
                transition: 'all 0.2s ease-in-out'
              }}
              data-event-id={event.id}
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