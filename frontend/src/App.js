import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  CssBaseline,
  ThemeProvider,
  createTheme,
  Drawer,
  List,
  ListItem,
  ListItemText,
  Paper,
  Typography,
  TextField,
  Button,
  IconButton,
  CircularProgress,
  Snackbar,
  InputAdornment,
} from '@mui/material';
import SaveIcon from '@mui/icons-material/Save';
import MenuIcon from '@mui/icons-material/Menu';
import EditIcon from '@mui/icons-material/Edit';
import CheckIcon from '@mui/icons-material/Check';
import DeleteIcon from '@mui/icons-material/Delete';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogContentText from '@mui/material/DialogContentText';
import DialogTitle from '@mui/material/DialogTitle';
import VeyraResults from './components/VeyraResults';
import './App.css';
import { useSnackbar } from './components/SnackbarProvider';

// Import new icons
import SendIcon from '@mui/icons-material/Send';
import AttachFileIcon from '@mui/icons-material/AttachFile';
import MicIcon from '@mui/icons-material/Mic';
// import MenuOpenIcon from '@mui/icons-material/MenuOpen'; // Alternative for sidebar toggle
// import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown'; // For model selector dropdown

const theme = createTheme({
  palette: {
    mode: 'light', // Assuming light mode as base
    primary: { main: '#1976d2' }, // Default primary, user messages will override this locally
    secondary: { main: '#388e3c' },
    background: {
      default: '#fff', // Main background of the app
      paper: '#ffffff', // Default for Paper components
      inputArea: '#f0f2f5', // Light grey for the input area container
      assistantMessage: '#f1f3f4', // Light grey for assistant messages
      userMessage: '#202123' // Dark grey/black for user messages
    },
    text: {
      primary: '#000000',
      secondary: '#5f6368',
      userMessage: '#ffffff'
    }
  },
  shape: {
    borderRadius: 8, // Default border radius
  },
  typography: {
    fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
    body1: {
      fontSize: '1rem',
    },
    body2: {
      fontSize: '0.875rem',
    },
    caption: {
      fontSize: '0.75rem',
    }
  },
});

const drawerWidth = 240; // Define drawer width as a constant

function App() {
  const { threadId } = useParams();
  const navigate = useNavigate();
  
  const [threads, setThreads] = useState([]);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  
  // Initialize isMobile and drawerOpen based on initial window width
  const initialIsMobile = window.innerWidth < 768; // Using 768 as the breakpoint
  const [isMobile, setIsMobile] = useState(initialIsMobile);
  const [drawerOpen, setDrawerOpen] = useState(!initialIsMobile); // Open on desktop, closed on mobile by default
  
  const [pendingConfirmation, setPendingConfirmation] = useState(null);
  const [editingThreadId, setEditingThreadId] = useState(null);
  const [editTitle, setEditTitle] = useState('');
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [threadToDelete, setThreadToDelete] = useState(null);

  const { showSnackbar } = useSnackbar();

  // Fetch threads on initial mount
  useEffect(() => {
    fetchThreads();
  }, []);

  // Handle resize for isMobile and drawerOpen adjustments
  useEffect(() => {
    const handleResize = () => {
      const newIsMobile = window.innerWidth < 768; // Consistent breakpoint
      setIsMobile(newIsMobile);
      if (newIsMobile) {
        // If screen becomes mobile, ensure drawer is closed (as it's 'temporary' variant)
        setDrawerOpen(false);
      }
      // On desktop, drawerOpen state is controlled by user toggle.
      // The initial state useState(!initialIsMobile) ensures it's open by default on desktop.
    };

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []); // Empty dependency array as it only sets up/cleans up a global listener

  // Load thread from URL parameter
  useEffect(() => {
    if (threadId) {
      loadThread(threadId);
    } else {
      // Clear messages when on root path
      setMessages([]);
    }
  }, [threadId]);

  // Fetch threads from backend
  const fetchThreads = async () => {
    setIsLoading(true);
    try {
      const response = await fetch('http://localhost:5001/threads');
      const data = await response.json();
      setThreads(data.threads || []);
    } catch (error) {
      console.error('Error fetching threads:', error);
    } finally {
      setIsLoading(false);
    }
  };

  // Load a specific thread
  const loadThread = async (threadId) => {
    setIsLoading(true);
    try {
      const response = await fetch(`http://localhost:5001/chat/${threadId}`);
      const data = await response.json();
      
      // If data is an array, use it directly
      if (Array.isArray(data)) {
        const formattedMessages = data.map(msg => ({
          role: msg.role,
          content: msg.content || '',
          timestamp: msg.timestamp || (msg.role === 'user' ? msg.query_timestamp : msg.response_timestamp),
          veyra_results: msg.veyra_results || null,
          message_id: msg.message_id,
          // Add pagination fields if they exist
          veyra_original_query_params: msg.veyra_original_query_params,
          veyra_current_offset: msg.veyra_current_offset,
          veyra_limit_per_page: msg.veyra_limit_per_page,
          veyra_total_emails_available: msg.veyra_total_emails_available,
          veyra_has_more: msg.veyra_has_more
        }));

        // Sort messages by timestamp in ascending order (oldest first)
        const sortedMessages = formattedMessages.sort((a, b) => 
          (a.timestamp || 0) - (b.timestamp || 0)
        );
        
        setMessages(sortedMessages);
      } else if (data && data.messages && Array.isArray(data.messages)) {
        // Handle the case where messages are nested in a data object
        const formattedMessages = data.messages
          .filter(msg => msg !== null && msg !== undefined)
          .map(msg => {
            if ('role' in msg) {
              return {
                role: msg.role,
                content: msg.content || '',
                timestamp: msg.role === 'user' ? msg.query_timestamp : msg.response_timestamp,
                veyra_results: msg.veyra_results || null,
                message_id: msg.message_id,
                veyra_original_query_params: msg.veyra_original_query_params,
                veyra_current_offset: msg.veyra_current_offset,
                veyra_limit_per_page: msg.veyra_limit_per_page,
                veyra_total_emails_available: msg.veyra_total_emails_available,
                veyra_has_more: msg.veyra_has_more
              };
            } else {
              return [
                {
                  role: 'user',
                  content: msg.query || '',
                  timestamp: msg.query_timestamp
                },
                {
                  role: 'assistant',
                  content: msg.response || '',
                  timestamp: msg.response_timestamp,
                  veyra_results: msg.veyra_results || null,
                  message_id: msg.message_id,
                  veyra_original_query_params: msg.veyra_original_query_params,
                  veyra_current_offset: msg.veyra_current_offset,
                  veyra_limit_per_page: msg.veyra_limit_per_page,
                  veyra_total_emails_available: msg.veyra_total_emails_available,
                  veyra_has_more: msg.veyra_has_more
                }
              ];
            }
          })
          .filter(Boolean)
          .flat();

        // Sort messages by timestamp in ascending order (oldest first)
        const sortedMessages = formattedMessages.sort((a, b) => 
          (a.timestamp || 0) - (b.timestamp || 0)
        );
        
        setMessages(sortedMessages);
      } else {
        console.warn('Invalid thread data format:', data);
        setMessages([]);
      }
      
      if (isMobile) setDrawerOpen(false);
    } catch (error) {
      console.error('Error loading thread:', error);
      setMessages([]);
    } finally {
      setIsLoading(false);
    }
  };

  // Send a message to the Co-Pilot
  const sendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage = { role: 'user', content: input };
    setMessages([...messages, userMessage]);
    setInput('');
    setIsLoading(true);

    // Build payload including pending confirmation context if present
    const payload = { query: input };
    if (threadId) payload.thread_id = threadId;
    if (pendingConfirmation) {
      payload.confirm_veyrax = true;
      payload.veyrax_context = pendingConfirmation.context;
      payload.confirmation_context = pendingConfirmation.context;
    }

    try {
      const response = await fetch('http://localhost:5001/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      const data = await response.json();
      
      console.log("Response data:", data);  // Debug log
      
      // Always show confirmation buttons when requires_confirmation is true
      if (data.requires_confirmation) {
        console.log("Confirmation required:", data.confirmation_context);
        // Use the confirmation_context if available, otherwise fall back to veyrax_context
        const context = data.confirmation_context || data.veyrax_context;
        // For delete actions we need user to type a number, not buttons
        const noButtons = !!context.email_ids;  // hide buttons for selection flows only
        setPendingConfirmation({
          context: context,
          threadId: data.thread_id,
          noButtons: noButtons
        });
      } else if (data.veyrax_context) {
        // For other VeyraX contexts without confirmation required
        setPendingConfirmation({
          context: data.veyrax_context,
          threadId: data.thread_id,
          noButtons: true // No buttons, just context pass-through
        });
      }
      
      // If a new thread was created, update the URL
      if (data.thread_id && (!threadId || data.thread_id !== threadId)) {
        navigate(`/${data.thread_id}`);
      }
      
      // Update to include veyra_results in the message state
      // AND the pagination data if available
      const assistantMessageData = { 
        role: 'assistant', 
        content: data.response,
        veyra_results: data.veyra_results, 
        message_id: data.message_id 
      };

      // Add pagination fields from the top level of the response to the message object
      // so VeyraResults can access them.
      if (data.veyra_original_query_params !== undefined) {
        assistantMessageData.veyra_original_query_params = data.veyra_original_query_params;
      }
      if (data.veyra_current_offset !== undefined) {
        assistantMessageData.veyra_current_offset = data.veyra_current_offset;
      }
      if (data.veyra_limit_per_page !== undefined) {
        assistantMessageData.veyra_limit_per_page = data.veyra_limit_per_page;
      }
      if (data.veyra_total_emails_available !== undefined) {
        assistantMessageData.veyra_total_emails_available = data.veyra_total_emails_available;
      }
      if (data.veyra_has_more !== undefined) {
        assistantMessageData.veyra_has_more = data.veyra_has_more;
      }

      console.log("[App.js handleSubmit] Assistant message data prepared:", assistantMessageData);

      setMessages(prevMessages => [...prevMessages, assistantMessageData]);
      fetchThreads();
    } catch (error) {
      setMessages((prev) => [...prev, { role: 'assistant', content: `Error: ${error.message}` }]);
    } finally {
      setIsLoading(false);
    }
  };

  // Handle VeyraX confirmation
  const handleConfirmation = async (confirmed) => {
    if (!pendingConfirmation) return;
    
    console.log("Handling confirmation:", confirmed);
    console.log("Pending confirmation context:", pendingConfirmation);
    
    setIsLoading(true);
    
    if (confirmed) {
      // User confirmed, proceed with VeyraX data fetch
      try {
        const payload = {
          query: "Yes, please proceed with that.",
          thread_id: pendingConfirmation.threadId,
          confirm_veyrax: true,
          veyrax_context: pendingConfirmation.context,
          confirmation_context: pendingConfirmation.context
        };
        
        console.log("Sending confirmation request with payload:", payload);
        
        const response = await fetch('http://localhost:5001/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const data = await response.json();
        console.log("Received confirmation response:", data);
        
        setMessages((prev) => [
          ...prev,
          { role: 'user', content: "Yes, please proceed with that." },
          { role: 'assistant', content: data.response }
        ]);
        
        // If thread ID changed, update URL
        if (data.thread_id && data.thread_id !== threadId) {
          navigate(`/${data.thread_id}`);
        }
      } catch (error) {
        console.error("Error during confirmation:", error);
        setMessages((prev) => [...prev, { role: 'assistant', content: `Error: ${error.message}` }]);
      }
    } else {
      // User declined
      setMessages((prev) => [
        ...prev,
        { role: 'user', content: "No, don't proceed with that." },
        { role: 'assistant', content: "I understand, I won't access that information." }
      ]);
    }
    
    // Reset confirmation state
    setPendingConfirmation(null);
    setIsLoading(false);
    fetchThreads();
  };

  // Save user message as insight
  const saveInsight = async (content) => {
    try {
      const response = await fetch('http://localhost:5001/save_insight', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content }),
      });
      if (!response.ok) throw new Error('Failed to save insight');
      setSnackbarOpen(true);
    } catch (error) {
      showSnackbar(`Error saving insight: ${error.message}`, 'error');
    }
  };

  // Start a new thread
  const startNewThread = () => {
    setMessages([]);
    navigate('/');
    setPendingConfirmation(null);
    if (isMobile) setDrawerOpen(false);
  };

  // Function to add a new assistant message to the state
  const handleNewAssistantMessage = (newMessageData) => {
    // Ensure the message has the minimum required fields
    const formattedMessage = {
      role: 'assistant',
      content: newMessageData.response || "Summary received.", // Use response field from backend
      message_id: newMessageData.message_id || `temp-${Date.now()}`, // Use message_id from backend
      timestamp: Date.now() / 1000, // Approximate timestamp
      veyra_results: newMessageData.veyra_results || null // Include if backend sends it
    };
    console.log("[App.js] Adding new assistant message:", formattedMessage);
    setMessages(prevMessages => [...prevMessages, formattedMessage]);
  };

  // Render message content with proper formatting
  const renderMessage = (message, onNewMessage) => {
    console.log('renderMessage called with full message:', message );
    console.log('renderMessage - veyra_results:', message.veyra_results);
    console.log('renderMessage - veyra_current_offset:', message.veyra_current_offset);
    console.log('renderMessage - condition check:', (message.veyra_results || message.veyra_current_offset !== undefined));
    
    return (
      <Box sx={{ mb: 0 }}>
        <Typography variant="body1" component="div" sx={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
          {message.content}
        </Typography>
        {(message.veyra_results || message.veyra_current_offset !== undefined) && ( // Check if there's Veyra data or pagination info
          <Box sx={{ mt: 1, bgcolor: 'transparent', borderRadius: 1 }}>
            <VeyraResults 
              results={message} // Pass the whole message object as results
              currentThreadId={threadId} // threadId is available in App.js scope
              message_id={message.message_id} // assistant's message_id
              onNewMessageReceived={onNewMessage}
              showSnackbar={showSnackbar}
            />
          </Box>
        )}
      </Box>
    );
  };

  const handleRenameThread = async (threadId, newTitle) => {
    if (!newTitle.trim()) return;
    
    try {
      const response = await fetch(`http://localhost:5001/threads/${threadId}/rename`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: newTitle }),
      });
      
      if (!response.ok) throw new Error('Failed to rename thread');
      
      // Update threads locally
      setThreads(threads.map(thread => 
        thread.thread_id === threadId ? { ...thread, title: newTitle } : thread
      ));
      
      // Exit edit mode
      setEditingThreadId(null);
    } catch (error) {
      console.error('Error renaming thread:', error);
      showSnackbar(`Error renaming thread: ${error.message}`, 'error');
    }
  };

  const handleDeleteThread = async (threadId) => {
    try {
      const response = await fetch(`http://localhost:5001/threads/${threadId}/delete`, {
        method: 'DELETE',
      });
      
      if (!response.ok) {
        throw new Error('Failed to delete thread');
      }
      
      // If we're currently viewing the deleted thread, navigate to home
      if (threadId === threadId) {
        navigate('/');
      }
      
      // Refresh the thread list
      fetchThreads();
      
      // Show success message
      setSnackbarOpen(true);
    } catch (error) {
      console.error('Error deleting thread:', error);
      // Show error message
      setSnackbarOpen(true);
    } finally {
      setDeleteDialogOpen(false);
      setThreadToDelete(null);
    }
  };

  const DeleteConfirmationDialog = () => (
    <Dialog
      open={deleteDialogOpen}
      onClose={() => setDeleteDialogOpen(false)}
    >
      <DialogTitle>Delete Thread</DialogTitle>
      <DialogContent>
        <DialogContentText>
          Are you sure you want to delete this thread and all its conversations? This action cannot be undone.
        </DialogContentText>
      </DialogContent>
      <DialogActions>
        <Button onClick={() => setDeleteDialogOpen(false)}>Cancel</Button>
        <Button 
          onClick={() => handleDeleteThread(threadToDelete)} 
          color="error"
          autoFocus
        >
          Delete
        </Button>
      </DialogActions>
    </Dialog>
  );

  const currentThreadTitle = threads.find(t => t.thread_id === threadId)?.title || "Playground";

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ display: 'flex', height: '100vh', backgroundColor: theme.palette.background.default }}>
        {/* Sidebar */}
        <Drawer
          variant={isMobile ? 'temporary' : 'persistent'}
          open={drawerOpen}
          onClose={() => setDrawerOpen(false)}
          sx={{
            // Conditionally set display to none to remove from layout when closed on desktop
            display: (isMobile || drawerOpen) ? 'flex' : 'none', 
            width: drawerWidth, // This width applies when display is not 'none'
            flexShrink: 0,
            '& .MuiDrawer-paper': { 
              width: drawerWidth, 
              boxSizing: 'border-box',
              backgroundColor: '#f8f9fa',
              borderRight: '1px solid #dee2e6'
            },
          }}
        >
          <Box sx={{ p: 2, display: 'flex', flexDirection: 'column', height: '100%' }}>
            <Button 
              onClick={startNewThread} 
              variant="outlined" 
              fullWidth 
              sx={{ 
                mb: 2, 
                borderColor: theme.palette.primary.main, 
                color: theme.palette.primary.main,
                '&:hover': {
                  backgroundColor: theme.palette.action.hover,
                  borderColor: theme.palette.primary.dark,
                }
              }}
            >
              New Thread
            </Button>
            <List sx={{ overflowY: 'auto', flexGrow: 1 }}>
              {threads.map((thread) => (
                <ListItem 
                  button 
                  key={thread.thread_id}
                  onClick={() => navigate(`/${thread.thread_id}`)}
                  selected={threadId === thread.thread_id}
                  sx={{
                    borderRadius: '4px',
                    marginBottom: '4px',
                    '&.Mui-selected': {
                      backgroundColor: theme.palette.action.selected,
                      '&:hover': {
                        backgroundColor: theme.palette.action.selected,
                      }
                    },
                    '&:hover': {
                      backgroundColor: theme.palette.action.hover,
                    },
                    maxHeight: '48px', // Keep this for consistency
                    '& .MuiListItemText-primary': {
                      fontSize: '0.875rem',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                      maxWidth: '200px'
                    }
                  }}
                >
                  {editingThreadId === thread.thread_id ? (
                    // Edit mode
                    <Box sx={{ display: 'flex', alignItems: 'center', width: '100%' }}>
                      <TextField
                        autoFocus
                        value={editTitle}
                        onChange={(e) => setEditTitle(e.target.value)}
                        size="small"
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') {
                            handleRenameThread(thread.thread_id, editTitle);
                          } else if (e.key === 'Escape') {
                            setEditingThreadId(null);
                          }
                        }}
                        sx={{ width: '85%' }}
                        onClick={(e) => e.stopPropagation()}
                      />
                      <IconButton 
                        onClick={(e) => {
                          e.stopPropagation();
                          handleRenameThread(thread.thread_id, editTitle);
                        }}
                        size="small"
                      >
                        <CheckIcon fontSize="small" />
                      </IconButton>
                    </Box>
                  ) : (
                    // Display mode
                    <>
                      <ListItemText 
                        primary={thread.title.length > 60 ? `${thread.title.substring(0, 60)}...` : thread.title} 
                      />
                      <Box sx={{ display: 'flex', gap: 1 }}>
                        <IconButton 
                          size="small"
                          onClick={(e) => {
                            e.stopPropagation();
                            setEditingThreadId(thread.thread_id);
                            setEditTitle(thread.title);
                          }}
                        >
                          <EditIcon fontSize="small" />
                        </IconButton>
                        <IconButton
                          size="small"
                          onClick={(e) => {
                            e.stopPropagation();
                            setThreadToDelete(thread.thread_id);
                            setDeleteDialogOpen(true);
                          }}
                        >
                          <DeleteIcon fontSize="small" />
                        </IconButton>
                      </Box>
                    </>
                  )}
                </ListItem>
              ))}
            </List>
          </Box>
        </Drawer>

        {/* Main content */}
        <Box 
          component="main"
          sx={{ 
            flexGrow: 1, // This will now correctly expand to fill available space
            display: 'flex', 
            flexDirection: 'column', 
            height: '100vh',
            overflow: 'hidden', // For internal content scroll, not page scroll
            transition: theme.transitions.create(['margin-left'], { // Transition only margin-left
               easing: theme.transitions.easing.sharp,
               duration: drawerOpen ? theme.transitions.duration.enteringScreen : theme.transitions.duration.leavingScreen,
            }),
            // marginLeft removed to allow main content to always fill available space
          }}
        >
          {/* Header for Toggle and Title */}
          <Box sx={{ p: 2, display: 'flex', alignItems: 'center', borderBottom: `1px solid ${theme.palette.divider}` }}>
            <IconButton 
              onClick={() => setDrawerOpen(!drawerOpen)} 
              sx={{ mr: 1 }}
              // Use MenuOpenIcon or a custom SVG for the specific toggle icon if available
            >
              <MenuIcon /> 
            </IconButton>
            <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
              {currentThreadTitle}
            </Typography>
             {/* Placeholder for other header items like Upgrade button if they move here */}
          </Box>

          {/* Messages area */}
          <Box sx={{ flexGrow: 1, overflowY: 'auto', p: 2, display: 'flex', flexDirection: 'column' }}>
            {messages.map((message, index) => (
              <Box
                key={index}
                sx={{
                  display: 'flex',
                  justifyContent: message.role === 'user' ? 'flex-end' : 'flex-start',
                  mb: 1.5, // Adjusted margin between bubbles
                  maxWidth: '100%', // Ensure bubbles don't overflow container
                }}
              >
                <Paper
                  elevation={1} // Subtle shadow
                  sx={{
                    p: '10px 15px', // Padding inside bubbles
                    maxWidth: 'calc(80% - 16px)', // Max width of bubbles, account for padding/margin
                    borderRadius: '20px', // Rounded corners
                    bgcolor: message.role === 'user' ? theme.palette.background.userMessage : theme.palette.background.assistantMessage,
                    color: message.role === 'user' ? theme.palette.text.userMessage : theme.palette.text.primary,
                    wordBreak: 'break-word', // Ensure long words break
                  }}
                  {...(message.role === 'assistant' && message.message_id && { 'data-message-id': message.message_id })}
                >
                  {renderMessage(
                    message, 
                    handleNewAssistantMessage
                  )}
                </Paper>
              </Box>
            ))}
            {isLoading && (
              <Box sx={{ display: 'flex', justifyContent: 'flex-start', mb: 2, pl:1 /* Align with assistant messages */ }}>
                <Paper 
                  elevation={1}
                  sx={{ 
                    p: '10px 15px', 
                    maxWidth: '80%', 
                    borderRadius: '20px',
                    bgcolor: theme.palette.background.assistantMessage,
                  }}
                >
                  <Typography>Thinking...</Typography>
                </Paper>
              </Box>
            )}
          </Box>

          {/* Input area */}
          <Box 
            sx={{ 
              p: '12px 16px', // Padding around the entire input container
              mt: 'auto', // Pushes to the bottom
              backgroundColor: theme.palette.background.inputArea,
              // borderRadius: '28px 28px 0 0', // Rounded top corners if desired
              boxShadow: '0 -2px 10px rgba(0,0,0,0.05)', // Shadow for separation
            }}
          >
            <Box 
              sx={{
                display: 'flex',
                alignItems: 'center',
                backgroundColor: theme.palette.background.paper, // White background for the input row itself
                borderRadius: '24px', // Rounded corners for the input row
                p: '4px 8px', // Padding inside the white row
                boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
              }}
            >
              <IconButton sx={{ p: '8px' }} size="small" color="secondary">
                <AttachFileIcon />
              </IconButton>
              <form onSubmit={sendMessage} style={{ flexGrow: 1, display: 'flex' }}>
                <TextField
                  fullWidth
                  variant="standard" // Use standard variant for cleaner look
                  placeholder="Ask about anything..."
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  disabled={isLoading}
                  multiline
                  maxRows={5}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey && !isLoading && input.trim()) {
                      e.preventDefault();
                      sendMessage(e);
                    }
                  }}
                  InputProps={{
                    disableUnderline: true,
                    sx: { 
                      p: '8px 12px', 
                      fontSize: '0.95rem',
                      lineHeight: '1.4',
                      maxHeight: '120px', // Limit height for multiline
                      overflowY: 'auto',
                    }
                  }}
                  sx={{ flexGrow: 1 }}
                />
                <IconButton 
                  type="submit" 
                  disabled={isLoading || !input.trim()} 
                  sx={{ p: '8px' }} 
                  size="small"
                  color="primary"
                >
                  <SendIcon />
                </IconButton>
              </form>
            </Box>
            <Box 
              sx={{ 
                display: 'flex', 
                justifyContent: 'center', // Center items or space-between
                alignItems: 'center', 
                pt: '10px', 
                pb: '2px',
                // borderTop: `1px solid ${theme.palette.divider}`, // Optional separator line
                // mt: '8px'
              }}
            >
              <Box sx={{ display: 'flex', alignItems: 'center', cursor: 'pointer', mr: 2 }}>
                {/* Basic SVG Placeholder for OpenAI logo - replace with actual SVG or Icon */}
                <svg width="18" height="18" viewBox="0 0 32 32" fill="currentColor" xmlns="http://www.w3.org/2000/svg" style={{ color: theme.palette.text.secondary }}>
                  <path fillRule="evenodd" clipRule="evenodd" d="M16 0C24.8366 0 32 7.16344 32 16C32 24.8366 24.8366 32 16 32C7.16344 32 0 24.8366 0 16C0 7.16344 7.16344 0 16 0ZM5.34879 19.9149C5.00347 20.2997 5.29828 20.9141 5.82033 20.9141H10.9163C11.3028 20.9141 11.6137 20.6442 11.6609 20.2656L12.6697 12.5H19.3303L20.3391 20.2656C20.3863 20.6442 20.6972 20.9141 21.0837 20.9141H26.1797C26.7017 20.9141 26.9965 20.2997 26.6512 19.9149L23.0984 15.9172L26.6512 11.9194C26.9965 11.5347 26.7017 10.9141 26.1797 10.9141H21.0837C20.6972 10.9141 20.3863 11.184 20.3391 11.5625L19.3303 19.3281H12.6697L11.6609 11.5625C11.6137 11.184 11.3028 10.9141 10.9163 10.9141H5.82033C5.29828 10.9141 5.00347 11.5347 5.34879 11.9194L8.90159 15.9172L5.34879 19.9149Z" />
                </svg>
                <Typography variant="body2" sx={{ ml: 0.8, color: theme.palette.text.secondary, fontWeight: 500 }}>
                  GPT-4.1 Mini
                </Typography>
                {/* <KeyboardArrowDownIcon sx={{ color: theme.palette.text.secondary, fontSize: '1.2rem' }} /> */}
              </Box>
              <IconButton size="small" sx={{ color: theme.palette.text.secondary }}>
                <MicIcon />
              </IconButton>
            </Box>
          </Box>
        </Box>

        <DeleteConfirmationDialog />
        <Snackbar
          open={snackbarOpen}
          autoHideDuration={3000}
          onClose={() => setSnackbarOpen(false)}
          message={threadToDelete ? "Thread deleted successfully" : "Error deleting thread"}
        />
      </Box>
    </ThemeProvider>
  );
}

export default App;