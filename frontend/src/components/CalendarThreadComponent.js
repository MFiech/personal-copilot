import React, { useState } from 'react';
import {
  Box,
  Typography,
  Avatar,
  Chip,
  Button,
  CircularProgress
} from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import WarningIcon from '@mui/icons-material/Warning';
import EventIcon from '@mui/icons-material/Event';
import { validateCalendarDraft, getDraftStatusColor, getDraftStatusLabel } from '../utils/draftValidation';

const CalendarThreadComponent = ({ 
  threadCalendarEvents = [], 
  threadCalendarDrafts = [], 
  onSendDraft = null,
  isSending = false,
  showSnackbar = null 
}) => {
  const [expandedItems, setExpandedItems] = useState(new Set());
  const [sendingDrafts, setSendingDrafts] = useState(new Set());

  const toggleItemExpansion = (itemId) => {
    const newExpanded = new Set(expandedItems);
    if (newExpanded.has(itemId)) {
      newExpanded.delete(itemId);
    } else {
      newExpanded.add(itemId);
    }
    setExpandedItems(newExpanded);
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'Unknown Date';
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString('en-GB', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
      }) + ', ' + date.toLocaleTimeString('en-GB', {
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch (error) {
      return dateString;
    }
  };

  const renderCalendarEventBody = (eventData) => {
    if (!eventData) return null;

    return (
      <Box sx={{ fontSize: '14px', lineHeight: 1.6 }}>
        {eventData.description && (
          <Typography variant="body2" sx={{ mb: 1, fontWeight: 500 }}>
            <strong>Description:</strong>
          </Typography>
        )}
        {eventData.description ? (
          <Typography variant="body2" sx={{ mb: 1, whiteSpace: 'pre-wrap' }}>
            {eventData.description}
          </Typography>
        ) : (
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            No description
          </Typography>
        )}
        
        {eventData.location && (
          <>
            <Typography variant="body2" sx={{ mb: 0.5, fontWeight: 500 }}>
              <strong>Location:</strong>
            </Typography>
            <Typography variant="body2" sx={{ mb: 1 }}>
              📍 {eventData.location}
            </Typography>
          </>
        )}
        
        {eventData.attendees && eventData.attendees.length > 0 && (
          <>
            <Typography variant="body2" sx={{ mb: 0.5, fontWeight: 500 }}>
              <strong>Attendees:</strong>
            </Typography>
            <Box sx={{ mb: 1 }}>
              {eventData.attendees.map((attendee, index) => (
                <Typography key={index} variant="body2" sx={{ mb: 0.5 }}>
                  👤 {attendee.displayName || attendee.email || 'Unknown'}
                  {attendee.responseStatus && (
                    <Chip 
                      label={attendee.responseStatus}
                      size="small"
                      sx={{ ml: 1, height: '20px', fontSize: '11px' }}
                    />
                  )}
                </Typography>
              ))}
            </Box>
          </>
        )}
      </Box>
    );
  };

  const renderCalendarDraftBody = (draftData) => {
    if (!draftData) return null;

    return (
      <Box sx={{ fontSize: '14px', lineHeight: 1.6 }}>
        {draftData.description && (
          <Typography variant="body2" sx={{ mb: 1, fontWeight: 500 }}>
            <strong>Description:</strong>
          </Typography>
        )}
        {draftData.description ? (
          <Typography variant="body2" sx={{ mb: 1, whiteSpace: 'pre-wrap' }}>
            {draftData.description}
          </Typography>
        ) : (
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
            No description
          </Typography>
        )}
        
        {draftData.location && (
          <>
            <Typography variant="body2" sx={{ mb: 0.5, fontWeight: 500 }}>
              <strong>Location:</strong>
            </Typography>
            <Typography variant="body2" sx={{ mb: 1 }}>
              📍 {draftData.location}
            </Typography>
          </>
        )}
        
        {draftData.attendees && draftData.attendees.length > 0 && (
          <>
            <Typography variant="body2" sx={{ mb: 0.5, fontWeight: 500 }}>
              <strong>Attendees:</strong>
            </Typography>
            <Box sx={{ mb: 1 }}>
              {draftData.attendees.map((attendee, index) => (
                <Typography key={index} variant="body2" sx={{ mb: 0.5 }}>
                  👤 {attendee.name || attendee.email || 'Unknown'}
                </Typography>
              ))}
            </Box>
          </>
        )}
      </Box>
    );
  };

  const handleSendDraft = async (draftItem) => {
    const validation = validateCalendarDraft(draftItem);
    if (!validation.isComplete) {
      if (showSnackbar) {
        showSnackbar(`Cannot send: ${validation.reason}`, 'warning');
      }
      return;
    }
    
    setSendingDrafts(prev => new Set(prev).add(draftItem.draft_id));
    try {
      if (onSendDraft) {
        await onSendDraft(draftItem);
      }
    } finally {
      setSendingDrafts(prev => {
        const newSet = new Set(prev);
        newSet.delete(draftItem.draft_id);
        return newSet;
      });
    }
  };

  // Transform sent drafts to look like events (similar to email pattern)
  const transformSentDraftsToEvents = (drafts) => {
    return drafts.map(draft => {
      // If draft is sent (closed), transform it to look like an event
      if (draft.status === 'closed' && draft.draft_id) {
        return {
          // Use internal_event_id to make it appear as an event, not a draft
          internal_event_id: draft.sent_event_id || `sent-draft-${draft.draft_id}`,
          summary: draft.summary || 'No Title',
          description: draft.description || '',
          start: draft.start_time ? { dateTime: draft.start_time } : null,
          end: draft.end_time ? { dateTime: draft.end_time } : null,
          location: draft.location || '',
          attendees: draft.attendees || [],
          status: 'confirmed',
          updated: new Date(draft.updated_at * 1000).toISOString()
          // Note: NOT including draft_id so it's treated as an event
        };
      }
      return draft; // Return active drafts unchanged
    });
  };

  // Combine events with transformed sent drafts, sort by date
  const transformedDrafts = transformSentDraftsToEvents(threadCalendarDrafts);
  const allItems = [...threadCalendarEvents, ...transformedDrafts]
    .sort((a, b) => {
      const aDate = a.start?.dateTime || a.created_at * 1000;
      const bDate = b.start?.dateTime || b.created_at * 1000;
      return new Date(aDate) - new Date(bDate);
    });

  if (allItems.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary" sx={{ p: 2, textAlign: 'center' }}>
        No calendar events or drafts to display
      </Typography>
    );
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      {allItems.map((item, index) => {
        const isEvent = !!item.internal_event_id || !!item.id;
        const isDraft = !!item.draft_id;
        const itemId = isEvent ? (item.internal_event_id || item.id) : item.draft_id;
        const isExpanded = expandedItems.has(itemId);
        const isLastItem = index === allItems.length - 1;
        
        // Auto-expand the last item or if there's only one item
        const shouldAutoExpand = isLastItem || allItems.length === 1;
        const isActuallyExpanded = isExpanded || shouldAutoExpand;
        
        return (
          <Box
            key={itemId || index}
            sx={{
              width: '100%',
              borderBottom: '1px solid #e0e0e0',
              backgroundColor: isDraft ? '#f8f9ff' : 'white',
              '&:last-child': { borderBottom: 'none' }
            }}
          >
            {/* Item Header */}
            <Box 
              sx={{
                pt: 2,
                pb: 2,
                pr: 2,
                cursor: 'pointer',
                borderRadius: 1
              }}
              onClick={() => toggleItemExpansion(itemId)}
            >
              <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2 }}>
                {/* Avatar */}
                <Avatar 
                  sx={{ 
                    width: 40, 
                    height: 40, 
                    bgcolor: isDraft ? getDraftStatusColor(item.status) : '#1976d2',
                    fontSize: '16px',
                    fontWeight: 500
                  }}
                >
                  {isEvent 
                    ? <EventIcon />
                    : 'D' // Draft indicator
                  }
                </Avatar>
                
                {/* Item Info */}
                <Box sx={{ flex: 1, minWidth: 0 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography variant="body1" sx={{ fontWeight: 500, color: '#202124' }}>
                        {isEvent 
                          ? (item.summary || 'Calendar Event')
                          : 'Draft Event'
                        }
                      </Typography>
                      {isDraft && (
                        <Box
                          sx={{
                            px: 1,
                            py: 0.5,
                            borderRadius: 1,
                            bgcolor: getDraftStatusColor(item.status),
                            color: 'white',
                            fontSize: '12px',
                            fontWeight: 500
                          }}
                        >
                          {getDraftStatusLabel(item.status)}
                        </Box>
                      )}
                    </Box>
                    <Typography variant="caption" color="#5f6368">
                      {formatDate(isEvent 
                        ? (item.start?.dateTime || item.updated) 
                        : new Date(item.created_at * 1000).toISOString()
                      )}
                    </Typography>
                  </Box>
                  
                  {/* Expanded details */}
                  {isActuallyExpanded && (
                    <Box sx={{ mb: 1 }}>
                      {isEvent ? (
                        <>
                          <Typography variant="body2" color="#5f6368" sx={{ fontWeight: 500, mb: 0.5 }}>
                            Time: {item.start?.dateTime 
                              ? formatDate(item.start.dateTime) 
                              : 'No start time'
                            }
                            {item.end?.dateTime && ` - ${formatDate(item.end.dateTime)}`}
                          </Typography>
                          {item.location && (
                            <Typography variant="body2" color="#5f6368" sx={{ fontWeight: 500, mb: 0.5 }}>
                              📍 Location: {item.location}
                            </Typography>
                          )}
                        </>
                      ) : (
                        <>
                          <Typography variant="body2" color="#5f6368" sx={{ fontWeight: 500, mb: 0.5 }}>
                            Title: {item.summary || 'No title'}
                          </Typography>
                          <Typography variant="body2" color="#5f6368" sx={{ fontWeight: 500, mb: 0.5 }}>
                            Time: {item.start_time 
                              ? formatDate(item.start_time) 
                              : 'No start time'
                            }
                            {item.end_time && ` - ${formatDate(item.end_time)}`}
                          </Typography>
                          {item.location && (
                            <Typography variant="body2" color="#5f6368" sx={{ fontWeight: 500 }}>
                              📍 Location: {item.location}
                            </Typography>
                          )}
                        </>
                      )}
                    </Box>
                  )}
                  
                  {/* Snippet (when collapsed) */}
                  {!isActuallyExpanded && (
                    <Typography 
                      variant="body2" 
                      color="#5f6368"
                      sx={{ 
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                        maxWidth: '100%'
                      }}
                    >
                      {(() => {
                        const text = isEvent 
                          ? (item.description || item.location || 'Calendar event')
                          : (item.description || item.location || 'No content');
                        const truncated = text.substring(0, 120);
                        return truncated + (text.length > 120 ? '...' : '');
                      })()}
                    </Typography>
                  )}
                </Box>
              </Box>
            </Box>
            
            {/* Expanded Content */}
            {isActuallyExpanded && (
              <Box sx={{ pl: 6, pr: 2, pb: 2 }}>
                <Box sx={{ mb: 2 }}>
                  {isEvent ? renderCalendarEventBody(item) : renderCalendarDraftBody(item)}
                </Box>
                
                {/* Draft send button */}
                {isDraft && item.status !== 'closed' && (
                  <Box sx={{ display: 'flex', gap: 1, justifyContent: 'flex-end', alignItems: 'center', mt: 2 }}>
                    {(() => {
                      const validation = validateCalendarDraft(item);
                      const isDraftSending = sendingDrafts.has(item.draft_id);
                      
                      return (
                        <>
                          <Chip
                            icon={validation.isComplete ? <CheckCircleIcon /> : <WarningIcon />}
                            label={validation.reason}
                            color={validation.isComplete ? "success" : "warning"}
                            size="small"
                            sx={{ mr: 1 }}
                          />
                          <Button
                            variant="contained"
                            size="small"
                            startIcon={isDraftSending ? <CircularProgress size={16} color="inherit" /> : <SendIcon />}
                            onClick={() => handleSendDraft(item)}
                            disabled={!validation.isComplete || isDraftSending}
                            sx={{
                              backgroundColor: validation.isComplete ? '#4caf50' : '#ff9800',
                              '&:hover': {
                                backgroundColor: validation.isComplete ? '#388e3c' : '#f57c00'
                              },
                              '&:disabled': {
                                backgroundColor: '#ccc'
                              }
                            }}
                          >
                            {isDraftSending ? 'Creating...' : (validation.isComplete ? 'Create Event' : 'Incomplete')}
                          </Button>
                        </>
                      );
                    })()}
                  </Box>
                )}
              </Box>
            )}
          </Box>
        );
      })}
    </Box>
  );
};

export default CalendarThreadComponent;