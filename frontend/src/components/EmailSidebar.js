import React from 'react';
import {
  Drawer,
  Box,
  Typography,
  IconButton,
  CircularProgress,
  Alert,
  Avatar
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import DOMPurify from 'dompurify';

const EmailSidebar = ({ 
  open, 
  email, 
  threadEmails = [],  // Array of emails in the thread
  gmailThreadId = null,  // Gmail thread ID for context
  loading, 
  error, 
  onClose
}) => {
  
  // Check if mobile using React state for responsive updates
  const [isMobile, setIsMobile] = React.useState(window.innerWidth < 768);
  const [expandedEmails, setExpandedEmails] = React.useState(new Set());

  React.useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth < 768);
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);
  
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
    
    // Prefer HTML content if available, otherwise use text
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



  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={onClose}
      variant="temporary" // Always temporary for overlay behavior
      sx={{
        zIndex: 1300, // Higher than main content
        '& .MuiDrawer-paper': {
          width: isMobile ? '100%' : '60%', // 60% of viewport width on desktop
          boxSizing: 'border-box',
          backgroundColor: '#f8f9fa',
          borderLeft: isMobile ? 'none' : '1px solid #dee2e6',
          height: '100vh',
          position: 'fixed',
          top: 0,
          right: 0,
        },
      }}
    >
      <Box sx={{ p: 2, display: 'flex', flexDirection: 'column', height: '100%', bgcolor: 'white' }}>
        {/* Header with close button and email subject */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            {threadEmails?.[0]?.subject || email?.subject || 'Email'}
          </Typography>
          <IconButton onClick={onClose} size="small">
            <CloseIcon />
          </IconButton>
        </Box>

        {/* Gmail-style Thread View */}
        <Box sx={{ flexGrow: 1, overflowY: 'auto', bgcolor: 'white' }}>
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
                    
                    // Auto-expand the last email (newest) or if it's the only email
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
                            borderRadius: 1
                          }}
                          onClick={() => toggleEmailExpansion(threadEmail.email_id)}
                        >
                          <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2 }}>
                            {/* Avatar */}
                            <Avatar 
                              sx={{ 
                                width: 40, 
                                height: 40, 
                                bgcolor: isCurrentEmail ? '#1976d2' : '#5f6368',
                                fontSize: '16px',
                                fontWeight: 500
                              }}
                            >
                              {getInitials(
                                threadEmail.from_email?.name,
                                threadEmail.from_email?.email
                              )}
                            </Avatar>
                            
                            {/* Email Info */}
                            <Box sx={{ flex: 1, minWidth: 0 }}>
                              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                                <Typography variant="body1" sx={{ fontWeight: 500, color: '#202124' }}>
                                  {threadEmail.from_email?.name || threadEmail.from_email?.email || 'Unknown Sender'}
                                </Typography>
                                <Typography variant="caption" color="#5f6368">
                                  {formatDate(threadEmail.date)}
                                </Typography>
                              </Box>
                              
                              {/* From and To fields */}
                              {isActuallyExpanded && (
                                <Box sx={{ mb: 1 }}>
                                  <Typography variant="body2" color="#5f6368" sx={{ fontWeight: 500, mb: 0.5 }}>
                                    From: {threadEmail.from_email?.name || 'Unknown'} &lt;{threadEmail.from_email?.email || 'unknown@example.com'}&gt;
                                  </Typography>
                                  <Typography variant="body2" color="#5f6368" sx={{ fontWeight: 500 }}>
                                    To: {threadEmail.to_emails?.map(recipient => 
                                      `${recipient.name || recipient.email || 'Unknown'} <${recipient.email || 'unknown@example.com'}>`
                                    ).join(', ') || 'No recipients'}
                                  </Typography>
                                </Box>
                              )}
                              
                              {/* Snippet (when collapsed) */}
                              {!isActuallyExpanded && threadEmail.content?.text && (
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
                                  {threadEmail.content.text.substring(0, 120)}
                                  {threadEmail.content.text.length > 120 ? '...' : ''}
                                  </Typography>
                                )}
                              </Box>
                          </Box>
                        </Box>
                        
                        {/* Expanded Email Content */}
                        {isActuallyExpanded && (
                          <Box sx={{ pl: 6, pr: 2, pb: 2 }}>
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
                    <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2, mb: 2 }}>
                      <Avatar 
                        sx={{ 
                          width: 40, 
                          height: 40, 
                          bgcolor: '#1976d2',
                          fontSize: '16px',
                          fontWeight: 500
                        }}
                      >
                        {getInitials(
                          email.from_email?.name,
                          email.from_email?.email
                        )}
                      </Avatar>
                      
                      <Box sx={{ flex: 1 }}>
                        <Typography variant="body1" sx={{ fontWeight: 500, color: '#202124', mb: 1 }}>
                          {email.from_email?.name || email.from_email?.email || 'Unknown Sender'}
                        </Typography>
                        <Typography variant="body2" color="#5f6368" sx={{ mb: 1 }}>
                          {formatDate(email.date)}
                        </Typography>
                        
                        {/* From and To fields */}
                        <Typography variant="body2" color="#5f6368" sx={{ fontWeight: 500, mb: 0.5 }}>
                          From: {email.from_email?.name || 'Unknown'} &lt;{email.from_email?.email || 'unknown@example.com'}&gt;
                        </Typography>
                        <Typography variant="body2" color="#5f6368" sx={{ fontWeight: 500 }}>
                          To: {email.to_emails?.map(recipient => 
                            `${recipient.name || recipient.email || 'Unknown'} <${recipient.email || 'unknown@example.com'}>`
                          ).join(', ') || 'No recipients'}
                        </Typography>
                      </Box>
                    </Box>
                    
                    <Box sx={{ pl: 6, mb: 2 }}>
                      {renderEmailBody(email)}
                    </Box>
                  </Box>
                </Box>
              )}
            </Box>
          )}
        </Box>
      </Box>
    </Drawer>
  );
};

export default EmailSidebar; 