import React from 'react';
import {
  Box,
  Typography,
  Chip,
  Button,
  CircularProgress
} from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import WarningIcon from '@mui/icons-material/Warning';
import { validateEmailDraft, formatRecipients, isDraftReply } from '../utils/draftValidation';

const EmailDraftComponent = ({ 
  draft, 
  onSendDraft = null, 
  isSending = false,
  showSnackbar = null 
}) => {
  if (!draft || draft.draft_type !== 'email') return null;

  const validation = validateEmailDraft(draft);
  const isReply = isDraftReply(draft);
  const isSent = draft.status === 'closed';

  const handleSend = async () => {
    if (!validation.isComplete) {
      if (showSnackbar) {
        showSnackbar(`Cannot send: ${validation.reason}`, 'warning');
      }
      return;
    }
    
    if (onSendDraft) {
      await onSendDraft(draft);
    }
  };

  // If sent, don't show as a draft anymore
  if (isSent) return null;

  return (
    <Box
      sx={{
        border: '1px solid #e0e0e0',
        borderRadius: '8px',
        p: 2,
        mb: 2,
        backgroundColor: '#f8f9ff',
        position: 'relative'
      }}
    >
      {/* Status Chip */}
      <Chip
        label={isReply ? 'Reply Draft' : 'Email Draft'}
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

      {/* To field */}
      <Box sx={{ mb: 1.5, mt: 1 }}>
        <Typography variant="body2" sx={{ fontWeight: 500, color: '#5f6368', mb: 0.5 }}>
          To:
        </Typography>
        <Typography variant="body2" sx={{ color: draft.to_emails?.length ? '#202124' : '#d32f2f' }}>
          {formatRecipients(draft.to_emails)}
        </Typography>
      </Box>

      {/* CC if present */}
      {draft.cc_emails && draft.cc_emails.length > 0 && (
        <Box sx={{ mb: 1.5 }}>
          <Typography variant="body2" sx={{ fontWeight: 500, color: '#5f6368', mb: 0.5 }}>
            CC:
          </Typography>
          <Typography variant="body2" sx={{ color: '#202124' }}>
            {formatRecipients(draft.cc_emails)}
          </Typography>
        </Box>
      )}

      {/* BCC if present */}
      {draft.bcc_emails && draft.bcc_emails.length > 0 && (
        <Box sx={{ mb: 1.5 }}>
          <Typography variant="body2" sx={{ fontWeight: 500, color: '#5f6368', mb: 0.5 }}>
            BCC:
          </Typography>
          <Typography variant="body2" sx={{ color: '#202124' }}>
            {formatRecipients(draft.bcc_emails)}
          </Typography>
        </Box>
      )}

      {/* Subject */}
      <Box sx={{ mb: 1.5 }}>
        <Typography variant="body2" sx={{ fontWeight: 500, color: '#5f6368', mb: 0.5 }}>
          Subject: {isReply && (
            <Typography component="span" variant="caption" sx={{ color: '#9e9e9e', ml: 0.5 }}>
              (auto-generated for replies)
            </Typography>
          )}
        </Typography>
        <Typography 
          variant="body2" 
          sx={{ 
            color: draft.subject ? '#202124' : (isReply ? '#9e9e9e' : '#d32f2f'), 
            fontStyle: isReply && !draft.subject ? 'italic' : 'normal' 
          }}
        >
          {draft.subject || (isReply ? 'Re: [Thread subject will be used]' : 'Not specified')}
        </Typography>
      </Box>

      {/* Body */}
      <Box sx={{ mb: 1.5 }}>
        <Typography variant="body2" sx={{ fontWeight: 500, color: '#5f6368', mb: 0.5 }}>
          Body:
        </Typography>
        {draft.body ? (
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
            {draft.body}
          </Typography>
        ) : (
          <Typography variant="body2" sx={{ color: '#d32f2f', fontStyle: 'italic' }}>
            Not specified
          </Typography>
        )}
      </Box>

      {/* Send Button Section - Always visible */}
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

        {/* Send Button */}
        <Button
          variant="contained"
          startIcon={isSending ? <CircularProgress size={16} color="inherit" /> : <SendIcon />}
          onClick={handleSend}
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
          {isSending ? 'Sending...' : (validation.isComplete ? 'Send Email' : 'Incomplete')}
        </Button>
      </Box>
    </Box>
  );
};

export default EmailDraftComponent;