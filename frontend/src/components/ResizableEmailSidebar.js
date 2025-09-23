import React, { useState, useRef, useEffect } from 'react';
import {
  Box,
  Typography,
  IconButton,
  CircularProgress,
  Alert,
  Avatar,
  Chip,
  Button
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import DragIndicatorIcon from '@mui/icons-material/DragIndicator';
import SendIcon from '@mui/icons-material/Send';
import DOMPurify from 'dompurify';

const ResizableEmailSidebar = ({
  open,
  email,
  threadEmails = [],
  threadDrafts = [],
  gmailThreadId = null,
  pmCopilotThreadId = null,
  draft = null,
  loading,
  error,
  onClose,
  onWidthChange,
  contentType = 'email', // 'email', 'draft', or 'combined'
  draftValidation = null,
  onSendDraft = null,
  isSendingDraft = false
}) => {
  const [width, setWidth] = useState(420);
  const [isResizing, setIsResizing] = useState(false);
  const [expandedEmails, setExpandedEmails] = useState(new Set());
  const sidebarRef = useRef(null);
  const resizeHandleRef = useRef(null);

  const MIN_WIDTH = 240;
  const MAX_WIDTH = 720;
  const DEFAULT_WIDTH = 420;

  useEffect(() => {
    if (onWidthChange) {
      onWidthChange(open ? width : 0);
    }
  }, [width, open, onWidthChange]);

  useEffect(() => {
    const handleMouseMove = (e) => {
      if (!isResizing) return;

      const newWidth = window.innerWidth - e.clientX;
      if (newWidth >= MIN_WIDTH && newWidth <= MAX_WIDTH) {
        setWidth(newWidth);
      }
    };

    const handleMouseUp = () => {
      setIsResizing(false);
      document.body.style.cursor = 'default';
      document.body.style.userSelect = 'auto';
    };

    if (isResizing) {
      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    }

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isResizing]);

  const handleMouseDown = (e) => {
    setIsResizing(true);
    e.preventDefault();
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

  const shouldShowDraft = () => {
    // Only hide drafts that are sent (status === 'closed') and have a sent_message_id
    if (!draft || draft.status !== 'closed' || !draft.sent_message_id) {
      return true; // Show active drafts and sent drafts without message ID
    }

    // Check if any email in the current thread matches this draft's sent_message_id
    const hasMatchingEmail = threadEmails.some(threadEmail => 
      threadEmail.email_id === draft.sent_message_id ||
      threadEmail.id === draft.sent_message_id
    );

    // If there's a matching email, hide the draft; otherwise show it
    return !hasMatchingEmail;
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

  const renderDraftContent = () => {
    if (!draft) return null;

    const isEmail = draft.draft_type === 'email';
    const isSent = draft.status === 'closed';
    const isComplete = draftValidation?.is_complete || false;
    const isReply = draft.gmail_thread_id ? true : false;

    const formatRecipients = (recipients) => {
      if (!recipients || recipients.length === 0) return 'Not specified';
      return recipients.map(recipient => {
        if (typeof recipient === 'string') return recipient;
        if (recipient.name && recipient.email) return `${recipient.name} <${recipient.email}>`;
        return recipient.email || recipient.name || 'Unknown';
      }).join(', ');
    };

    return (
      <Box
        sx={{
          border: '1px solid #e0e0e0',
          borderRadius: '8px',
          p: 2,
          mb: 2,
          position: 'relative'
        }}
      >
        {/* Status Chip */}
        <Chip
          label={
            isSent
              ? (isEmail ? (isReply ? 'Reply Sent' : 'Email Sent') : 'Event Created')
              : (isEmail ? (isReply ? 'Reply Draft' : 'Email Draft') : 'Event Draft')
          }
          size="small"
          sx={{
            position: 'absolute',
            top: 12,
            right: 12,
            backgroundColor: isSent ? '#4caf50' : '#ff9800',
            color: 'white',
            fontWeight: 500
          }}
        />

        {isEmail ? (
          <>
            {/* To field */}
            <Box sx={{ mb: 1.5, mt: 1 }}>
              <Typography variant="body2" sx={{ fontWeight: 500, color: '#5f6368', mb: 0.5 }}>
                To:
              </Typography>
              <Typography variant="body2" sx={{ color: draft.to_emails?.length ? '#202124' : '#d32f2f' }}>
                {formatRecipients(draft.to_emails)}
              </Typography>
            </Box>

            {/* CC/BCC if present */}
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
                Subject: {isReply && <Typography component="span" variant="caption" sx={{ color: '#9e9e9e', ml: 0.5 }}>(read-only)</Typography>}
              </Typography>
              <Typography variant="body2" sx={{ color: draft.subject ? '#202124' : (isReply ? '#9e9e9e' : '#d32f2f'), fontStyle: isReply && !draft.subject ? 'italic' : 'normal' }}>
                {draft.subject || (isReply ? 'Re: [Thread subject will be used]' : 'Not specified')}
              </Typography>
            </Box>

            {/* Body */}
            {draft.body && (
              <Box sx={{ mb: 1.5 }}>
                <Typography variant="body2" sx={{ fontWeight: 500, color: '#5f6368', mb: 0.5 }}>
                  Body:
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
                    color: '#202124'
                  }}
                >
                  {draft.body}
                </Typography>
              </Box>
            )}
          </>
        ) : (
          <>
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
              <Typography variant="body2" sx={{ color: '#202124' }}>
                {draft.start_time && draft.end_time ? (
                  `${new Date(draft.start_time).toLocaleString()} - ${new Date(draft.end_time).toLocaleString()}`
                ) : (
                  <span style={{ color: '#d32f2f' }}>Not specified</span>
                )}
              </Typography>
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
                    color: '#202124'
                  }}
                >
                  {draft.description}
                </Typography>
              </Box>
            )}
          </>
        )}

        {/* Send Button - only show for drafts that are complete and not sent */}
        {!isSent && isComplete && onSendDraft && (
          <Button
            variant="contained"
            startIcon={<SendIcon />}
            onClick={onSendDraft}
            disabled={isSendingDraft}
            sx={{
              mt: 2,
              backgroundColor: '#4caf50',
              '&:hover': {
                backgroundColor: '#388e3c'
              },
              '&:disabled': {
                backgroundColor: '#ccc'
              }
            }}
            fullWidth
          >
            {isSendingDraft ? 'Sending...' : (isEmail ? 'Send Email' : 'Create Event')}
          </Button>
        )}
      </Box>
    );
  };

  if (!open) return null;

  return (
    <Box
      ref={sidebarRef}
      sx={{
        position: 'fixed',
        top: '73px', // Start below the header (header height + padding)
        right: 0,
        width: `${width}px`,
        height: 'calc(100vh - 73px)', // Adjust height to account for header
        backgroundColor: 'white',
        borderLeft: '1px solid #dee2e6',
        display: 'flex',
        flexDirection: 'row',
        zIndex: 1000, // Lower than header's z-index (1100)
        transition: isResizing ? 'none' : 'width 0.2s ease',
        boxShadow: '-2px 0 8px rgba(0,0,0,0.1)'
      }}
    >
      {/* Resize Handle */}
      <Box
        ref={resizeHandleRef}
        onMouseDown={handleMouseDown}
        sx={{
          position: 'absolute',
          left: '-4px',
          top: 0,
          bottom: 0,
          width: '8px',
          cursor: 'col-resize',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          '&:hover': {
            backgroundColor: 'rgba(0, 0, 0, 0.05)',
          },
          '&:hover .resize-indicator': {
            opacity: 1
          }
        }}
      >
        <DragIndicatorIcon
          className="resize-indicator"
          sx={{
            fontSize: '16px',
            color: '#5f6368',
            opacity: 0,
            transition: 'opacity 0.2s',
            pointerEvents: 'none'
          }}
        />
      </Box>

      {/* Content */}
      <Box sx={{ p: 2, display: 'flex', flexDirection: 'column', width: '100%', overflow: 'hidden' }}>
        {/* Header with close button and title */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography
            variant="h6"
            sx={{
              fontWeight: 600,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              flexGrow: 1,
              mr: 1
            }}
          >
            {contentType === 'draft'
              ? (draft?.draft_type === 'email' ? 'Email Draft' : 'Event Draft')
              : contentType === 'combined'
                ? (threadEmails?.[0]?.subject || draft?.subject || 'Thread')
                : (threadEmails?.[0]?.subject || email?.subject || 'Email')
            }
          </Typography>
          <IconButton onClick={onClose} size="small">
            <CloseIcon />
          </IconButton>
        </Box>

        {/* Content Area */}
        <Box sx={{ flexGrow: 1, overflowY: 'auto', overflowX: 'hidden' }}>
          {loading && (
            <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
              <CircularProgress />
            </Box>
          )}

          {error && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {error}
            </Alert>
          )}

          {contentType === 'draft' && draft && !loading && !error && (
            renderDraftContent()
          )}

          {contentType === 'combined' && !loading && !error && (threadEmails.length > 0 || threadDrafts.length > 0) && (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              {/* Combine emails and drafts, sort by date */}
              {[...threadEmails, ...threadDrafts]
                .sort((a, b) => new Date(a.date || a.created_at * 1000) - new Date(b.date || b.created_at * 1000))
                .map((item, index) => {
                  const isEmail = !!item.email_id;
                  const isDraft = !!item.draft_id;
                  const itemId = isEmail ? item.email_id : item.draft_id;
                  const isExpanded = expandedEmails.has(itemId);
                  const isLastItem = index === (threadEmails.length + threadDrafts.length - 1);
                  
                  // Auto-expand the last item or if there's only one item
                  const shouldAutoExpand = isLastItem || (threadEmails.length + threadDrafts.length === 1);
                  const isActuallyExpanded = isExpanded || shouldAutoExpand;
                  
                  const getDraftStatusColor = (status) => {
                    switch (status) {
                      case 'active': return '#1976d2';
                      case 'closed': return '#4caf50';
                      case 'composio_error': return '#f44336';
                      default: return '#757575';
                    }
                  };

                  const getDraftStatusLabel = (status) => {
                    switch (status) {
                      case 'active': return 'Draft';
                      case 'closed': return 'Sent';
                      case 'composio_error': return 'Error';
                      default: return 'Draft';
                    }
                  };
                  
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
                          borderRadius: 1,
                          '&:hover': {
                            backgroundColor: isDraft ? 'rgba(63, 81, 181, 0.05)' : 'rgba(0, 0, 0, 0.02)'
                          }
                        }}
                        onClick={() => toggleEmailExpansion(itemId)}
                      >
                        <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1.5 }}>
                          {/* Avatar */}
                          <Avatar
                            sx={{
                              width: 36,
                              height: 36,
                              bgcolor: isDraft ? getDraftStatusColor(item.status) : '#5f6368',
                              fontSize: '14px',
                              fontWeight: 500,
                              flexShrink: 0
                            }}
                          >
                            {isEmail 
                              ? getInitials(item.from_email?.name, item.from_email?.email)
                              : 'D' // Draft indicator
                            }
                          </Avatar>
                          
                          {/* Item Info */}
                          <Box sx={{ flex: 1, minWidth: 0 }}>
                            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 0.5 }}>
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mr: 1 }}>
                                <Typography
                                  variant="body2"
                                  sx={{
                                    fontWeight: 500,
                                    color: '#202124',
                                    overflow: 'hidden',
                                    textOverflow: 'ellipsis',
                                    whiteSpace: 'nowrap',
                                    maxWidth: '150px'
                                  }}
                                >
                                  {isEmail 
                                    ? (item.from_email?.name || item.from_email?.email || 'Unknown Sender')
                                    : 'Draft'
                                  }
                                </Typography>
                                {isDraft && (
                                  <Chip
                                    size="small"
                                    label={getDraftStatusLabel(item.status)}
                                    sx={{
                                      height: '18px',
                                      fontSize: '11px',
                                      fontWeight: 500,
                                      bgcolor: getDraftStatusColor(item.status),
                                      color: 'white',
                                      '& .MuiChip-label': { px: 1 }
                                    }}
                                  />
                                )}
                              </Box>
                              <Typography
                                variant="caption"
                                color="#5f6368"
                                sx={{ flexShrink: 0 }}
                              >
                                {formatDate(isEmail ? item.date : new Date(item.created_at * 1000).toISOString())}
                              </Typography>
                            </Box>
                            
                            {/* Expanded details */}
                            {isActuallyExpanded && (
                              <Box sx={{ mb: 1 }}>
                                {isEmail ? (
                                  <>
                                    <Typography
                                      variant="caption"
                                      color="#5f6368"
                                      sx={{
                                        fontWeight: 400,
                                        mb: 0.25,
                                        display: 'block',
                                        overflow: 'hidden',
                                        textOverflow: 'ellipsis',
                                        whiteSpace: 'nowrap'
                                      }}
                                    >
                                      From: {item.from_email?.name || 'Unknown'} &lt;{item.from_email?.email || 'unknown@example.com'}&gt;
                                    </Typography>
                                    <Typography
                                      variant="caption"
                                      color="#5f6368"
                                      sx={{
                                        fontWeight: 400,
                                        display: 'block',
                                        overflow: 'hidden',
                                        textOverflow: 'ellipsis',
                                        whiteSpace: 'nowrap'
                                      }}
                                    >
                                      To: {item.to_emails?.map(recipient =>
                                        `${recipient.name || recipient.email || 'Unknown'} <${recipient.email || 'unknown@example.com'}>`
                                      ).join(', ') || 'No recipients'}
                                    </Typography>
                                  </>
                                ) : (
                                  <>
                                    <Typography
                                      variant="caption"
                                      color="#5f6368"
                                      sx={{
                                        fontWeight: 400,
                                        mb: 0.25,
                                        display: 'block',
                                        overflow: 'hidden',
                                        textOverflow: 'ellipsis',
                                        whiteSpace: 'nowrap'
                                      }}
                                    >
                                      Subject: {item.subject || 'No subject'}
                                    </Typography>
                                    <Typography
                                      variant="caption"
                                      color="#5f6368"
                                      sx={{
                                        fontWeight: 400,
                                        display: 'block',
                                        overflow: 'hidden',
                                        textOverflow: 'ellipsis',
                                        whiteSpace: 'nowrap'
                                      }}
                                    >
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
                                variant="caption"
                                color="#5f6368"
                                sx={{
                                  overflow: 'hidden',
                                  textOverflow: 'ellipsis',
                                  whiteSpace: 'nowrap',
                                  maxWidth: '100%',
                                  display: 'block'
                                }}
                              >
                                {isEmail 
                                  ? (item.content?.text?.substring(0, 100) || 'No content')
                                  : (item.body?.substring(0, 100) || 'No content')
                                }
                                {((isEmail ? item.content?.text?.length : item.body?.length) > 100) ? '...' : ''}
                              </Typography>
                            )}
                          </Box>
                        </Box>
                      </Box>
                      
                      {/* Expanded Content */}
                      {isActuallyExpanded && (
                        <Box sx={{ pl: 5.5, pr: 2, pb: 2 }}>
                          <Box sx={{ mb: 2 }}>
                            {isEmail ? renderEmailBody(item) : (
                              <>
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
                                  {item.body || 'No content available'}
                                </Typography>
                                
                                {/* Send Button for active drafts - only show for the primary draft */}
                                {isDraft && item.status !== 'closed' && onSendDraft && draft && item.draft_id === draft.draft_id && draftValidation?.is_complete && (
                                  <Button
                                    variant="contained"
                                    startIcon={<SendIcon />}
                                    onClick={() => onSendDraft(item.draft_id)}
                                    disabled={isSendingDraft}
                                    sx={{
                                      mt: 2,
                                      backgroundColor: '#4caf50',
                                      '&:hover': {
                                        backgroundColor: '#388e3c'
                                      },
                                      '&:disabled': {
                                        backgroundColor: '#ccc'
                                      }
                                    }}
                                    size="small"
                                  >
                                    {isSendingDraft ? 'Sending...' : (item.draft_type === 'email' ? 'Send Email' : 'Create Event')}
                                  </Button>
                                )}
                              </>
                            )}
                          </Box>
                        </Box>
                      )}
                    </Box>
                  );
                })}
            </Box>
          )}

          {contentType === 'email' && email && !loading && !error && (
            <Box>
              {/* Thread Emails */}
              {threadEmails && threadEmails.length > 0 ? (
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  {threadEmails.map((threadEmail, index) => {
                    const isExpanded = expandedEmails.has(threadEmail.email_id);
                    const isCurrentEmail = threadEmail.email_id === email.email_id;
                    const isLastEmail = index === threadEmails.length - 1;
                    const isOnlyEmail = threadEmails.length === 1;

                    const shouldAutoExpand = isLastEmail || isOnlyEmail;
                    const isActuallyExpanded = isExpanded || shouldAutoExpand;

                    return (
                      <Box
                        key={threadEmail.email_id || index}
                        sx={{
                          width: '100%',
                          borderBottom: '1px solid #e0e0e0',
                          '&:last-child': { borderBottom: 'none' }
                        }}
                      >
                        {/* Email Header */}
                        <Box
                          sx={{
                            pt: 2,
                            pb: 2,
                            pr: 2,
                            cursor: 'pointer',
                            borderRadius: 1,
                            '&:hover': {
                              backgroundColor: 'rgba(0, 0, 0, 0.02)'
                            }
                          }}
                          onClick={() => toggleEmailExpansion(threadEmail.email_id)}
                        >
                          <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1.5 }}>
                            {/* Avatar */}
                            <Avatar
                              sx={{
                                width: 36,
                                height: 36,
                                bgcolor: isCurrentEmail ? '#1976d2' : '#5f6368',
                                fontSize: '14px',
                                fontWeight: 500,
                                flexShrink: 0
                              }}
                            >
                              {getInitials(
                                threadEmail.from_email?.name,
                                threadEmail.from_email?.email
                              )}
                            </Avatar>

                            {/* Email Info */}
                            <Box sx={{ flex: 1, minWidth: 0 }}>
                              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 0.5 }}>
                                <Typography
                                  variant="body2"
                                  sx={{
                                    fontWeight: 500,
                                    color: '#202124',
                                    overflow: 'hidden',
                                    textOverflow: 'ellipsis',
                                    whiteSpace: 'nowrap',
                                    mr: 1
                                  }}
                                >
                                  {threadEmail.from_email?.name || threadEmail.from_email?.email || 'Unknown Sender'}
                                </Typography>
                                <Typography
                                  variant="caption"
                                  color="#5f6368"
                                  sx={{ flexShrink: 0 }}
                                >
                                  {formatDate(threadEmail.date)}
                                </Typography>
                              </Box>

                              {/* From and To fields */}
                              {isActuallyExpanded && (
                                <Box sx={{ mb: 1 }}>
                                  <Typography
                                    variant="caption"
                                    color="#5f6368"
                                    sx={{
                                      fontWeight: 400,
                                      mb: 0.25,
                                      display: 'block',
                                      overflow: 'hidden',
                                      textOverflow: 'ellipsis',
                                      whiteSpace: 'nowrap'
                                    }}
                                  >
                                    From: {threadEmail.from_email?.name || 'Unknown'} &lt;{threadEmail.from_email?.email || 'unknown@example.com'}&gt;
                                  </Typography>
                                  <Typography
                                    variant="caption"
                                    color="#5f6368"
                                    sx={{
                                      fontWeight: 400,
                                      display: 'block',
                                      overflow: 'hidden',
                                      textOverflow: 'ellipsis',
                                      whiteSpace: 'nowrap'
                                    }}
                                  >
                                    To: {threadEmail.to_emails?.map(recipient =>
                                      `${recipient.name || recipient.email || 'Unknown'} <${recipient.email || 'unknown@example.com'}>`
                                    ).join(', ') || 'No recipients'}
                                  </Typography>
                                </Box>
                              )}

                              {/* Snippet (when collapsed) */}
                              {!isActuallyExpanded && threadEmail.content?.text && (
                                <Typography
                                  variant="caption"
                                  color="#5f6368"
                                  sx={{
                                    overflow: 'hidden',
                                    textOverflow: 'ellipsis',
                                    whiteSpace: 'nowrap',
                                    maxWidth: '100%',
                                    display: 'block'
                                  }}
                                >
                                  {threadEmail.content.text.substring(0, 100)}
                                  {threadEmail.content.text.length > 100 ? '...' : ''}
                                </Typography>
                              )}
                            </Box>
                          </Box>
                        </Box>

                        {/* Expanded Email Content */}
                        {isActuallyExpanded && (
                          <Box sx={{ pl: 5.5, pr: 2, pb: 2 }}>
                            <Box sx={{ mb: 2 }}>
                              {renderEmailBody(threadEmail)}
                            </Box>
                          </Box>
                        )}
                      </Box>
                    );
                  })}

                  {/* Show reply draft below thread if it exists and is not already displayed as an email */}
                  {draft && draft.gmail_thread_id && shouldShowDraft() && (
                    <Box sx={{ width: '100%', borderTop: '1px solid #e0e0e0', pt: 2 }}>
                      {renderDraftContent()}
                    </Box>
                  )}
                </Box>
              ) : (
                /* Single Email View */
                <Box
                  sx={{
                    width: '100%',
                    borderBottom: '1px solid #e0e0e0'
                  }}
                >
                  <Box sx={{ pt: 2, pb: 2, pr: 2, borderRadius: 1 }}>
                    <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1.5, mb: 2 }}>
                      <Avatar
                        sx={{
                          width: 36,
                          height: 36,
                          bgcolor: '#1976d2',
                          fontSize: '14px',
                          fontWeight: 500,
                          flexShrink: 0
                        }}
                      >
                        {getInitials(
                          email.from_email?.name,
                          email.from_email?.email
                        )}
                      </Avatar>

                      <Box sx={{ flex: 1, minWidth: 0 }}>
                        <Typography
                          variant="body2"
                          sx={{
                            fontWeight: 500,
                            color: '#202124',
                            mb: 0.5,
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap'
                          }}
                        >
                          {email.from_email?.name || email.from_email?.email || 'Unknown Sender'}
                        </Typography>
                        <Typography variant="caption" color="#5f6368" sx={{ mb: 1, display: 'block' }}>
                          {formatDate(email.date)}
                        </Typography>

                        {/* From and To fields */}
                        <Typography
                          variant="caption"
                          color="#5f6368"
                          sx={{
                            fontWeight: 400,
                            mb: 0.25,
                            display: 'block',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap'
                          }}
                        >
                          From: {email.from_email?.name || 'Unknown'} &lt;{email.from_email?.email || 'unknown@example.com'}&gt;
                        </Typography>
                        <Typography
                          variant="caption"
                          color="#5f6368"
                          sx={{
                            fontWeight: 400,
                            display: 'block',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap'
                          }}
                        >
                          To: {email.to_emails?.map(recipient =>
                            `${recipient.name || recipient.email || 'Unknown'} <${recipient.email || 'unknown@example.com'}>`
                          ).join(', ') || 'No recipients'}
                        </Typography>
                      </Box>
                    </Box>

                    <Box sx={{ pl: 5.5, mb: 2 }}>
                      {renderEmailBody(email)}
                    </Box>
                  </Box>
                </Box>
              )}
            </Box>
          )}
        </Box>
      </Box>
    </Box>
  );
};

export default ResizableEmailSidebar;