import React, { useState } from 'react';
import ToolTile from './ToolTile';
import SelectionControlPanel from './SelectionControlPanel';
import TipsAndUpdatesOutlinedIcon from '@mui/icons-material/TipsAndUpdatesOutlined';
import OpenInFullOutlinedIcon from '@mui/icons-material/OpenInFullOutlined';
import DeleteOutlinedIcon from '@mui/icons-material/DeleteOutlined';
import './VeyraResults.css'; // Import the original styling

const ToolResults = ({ results, threadId, messageId, onUpdate, onNewMessageReceived, showSnackbar, ...paginationProps }) => {
  const [selectedEmails, setSelectedEmails] = useState([]);
  const [selectedEvents, setSelectedEvents] = useState([]);
  const [hoveredEmailId, setHoveredEmailId] = useState(null);
  const [summarizingEmails, setSummarizingEmails] = useState(new Set());

  if (!results || (!results.emails && !results.calendar_events)) {
    console.log('[ToolResults] No results to display');
    return null;
  }

  const { emails, calendar_events } = results;

  // Helper function to get email content
  const getEmailContent = async (emailId) => {
    try {
      const response = await fetch('http://localhost:5001/get_email_content', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email_id: emailId }),
      });
      
      if (!response.ok) {
        throw new Error(`Failed to get email content: ${response.status}`);
      }
      
      const data = await response.json();
      return data.content;
    } catch (error) {
      console.error('[ToolResults] Error getting email content:', error);
      throw error;
    }
  };

  // Helper function to summarize a single email
  const summarizeSingleEmail = async (emailId) => {
    try {
      setSummarizingEmails(prev => new Set([...prev, emailId]));
      
      // First, get the email content
      const emailContent = await getEmailContent(emailId);
      
      // Use text content for summarization (it's already converted from HTML)
      const contentToSummarize = emailContent.text || emailContent.html || '';
      
      // Truncate content if it's too long (backend expects truncated content)
      const maxLength = 4000; // Reasonable limit for LLM processing
      const truncatedContent = contentToSummarize.length > maxLength 
        ? contentToSummarize.substring(0, maxLength) + '...'
        : contentToSummarize;
      
      const response = await fetch('http://localhost:5001/summarize_single_email', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email_id: emailId,
          thread_id: threadId,
          assistant_message_id: messageId,
          email_content_full: contentToSummarize,
          email_content_truncated: truncatedContent
        }),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `Failed to summarize email: ${response.status}`);
      }
      
      const data = await response.json();
      
      // Add the summary as a new assistant message
      if (onNewMessageReceived && data.success) {
        onNewMessageReceived(data);
        if (showSnackbar) {
          showSnackbar('Email summarized successfully!', 'success');
        }
      }
      
      return data;
    } catch (error) {
      console.error('[ToolResults] Error summarizing email:', error);
      if (showSnackbar) {
        showSnackbar(`Failed to summarize email: ${error.message}`, 'error');
      }
      throw error;
    } finally {
      setSummarizingEmails(prev => {
        const newSet = new Set(prev);
        newSet.delete(emailId);
        return newSet;
      });
    }
  };

  // Email selection handlers
  const handleEmailSelection = (emailId) => {
    setSelectedEmails(prev => 
      prev.includes(emailId) 
        ? prev.filter(id => id !== emailId)
        : [...prev, emailId]
    );
  };

  const handleSelectAllEmails = () => {
    const allEmailIds = emails.map(email => email.email_id || email._id);
    setSelectedEmails(allEmailIds);
  };

  const handleDeselectAllEmails = () => {
    setSelectedEmails([]);
  };

  const handleEmailDeleted = (deletedEmailId) => {
    const updatedEmails = emails.filter(email => email.email_id !== deletedEmailId);
    setSelectedEmails(prev => prev.filter(id => id !== deletedEmailId));
    if (onUpdate) {
      onUpdate(messageId, { ...results, emails: updatedEmails });
    }
  };

  const handleBulkDeleteEmails = () => {
    const updatedEmails = emails.filter(email => 
      !selectedEmails.includes(email.email_id || email._id)
    );
    setSelectedEmails([]);
    if (onUpdate) {
      onUpdate(messageId, { ...results, emails: updatedEmails });
    }
  };

  const handleSummarizeEmails = async () => {
    const selectedEmailData = emails.filter(email => 
      selectedEmails.includes(email.email_id || email._id)
    );
    
    if (selectedEmailData.length === 0) {
      if (showSnackbar) {
        showSnackbar('No emails selected for summarization', 'warning');
      }
      return;
    }

    if (selectedEmailData.length === 1) {
      // For single email, use the single email summarization
      const emailId = selectedEmailData[0].email_id || selectedEmailData[0]._id;
      try {
        await summarizeSingleEmail(emailId);
        setSelectedEmails([]); // Clear selection after successful summarization
      } catch (error) {
        // Error handling is done in summarizeSingleEmail
      }
    } else {
      // For multiple emails, summarize each one individually
      // This could be enhanced in the future to create a combined summary
      if (showSnackbar) {
        showSnackbar(`Summarizing ${selectedEmailData.length} emails...`, 'info');
      }
      
      let successCount = 0;
      for (const email of selectedEmailData) {
        const emailId = email.email_id || email._id;
        try {
          await summarizeSingleEmail(emailId);
          successCount++;
        } catch (error) {
          console.error(`Failed to summarize email ${emailId}:`, error);
        }
      }
      
      if (showSnackbar) {
        if (successCount === selectedEmailData.length) {
          showSnackbar(`Successfully summarized all ${successCount} emails!`, 'success');
        } else {
          showSnackbar(`Summarized ${successCount} out of ${selectedEmailData.length} emails`, 'warning');
        }
      }
      
      setSelectedEmails([]); // Clear selection after processing
    }
  };

  const handleSingleEmailSummarize = async (emailId) => {
    try {
      await summarizeSingleEmail(emailId);
    } catch (error) {
      // Error handling is done in summarizeSingleEmail
    }
  };

  const handleMasterCheckboxChange = () => {
    if (selectedEmails.length === emails.length) {
      handleDeselectAllEmails();
    } else {
      handleSelectAllEmails();
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return '';
    try {
      const date = new Date(dateString);
      const now = new Date();
      const diffTime = Math.abs(now - date);
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
      
      if (diffDays === 1) {
        return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
      } else if (diffDays <= 7) {
        return date.toLocaleDateString('en-US', { weekday: 'short' });
      } else {
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      }
    } catch (error) {
      return dateString;
    }
  };

  const totalSelected = selectedEmails.length + selectedEvents.length;

  return (
    <>
      <div className="gmail-email-list">
        {emails && emails.length > 0 && (
          <div className="email-table">
            {/* Action row - always visible with consistent height */}
            <div className="email-action-row">
              <div className="email-checkbox-cell">
                <input
                  type="checkbox"
                  className="email-checkbox"
                  checked={selectedEmails.length === emails.length && emails.length > 0}
                  onChange={handleMasterCheckboxChange}
                />
              </div>
              <div className="email-action-spacer"></div>
              <div className="email-actions">
                {selectedEmails.length > 0 && (
                  <>
                    <button 
                      onClick={handleSummarizeEmails} 
                      className="action-text-btn summarize-text-btn"
                      disabled={selectedEmails.some(emailId => summarizingEmails.has(emailId))}
                    >
                      {selectedEmails.some(emailId => summarizingEmails.has(emailId)) ? 'SUMMARIZING...' : 'SUMMARIZE'}
                    </button>
                    <button onClick={handleBulkDeleteEmails} className="action-text-btn delete-text-btn">
                      DELETE
                    </button>
                  </>
                )}
              </div>
            </div>
            
            {/* Email rows */}
            {emails.map((email, index) => {
              const emailId = email.email_id || email._id;
              const isSelected = selectedEmails.includes(emailId);
              const isHovered = hoveredEmailId === emailId;
              const isSummarizing = summarizingEmails.has(emailId);
              const fromName = email.from_email?.name || email.from?.name || 'Unknown Sender';
              const subject = email.subject || 'No Subject';
              const date = formatDate(email.date);
              
              return (
                <div 
                  key={emailId || index}
                  className={`email-row ${isSelected ? 'selected' : ''}`}
                  onClick={() => handleEmailSelection(emailId)}
                  onMouseEnter={() => setHoveredEmailId(emailId)}
                  onMouseLeave={() => setHoveredEmailId(null)}
                >
                  <div className="email-checkbox-cell">
                    <input
                      type="checkbox"
                      className="email-checkbox"
                      checked={isSelected}
                      onChange={() => handleEmailSelection(emailId)}
                      onClick={(e) => e.stopPropagation()}
                    />
                  </div>
                  <div className="email-from" title={fromName}>
                    {fromName}
                  </div>
                  <div className="email-subject" title={subject}>
                    {subject}
                  </div>
                  <div className="email-date-actions">
                    {isHovered ? (
                      <div className="email-hover-icons">
                        <button 
                          className="hover-icon-btn summarize-hover-btn"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleSingleEmailSummarize(emailId);
                          }}
                          disabled={isSummarizing}
                          title={isSummarizing ? "Summarizing..." : "Summarize"}
                        >
                          <TipsAndUpdatesOutlinedIcon />
                        </button>
                        <button 
                          className="hover-icon-btn open-hover-btn"
                          onClick={(e) => {
                            e.stopPropagation();
                            console.log('Open email:', emailId);
                            // TODO: Implement email opening
                          }}
                          title="Open"
                        >
                          <OpenInFullOutlinedIcon />
                        </button>
                        <button 
                          className="hover-icon-btn delete-hover-btn"
                          onClick={(e) => {
                            e.stopPropagation();
                            console.log('Delete single email:', emailId);
                            // TODO: Implement single email delete
                          }}
                          title="Delete"
                        >
                          <DeleteOutlinedIcon />
                        </button>
                      </div>
                    ) : (
                      <div className="email-date">
                        {date}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
        
        {calendar_events && calendar_events.length > 0 && (
          <div className="veyra-section">
            <h2>Calendar Events ({calendar_events.length})</h2>
            <div className="veyra-grid">
              {calendar_events.map((event, index) => (
                <ToolTile 
                  key={event.id || index}
                  type="event"
                  data={event} 
                  threadId={threadId}
                  messageId={messageId}
                  isSelected={selectedEvents.includes(event.id)}
                  onSelect={() => {
                    const eventId = event.id;
                    setSelectedEvents(prev => 
                      prev.includes(eventId) 
                        ? prev.filter(id => id !== eventId)
                        : [...prev, eventId]
                    );
                  }}
                  showCheckbox={true}
                />
              ))}
            </div>
          </div>
        )}
      </div>
    </>
  );
};

export default ToolResults;