import React from 'react';
import {
  Drawer,
  Box,
  Typography,
  IconButton,
  Divider,
  Paper,
  CircularProgress,
  Alert
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import PersonIcon from '@mui/icons-material/Person';
import SubjectIcon from '@mui/icons-material/Subject';
import DateRangeIcon from '@mui/icons-material/DateRange';
import DOMPurify from 'dompurify';

const EmailSidebar = ({ 
  open, 
  email, 
  loading, 
  error, 
  onClose
}) => {
  
  // Check if mobile using React state for responsive updates
  const [isMobile, setIsMobile] = React.useState(window.innerWidth < 768);

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
      return date.toLocaleString('en-US', {
        weekday: 'short',
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
        hour12: true
      });
    } catch (error) {
      return dateString;
    }
  };

  const sanitizeHTML = (html) => {
    return DOMPurify.sanitize(html, {
      ALLOWED_TAGS: ['p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'a', 'div', 'span', 'table', 'tr', 'td', 'th', 'thead', 'tbody'],
      ALLOWED_ATTR: ['href', 'target', 'style'],
      ALLOW_DATA_ATTR: false
    });
  };

  const renderEmailBody = () => {
    if (!email || !email.content) return null;

    const { html, text } = email.content;
    
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
      <Box sx={{ p: 2, display: 'flex', flexDirection: 'column', height: '100%' }}>
        {/* Header with close button */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6" sx={{ fontWeight: 600 }}>
            Email
          </Typography>
          <IconButton onClick={onClose} size="small">
            <CloseIcon />
          </IconButton>
        </Box>

        {/* Content */}
        <Box sx={{ flexGrow: 1, overflowY: 'auto' }}>
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
            <Paper elevation={0} sx={{ p: 2, backgroundColor: 'white', borderRadius: 2 }}>
              {/* Subject */}
              <Box sx={{ mb: 2 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <SubjectIcon sx={{ fontSize: 16, mr: 1, color: 'text.secondary' }} />
                  <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'uppercase', fontWeight: 600 }}>
                    Subject
                  </Typography>
                </Box>
                <Typography variant="h6" sx={{ fontWeight: 500, mb: 1 }}>
                  {email.subject || 'No Subject'}
                </Typography>
              </Box>

              <Divider sx={{ mb: 2 }} />

              {/* From */}
              <Box sx={{ mb: 2 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <PersonIcon sx={{ fontSize: 16, mr: 1, color: 'text.secondary' }} />
                  <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'uppercase', fontWeight: 600 }}>
                    From
                  </Typography>
                </Box>
                <Typography variant="body2">
                  {email.from_email?.name || 'Unknown Sender'}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {email.from_email?.email || 'unknown@unknown.com'}
                </Typography>
              </Box>

              <Divider sx={{ mb: 2 }} />

              {/* Date */}
              <Box sx={{ mb: 2 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                  <DateRangeIcon sx={{ fontSize: 16, mr: 1, color: 'text.secondary' }} />
                  <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'uppercase', fontWeight: 600 }}>
                    Date
                  </Typography>
                </Box>
                <Typography variant="body2">
                  {formatDate(email.date)}
                </Typography>
              </Box>

              <Divider sx={{ mb: 2 }} />

              {/* Body */}
              <Box>
                <Typography variant="caption" color="text.secondary" sx={{ textTransform: 'uppercase', fontWeight: 600, mb: 1, display: 'block' }}>
                  Message
                </Typography>
                <Box sx={{ mt: 1 }}>
                  {renderEmailBody()}
                </Box>
              </Box>
            </Paper>
          )}
        </Box>
      </Box>
    </Drawer>
  );
};

export default EmailSidebar; 