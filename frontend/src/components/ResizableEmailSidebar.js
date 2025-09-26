import React, { useState, useRef, useEffect } from 'react';
import {
  Box,
  Typography,
  IconButton,
  CircularProgress,
  Alert
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import DragIndicatorIcon from '@mui/icons-material/DragIndicator';
import EmailThreadComponent from './EmailThreadComponent';
import EmailDraftComponent from './EmailDraftComponent';
import CalendarDraftComponent from './CalendarDraftComponent';
import CalendarEventComponent from './CalendarEventComponent';
import CalendarThreadComponent from './CalendarThreadComponent';
import { DraftService } from '../utils/draftService';
import { useSnackbar } from './SnackbarProvider';

const UnifiedSidebar = ({
  open,
  email,
  threadEmails = [],
  threadDrafts = [],
  gmailThreadId = null,
  pmCopilotThreadId = null,
  draft = null,
  calendarEvent = null,
  threadCalendarEvents = [],
  threadCalendarDrafts = [],
  loading,
  error,
  onClose,
  onWidthChange,
  contentType = 'email', // 'email', 'thread', 'email-draft', 'calendar-draft', 'calendar-event', 'calendar-combined'
  onSendDraft = null,
  isSendingDraft = false
}) => {
  const [width, setWidth] = useState(420);
  const [isResizing, setIsResizing] = useState(false);
  const sidebarRef = useRef(null);
  const resizeHandleRef = useRef(null);
  const { showSnackbar } = useSnackbar();

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

  // Function to handle sending drafts
  const handleSendDraft = async (draftToSend) => {
    if (!onSendDraft) return;

    try {
      await onSendDraft(draftToSend);
      // Don't show success message here - let App.js handle it along with sidebar refresh
    } catch (error) {
      console.error('Error sending draft:', error);
      showSnackbar('Failed to send draft. Please try again.', 'error');
    }
  };

  // Function to render content based on content type
  const renderContent = () => {
    if (loading) {
      return (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
          <CircularProgress />
        </Box>
      );
    }

    if (error) {
      return (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      );
    }

    switch (contentType) {
      case 'thread':
        return (
          <EmailThreadComponent
            threadEmails={threadEmails}
            threadDrafts={threadDrafts}
            onSendDraft={handleSendDraft}
            isSendingDraft={isSendingDraft}
          />
        );
      
      case 'email-draft':
        return (
          <EmailDraftComponent
            draft={draft}
            onSendDraft={handleSendDraft}
            isSendingDraft={isSendingDraft}
          />
        );
      
      case 'calendar-draft':
        return (
          <CalendarDraftComponent
            draft={draft}
            onSendDraft={handleSendDraft}
            isSendingDraft={isSendingDraft}
          />
        );

      case 'calendar-event':
        return (
          <CalendarEventComponent
            event={calendarEvent}
            showHeader={true}
            showActions={true}
          />
        );

      case 'calendar-combined':
        // Combined view shows calendar event and related draft
        return (
          <Box>
            {calendarEvent && (
              <CalendarEventComponent
                event={calendarEvent}
                showHeader={true}
                showActions={false}
              />
            )}
            {draft && (
              <Box sx={{ mt: 2, pt: 2, borderTop: 1, borderColor: 'divider' }}>
                <CalendarDraftComponent
                  draft={draft}
                  onSendDraft={handleSendDraft}
                  isSendingDraft={isSendingDraft}
                />
              </Box>
            )}
          </Box>
        );

      case 'combined':
        // Check if we have calendar data - use calendar thread component
        if ((threadCalendarEvents && threadCalendarEvents.length > 0) || (threadCalendarDrafts && threadCalendarDrafts.length > 0)) {
          return (
            <CalendarThreadComponent
              threadCalendarEvents={threadCalendarEvents}
              threadCalendarDrafts={threadCalendarDrafts}
              onSendDraft={handleSendDraft}
              isSendingDraft={isSendingDraft}
              showSnackbar={showSnackbar}
            />
          );
        }
        // Otherwise use email thread component for emails + drafts
        return (
          <EmailThreadComponent
            threadEmails={threadEmails}
            threadDrafts={threadDrafts}
            onSendDraft={handleSendDraft}
            isSendingDraft={isSendingDraft}
          />
        );

      case 'email':
      default:
        // For single email view, we can create a simple email display
        // or use EmailThreadComponent with just one email
        return (
          <EmailThreadComponent
            threadEmails={email ? [email] : []}
            threadDrafts={draft ? [draft] : []}
            onSendDraft={handleSendDraft}
            isSendingDraft={isSendingDraft}
          />
        );
    }
  };

  // Function to get appropriate title based on content
  const getSidebarTitle = () => {
    switch (contentType) {
      case 'thread':
        return threadEmails?.[0]?.subject || 'Email Thread';
      
      case 'email-draft':
        if (draft?.status === 'closed') {
          return draft?.gmail_thread_id ? 'Reply Sent' : 'Email Sent';
        }
        return draft?.gmail_thread_id ? 'Reply Draft' : 'Email Draft';
      
      case 'calendar-draft':
        return draft?.status === 'closed' ? 'Event Created' : 'Calendar Draft';

      case 'calendar-event':
        return calendarEvent?.summary || 'Calendar Event';

      case 'calendar-combined':
        if (draft?.status === 'closed') {
          return 'Event Updated';
        }
        return calendarEvent?.summary ? `Modifying: ${calendarEvent.summary}` : 'Calendar Event & Draft';

      case 'email':
      default:
        return email?.subject || 'Email';
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
            {getSidebarTitle()}
          </Typography>
          <IconButton onClick={onClose} size="small">
            <CloseIcon />
          </IconButton>
        </Box>

        {/* Content Area */}
        <Box sx={{ flexGrow: 1, overflowY: 'auto', overflowX: 'hidden' }}>
          {renderContent()}
        </Box>
      </Box>
    </Box>
  );
};

export default UnifiedSidebar;
