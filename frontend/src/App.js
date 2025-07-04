import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { createPortal } from 'react-dom';
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
  Snackbar,
  Divider,
  Menu,
  MenuItem,
  ListItemIcon,
  Popover,
} from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import EditIcon from '@mui/icons-material/Edit';
import CheckIcon from '@mui/icons-material/Check';
import DeleteIcon from '@mui/icons-material/Delete';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogContentText from '@mui/material/DialogContentText';
import DialogTitle from '@mui/material/DialogTitle';
import ToolResults from './components/ToolResults';
import EmailSidebar from './components/EmailSidebar';
import './App.css';
import { useSnackbar } from './components/SnackbarProvider';
import { DraftService, formatDraftDisplayText, getMissingFieldsText } from './utils/draftService';

// Import new icons
import SendIcon from '@mui/icons-material/Send';
import AttachFileIcon from '@mui/icons-material/AttachFile';
import MicIcon from '@mui/icons-material/Mic';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import RepeatIcon from '@mui/icons-material/Repeat';
import AddIcon from '@mui/icons-material/Add';
import AccountCircleIcon from '@mui/icons-material/AccountCircle';
import SettingsIcon from '@mui/icons-material/Settings';
import ChevronLeftIcon from '@mui/icons-material/ChevronLeft';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import CameraAltIcon from '@mui/icons-material/CameraAlt';
import ImageIcon from '@mui/icons-material/Image';
import CodeIcon from '@mui/icons-material/Code';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import LightbulbIcon from '@mui/icons-material/Lightbulb';
import MoreHorizIcon from '@mui/icons-material/MoreHoriz';
import AnchorIcon from '@mui/icons-material/Anchor';
import CloseIcon from '@mui/icons-material/Close';
import CreateIcon from '@mui/icons-material/Create';
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
const drawerWidthCollapsed = 60; // Width when collapsed
// Email sidebar will be 60% of main content width, calculated dynamically

// Custom ChatGPT Sidebar Toggle Icon
const ChatGPTSidebarIcon = ({ collapsed }) => (
  <svg 
    width="20" 
    height="20" 
    viewBox="0 0 20 20" 
    fill="currentColor" 
    xmlns="http://www.w3.org/2000/svg"
    style={{ 
      transform: collapsed ? 'scaleX(1)' : 'scaleX(-1)',
      transition: 'transform 0.2s ease-in-out'
    }}
  >
    <path d="M6.83496 3.99992C6.38353 4.00411 6.01421 4.0122 5.69824 4.03801C5.31232 4.06954 5.03904 4.12266 4.82227 4.20012L4.62207 4.28606C4.18264 4.50996 3.81498 4.85035 3.55859 5.26848L3.45605 5.45207C3.33013 5.69922 3.25006 6.01354 3.20801 6.52824C3.16533 7.05065 3.16504 7.71885 3.16504 8.66301V11.3271C3.16504 12.2712 3.16533 12.9394 3.20801 13.4618C3.25006 13.9766 3.33013 14.2909 3.45605 14.538L3.55859 14.7216C3.81498 15.1397 4.18266 15.4801 4.62207 15.704L4.82227 15.79C5.03904 15.8674 5.31234 15.9205 5.69824 15.9521C6.01398 15.9779 6.383 15.986 6.83398 15.9902L6.83496 3.99992ZM18.165 11.3271C18.165 12.2493 18.1653 12.9811 18.1172 13.5702C18.0745 14.0924 17.9916 14.5472 17.8125 14.9648L17.7295 15.1415C17.394 15.8 16.8834 16.3511 16.2568 16.7353L15.9814 16.8896C15.5157 17.1268 15.0069 17.2285 14.4102 17.2773C13.821 17.3254 13.0893 17.3251 12.167 17.3251H7.83301C6.91071 17.3251 6.17898 17.3254 5.58984 17.2773C5.06757 17.2346 4.61294 17.1508 4.19531 16.9716L4.01855 16.8896C3.36014 16.5541 2.80898 16.0434 2.4248 15.4169L2.27051 15.1415C2.03328 14.6758 1.93158 14.167 1.88281 13.5702C1.83468 12.9811 1.83496 12.2493 1.83496 11.3271V8.66301C1.83496 7.74072 1.83468 7.00898 1.88281 6.41985C1.93157 5.82309 2.03329 5.31432 2.27051 4.84856L2.4248 4.57317C2.80898 3.94666 3.36012 3.436 4.01855 3.10051L4.19531 3.0175C4.61285 2.83843 5.06771 2.75548 5.58984 2.71281C6.17898 2.66468 6.91071 2.66496 7.83301 2.66496H12.167C13.0893 2.66496 13.821 2.66468 14.4102 2.71281C15.0069 2.76157 15.5157 2.86329 15.9814 3.10051L16.2568 3.25481C16.8833 3.63898 17.394 4.19012 17.7295 4.84856L17.8125 5.02531C17.9916 5.44285 18.0745 5.89771 18.1172 6.41985C18.1653 7.00898 18.165 7.74072 18.165 8.66301V11.3271ZM8.16406 15.995H12.167C13.1112 15.995 13.7794 15.9947 14.3018 15.9521C14.8164 15.91 15.1308 15.8299 15.3779 15.704L15.5615 15.6015C15.9797 15.3451 16.32 14.9774 16.5439 14.538L16.6299 14.3378C16.7074 14.121 16.7605 13.8478 16.792 13.4618C16.8347 12.9394 16.835 12.2712 16.835 11.3271V8.66301C16.835 7.71885 16.8347 7.05065 16.792 6.52824C16.7605 6.14232 16.7073 5.86904 16.6299 5.65227L16.5439 5.45207C16.32 5.01264 15.9796 4.64498 15.5615 4.3886L15.3779 4.28606C15.1308 4.16013 14.8165 4.08006 14.3018 4.03801C13.7794 3.99533 13.1112 3.99504 12.167 3.99504H8.16406C8.16407 3.99667 8.16504 3.99829 8.16504 3.99992L8.16406 15.995Z"></path>
  </svg>
);

// Reusable Chat Input Component
const ChatInput = ({ 
  input, 
  setInput, 
  isLoading, 
  onSubmit, 
  placeholder = "Ask about anything...",
  showSuggestions = false,
  onSuggestionClick,
  theme,
  isWelcome = false,
  onAttachmentClick
}) => {
  return (
    <Box 
      sx={{ 
        p: '12px 16px',
        mt: 'auto',
        backgroundColor: 'transparent', // Remove grey background for all screens
        boxShadow: 'none', // Remove shadow for all screens
      }}
    >
      {/* Input area */}
      <Box 
        sx={{
          display: 'flex',
          alignItems: 'center',
          backgroundColor: theme.palette.background.paper,
          borderRadius: '24px',
          p: '4px 8px',
          boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
          border: '1px solid',
          borderColor: 'rgba(0,0,0,0.2)',
          maxWidth: isWelcome ? '800px' : 'none',
          mx: isWelcome ? 'auto' : 'inherit',
          '&:hover': {
            borderColor: 'rgba(0,0,0,0.3)',
          },
          '&:focus-within': {
            borderColor: theme.palette.primary.main,
            boxShadow: `0 0 0 2px ${theme.palette.primary.main}25`,
          }
        }}
      >
        <IconButton 
          onClick={onAttachmentClick}
          sx={{ p: '8px' }} 
          size="small" 
          color="secondary"
        >
          <AttachFileIcon />
        </IconButton>
        <form onSubmit={onSubmit} style={{ flexGrow: 1, display: 'flex' }}>
          <TextField
            fullWidth
            variant="standard"
            placeholder={placeholder}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isLoading}
            multiline
            maxRows={5}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey && !isLoading && input.trim()) {
                e.preventDefault();
                onSubmit(e);
              }
            }}
            InputProps={{
              disableUnderline: true,
              sx: { 
                p: '8px 12px', 
                fontSize: '0.95rem',
                lineHeight: '1.4',
                maxHeight: '120px',
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
    </Box>
  );
};

function App() {
  const { threadId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  
  const [threads, setThreads] = useState([]);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  
  // Initialize isMobile and drawerOpen based on initial window width
  const initialIsMobile = window.innerWidth < 768; // Using 768 as the breakpoint
  const [isMobile, setIsMobile] = useState(initialIsMobile);
  const [drawerOpen, setDrawerOpen] = useState(!initialIsMobile); // Open on desktop, closed on mobile by default
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false); // New state for collapsed sidebar
  
  const [pendingConfirmation, setPendingConfirmation] = useState(null);
  const [editingThreadId, setEditingThreadId] = useState(null);
  const [editTitle, setEditTitle] = useState('');
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [threadToDelete, setThreadToDelete] = useState(null);
  const [menuAnchorEl, setMenuAnchorEl] = useState(null);
  const [selectedThreadId, setSelectedThreadId] = useState(null);
  const [hoveredThreadId, setHoveredThreadId] = useState(null);

  // Email sidebar state
  const [emailSidebar, setEmailSidebar] = useState({
    open: false,
    email: null,
    loading: false,
    error: null
  });

  // Anchor state - thread-level
  const [anchoredItem, setAnchoredItem] = useState(null);

  // Draft state
  const [draftValidation, setDraftValidation] = useState(null);
  const [isSendingDraft, setIsSendingDraft] = useState(false);

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
    // Clear anchor when switching threads
    setAnchoredItem(null);
  }, [threadId]);

  // Handle clicking outside menu to close it
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (menuAnchorEl && !event.target.closest('[data-menu-container]')) {
        handleThreadMenuClose();
      }
    };

    if (menuAnchorEl) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [menuAnchorEl]);

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
          id: msg.id || msg.message_id,
          role: msg.role,
          content: msg.content,
          tool_results: msg.tool_results || null,
          insight_id: msg.insight_id,
          tool_original_query_params: msg.tool_original_query_params,
          tool_current_offset: msg.tool_current_offset,
          tool_limit_per_page: msg.tool_limit_per_page,
          tool_total_emails_available: msg.tool_total_emails_available,
          tool_has_more: msg.tool_has_more
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
                id: msg.id || msg.message_id,
                role: msg.role,
                content: msg.content || '',
                tool_results: msg.tool_results || null,
                insight_id: msg.insight_id,
                tool_original_query_params: msg.tool_original_query_params,
                tool_current_offset: msg.tool_current_offset,
                tool_limit_per_page: msg.tool_limit_per_page,
                tool_total_emails_available: msg.tool_total_emails_available,
                tool_has_more: msg.tool_has_more
              };
            } else {
              return [
                {
                  id: msg.query_timestamp,
                  role: 'user',
                  content: msg.query || '',
                  tool_results: null,
                  insight_id: null,
                  tool_original_query_params: null,
                  tool_current_offset: null,
                  tool_limit_per_page: null,
                  tool_total_emails_available: null,
                  tool_has_more: null
                },
                {
                  id: msg.response_timestamp,
                  role: 'assistant',
                  content: msg.response || '',
                  tool_results: msg.tool_results || null,
                  insight_id: msg.insight_id,
                  tool_original_query_params: msg.tool_original_query_params,
                  tool_current_offset: msg.tool_current_offset,
                  tool_limit_per_page: msg.tool_limit_per_page,
                  tool_total_emails_available: msg.tool_total_emails_available,
                  tool_has_more: msg.tool_has_more
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
    const userMessageId = `user-${Date.now()}`;
    const userMessageWithId = { ...userMessage, id: userMessageId };
    setMessages([...messages, userMessageWithId]);
    setInput('');
    setIsLoading(true);

    // Build payload including pending confirmation context and anchored item if present
    const payload = { query: input };
    if (threadId) payload.thread_id = threadId;
    if (anchoredItem) payload.anchored_item = anchoredItem;
    if (pendingConfirmation) {
      payload.confirm_tooling = true;
      payload.tool_context = pendingConfirmation.context;
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
        // Use the confirmation_context if available, otherwise fall back to tool_context
        const context = data.confirmation_context || data.tool_context;
        // For delete actions we need user to type a number, not buttons
        const noButtons = !!context.email_ids;  // hide buttons for selection flows only
        setPendingConfirmation({
          message: data.confirmation_prompt,
          context: context,
          noButtons: noButtons
        });
      } else if (data.tool_context) {
        // For other Tooling contexts without confirmation required
        setPendingConfirmation({
          message: data.confirmation_prompt,
          context: data.tool_context,
          noButtons: true // No buttons, just context pass-through
        });
      }
      
      // If a new thread was created, update the URL
      if (data.thread_id && (!threadId || data.thread_id !== threadId)) {
        navigate(`/${data.thread_id}`);
      }
      
      // Update to include tool_results in the message state
      // AND the pagination data if available
      const assistantMessageData = { 
        id: data.message_id,
        role: 'assistant', 
        content: data.response,
        tool_results: data.tool_results, 
        insight_id: data.insight_id
      };

      // Add pagination fields from the top level of the response to the message object
      // so ToolResults can access them.
      if (data.tool_original_query_params !== undefined) {
        assistantMessageData.tool_original_query_params = data.tool_original_query_params;
      }
      if (data.tool_current_offset !== undefined) {
        assistantMessageData.tool_current_offset = data.tool_current_offset;
      }
      if (data.tool_limit_per_page !== undefined) {
        assistantMessageData.tool_limit_per_page = data.tool_limit_per_page;
      }
      if (data.tool_total_emails_available !== undefined) {
        assistantMessageData.tool_total_emails_available = data.tool_total_emails_available;
      }
      if (data.tool_has_more !== undefined) {
        assistantMessageData.tool_has_more = data.tool_has_more;
      }

      console.log("[App.js handleSubmit] Assistant message data prepared:", assistantMessageData);

      setMessages(prevMessages => [...prevMessages, assistantMessageData]);
      fetchThreads();
      
      // Auto-refresh draft display if there's an anchored draft
      if (anchoredItem && anchoredItem.type === 'draft') {
        console.log('[DEBUG] Auto-refreshing draft display after message');
        setTimeout(() => {
          fetchDraftValidation(anchoredItem.data.draft_id);
        }, 500); // Small delay to ensure backend processing is complete
      }
      
      // Check if a draft was created and auto-anchor it
      if (data.draft_created) {
        console.log('[App.js] Draft created detected:', data.draft_created);
        
        // Immediately check for and anchor the draft
        setTimeout(() => {
          checkForDraftInMessage(data.draft_created.user_message_id);
        }, 100); // Small delay to ensure database update
      } else {
        // Fallback: Check if a draft was created for the user message
        setTimeout(() => {
          checkForDraftInMessage(userMessageId);
        }, 500); // Longer delay for fallback detection
      }
      
    } catch (error) {
      setMessages((prev) => [...prev, { role: 'assistant', content: `Error: ${error.message}` }]);
    } finally {
      setIsLoading(false);
    }
  };

  // Handle Tooling confirmation
  const handleConfirmation = async (confirmed) => {
    if (!pendingConfirmation) return;
    
    console.log("Handling confirmation:", confirmed);
    console.log("Pending confirmation context:", pendingConfirmation);
    
    setIsLoading(true);
    
    if (confirmed) {
      // User confirmed, proceed with Tooling data fetch
      try {
        const payload = {
          query: pendingConfirmation.message,
          thread_id: threadId,
          confirm_tooling: true,
          tool_context: pendingConfirmation.context,
        };
        if (anchoredItem) payload.anchored_item = anchoredItem;
        
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
          { role: 'user', content: pendingConfirmation.message },
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

  // Toggle sidebar collapsed state
  const toggleSidebarCollapse = () => {
    setSidebarCollapsed(!sidebarCollapsed);
  };

  // Handle menu actions
  const handleNewChat = () => {
    startNewThread();
  };

  const handleMyAccount = () => {
    // Placeholder for account functionality
    showSnackbar('My Account clicked', 'info');
  };

  const handleSettings = () => {
    // Placeholder for settings functionality
    showSnackbar('Settings clicked', 'info');
  };

  // Handle suggestion clicks
  const handleSuggestionClick = (suggestionText) => {
    setInput(suggestionText);
    // Auto-focus the input field
    setTimeout(() => {
      const inputElement = document.querySelector('input[placeholder="Ask about anything..."]');
      if (inputElement) {
        inputElement.focus();
      }
    }, 100);
  };

  // Handle attachment click
  const handleAttachmentClick = () => {
    showSnackbar('File attachment feature is in development', 'info');
  };

  // Handle thread menu
  const handleThreadMenuOpen = (event, threadId) => {
    event.stopPropagation();
    const buttonRect = event.currentTarget.getBoundingClientRect();
    setMenuAnchorEl({
      top: buttonRect.bottom,
      left: buttonRect.left,
      element: event.currentTarget
    });
    setSelectedThreadId(threadId);
  };

  const handleThreadMenuClose = () => {
    setMenuAnchorEl(null);
    setSelectedThreadId(null);
  };

  const handleMenuRename = () => {
    const thread = threads.find(t => t.thread_id === selectedThreadId);
    if (thread) {
      setEditingThreadId(selectedThreadId);
      setEditTitle(thread.title);
    }
    handleThreadMenuClose();
  };

  const handleMenuDelete = () => {
    setThreadToDelete(selectedThreadId);
    setDeleteDialogOpen(true);
    handleThreadMenuClose();
  };

  // Function to add a new assistant message to the state
  const handleNewAssistantMessage = (newMessageData) => {
    // Ensure the message has the minimum required fields
    const formattedMessage = {
      id: newMessageData.message_id || `temp-${Date.now()}`,
      role: 'assistant',
      content: newMessageData.response || "Summary received.", // Use response field from backend
      tool_results: newMessageData.tool_results || null,
      insight_id: newMessageData.insight_id,
      tool_original_query_params: newMessageData.tool_original_query_params,
      tool_current_offset: newMessageData.tool_current_offset,
      tool_limit_per_page: newMessageData.tool_limit_per_page,
      tool_total_emails_available: newMessageData.tool_total_emails_available,
      tool_has_more: newMessageData.tool_has_more
    };
    console.log("[App.js] Adding new assistant message:", formattedMessage);
    setMessages(prevMessages => [...prevMessages, formattedMessage]);
  };

  // Render message content with proper formatting
  const handleUpdateMessage = (messageId, updatedResults, paginationData) => {
    setMessages(prevMessages => 
      prevMessages.map(msg => {
        if (msg.id === messageId) {
          const updatedMessage = {
            ...msg,
            tool_results: updatedResults
          };
          
          // Update pagination data if provided
          if (paginationData) {
            updatedMessage.tool_current_offset = paginationData.currentOffset;
            updatedMessage.tool_limit_per_page = paginationData.limitPerPage;
            updatedMessage.tool_total_emails_available = paginationData.totalEmailsAvailable;
            updatedMessage.tool_has_more = paginationData.hasMore;
          }
          
          return updatedMessage;
        }
        return msg;
      })
    );
  };

  const renderMessage = (message, onNewMessage) => {
    console.log('renderMessage called with full message:', message );
    console.log('renderMessage - tool_results:', message.tool_results);
                console.log('renderMessage - tool_current_offset:', message.tool_current_offset);
            console.log('renderMessage - condition check:', (message.tool_results || message.tool_current_offset !== undefined));
            console.log('renderMessage - pagination props to pass:', {
              currentOffset: message.tool_current_offset,
              limitPerPage: message.tool_limit_per_page,
              totalEmailsAvailable: message.tool_total_emails_available,
              hasMore: message.tool_has_more
            });
    
    return (
      <Box sx={{ mb: 0 }}>
        <Typography variant="body1" component="div" sx={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
          {message.content}
        </Typography>
        {(message.tool_results || message.tool_current_offset !== undefined) && ( // Check if there's Tooling data or pagination info
          <Box sx={{ mt: 1, bgcolor: 'transparent', borderRadius: 1 }}>
            <ToolResults 
              results={message.tool_results} // Pass the tool_results object, not the whole message
              threadId={threadId} // threadId is available in App.js scope
              messageId={message.id} // assistant's message_id
              onNewMessageReceived={onNewMessage}
              onUpdate={handleUpdateMessage}
              showSnackbar={showSnackbar}
              onOpenEmail={handleOpenEmail}
              // Pass pagination props
              currentOffset={message.tool_current_offset}
              limitPerPage={message.tool_limit_per_page}
              totalEmailsAvailable={message.tool_total_emails_available}
              hasMore={message.tool_has_more}
              // Pass anchor props
              anchoredItem={anchoredItem}
              onAnchorChange={handleAnchorChange}
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

  // Email sidebar functions
  const handleOpenEmail = async (email) => {
    console.log('Opening email:', email);
    
    // On mobile, close the drawer sidebar to make room for email sidebar
    if (isMobile) {
      setDrawerOpen(false);
    }
    
    // Close any existing sidebar and set loading state
    setEmailSidebar({
      open: true,
      email: null,
      loading: true,
      error: null
    });

    try {
      // Fetch email content if not already present
      const response = await fetch('http://localhost:5001/get_email_content', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email_id: email.email_id || email.id }),
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch email content: ${response.status}`);
      }

      const data = await response.json();
      
      if (data.success) {
        // Merge the fetched content with the existing email data
        const emailWithContent = {
          ...email,
          content: data.content
        };

        setEmailSidebar({
          open: true,
          email: emailWithContent,
          loading: false,
          error: null
        });
      } else {
        throw new Error('Failed to retrieve email content');
      }
    } catch (error) {
      console.error('Error fetching email content:', error);
      setEmailSidebar({
        open: true,
        email: null,
        loading: false,
        error: error.message
      });
    }
  };

  const handleCloseEmailSidebar = () => {
    setEmailSidebar({
      open: false,
      email: null,
      loading: false,
      error: null
    });
  };

  // --- Sync anchor state with URL query params ---
  // Restore anchor from URL on mount/thread change
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const anchorType = params.get('anchorType');
    const anchorId = params.get('anchorId');
    if (anchorType && anchorId) {
      // Only update if not already set
      if (!anchoredItem || anchoredItem.type !== anchorType || anchoredItem.id !== anchorId) {
        if (anchorType === 'draft') {
          // Try to fetch draft and validate
          (async () => {
            try {
              const response = await DraftService.validateDraft(anchorId);
              if (response.success) {
                setAnchoredItem({ id: anchorId, type: 'draft', data: { draft_id: anchorId, ...response.draft } });
                setDraftValidation(response.validation);
              } else {
                setAnchoredItem({ id: anchorId, type: 'draft', data: { draft_id: anchorId } });
              }
            } catch {
              setAnchoredItem({ id: anchorId, type: 'draft', data: { draft_id: anchorId } });
            }
          })();
        } else if (anchorType === 'message') {
          // Look up the draft for this message and anchor it
          (async () => {
            const found = await checkForDraftInMessage(anchorId);
            if (!found) {
              setAnchoredItem(null);
            }
          })();
        } else {
          setAnchoredItem({ id: anchorId, type: anchorType, data: { id: anchorId } });
        }
      }
    } else if (anchoredItem) {
      // If no anchor in URL, clear anchor
      setAnchoredItem(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.search, threadId]);

  // Update URL when anchor changes
  const handleAnchorChange = (anchorData) => {
    setAnchoredItem(anchorData);
    setDraftValidation(null);
    // If anchoring a draft, fetch its validation status
    if (anchorData && anchorData.type === 'draft') {
      fetchDraftValidation(anchorData.id);
    }
    // Update the URL query params
    const params = new URLSearchParams(location.search);
    if (anchorData) {
      params.set('anchorType', anchorData.type);
      params.set('anchorId', anchorData.id);
    } else {
      params.delete('anchorType');
      params.delete('anchorId');
    }
    // Use navigate to update the URL without reloading
    navigate({ pathname: location.pathname, search: params.toString() }, { replace: true });
  };

  // Fetch draft validation status
  const fetchDraftValidation = async (draftId) => {
    try {
      const response = await DraftService.validateDraft(draftId);
      if (response.success) {
        setDraftValidation(response.validation);
      }
    } catch (error) {
      console.error('Error fetching draft validation:', error);
    }
  };

  // Check for draft associated with user message
  const checkForDraftInMessage = async (messageId) => {
    try {
      const response = await DraftService.getDraftByMessage(messageId);
      if (response.success) {
        const draft = response.draft;
        
        // Auto-anchor this draft
        const anchorData = {
          id: draft.draft_id,
          type: 'draft',
          data: draft
        };
        
        setAnchoredItem(anchorData);
        await fetchDraftValidation(draft.draft_id);
        
        console.log('[App.js] Auto-anchored draft:', draft.draft_id);
        return true;
      }
    } catch (error) {
      // Draft not found - this is normal for most messages
      console.log('[App.js] No draft found for message:', messageId);
    }
    return false;
  };

  // Send draft via Composio
  const handleSendDraft = async () => {
    if (!anchoredItem || anchoredItem.type !== 'draft') return;
    
    setIsSendingDraft(true);
    try {
      const response = await DraftService.sendDraft(anchoredItem.id);
      if (response.success) {
        showSnackbar(response.message || 'Draft sent successfully!', 'success');
        
        // Clear the anchored draft
        setAnchoredItem(null);
        setDraftValidation(null);
        
        // Refresh the thread to show any new messages
        if (threadId) {
          loadThread(threadId);
        }
      } else {
        showSnackbar(response.error || 'Failed to send draft', 'error');
      }
    } catch (error) {
      console.error('Error sending draft:', error);
      showSnackbar(`Failed to send draft: ${error.message}`, 'error');
    } finally {
      setIsSendingDraft(false);
    }
  };

  // Copy message content to clipboard
  const copyToClipboard = async (text) => {
    try {
      await navigator.clipboard.writeText(text);
      showSnackbar('Message copied to clipboard', 'success');
    } catch (error) {
      console.error('Failed to copy text:', error);
      showSnackbar('Failed to copy message', 'error');
    }
  };

  // Repeat user message (for testing)
  const repeatMessage = (messageContent) => {
    setInput(messageContent);
    // Auto-focus the input field
    setTimeout(() => {
      const inputElement = document.querySelector('input[placeholder="Ask about anything..."]');
      if (inputElement) {
        inputElement.focus();
      }
    }, 100);
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
            width: sidebarCollapsed ? drawerWidthCollapsed : drawerWidth, // Dynamic width based on collapsed state
            flexShrink: 0,
            '& .MuiDrawer-paper': { 
              width: sidebarCollapsed ? drawerWidthCollapsed : drawerWidth, 
              boxSizing: 'border-box',
              backgroundColor: '#f8f9fa',
              borderRight: '1px solid #dee2e6',
              transition: 'width 0.2s ease-in-out', // Smooth transition
              overflow: 'visible',
            },
          }}
        >
          <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'visible' }}>
            {/* Top section with header and menu items */}
            <Box sx={{ p: 1 }}>
              {/* Header and collapse button */}
              <Box sx={{ 
                display: 'flex', 
                alignItems: 'center', 
                justifyContent: 'space-between', 
                mb: 1,
                px: 1 
              }}>
                {!sidebarCollapsed && (
                  <Typography 
                    variant="h6" 
                    sx={{ 
                      fontWeight: 600, 
                      background: 'linear-gradient(45deg, #1976d2, #42a5f5)',
                      backgroundClip: 'text',
                      WebkitBackgroundClip: 'text',
                      WebkitTextFillColor: 'transparent',
                    }}
                  >
                    Hi Fiechu!
                  </Typography>
                )}
                <IconButton 
                  onClick={toggleSidebarCollapse} 
                  size="small"
                  sx={{ 
                    ml: sidebarCollapsed ? 0 : 'auto',
                    color: 'text.secondary',
                    '&:hover': { bgcolor: 'action.hover' },
                    cursor: sidebarCollapsed ? 'e-resize' : 'w-resize', // Right arrow when collapsed, left arrow when expanded
                  }}
                >
                  <ChatGPTSidebarIcon collapsed={sidebarCollapsed} />
                </IconButton>
              </Box>

              {/* Menu items */}
              <List sx={{ p: 0 }}>
                {/* New Chat */}
                <ListItem 
                  button 
                  onClick={handleNewChat}
                  sx={{
                    borderRadius: '8px',
                    mb: 0.5,
                    px: 1,
                    py: 0.75,
                    '&:hover': { bgcolor: 'action.hover' },
                    justifyContent: sidebarCollapsed ? 'center' : 'flex-start'
                  }}
                >
                  <AddIcon sx={{ 
                    fontSize: 20, 
                    color: 'text.secondary',
                    mr: sidebarCollapsed ? 0 : 1.5 
                  }} />
                  {!sidebarCollapsed && (
                    <ListItemText 
                      primary="New chat" 
                      primaryTypographyProps={{ fontSize: '0.875rem', fontWeight: 500 }}
                    />
                  )}
                </ListItem>

                {/* My Account */}
                <ListItem 
                  button 
                  onClick={handleMyAccount}
                  sx={{
                    borderRadius: '8px',
                    mb: 0.5,
                    px: 1,
                    py: 0.75,
                    '&:hover': { bgcolor: 'action.hover' },
                    justifyContent: sidebarCollapsed ? 'center' : 'flex-start'
                  }}
                >
                  <AccountCircleIcon sx={{ 
                    fontSize: 20, 
                    color: 'text.secondary',
                    mr: sidebarCollapsed ? 0 : 1.5 
                  }} />
                  {!sidebarCollapsed && (
                    <ListItemText 
                      primary="My account" 
                      primaryTypographyProps={{ fontSize: '0.875rem', fontWeight: 500 }}
                    />
                  )}
                </ListItem>

                {/* Settings */}
                <ListItem 
                  button 
                  onClick={handleSettings}
                  sx={{
                    borderRadius: '8px',
                    mb: 0.5,
                    px: 1,
                    py: 0.75,
                    '&:hover': { bgcolor: 'action.hover' },
                    justifyContent: sidebarCollapsed ? 'center' : 'flex-start'
                  }}
                >
                  <SettingsIcon sx={{ 
                    fontSize: 20, 
                    color: 'text.secondary',
                    mr: sidebarCollapsed ? 0 : 1.5 
                  }} />
                  {!sidebarCollapsed && (
                    <ListItemText 
                      primary="Settings" 
                      primaryTypographyProps={{ fontSize: '0.875rem', fontWeight: 500 }}
                    />
                  )}
                </ListItem>
              </List>

              {/* Divider */}
              {!sidebarCollapsed && (
                <>
                  <Divider sx={{ my: 2 }} />
                  <Typography 
                    variant="body2" 
                    sx={{ 
                      px: 1, 
                      mb: 1, 
                      color: 'text.secondary', 
                      fontWeight: 600,
                      fontSize: '0.75rem',
                      textTransform: 'uppercase',
                      letterSpacing: '0.5px'
                    }}
                  >
                    Past conversations
                  </Typography>
                </>
              )}
            </Box>

            {/* Past conversations list */}
            {!sidebarCollapsed && (
              <List sx={{ overflowY: 'auto', overflowX: 'visible', flexGrow: 1, px: 1 }}>
                {threads.map((thread) => (
                  <ListItem 
                    button 
                    key={thread.thread_id}
                    onClick={() => navigate(`/${thread.thread_id}`)}
                    selected={threadId === thread.thread_id}
                    onMouseEnter={() => setHoveredThreadId(thread.thread_id)}
                    onMouseLeave={() => setHoveredThreadId(null)}
                    sx={{
                      borderRadius: '8px',
                      marginBottom: '2px',
                      px: 1,
                      py: 0.75,
                      '&.Mui-selected': {
                        backgroundColor: theme.palette.action.selected,
                        '&:hover': {
                          backgroundColor: theme.palette.action.selected,
                        }
                      },
                      '&:hover': {
                        backgroundColor: theme.palette.action.hover,
                      },
                      maxHeight: '48px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between'
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
                          sx={{ width: '100%' }}
                          onClick={(e) => e.stopPropagation()}
                        />
                      </Box>
                    ) : (
                      // Display mode
                      <>
                        <ListItemText 
                          primary={thread.title}
                          primaryTypographyProps={{
                            fontSize: '0.875rem',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                            maxWidth: hoveredThreadId === thread.thread_id ? '140px' : '180px',
                            transition: 'max-width 0.2s ease'
                          }}
                        />
                        {hoveredThreadId === thread.thread_id && (
                          <Box sx={{ position: 'relative' }} data-menu-container>
                            <IconButton 
                              size="small"
                              onClick={(e) => handleThreadMenuOpen(e, thread.thread_id)}
                              sx={{ 
                                p: 0.5,
                                opacity: 0.7,
                                '&:hover': { opacity: 1 }
                              }}
                            >
                              <MoreHorizIcon fontSize="small" />
                            </IconButton>
                            

                          </Box>
                        )}
                      </>
                    )}
                  </ListItem>
                ))}
              </List>
            )}
            

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
            position: 'relative', // For overlay positioning
          }}
        >
          {/* Header for Toggle and Title - only show when there are messages */}
          {messages.length > 0 && (
            <Box sx={{ p: 2, display: 'flex', alignItems: 'center', borderBottom: `1px solid ${theme.palette.divider}` }}>
              <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
                {currentThreadTitle}
              </Typography>
               {/* Placeholder for other header items like Upgrade button if they move here */}
            </Box>
          )}



          {/* Messages area */}
          <Box sx={{ 
            flexGrow: 1, 
            overflowY: 'auto', 
            p: messages.length > 0 ? 2 : 0, 
            display: 'flex', 
            flexDirection: 'column' 
          }}>
            {messages.length === 0 ? (
              // Welcome screen
              <Box sx={{ 
                display: 'flex', 
                flexDirection: 'column', 
                alignItems: 'center', 
                justifyContent: 'center',
                height: '100%',
                textAlign: 'center',
                px: 2,
                gap: 4
              }}>
                <Typography 
                  variant="h3" 
                  sx={{ 
                    fontWeight: 600, 
                    background: 'linear-gradient(45deg, #1976d2, #42a5f5)',
                    backgroundClip: 'text',
                    WebkitBackgroundClip: 'text',
                    WebkitTextFillColor: 'transparent',
                    fontSize: { xs: '2rem', sm: '2.5rem', md: '3rem' }
                  }}
                >
                  What can I help you with, Fiechu?
                </Typography>
                
                {/* Input area positioned directly below title */}
                <Box sx={{ width: '100%', maxWidth: '800px', px: 2 }}>
                  <ChatInput
                    input={input}
                    setInput={setInput}
                    isLoading={isLoading}
                    onSubmit={sendMessage}
                    onSuggestionClick={handleSuggestionClick}
                    theme={theme}
                    isWelcome={true}
                    onAttachmentClick={handleAttachmentClick}
                  />
                </Box>
              </Box>
            ) : (
              // Chat messages
              messages.map((message, index) => (
                <Box
                  key={index}
                  sx={{
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: message.role === 'user' ? 'flex-end' : 'flex-start',
                    mb: 1.5, // Adjusted margin between message groups
                    maxWidth: '100%', // Ensure bubbles don't overflow container
                  }}
                >
                  {/* Message bubble */}
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
                    {...(message.role === 'assistant' && message.id && { 'data-message-id': message.id })}
                  >
                    {renderMessage(
                      message, 
                      handleNewAssistantMessage
                    )}
                  </Paper>
                  
                  {/* Action buttons below message bubble */}
                  <Box sx={{ 
                    display: 'flex', 
                    gap: 0.5, 
                    mt: 0.5,
                    ml: message.role === 'user' ? 0 : 1, // Align with message bubble
                    mr: message.role === 'user' ? 1 : 0, // Align with message bubble
                    opacity: 0.6,
                    '&:hover': { opacity: 1 },
                    transition: 'opacity 0.2s ease'
                  }}>
                    {/* Copy button - for both user and assistant messages */}
                    <IconButton 
                      size="small" 
                      onClick={() => copyToClipboard(message.content)}
                      sx={{ 
                        p: 0.5,
                        color: 'text.secondary',
                        '&:hover': { 
                          color: 'primary.main',
                          bgcolor: 'action.hover'
                        }
                      }}
                    >
                      <ContentCopyIcon fontSize="inherit" />
                    </IconButton>
                    
                    {/* Anchor button - only for user messages */}
                    {message.role === 'user' && (
                      <IconButton 
                        size="small" 
                        onClick={async () => {
                          // Check if this message has a draft
                          const response = await DraftService.getDraftByMessage(message.id);
                          if (response.success) {
                            // Anchor by message, not by draft
                            handleAnchorChange({ id: message.id, type: 'message', data: { message_id: message.id } });
                          } else {
                            showSnackbar('No draft found for this message', 'info');
                          }
                        }}
                        sx={{ 
                          p: 0.5,
                          color: anchoredItem?.type === 'message' && anchoredItem?.id === message.id ? '#ff9800' : 'text.secondary',
                          '&:hover': { 
                            color: '#ff9800',
                            bgcolor: 'action.hover'
                          }
                        }}
                      >
                        <AnchorIcon fontSize="inherit" />
                      </IconButton>
                    )}
                    
                    {/* Repeat button - only for user messages */}
                    {message.role === 'user' && (
                      <IconButton 
                        size="small" 
                        onClick={() => repeatMessage(message.content)}
                        sx={{ 
                          p: 0.5,
                          color: 'text.secondary',
                          '&:hover': { 
                            color: 'primary.main',
                            bgcolor: 'action.hover'
                          }
                        }}
                      >
                        <RepeatIcon fontSize="inherit" />
                      </IconButton>
                    )}
                  </Box>
                </Box>
              ))
            )}
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

          {/* Anchor Information Bar - positioned just above text area */}
          {anchoredItem && messages.length > 0 && (
            <Box sx={{ 
              p: 2, 
              backgroundColor: '#fff3e0',
              borderTop: '1px solid #ffcc02',
              display: 'flex',
              alignItems: 'center',
              gap: 1
            }}>
              <AnchorIcon sx={{ color: '#ff9800' }} />
              <Box sx={{ flexGrow: 1 }}>
                {anchoredItem.type === 'draft' ? (
                  <Box>
                    <Typography variant="body2" sx={{ fontWeight: 'bold', color: '#ef6c00', mb: 1 }}>
                      Draft {anchoredItem.data.draft_type === 'email' ? 'Email' : 'Calendar Event'}
                    </Typography>
                    
                    {/* Email Draft Details */}
                    {anchoredItem.data.draft_type === 'email' && (
                      <Box sx={{ pl: 1 }}>
                        <Typography variant="body2" sx={{ mb: 0.5 }}>
                          <strong>To:</strong> {
                            anchoredItem.data.to_emails && anchoredItem.data.to_emails.length > 0 
                              ? anchoredItem.data.to_emails.map(email => {
                                  if (email.name && email.email) {
                                    return `${email.name} (${email.email})`;
                                  } else if (email.email) {
                                    return email.email;
                                  } else if (email.name) {
                                    return email.name;
                                  } else {
                                    return 'Unknown recipient';
                                  }
                                }).join(', ')
                              : <span style={{ color: '#d32f2f', fontStyle: 'italic' }}>Not specified</span>
                          }
                        </Typography>
                        <Typography variant="body2" sx={{ mb: 0.5 }}>
                          <strong>Subject:</strong> {
                            anchoredItem.data.subject 
                              ? anchoredItem.data.subject
                              : <span style={{ color: '#d32f2f', fontStyle: 'italic' }}>Not specified</span>
                          }
                        </Typography>
                        {anchoredItem.data.cc_emails && anchoredItem.data.cc_emails.length > 0 && (
                          <Typography variant="body2" sx={{ mb: 0.5 }}>
                            <strong>CC:</strong> {anchoredItem.data.cc_emails.map(email => {
                              if (email.name && email.email) {
                                return `${email.name} (${email.email})`;
                              } else if (email.email) {
                                return email.email;
                              } else if (email.name) {
                                return email.name;
                              } else {
                                return 'Unknown recipient';
                              }
                            }).join(', ')}
                          </Typography>
                        )}
                        {anchoredItem.data.bcc_emails && anchoredItem.data.bcc_emails.length > 0 && (
                          <Typography variant="body2" sx={{ mb: 0.5 }}>
                            <strong>BCC:</strong> {anchoredItem.data.bcc_emails.map(email => {
                              if (email.name && email.email) {
                                return `${email.name} (${email.email})`;
                              } else if (email.email) {
                                return email.email;
                              } else if (email.name) {
                                return email.name;
                              } else {
                                return 'Unknown recipient';
                              }
                            }).join(', ')}
                          </Typography>
                        )}
                        {anchoredItem.data.body && (
                          <Typography variant="body2" sx={{ mb: 0.5 }}>
                            <strong>Body:</strong> {
                              anchoredItem.data.body.length > 80 
                                ? anchoredItem.data.body.substring(0, 80) + '...'
                                : anchoredItem.data.body
                            }
                          </Typography>
                        )}
                      </Box>
                    )}

                    {/* Calendar Event Draft Details */}
                    {anchoredItem.data.draft_type === 'calendar_event' && (
                      <Box sx={{ pl: 1 }}>
                        <Typography variant="body2" sx={{ mb: 0.5 }}>
                          <strong>Title:</strong> {
                            anchoredItem.data.summary 
                              ? anchoredItem.data.summary
                              : <span style={{ color: '#d32f2f', fontStyle: 'italic' }}>Not specified</span>
                          }
                        </Typography>
                        <Typography variant="body2" sx={{ mb: 0.5 }}>
                          <strong>Start:</strong> {
                            anchoredItem.data.start_time 
                              ? (() => {
                                  try {
                                    const date = new Date(anchoredItem.data.start_time);
                                    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
                                  } catch (e) {
                                    return anchoredItem.data.start_time;
                                  }
                                })()
                              : <span style={{ color: '#d32f2f', fontStyle: 'italic' }}>Not specified</span>
                          }
                        </Typography>
                        <Typography variant="body2" sx={{ mb: 0.5 }}>
                          <strong>End:</strong> {
                            anchoredItem.data.end_time 
                              ? (() => {
                                  try {
                                    const date = new Date(anchoredItem.data.end_time);
                                    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
                                  } catch (e) {
                                    return anchoredItem.data.end_time;
                                  }
                                })()
                              : <span style={{ color: '#d32f2f', fontStyle: 'italic' }}>Not specified</span>
                          }
                        </Typography>
                        {anchoredItem.data.location && (
                          <Typography variant="body2" sx={{ mb: 0.5 }}>
                            <strong>Location:</strong> {anchoredItem.data.location}
                          </Typography>
                        )}
                        {anchoredItem.data.attendees && anchoredItem.data.attendees.length > 0 && (
                          <Typography variant="body2" sx={{ mb: 0.5 }}>
                            <strong>Attendees:</strong> {anchoredItem.data.attendees.map((attendee, index) => {
                              console.log(`Attendee ${index}:`, attendee, `name: "${attendee.name}", email: "${attendee.email}"`);
                              if (attendee.name && attendee.email) {
                                return `${attendee.name} (${attendee.email})`;
                              } else if (attendee.email) {
                                return attendee.email;
                              } else if (attendee.name) {
                                return `${attendee.name} (no email)`;
                              } else {
                                return 'Unknown attendee';
                              }
                            }).join(', ')}
                          </Typography>
                        )}
                        {anchoredItem.data.description && (
                          <Typography variant="body2" sx={{ mb: 0.5 }}>
                            <strong>Description:</strong> {
                              anchoredItem.data.description.length > 80 
                                ? anchoredItem.data.description.substring(0, 80) + '...'
                                : anchoredItem.data.description
                            }
                          </Typography>
                        )}
                      </Box>
                    )}
                    
                    {/* Missing fields warning */}
                    {draftValidation && !draftValidation.is_complete && (
                      <Typography variant="caption" sx={{ color: '#d32f2f', fontStyle: 'italic', mt: 1, display: 'block' }}>
                        ⚠️ {getMissingFieldsText(draftValidation)}
                      </Typography>
                    )}
                  </Box>
                ) : (
                  <Box>
                    <Typography variant="body2" sx={{ fontWeight: 'bold', color: '#ef6c00' }}>
                      Anchored {anchoredItem.type === 'email' ? 'Email' : 'Calendar Event'}:
                    </Typography>
                    {anchoredItem.type === 'email' ? (
                      <Box>
                        <Typography variant="body2">
                          <strong>Subject:</strong> {anchoredItem.data.subject || 'No Subject'}
                        </Typography>
                        <Typography variant="body2">
                          <strong>From:</strong> {anchoredItem.data.from_email?.name || anchoredItem.data.from?.name || 'Unknown Sender'}
                        </Typography>
                        <Typography variant="body2">
                          <strong>Date:</strong> {new Date(anchoredItem.data.date).toLocaleDateString()}
                        </Typography>
                      </Box>
                    ) : (
                      <Box>
                        <Typography variant="body2">
                          <strong>Name:</strong> {anchoredItem.data.summary || 'Untitled Event'}
                        </Typography>
                        <Typography variant="body2">
                          <strong>Start:</strong> {new Date(anchoredItem.data.start?.dateTime || anchoredItem.data.start?.date).toLocaleString()}
                        </Typography>
                        <Typography variant="body2">
                          <strong>End:</strong> {new Date(anchoredItem.data.end?.dateTime || anchoredItem.data.end?.date).toLocaleString()}
                        </Typography>
                      </Box>
                    )}
                  </Box>
                )}
              </Box>
              
              {/* Action buttons */}
              <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                {anchoredItem.type === 'draft' && (
                  <Button
                    variant="contained"
                    size="small"
                    startIcon={draftValidation?.is_complete ? <SendIcon /> : <CreateIcon />}
                    onClick={handleSendDraft}
                    disabled={isSendingDraft}
                    sx={{
                      backgroundColor: draftValidation?.is_complete ? '#4caf50' : '#ff9800',
                      '&:hover': {
                        backgroundColor: draftValidation?.is_complete ? '#388e3c' : '#f57c00'
                      },
                      '&:disabled': {
                        backgroundColor: '#ccc'
                      }
                    }}
                  >
                    {isSendingDraft ? 'Sending...' : 
                     draftValidation?.is_complete ? 'Send' : 'Needs Info'}
                  </Button>
                )}
                <IconButton 
                  size="small" 
                  onClick={() => handleAnchorChange(null)}
                  sx={{ color: '#ef6c00' }}
                >
                  <CloseIcon />
                </IconButton>
              </Box>
            </Box>
          )}

          {/* Input area - only show for chat conversations */}
          {messages.length > 0 && (
            <ChatInput
              input={input}
              setInput={setInput}
              isLoading={isLoading}
              onSubmit={sendMessage}
              onSuggestionClick={handleSuggestionClick}
              theme={theme}
              isWelcome={false}
              onAttachmentClick={handleAttachmentClick}
            />
          )}
        </Box>

        {/* Email Sidebar */}
        <EmailSidebar
          open={emailSidebar.open}
          email={emailSidebar.email}
          loading={emailSidebar.loading}
          error={emailSidebar.error}
          onClose={handleCloseEmailSidebar}
        />

        <DeleteConfirmationDialog />
        
        <Snackbar
          open={snackbarOpen}
          autoHideDuration={3000}
          onClose={() => setSnackbarOpen(false)}
          message={threadToDelete ? "Thread deleted successfully" : "Error deleting thread"}
        />

        {/* Thread menu portal */}
        {menuAnchorEl && createPortal(
          <ThemeProvider theme={theme}>
            <Paper
              data-menu-container
              sx={{
                position: 'fixed',
                top: menuAnchorEl.top,
                left: menuAnchorEl.left,
                zIndex: 9999,
                borderRadius: '8px',
                border: '1px solid',
                borderColor: 'divider',
                boxShadow: '0 4px 20px rgba(0,0,0,0.1)',
                minWidth: '160px',
                py: 0.5
              }}
            >
              <List sx={{ py: 0 }}>
                <ListItem 
                  button
                  onClick={handleMenuRename}
                  sx={{ 
                    py: 1,
                    px: 2,
                    '&:hover': { bgcolor: 'action.hover' }
                  }}
                >
                  <ListItemIcon sx={{ minWidth: '32px' }}>
                    <EditIcon fontSize="small" />
                  </ListItemIcon>
                  <ListItemText 
                    primary="Rename" 
                    primaryTypographyProps={{ fontSize: '0.875rem' }}
                  />
                </ListItem>
                <ListItem 
                  button
                  onClick={handleMenuDelete}
                  sx={{ 
                    py: 1,
                    px: 2,
                    color: 'error.main',
                    '&:hover': { 
                      bgcolor: 'error.light',
                      color: 'error.contrastText'
                    }
                  }}
                >
                  <ListItemIcon sx={{ minWidth: '32px' }}>
                    <DeleteIcon fontSize="small" sx={{ color: 'inherit' }} />
                  </ListItemIcon>
                  <ListItemText 
                    primary="Delete" 
                    primaryTypographyProps={{ fontSize: '0.875rem' }}
                  />
                </ListItem>
              </List>
            </Paper>
          </ThemeProvider>,
          document.body
        )}
      </Box>
    </ThemeProvider>
  );
}

export default App;