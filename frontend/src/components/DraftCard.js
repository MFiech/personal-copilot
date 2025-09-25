import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  IconButton,
  Chip,
  Divider,
  CircularProgress,
  Fade,
} from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import AnchorIcon from '@mui/icons-material/Anchor';
import EmailIcon from '@mui/icons-material/Email';
import EventIcon from '@mui/icons-material/Event';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import WarningIcon from '@mui/icons-material/Warning';
import { DraftService, getMissingFieldsText } from '../utils/draftService';

const DraftCard = ({ 
  draft, 
  messageId,
  isAnchored = false,
  onAnchor, 
  onSend, 
  showSnackbar 
}) => {
  const [validation, setValidation] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSending, setIsSending] = useState(false);

  // Fetch validation status on mount and when draft changes
  useEffect(() => {
    if (draft && draft.draft_id) {
      // Immediate fetch
      fetchValidation();
      // Additional fetch after short delay to ensure backend consistency
      // This is especially important for newly created drafts
      const refreshTimer = setTimeout(() => {
        fetchValidation();
      }, 200);
      return () => clearTimeout(refreshTimer);
    }
  }, [draft]);
  
  // Additional effect to refresh validation when draft is updated
  useEffect(() => {
    if (draft?.draft_id && draft?.updated_at) {
      const refreshTimer = setTimeout(() => {
        fetchValidation();
      }, 100);
      return () => clearTimeout(refreshTimer);
    }
  }, [draft?.updated_at]);

  const fetchValidation = async () => {
    if (!draft?.draft_id) return;
    
    try {
      const response = await DraftService.validateDraft(draft.draft_id);
      if (response.success) {
        setValidation(response.validation);
      }
    } catch (error) {
      console.error('Error fetching draft validation:', error);
    }
  };

  const handleAnchor = () => {
    if (onAnchor) {
      const anchorData = {
        id: draft.draft_id,
        type: 'draft',
        data: draft
      };
      onAnchor(anchorData);
    }
  };

  const handleSend = async () => {
    if (!validation?.is_complete) {
      showSnackbar('Draft is incomplete. Please anchor and fill missing fields first.', 'warning');
      return;
    }
    
    setIsSending(true);
    try {
      const response = await DraftService.sendDraft(draft.draft_id);
      if (response.success) {
        showSnackbar(response.message || 'Draft sent successfully!', 'success');
        if (onSend) onSend(draft.draft_id);
      } else {
        showSnackbar(response.error || 'Failed to send draft', 'error');
      }
    } catch (error) {
      console.error('Error sending draft:', error);
      showSnackbar(`Failed to send draft: ${error.message}`, 'error');
    } finally {
      setIsSending(false);
    }
  };

  if (!draft) return null;

  const isEmail = draft.draft_type === 'email';
  const isComplete = validation?.is_complete;
  const isSent = draft.status === 'closed'; // Draft is sent and completed

  return (
    <Fade in={true} timeout={500}>
      <Paper
        elevation={2}
        sx={{
          mt: 1,
          mb: 1,
          p: 2,
          backgroundColor: isAnchored ? '#fff8e1' : '#f5f5f5',
          border: isAnchored ? '1px solid #ffcc02' : '1px solid #ccc',
          borderRadius: '12px',
          position: 'relative',
          maxWidth: '100%',
        }}
      >
        {/* Header */}
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 1.5 }}>
          {isEmail ? (
            <EmailIcon sx={{ color: isAnchored ? '#ff9800' : '#666', mr: 1 }} />
          ) : (
            <EventIcon sx={{ color: isAnchored ? '#ff9800' : '#666', mr: 1 }} />
          )}
          
          <Typography variant="h6" sx={{ color: isAnchored ? '#ef6c00' : '#555', fontWeight: 'bold', flexGrow: 1 }}>
            {isSent 
              ? (isEmail ? 'Email' : 'Calendar Event')
              : (isEmail ? 'Email Draft' : 'Calendar Event Draft')
            }
          </Typography>

          {/* Status indicator */}
          <Box>
            {isSent ? (
              <Chip
                icon={<CheckCircleIcon />}
                label={isEmail ? "Email sent" : "Event created"}
                sx={{ 
                  backgroundColor: isAnchored ? '#e8f5e8' : '#e0e0e0',
                  color: isAnchored ? '#2e7d32' : '#666',
                  '& .MuiChip-icon': {
                    color: isAnchored ? '#2e7d32' : '#666'
                  }
                }}
                size="small"
              />
            ) : validation && isComplete ? (
              <Chip
                icon={<CheckCircleIcon />}
                label="Ready to Send"
                color="success"
                size="small"
              />
            ) : validation && !isComplete ? (
              <Chip
                icon={<WarningIcon />}
                label="Needs Info"
                color="warning"
                size="small"
              />
            ) : null}
          </Box>
        </Box>

        {/* Draft Content */}
        <Box sx={{ mb: 1.5 }}>
          {isEmail ? (
            <Box>
              {/* To field */}
              <Box sx={{ mb: 1 }}>
                <Typography variant="body2" sx={{ fontWeight: 'bold', color: '#333' }}>
                  To:
                </Typography>
                <Typography variant="body2" sx={{ ml: 1, color: draft.to_emails?.length ? '#333' : '#d32f2f' }}>
                  {draft.to_emails?.length > 0 
                    ? draft.to_emails.map(email => {
                        if (typeof email === 'string') return email;
                        if (email.name && email.email) return `${email.name} (${email.email})`;
                        return email.email || email.name || 'Unknown recipient';
                      }).join(', ')
                    : <span style={{ fontStyle: 'italic' }}>Not specified</span>
                  }
                </Typography>
              </Box>

              {/* Subject field */}
              <Box sx={{ mb: 1 }}>
                <Typography variant="body2" sx={{ fontWeight: 'bold', color: '#333' }}>
                  Subject:
                </Typography>
                <Typography variant="body2" sx={{ ml: 1, color: draft.subject ? '#333' : '#d32f2f' }}>
                  {draft.subject || <span style={{ fontStyle: 'italic' }}>Not specified</span>}
                </Typography>
              </Box>

              {/* CC/BCC fields if present */}
              {draft.cc_emails && draft.cc_emails.length > 0 && (
                <Box sx={{ mb: 1 }}>
                  <Typography variant="body2" sx={{ fontWeight: 'bold', color: '#333' }}>
                    CC:
                  </Typography>
                  <Typography variant="body2" sx={{ ml: 1, color: '#333' }}>
                    {draft.cc_emails.map(email => {
                      if (typeof email === 'string') return email;
                      if (email.name && email.email) return `${email.name} (${email.email})`;
                      return email.email || email.name || 'Unknown recipient';
                    }).join(', ')}
                  </Typography>
                </Box>
              )}

              {/* Body preview */}
              {draft.body && (
                <Box sx={{ mb: 1 }}>
                  <Typography variant="body2" sx={{ fontWeight: 'bold', color: '#333' }}>
                    Body:
                  </Typography>
                  <Typography 
                    variant="body2" 
                    sx={{ 
                      ml: 1, 
                      color: '#555',
                      fontStyle: 'italic',
                      maxHeight: '60px',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      display: '-webkit-box',
                      WebkitLineClamp: 3,
                      WebkitBoxOrient: 'vertical',
                    }}
                  >
                    {draft.body}
                  </Typography>
                </Box>
              )}
            </Box>
          ) : (
            <Box>
              {/* Calendar event fields */}
              <Box sx={{ mb: 1 }}>
                <Typography variant="body2" sx={{ fontWeight: 'bold', color: '#333' }}>
                  Title:
                </Typography>
                <Typography variant="body2" sx={{ ml: 1, color: draft.summary ? '#333' : '#d32f2f' }}>
                  {draft.summary || <span style={{ fontStyle: 'italic' }}>Not specified</span>}
                </Typography>
              </Box>

              {/* Start/End time */}
              <Box sx={{ mb: 1 }}>
                <Typography variant="body2" sx={{ fontWeight: 'bold', color: '#333' }}>
                  Time:
                </Typography>
                <Typography variant="body2" sx={{ ml: 1, color: '#333' }}>
                  {draft.start_time && draft.end_time ? (
                    <>
                      {new Date(draft.start_time).toLocaleString([], {
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit'
                      })} - {new Date(draft.end_time).toLocaleTimeString([], {
                        hour: '2-digit',
                        minute: '2-digit'
                      })}
                    </>
                  ) : (
                    <span style={{ fontStyle: 'italic', color: '#d32f2f' }}>Not specified</span>
                  )}
                </Typography>
              </Box>

              {/* Location if present */}
              {draft.location && (
                <Box sx={{ mb: 1 }}>
                  <Typography variant="body2" sx={{ fontWeight: 'bold', color: '#333' }}>
                    Location:
                  </Typography>
                  <Typography variant="body2" sx={{ ml: 1, color: '#333' }}>
                    {draft.location}
                  </Typography>
                </Box>
              )}

              {/* Attendees if present */}
              {draft.attendees && draft.attendees.length > 0 && (
                <Box sx={{ mb: 1 }}>
                  <Typography variant="body2" sx={{ fontWeight: 'bold', color: '#333' }}>
                    Attendees:
                  </Typography>
                  <Typography variant="body2" sx={{ ml: 1, color: '#333' }}>
                    {draft.attendees.map(attendee => {
                      if (typeof attendee === 'string') return attendee;
                      if (attendee.name && attendee.email) return `${attendee.name} (${attendee.email})`;
                      return attendee.email || attendee.name || 'Unknown attendee';
                    }).join(', ')}
                  </Typography>
                </Box>
              )}
            </Box>
          )}
        </Box>

        {/* Missing fields warning */}
        {validation && !validation.is_complete && (
          <Box sx={{ mb: 1.5 }}>
            <Typography variant="caption" sx={{ color: '#d32f2f', fontStyle: 'italic' }}>
              ⚠️ {getMissingFieldsText(validation)}
            </Typography>
          </Box>
        )}

        {/* Show divider and action buttons only if not sent */}
        {!isSent && (
          <>
            <Divider sx={{ my: 1.5, borderColor: isAnchored ? '#ffcc02' : '#ccc' }} />

            {/* Action buttons */}
            <Box sx={{ display: 'flex', gap: 1, justifyContent: 'flex-end', alignItems: 'center' }}>
              <IconButton
                size="small"
                onClick={handleAnchor}
                sx={{
                  color: isAnchored ? '#ff9800' : '#666',
                  '&:hover': {
                    color: '#ff9800',
                    backgroundColor: 'rgba(255, 152, 0, 0.1)'
                  }
                }}
              >
                <AnchorIcon />
              </IconButton>

              <Button
                variant="contained"
                size="small"
                startIcon={isSending ? <CircularProgress size={16} color="inherit" /> : <SendIcon />}
                onClick={handleSend}
                disabled={!isComplete || isSending}
                sx={{
                  backgroundColor: isComplete ? '#4caf50' : '#ff9800',
                  '&:hover': {
                    backgroundColor: isComplete ? '#388e3c' : '#f57c00'
                  },
                  '&:disabled': {
                    backgroundColor: '#ccc'
                  }
                }}
              >
                {isSending ? 'Sending...' : (isComplete ? 'Send' : 'Needs Info')}
              </Button>
            </Box>
          </>
        )}
      </Paper>
    </Fade>
  );
};

export default DraftCard;