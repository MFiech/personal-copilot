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
  threadDrafts = [],  // Array of drafts in the thread  
  gmailThreadId = null,  // Gmail thread ID for context
  pmCopilotThreadId = null,  // PM Co-Pilot thread ID for context
  contentType = 'email', // 'email', 'draft', or 'combined'
  draft = null,  // Current draft object
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
        {/* Header with close button and thread subject */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            {contentType === 'combined' 
              ? (threadEmails?.[0]?.subject || draft?.subject || 'Thread') 
              : (threadEmails?.[0]?.subject || email?.subject || draft?.subject || 'Email')
            }
          </Typography>
          <IconButton onClick={onClose} size="small">
            <CloseIcon />
          </IconButton>
        </Box>

        {/* Combined Thread View (Emails + Drafts) */}
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

          {!loading && !error && (contentType === 'combined' ? (threadEmails.length > 0 || threadDrafts.length > 0) : (email || draft)) && (
            <Box>


              {/* Combined View: Display both emails and drafts chronologically */}
              {contentType === 'combined' ? (
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
                                    {isEmail 
                                      ? (item.content?.text?.substring(0, 120) || 'No content')
                                      : (item.body?.substring(0, 120) || 'No content')
                                    }
                                    {((isEmail ? item.content?.text?.length : item.body?.length) > 120) ? '...' : ''}
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
                            </Box>
                          )}
                        </Box>
                      );
                    })}
                </Box>
              ) : (
                /* Traditional single email/draft view */
                <Box>
                  {email && (
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
                  {draft && (
                    <Box
                      sx={{
                        width: '100%',
                        borderBottom: '1px solid #e0e0e0',
                        backgroundColor: '#f8f9ff'
                      }}
                    >
                      <Box sx={{ pt: 2, pb: 2, pr: 2, borderRadius: 1 }}>
                        <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2, mb: 2 }}>
                          <Avatar 
                            sx={{ 
                              width: 40, 
                              height: 40, 
                              bgcolor: getDraftStatusColor(draft.status),
                              fontSize: '16px',
                              fontWeight: 500
                            }}
                          >
                            D
                          </Avatar>
                          
                          <Box sx={{ flex: 1 }}>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                              <Typography variant="body1" sx={{ fontWeight: 500, color: '#202124' }}>
                                Draft
                              </Typography>
                              <Box
                                sx={{
                                  px: 1,
                                  py: 0.5,
                                  borderRadius: 1,
                                  bgcolor: getDraftStatusColor(draft.status),
                                  color: 'white',
                                  fontSize: '12px',
                                  fontWeight: 500
                                }}
                              >
                                {getDraftStatusLabel(draft.status)}
                              </Box>
                            </Box>
                            <Typography variant="body2" color="#5f6368" sx={{ mb: 1 }}>
                              {formatDate(new Date(draft.created_at * 1000).toISOString())}
                            </Typography>
                            
                            <Typography variant="body2" color="#5f6368" sx={{ fontWeight: 500, mb: 0.5 }}>
                              Subject: {draft.subject || 'No subject'}
                            </Typography>
                            <Typography variant="body2" color="#5f6368" sx={{ fontWeight: 500 }}>
                              To: {draft.to_emails?.map(recipient => 
                                `${recipient.name || recipient.email || 'Unknown'} <${recipient.email || 'unknown@example.com'}>`
                              ).join(', ') || 'No recipients'}
                            </Typography>
                          </Box>
                        </Box>
                        
                        <Box sx={{ pl: 6, mb: 2 }}>
                          {renderDraftBody(draft)}
                        </Box>
                      </Box>
                    </Box>
                  )}
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