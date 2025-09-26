import React from 'react';
import {
  Drawer,
  Box,
  Typography,
  IconButton,
  CircularProgress,
  Alert,
  Avatar,
  Button,
  Chip
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import SendIcon from '@mui/icons-material/Send';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import WarningIcon from '@mui/icons-material/Warning';
import DOMPurify from 'dompurify';
import { DraftService } from '../utils/draftService';

const EmailSidebar = ({ 
  open, 
  email, 
  threadEmails = [],  // Array of emails in the thread
  threadDrafts = [],  // Array of drafts in the thread  
  gmailThreadId = null,  // Gmail thread ID for context
  pmCopilotThreadId = null,  // PM Co-Pilot thread ID for context
  contentType = 'email', // 'email', 'draft', 'combined', 'calendar-event', 'calendar-event-combined'
  draft = null,  // Current draft object
  calendarEvent = null,  // Single calendar event
  threadCalendarEvents = [],  // Array of calendar events in thread
  threadCalendarDrafts = [],  // Array of calendar drafts in thread
  loading, 
  error, 
  onClose,
  onSendDraft = null,  // Callback when draft is sent
  showSnackbar = null  // Callback to show snackbar messages
}) => {
  
  // Debug logging for calendar sidebar
  console.log('[EmailSidebar] Props received:', {
    open,
    contentType,
    calendarEvent: calendarEvent ? 'present' : 'null',
    threadCalendarEvents: threadCalendarEvents?.length || 0,
    threadCalendarDrafts: threadCalendarDrafts?.length || 0,
    loading,
    error
  });
  
  // Debug the actual data
  console.log('[EmailSidebar] Props received:', {
    open,
    contentType,
    calendarEvent: calendarEvent ? 'present' : 'null',
    threadCalendarEvents: threadCalendarEvents?.length || 0,
    threadCalendarDrafts: threadCalendarDrafts?.length || 0,
    threadEmails: threadEmails?.length || 0,
    threadDrafts: threadDrafts?.length || 0,
    loading,
    error
  });
  
  if (contentType === 'calendar-event-combined') {
    console.log('[EmailSidebar] Calendar combined data:', {
      threadCalendarEvents,
      threadCalendarDrafts,
      combinedLength: [...threadCalendarEvents, ...threadCalendarDrafts].length
    });
  }
  
  // Check if mobile using React state for responsive updates
  const [isMobile, setIsMobile] = React.useState(window.innerWidth < 768);
  const [expandedEmails, setExpandedEmails] = React.useState(new Set());
  const [emailsWithContent, setEmailsWithContent] = React.useState(new Map());
  const [loadingContent, setLoadingContent] = React.useState(new Set());
  const [sendingDrafts, setSendingDrafts] = React.useState(new Set());

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

  // Simplified frontend validation function
  const validateDraftLocally = (draftItem) => {
    if (!draftItem) return { isComplete: false, reason: 'No draft', missingFields: [] };
    
    const missingFields = [];
    
    // For email drafts
    if (draftItem.draft_type === 'email') {
      // Check to_emails (always required)
      if (!draftItem.to_emails || draftItem.to_emails.length === 0) {
        missingFields.push('recipients');
      }
      
      // Check subject (required unless it's a reply with gmail_thread_id)
      const hasSubject = Boolean(draftItem.subject?.trim());
      const isReply = Boolean(draftItem.gmail_thread_id);
      if (!hasSubject && !isReply) {
        missingFields.push('subject');
      }
      
      // Check body (always required)
      if (!draftItem.body?.trim()) {
        missingFields.push('body');
      }
      
      const isComplete = missingFields.length === 0;
      let reason;
      if (isComplete) {
        reason = 'Ready to send';
      } else if (missingFields.length === 1) {
        reason = `Missing ${missingFields[0]}`;
      } else {
        reason = `Missing ${missingFields.slice(0, -1).join(', ')} and ${missingFields.slice(-1)}`;
      }
      
      return { isComplete, reason, missingFields };
    }
    
    // For calendar drafts
    if (draftItem.draft_type === 'calendar_event') {
      if (!draftItem.summary?.trim()) missingFields.push('title');
      if (!draftItem.start_time) missingFields.push('start time');
      if (!draftItem.end_time) missingFields.push('end time');
      
      const isComplete = missingFields.length === 0;
      let reason;
      if (isComplete) {
        reason = 'Ready to create';
      } else if (missingFields.length === 1) {
        reason = `Missing ${missingFields[0]}`;
      } else {
        reason = `Missing ${missingFields.slice(0, -1).join(', ')} and ${missingFields.slice(-1)}`;
      }
      
      return { isComplete, reason, missingFields };
    }
    
    return { isComplete: false, reason: 'Unknown draft type', missingFields: [] };
  };

  // Helper function to get clean text for preview (removes HTML and Markdown)
  const getCleanTextPreview = (emailContent) => {
    if (!emailContent) return 'No content';
    
    const { html, text } = emailContent;
    let cleanText = '';
    
    // Try text field first, but strip HTML if it contains HTML tags
    if (text && text.trim()) {
      if (text.includes('<') && text.includes('>')) {
        // Text field contains HTML, strip it
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = DOMPurify.sanitize(text, { ALLOWED_TAGS: [] });
        cleanText = tempDiv.textContent || tempDiv.innerText || '';
      } else {
        // Text field is clean, just remove any Markdown formatting
        cleanText = text
          .replace(/\*\*(.*?)\*\*/g, '$1') // Remove **bold**
          .replace(/\*(.*?)\*/g, '$1')     // Remove *italic*
          .replace(/\[(.*?)\]\(.*?\)/g, '$1') // Remove [link](url)
          .replace(/#{1,6}\s/g, '')        // Remove # headers
          .replace(/^\s*[-*+]\s/gm, '')   // Remove bullet points
          .replace(/^\s*\d+\.\s/gm, '')   // Remove numbered lists
      }
    } else if (html && html.trim()) {
      // Fallback: use HTML field and strip HTML tags
      const tempDiv = document.createElement('div');
      tempDiv.innerHTML = DOMPurify.sanitize(html, { ALLOWED_TAGS: [] });
      cleanText = tempDiv.textContent || tempDiv.innerText || '';
    }
    
    // Clean up whitespace
    cleanText = cleanText
      .replace(/\n\s*\n/g, ' ')  // Replace multiple newlines with space
      .replace(/\s+/g, ' ')     // Replace multiple spaces with single space
      .trim();
    
    return cleanText || 'No content';
  };

  // Send draft
  const handleSendDraft = async (draftItem) => {
    // Quick local validation before sending
    const validation = validateDraftLocally(draftItem);
    if (!validation.isComplete) {
      if (showSnackbar) {
        showSnackbar(`Cannot send: ${validation.reason}`, 'warning');
      }
      return;
    }
    
    setSendingDrafts(prev => new Set(prev).add(draftItem.draft_id));
    try {
      const response = await DraftService.sendDraft(draftItem.draft_id);
      if (response.success) {
        if (showSnackbar) {
          showSnackbar(response.message || 'Draft sent successfully!', 'success');
        }
        if (onSendDraft) onSendDraft(draftItem.draft_id);
      } else {
        if (showSnackbar) {
          showSnackbar(response.error || 'Failed to send draft', 'error');
        }
      }
    } catch (error) {
      console.error('Error sending draft:', error);
      if (showSnackbar) {
        showSnackbar(`Failed to send draft: ${error.message}`, 'error');
      }
    } finally {
      setSendingDrafts(prev => {
        const newSet = new Set(prev);
        newSet.delete(draftItem.draft_id);
        return newSet;
      });
    }
  };

  // No complex validation effects needed - we use simple frontend validation now



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
              : contentType === 'calendar-event-combined'
              ? (threadCalendarEvents?.[0]?.summary || threadCalendarDrafts?.[0]?.summary || 'Calendar Event')
              : contentType === 'calendar-event'
              ? (calendarEvent?.summary || 'Calendar Event')
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

          {!loading && !error && (
            contentType === 'combined' ? (threadEmails.length > 0 || threadDrafts.length > 0 || threadCalendarEvents.length > 0 || threadCalendarDrafts.length > 0) :
            contentType === 'calendar-event-combined' ? (threadCalendarEvents.length > 0 || threadCalendarDrafts.length > 0) :
            contentType === 'calendar-event' ? calendarEvent :
            (email || draft)
          ) && (
            <Box>


              {/* Combined View: Display both emails and drafts chronologically, or calendar events and drafts */}
              {contentType === 'combined' ? (
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  {/* Check if this is calendar data or email data */}
                  {threadCalendarEvents.length > 0 || threadCalendarDrafts.length > 0 ? (
                    /* Calendar Event Combined View */
                    <>
                      {/* Debug logging */}
                      {console.log('[EmailSidebar] Calendar combined view - threadCalendarEvents:', threadCalendarEvents)}
                      {console.log('[EmailSidebar] Calendar combined view - threadCalendarDrafts:', threadCalendarDrafts)}
                      {console.log('[EmailSidebar] Calendar combined view - combined items:', [...threadCalendarEvents, ...threadCalendarDrafts])}
                      
                      {/* Combine calendar events and drafts, sort by date */}
                      {[...threadCalendarEvents, ...threadCalendarDrafts]
                        .sort((a, b) => new Date(a.start?.dateTime || a.created_at * 1000) - new Date(b.start?.dateTime || b.created_at * 1000))
                        .map((item, index) => {
                          const isCalendarEvent = !!item.internal_event_id;
                          const isDraft = !!item.draft_id;
                          const itemId = isCalendarEvent ? item.internal_event_id : item.draft_id;
                          const isExpanded = expandedEmails.has(itemId);
                          const isLastItem = index === (threadCalendarEvents.length + threadCalendarDrafts.length - 1);
                      
                          // Auto-expand the last item or if there's only one item
                          const shouldAutoExpand = isLastItem || (threadCalendarEvents.length + threadCalendarDrafts.length === 1);
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
                                    {isCalendarEvent 
                                      ? '📅' // Calendar event indicator
                                      : 'D' // Draft indicator
                                    }
                                  </Avatar>
                              
                                  {/* Item Info */}
                                  <Box sx={{ flex: 1, minWidth: 0 }}>
                                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                        <Typography variant="body1" sx={{ fontWeight: 500, color: '#202124' }}>
                                          {isCalendarEvent
                                            ? (item.summary || 'Calendar Event')
                                            : (item.summary || 'Draft')
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
                                        {formatDate(isCalendarEvent ? item.start?.dateTime : new Date(item.created_at * 1000).toISOString())}
                                      </Typography>
                                    </Box>
                                
                                    {/* Expanded details */}
                                    {isActuallyExpanded && (
                                      <Box sx={{ mb: 1 }}>
                                        {isCalendarEvent ? (
                                          <>
                                            <Typography variant="body2" color="#5f6368" sx={{ fontWeight: 500, mb: 0.5 }}>
                                              📅 {item.summary || 'Calendar Event'}
                                            </Typography>
                                            {item.description && (
                                              <Typography variant="body2" color="#5f6368" sx={{ fontWeight: 500, mb: 0.5 }}>
                                                Description: {item.description}
                                              </Typography>
                                            )}
                                            {item.location && (
                                              <Typography variant="body2" color="#5f6368" sx={{ fontWeight: 500, mb: 0.5 }}>
                                                📍 Location: {item.location}
                                              </Typography>
                                            )}
                                            {item.start?.dateTime && (
                                              <Typography variant="body2" color="#5f6368" sx={{ fontWeight: 500 }}>
                                                ⏰ Time: {new Date(item.start.dateTime).toLocaleString()}
                                              </Typography>
                                            )}
                                          </>
                                        ) : (
                                          <>
                                            <Typography variant="body2" color="#5f6368" sx={{ fontWeight: 500, mb: 0.5 }}>
                                              Summary: {item.summary || 'No summary'}
                                            </Typography>
                                            <Typography variant="body2" color="#5f6368" sx={{ fontWeight: 500 }}>
                                              Draft Type: {item.draft_type || 'calendar_event'}
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
                                          const cleanText = isCalendarEvent 
                                            ? (item.description || item.location || 'Calendar event')
                                            : (item.body || 'No content');
                                          const truncated = cleanText.substring(0, 120);
                                          return truncated + (cleanText.length > 120 ? '...' : '');
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
                                    {isCalendarEvent ? (
                                      <Box>
                                        <Typography variant="body2" sx={{ mb: 1 }}>
                                          <strong>Summary:</strong> {item.summary || 'No summary'}
                                        </Typography>
                                        {item.description && (
                                          <Typography variant="body2" sx={{ mb: 1 }}>
                                            <strong>Description:</strong> {item.description}
                                          </Typography>
                                        )}
                                        {item.location && (
                                          <Typography variant="body2" sx={{ mb: 1 }}>
                                            <strong>Location:</strong> {item.location}
                                          </Typography>
                                        )}
                                        {item.start?.dateTime && (
                                          <Typography variant="body2" sx={{ mb: 1 }}>
                                            <strong>Start:</strong> {new Date(item.start.dateTime).toLocaleString()}
                                          </Typography>
                                        )}
                                        {item.end?.dateTime && (
                                          <Typography variant="body2" sx={{ mb: 1 }}>
                                            <strong>End:</strong> {new Date(item.end.dateTime).toLocaleString()}
                                          </Typography>
                                        )}
                                      </Box>
                                    ) : (
                                      renderDraftBody(item)
                                    )}
                                  </Box>
                              
                              {/* Draft send button - Always visible with simplified validation */}
                              {isDraft && item.status !== 'closed' && (
                                <Box sx={{ display: 'flex', gap: 1, justifyContent: 'flex-end', alignItems: 'center', mt: 2 }}>
                                  {(() => {
                                    const validation = validateDraftLocally(item);
                                    const isSending = sendingDrafts.has(item.draft_id);
                                    
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
                                          startIcon={isSending ? <CircularProgress size={16} color="inherit" /> : <SendIcon />}
                                          onClick={() => handleSendDraft(item)}
                                          disabled={!validation.isComplete || isSending}
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
                                          {isSending ? 'Sending...' : (validation.isComplete ? 'Send' : 'Incomplete')}
                                        </Button>
                                      </>
                                    );
                                  })()
                                )}
                                </Box>
                              )}
                            </Box>
                          )}
                        </Box>
                      );
                    })}
                    </>
                  ) : (
                    /* Email Combined View */
                    <>
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
                                        {(() => {
                                          const cleanText = isEmail 
                                            ? getCleanTextPreview(item.content)
                                            : (item.body || 'No content');
                                          const truncated = cleanText.substring(0, 120);
                                          return truncated + (cleanText.length > 120 ? '...' : '');
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
                                  
                                  {/* Draft send button - Always visible with simplified validation */}
                                  {isDraft && item.status !== 'closed' && (
                                    <Box sx={{ display: 'flex', gap: 1, justifyContent: 'flex-end', alignItems: 'center', mt: 2 }}>
                                      {(() => {
                                        const validation = validateDraftLocally(item);
                                        const isSending = sendingDrafts.has(item.draft_id);
                                        
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
                                              startIcon={isSending ? <CircularProgress size={16} color="inherit" /> : <SendIcon />}
                                              onClick={() => handleSendDraft(item)}
                                              disabled={!validation.isComplete || isSending}
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
                                              {isSending ? 'Sending...' : 'Send Draft'}
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
                    </>
                  )}
                </Box>
              ) : contentType === 'calendar-event-combined' ? (
                /* Calendar Event Combined View: Display original event and drafts chronologically */
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  {/* Debug logging */}
                  {console.log('[EmailSidebar] Calendar combined view - threadCalendarEvents:', threadCalendarEvents)}
                  {console.log('[EmailSidebar] Calendar combined view - threadCalendarDrafts:', threadCalendarDrafts)}
                  {console.log('[EmailSidebar] Calendar combined view - combined items:', [...threadCalendarEvents, ...threadCalendarDrafts])}
                  
                  {/* Combine calendar events and drafts, sort by date */}
                  {[...threadCalendarEvents, ...threadCalendarDrafts]
                    .sort((a, b) => new Date(a.start?.dateTime || a.created_at * 1000) - new Date(b.start?.dateTime || b.created_at * 1000))
                    .map((item, index) => {
                      const isCalendarEvent = !!item.id && !item.draft_id;
                      const isDraft = !!item.draft_id;
                      const itemId = isCalendarEvent ? item.id : item.draft_id;
                      const isExpanded = expandedEmails.has(itemId);
                      const isLastItem = index === (threadCalendarEvents.length + threadCalendarDrafts.length - 1);
                      
                      // Auto-expand the last item or if there's only one item
                      const shouldAutoExpand = isLastItem || (threadCalendarEvents.length + threadCalendarDrafts.length === 1);
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
                                  bgcolor: isDraft ? getDraftStatusColor(item.status) : '#1976d2',
                                  fontSize: '16px',
                                  fontWeight: 500
                                }}
                              >
                                {isCalendarEvent ? '📅' : 'D'} {/* Calendar icon for events, D for drafts */}
                              </Avatar>
                              
                              {/* Item Info */}
                              <Box sx={{ flex: 1, minWidth: 0 }}>
                                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                    <Typography variant="body1" sx={{ fontWeight: 500, color: '#202124' }}>
                                      {isCalendarEvent ? 'Calendar Event' : 'Draft'}
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
                                    {formatDate(isCalendarEvent ? item.start?.dateTime : new Date(item.created_at * 1000).toISOString())}
                                  </Typography>
                                </Box>
                                
                                {/* Expanded details */}
                                {isActuallyExpanded && (
                                  <Box sx={{ mb: 1 }}>
                                    {isCalendarEvent ? (
                                      <>
                                        <Typography variant="body2" color="#5f6368" sx={{ fontWeight: 500, mb: 0.5 }}>
                                          Title: {item.summary || 'No title'}
                                        </Typography>
                                        <Typography variant="body2" color="#5f6368" sx={{ fontWeight: 500 }}>
                                          Time: {item.start?.dateTime ? new Date(item.start.dateTime).toLocaleString() : 'No time set'}
                                        </Typography>
                                      </>
                                    ) : (
                                      <>
                                        <Typography variant="body2" color="#5f6368" sx={{ fontWeight: 500, mb: 0.5 }}>
                                          Title: {item.summary || 'No title'}
                                        </Typography>
                                        <Typography variant="body2" color="#5f6368" sx={{ fontWeight: 500 }}>
                                          Time: {item.start_time ? new Date(item.start_time.dateTime || item.start_time).toLocaleString() : 'No time set'}
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
                                      const cleanText = isCalendarEvent 
                                        ? (item.description || item.summary || 'No content')
                                        : (item.description || item.summary || 'No content');
                                      const truncated = cleanText.substring(0, 120);
                                      return truncated + (cleanText.length > 120 ? '...' : '');
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
                                {isCalendarEvent ? (
                                  <Box>
                                    <Typography variant="body2" sx={{ mb: 1, fontWeight: 500 }}>
                                      {item.summary || 'No title'}
                                    </Typography>
                                    <Typography variant="body2" color="#5f6368" sx={{ mb: 1 }}>
                                      {item.description || 'No description'}
                                    </Typography>
                                    <Typography variant="body2" color="#5f6368">
                                      Start: {item.start?.dateTime ? new Date(item.start.dateTime).toLocaleString() : 'No start time'}
                                    </Typography>
                                    <Typography variant="body2" color="#5f6368">
                                      End: {item.end?.dateTime ? new Date(item.end.dateTime).toLocaleString() : 'No end time'}
                                    </Typography>
                                    {item.location && (
                                      <Typography variant="body2" color="#5f6368">
                                        Location: {item.location}
                                      </Typography>
                                    )}
                                  </Box>
                                ) : (
                                  renderDraftBody(item)
                                )}
                              </Box>
                              
                              {/* Draft send button - Always visible with simplified validation */}
                              {isDraft && item.status !== 'closed' && (
                                <Box sx={{ display: 'flex', gap: 1, justifyContent: 'flex-end', alignItems: 'center', mt: 2 }}>
                                  {(() => {
                                    const validation = validateDraftLocally(item);
                                    const isSending = sendingDrafts.has(item.draft_id);
                                    
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
                                          startIcon={isSending ? <CircularProgress size={16} color="inherit" /> : <SendIcon />}
                                          onClick={() => handleSendDraft(item)}
                                          disabled={!validation.isComplete || isSending}
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
                                          {isSending ? 'Sending...' : (validation.isComplete ? 'Send' : 'Incomplete')}
                                        </Button>
                                      </>
                                    );
                                  })()
                                )}
                                </Box>
                              )}
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
                  {calendarEvent && (
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
                            📅
                          </Avatar>
                          
                          <Box sx={{ flex: 1 }}>
                            <Typography variant="body1" sx={{ fontWeight: 500, color: '#202124', mb: 1 }}>
                              Calendar Event
                            </Typography>
                            <Typography variant="body2" color="#5f6368" sx={{ mb: 1 }}>
                              {formatDate(calendarEvent.start?.dateTime)}
                            </Typography>
                            
                            <Typography variant="body2" color="#5f6368" sx={{ fontWeight: 500, mb: 0.5 }}>
                              Title: {calendarEvent.summary || 'No title'}
                            </Typography>
                            <Typography variant="body2" color="#5f6368" sx={{ fontWeight: 500 }}>
                              Time: {calendarEvent.start?.dateTime ? new Date(calendarEvent.start.dateTime).toLocaleString() : 'No time set'}
                            </Typography>
                          </Box>
                        </Box>
                        
                        <Box sx={{ pl: 6, mb: 2 }}>
                          <Box>
                            <Typography variant="body2" sx={{ mb: 1, fontWeight: 500 }}>
                              {calendarEvent.summary || 'No title'}
                            </Typography>
                            <Typography variant="body2" color="#5f6368" sx={{ mb: 1 }}>
                              {calendarEvent.description || 'No description'}
                            </Typography>
                            <Typography variant="body2" color="#5f6368">
                              Start: {calendarEvent.start?.dateTime ? new Date(calendarEvent.start.dateTime).toLocaleString() : 'No start time'}
                            </Typography>
                            <Typography variant="body2" color="#5f6368">
                              End: {calendarEvent.end?.dateTime ? new Date(calendarEvent.end.dateTime).toLocaleString() : 'No end time'}
                            </Typography>
                            {calendarEvent.location && (
                              <Typography variant="body2" color="#5f6368">
                                Location: {calendarEvent.location}
                              </Typography>
                            )}
                          </Box>
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
                        
                        {/* Draft send button - Always visible with simplified validation */}
                        {draft.status !== 'closed' && (
                          <Box sx={{ display: 'flex', gap: 1, justifyContent: 'flex-end', alignItems: 'center', px: 2, pb: 2 }}>
                            {(() => {
                              const validation = validateDraftLocally(draft);
                              const isSending = sendingDrafts.has(draft.draft_id);
                              
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
                                    startIcon={isSending ? <CircularProgress size={16} color="inherit" /> : <SendIcon />}
                                    onClick={() => handleSendDraft(draft)}
                                    disabled={!validation.isComplete || isSending}
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
                                    {isSending ? 'Sending...' : (validation.isComplete ? 'Send' : 'Incomplete')}
                                  </Button>
                                </>
                              );
                            })()
                          )}
                          </Box>
                        )}
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