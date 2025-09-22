import React, { useState, useRef, useEffect } from 'react';
import {
  Box,
  Typography,
  IconButton,
  CircularProgress,
  Alert,
  Avatar
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import DragIndicatorIcon from '@mui/icons-material/DragIndicator';
import DOMPurify from 'dompurify';

const ResizableEmailSidebar = ({
  open,
  email,
  threadEmails = [],
  gmailThreadId = null,
  loading,
  error,
  onClose,
  onWidthChange
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
        {/* Header with close button and email subject */}
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
            {threadEmails?.[0]?.subject || email?.subject || 'Email'}
          </Typography>
          <IconButton onClick={onClose} size="small">
            <CloseIcon />
          </IconButton>
        </Box>

        {/* Email Content Area */}
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

          {email && !loading && !error && (
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