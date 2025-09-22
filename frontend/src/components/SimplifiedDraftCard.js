import React from 'react';
import {
  Box,
  Paper,
  Typography,
} from '@mui/material';
import EmailIcon from '@mui/icons-material/Email';
import EventIcon from '@mui/icons-material/Event';

const SimplifiedDraftCard = ({
  draft,
  messageId,
  onDraftClick
}) => {

  const handleClick = () => {
    if (onDraftClick && draft) {
      onDraftClick(draft);
    }
  };

  if (!draft) return null;

  const isEmail = draft.draft_type === 'email';
  const isSent = draft.status === 'closed';

  // Helper function to truncate recipients
  const formatRecipients = (recipients) => {
    if (!recipients || recipients.length === 0) return 'Not specified';

    const formatRecipient = (recipient) => {
      if (typeof recipient === 'string') return recipient;
      if (recipient.name && recipient.email) return `${recipient.name} (${recipient.email})`;
      return recipient.email || recipient.name || 'Unknown';
    };

    if (recipients.length <= 2) {
      return recipients.map(formatRecipient).join(', ');
    } else {
      const first = formatRecipient(recipients[0]);
      const second = formatRecipient(recipients[1]);
      const remaining = recipients.length - 2;
      return `${first}, ${second} and ${remaining} other${remaining > 1 ? 's' : ''}`;
    }
  };

  // Helper function to truncate text
  const truncateText = (text, maxLength) => {
    if (!text) return '';
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  };

  return (
    <Paper
      elevation={1}
      onClick={handleClick}
      sx={{
        mt: 1,
        mb: 1,
        p: 1.5,
        backgroundColor: '#f8f9fa',
        border: '1px solid #e0e0e0',
        borderRadius: '8px',
        cursor: 'pointer',
        transition: 'all 0.2s ease',
        '&:hover': {
          backgroundColor: '#f0f0f0',
          borderColor: '#1976d2',
          transform: 'translateY(-1px)',
          boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
        },
        maxWidth: '480px',
        width: '480px',
        alignSelf: 'flex-end', // Align to right edge
      }}
    >
      {/* Header */}
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
        {isEmail ? (
          <EmailIcon sx={{ color: '#666', mr: 1, fontSize: '18px' }} />
        ) : (
          <EventIcon sx={{ color: '#666', mr: 1, fontSize: '18px' }} />
        )}

        <Typography
          variant="body2"
          sx={{
            color: '#555',
            fontWeight: 600,
            fontSize: '13px'
          }}
        >
          {isSent
            ? (isEmail ? 'Email' : 'Event')
            : (isEmail ? 'Email Draft' : 'Event Draft')
          }
        </Typography>
      </Box>

      {/* Content */}
      <Box sx={{ ml: 3 }}>
        {isEmail ? (
          <>
            {/* To field */}
            <Box sx={{ mb: 0.5 }}>
              <Typography
                variant="caption"
                sx={{
                  color: '#888',
                  fontWeight: 500,
                  display: 'inline',
                  mr: 0.5
                }}
              >
                To:
              </Typography>
              <Typography
                variant="caption"
                sx={{
                  color: draft.to_emails?.length ? '#333' : '#d32f2f',
                  display: 'inline'
                }}
              >
                {formatRecipients(draft.to_emails)}
              </Typography>
            </Box>

            {/* Subject field */}
            <Box sx={{ mb: 0.5 }}>
              <Typography
                variant="caption"
                sx={{
                  color: '#888',
                  fontWeight: 500,
                  display: 'inline',
                  mr: 0.5
                }}
              >
                Subject:
              </Typography>
              <Typography
                variant="caption"
                sx={{
                  color: draft.subject ? '#333' : '#d32f2f',
                  display: 'inline'
                }}
              >
                {truncateText(draft.subject, 50) || 'Not specified'}
              </Typography>
            </Box>

            {/* Body preview */}
            {draft.body && (
              <Typography
                variant="caption"
                sx={{
                  color: '#666',
                  fontStyle: 'italic',
                  display: 'block',
                  lineHeight: 1.3
                }}
              >
                {truncateText(draft.body.replace(/\n/g, ' '), 20)}
              </Typography>
            )}
          </>
        ) : (
          <>
            {/* Calendar event title */}
            <Box sx={{ mb: 0.5 }}>
              <Typography
                variant="caption"
                sx={{
                  color: '#888',
                  fontWeight: 500,
                  display: 'inline',
                  mr: 0.5
                }}
              >
                Title:
              </Typography>
              <Typography
                variant="caption"
                sx={{
                  color: draft.summary ? '#333' : '#d32f2f',
                  display: 'inline'
                }}
              >
                {truncateText(draft.summary, 50) || 'Not specified'}
              </Typography>
            </Box>

            {/* Time preview */}
            <Typography
              variant="caption"
              sx={{
                color: '#666',
                fontStyle: 'italic',
                display: 'block'
              }}
            >
              {draft.start_time && draft.end_time ? (
                `${new Date(draft.start_time).toLocaleString([], {
                  month: 'short',
                  day: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit'
                })} - ${new Date(draft.end_time).toLocaleTimeString([], {
                  hour: '2-digit',
                  minute: '2-digit'
                })}`
              ) : (
                'Time not specified'
              )}
            </Typography>
          </>
        )}
      </Box>
    </Paper>
  );
};

export default SimplifiedDraftCard;