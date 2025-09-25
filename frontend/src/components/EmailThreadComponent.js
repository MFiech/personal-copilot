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
import DOMPurify from 'dompurify';
import { validateDraft, getDraftStatusColor, getDraftStatusLabel } from '../utils/draftValidation';

const EmailThreadComponent = ({ 
  threadEmails = [], 
  threadDrafts = [], 
  onSendDraft = null,
  isSending = false,
  showSnackbar = null 
}) => {
  const [expandedEmails, setExpandedEmails] = useState(new Set());
  const [sendingDrafts, setSendingDrafts] = useState(new Set());

  const toggleEmailExpansion = (emailId) => {
    const newExpanded = new Set(expandedEmails);
    if (newExpanded.has(emailId)) {
      newExpanded.delete(emailId);
    } else {
      newExpanded.add(emailId);
    }
    setExpandedEmails(newExpanded);
  };

  const getInitials = (name, email) => {
    if (name && name.trim()) {
      return name.trim().charAt(0).toUpperCase();
    }
    if (email && email.includes('@')) {
      return email.split('@')[0].charAt(0).toUpperCase();
    }
    return '?';
  };

  const sanitizeHTML = (html) => {
    return DOMPurify.sanitize(html, {
      ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'a', 'div', 'span', 'table', 'tr', 'td', 'th', 'thead', 'tbody'],
      ALLOWED_ATTR: ['href', 'target', 'style'],
      ALLOW_DATA_ATTR: false
    });
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

  const renderEmailBody = (emailData) => {
    if (!emailData || !emailData.content) return null;

    const { html, text } = emailData.content;
    
    if (html && html.trim()) {
      return (
        <Box
          dangerouslySetInnerHTML={{
            __html: sanitizeHTML(html)
          }}
          sx={{
            '& img': { maxWidth: '100%', height: 'auto' },
            '& a': { color: 'primary.main' },
            '& table': { width: '100%', borderCollapse: 'collapse' },
            '& td, & th': { padding: '8px', borderBottom: '1px solid #eee' },
            lineHeight: 1.6,
            fontSize: '14px'
          }}
        />
      );
    } else if (text && text.trim()) {
      return (
        <Typography
          variant="body2"
          component="pre"
          sx={{
            whiteSpace: 'pre-wrap',
            fontFamily: 'inherit',
            fontSize: '14px',
            lineHeight: 1.6,
            wordBreak: 'break-word'
          }}
        >
          {text}
        </Typography>
      );
    } else {
      return (
        <Typography variant="body2" color="text.secondary">
          No content available
        </Typography>
      );
    }
  };

  const renderDraftBody = (draftData) => {
    if (!draftData || !draftData.body) {
      return (
        <Typography variant="body2" color="text.secondary">
          No content available
        </Typography>
      );
    }

    return (
      <Typography
        variant="body2"
        component="pre"
        sx={{
          whiteSpace: 'pre-wrap',
          fontFamily: 'inherit',
          fontSize: '14px',
          lineHeight: 1.6,
          wordBreak: 'break-word'
        }}
      >
        {draftData.body}
      </Typography>
    );
  };

  const handleSendDraft = async (draftItem) => {
    const validation = validateDraft(draftItem);
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

  // Combine emails and drafts, sort by date
  const allItems = [...threadEmails, ...threadDrafts]
    .sort((a, b) => new Date(a.date || a.created_at * 1000) - new Date(b.date || b.created_at * 1000));

  if (allItems.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary" sx={{ p: 2, textAlign: 'center' }}>
        No emails or drafts to display
      </Typography>
    );
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      {allItems.map((item, index) => {
        const isEmail = !!item.email_id;
        const isDraft = !!item.draft_id;
        const itemId = isEmail ? item.email_id : item.draft_id;
        const isExpanded = expandedEmails.has(itemId);
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
              onClick={() => toggleEmailExpansion(itemId)}
            >
              <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2 }}>
                {/* Avatar */}
                <Avatar 
                  sx={{ 
                    width: 40, 
                    height: 40, 
                    bgcolor: isDraft ? getDraftStatusColor(item.status) : '#5f6368',
                    fontSize: '16px',
                    fontWeight: 500
                  }}
                >
                  {isEmail 
                    ? getInitials(item.from_email?.name, item.from_email?.email)
                    : 'D' // Draft indicator
                  }
                </Avatar>
                
                {/* Item Info */}
                <Box sx={{ flex: 1, minWidth: 0 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                      <Typography variant="body1" sx={{ fontWeight: 500, color: '#202124' }}>
                        {isEmail 
                          ? (item.from_email?.name || item.from_email?.email || 'Unknown Sender')
                          : 'Draft'
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
                      {formatDate(isEmail ? item.date : new Date(item.created_at * 1000).toISOString())}
                    </Typography>
                  </Box>
                  
                  {/* Expanded details */}
                  {isActuallyExpanded && (
                    <Box sx={{ mb: 1 }}>
                      {isEmail ? (
                        <>
                          <Typography variant="body2" color="#5f6368" sx={{ fontWeight: 500, mb: 0.5 }}>
                            From: {item.from_email?.name || 'Unknown'} &lt;{item.from_email?.email || 'unknown@example.com'}&gt;
                          </Typography>
                          <Typography variant="body2" color="#5f6368" sx={{ fontWeight: 500 }}>
                            To: {item.to_emails?.map(recipient => 
                              `${recipient.name || recipient.email || 'Unknown'} <${recipient.email || 'unknown@example.com'}>`
                            ).join(', ') || 'No recipients'}
                          </Typography>
                        </>
                      ) : (
                        <>
                          <Typography variant="body2" color="#5f6368" sx={{ fontWeight: 500, mb: 0.5 }}>
                            Subject: {item.subject || 'No subject'}
                          </Typography>
                          <Typography variant="body2" color="#5f6368" sx={{ fontWeight: 500 }}>
                            To: {item.to_emails?.map(recipient => 
                              `${recipient.name || recipient.email || 'Unknown'} <${recipient.email || 'unknown@example.com'}>`
                            ).join(', ') || 'No recipients'}
                          </Typography>
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
                        const text = isEmail 
                          ? (item.content?.text || 'No content')
                          : (item.body || 'No content');
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
                  {isEmail ? renderEmailBody(item) : renderDraftBody(item)}
                </Box>
                
                {/* Draft send button */}
                {isDraft && item.status !== 'closed' && (
                  <Box sx={{ display: 'flex', gap: 1, justifyContent: 'flex-end', alignItems: 'center', mt: 2 }}>
                    {(() => {
                      const validation = validateDraft(item);
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
                            {isDraftSending ? 'Sending...' : (validation.isComplete ? 'Send' : 'Incomplete')}
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

export default EmailThreadComponent;