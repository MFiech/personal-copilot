import React from 'react';
import {
  Box,
  Typography,
  Chip,
  Button,
  CircularProgress
} from '@mui/material';
import EventIcon from '@mui/icons-material/Event';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import WarningIcon from '@mui/icons-material/Warning';
import { validateCalendarDraft, formatRecipients } from '../utils/draftValidation';

const CalendarDraftComponent = ({ 
  draft, 
  onSendDraft = null, 
  isSending = false,
  showSnackbar = null 
}) => {
  if (!draft || draft.draft_type !== 'calendar_event') return null;

  const validation = validateCalendarDraft(draft);
  const isSent = draft.status === 'closed';

  const handleCreate = async () => {
    if (!validation.isComplete) {
      if (showSnackbar) {
        showSnackbar(`Cannot create: ${validation.reason}`, 'warning');
      }
      return;
    }
    
    if (onSendDraft) {
      await onSendDraft(draft);
    }
  };

  // If sent/created, don't show as a draft anymore
  if (isSent) return null;

  const formatDateTime = (dateTimeString) => {
    if (!dateTimeString) return 'Not specified';
    try {
      const date = new Date(dateTimeString);
      return date.toLocaleString([], {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch (e) {
      return dateTimeString;
    }
  };

  return (
    <Box
      sx={{
        border: '1px solid #e0e0e0',
        borderRadius: '8px',
        p: 2,
        mb: 2,
        backgroundColor: '#fff8e1',
        position: 'relative'
      }}
    >
      {/* Status Chip */}
      <Chip
        label="Event Draft"
        size="small"
        sx={{
          position: 'absolute',
          top: 12,
          right: 12,
          backgroundColor: '#ff9800',
          color: 'white',
          fontWeight: 500
        }}
      />

      {/* Title */}
      <Box sx={{ mb: 1.5, mt: 1 }}>
        <Typography variant="body2" sx={{ fontWeight: 500, color: '#5f6368', mb: 0.5 }}>
          Title:
        </Typography>
        <Typography variant="body2" sx={{ color: draft.summary ? '#202124' : '#d32f2f' }}>
          {draft.summary || 'Not specified'}
        </Typography>
      </Box>

      {/* Time */}
      <Box sx={{ mb: 1.5 }}>
        <Typography variant="body2" sx={{ fontWeight: 500, color: '#5f6368', mb: 0.5 }}>
          Time:
        </Typography>
        {draft.start_time && draft.end_time ? (
          <Box>
            <Typography variant="body2" sx={{ color: '#202124' }}>
              <strong>Start:</strong> {formatDateTime(draft.start_time)}
            </Typography>
            <Typography variant="body2" sx={{ color: '#202124' }}>
              <strong>End:</strong> {formatDateTime(draft.end_time)}
            </Typography>
          </Box>
        ) : (
          <Typography variant="body2" sx={{ color: '#d32f2f', fontStyle: 'italic' }}>
            {!draft.start_time && !draft.end_time ? 'Start and end time not specified' :
             !draft.start_time ? 'Start time not specified' :
             'End time not specified'}
          </Typography>
        )}
      </Box>

      {/* Location */}
      {draft.location && (
        <Box sx={{ mb: 1.5 }}>
          <Typography variant="body2" sx={{ fontWeight: 500, color: '#5f6368', mb: 0.5 }}>
            Location:
          </Typography>
          <Typography variant="body2" sx={{ color: '#202124' }}>
            {draft.location}
          </Typography>
        </Box>
      )}

      {/* Attendees */}
      {draft.attendees && draft.attendees.length > 0 && (
        <Box sx={{ mb: 1.5 }}>
          <Typography variant="body2" sx={{ fontWeight: 500, color: '#5f6368', mb: 0.5 }}>
            Attendees:
          </Typography>
          <Typography variant="body2" sx={{ color: '#202124' }}>
            {formatRecipients(draft.attendees)}
          </Typography>
        </Box>
      )}

      {/* Description */}
      {draft.description && (
        <Box sx={{ mb: 1.5 }}>
          <Typography variant="body2" sx={{ fontWeight: 500, color: '#5f6368', mb: 0.5 }}>
            Description:
          </Typography>
          <Typography
            variant="body2"
            component="pre"
            sx={{
              whiteSpace: 'pre-wrap',
              fontFamily: 'inherit',
              fontSize: '14px',
              lineHeight: 1.6,
              wordBreak: 'break-word',
              color: '#202124',
              backgroundColor: '#f8f9fa',
              p: 1,
              borderRadius: '4px',
              border: '1px solid #e9ecef'
            }}
          >
            {draft.description}
          </Typography>
        </Box>
      )}

      {/* Create Button Section - Always visible */}
      <Box sx={{ mt: 2, pt: 2, borderTop: '1px solid #e0e0e0' }}>
        {/* Validation Status Chip */}
        <Box sx={{ mb: 2, textAlign: 'center' }}>
          <Chip
            icon={validation.isComplete ? <CheckCircleIcon /> : <WarningIcon />}
            label={validation.reason}
            color={validation.isComplete ? "success" : "warning"}
            size="small"
          />
        </Box>

        {/* Create Button */}
        <Button
          variant="contained"
          startIcon={isSending ? <CircularProgress size={16} color="inherit" /> : <EventIcon />}
          onClick={handleCreate}
          disabled={!validation.isComplete || isSending}
          sx={{
            width: '100%',
            backgroundColor: validation.isComplete ? '#4caf50' : '#ff9800',
            '&:hover': {
              backgroundColor: validation.isComplete ? '#388e3c' : '#f57c00'
            },
            '&:disabled': {
              backgroundColor: '#ccc'
            }
          }}
        >
          {isSending ? 'Creating...' : (validation.isComplete ? 'Create Event' : 'Incomplete')}
        </Button>
      </Box>
    </Box>
  );
};

export default CalendarDraftComponent;