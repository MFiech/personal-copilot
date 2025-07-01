import React, { useState } from 'react';
import ToolTile from './ToolTile';
import TipsAndUpdatesOutlinedIcon from '@mui/icons-material/TipsAndUpdatesOutlined';
import OpenInFullOutlinedIcon from '@mui/icons-material/OpenInFullOutlined';
import DeleteOutlinedIcon from '@mui/icons-material/DeleteOutlined';
import AnchorIcon from '@mui/icons-material/Anchor';
import './VeyraResults.css'; // Import the original styling

const ToolResults = ({ results, threadId, messageId, onUpdate, onNewMessageReceived, showSnackbar, onOpenEmail, currentOffset, limitPerPage, totalEmailsAvailable, hasMore, anchoredItem, onAnchorChange, ...paginationProps }) => {
  const [selectedEmails, setSelectedEmails] = useState([]);
  const [selectedEvents, setSelectedEvents] = useState([]);
  const [hoveredEmailId, setHoveredEmailId] = useState(null);
  const [summarizingEmails, setSummarizingEmails] = useState(new Set());
  const [loadingMoreEmails, setLoadingMoreEmails] = useState(false);

  // Debug pagination props
  console.log('[ToolResults] Pagination props:', {
    currentOffset,
    limitPerPage,
    totalEmailsAvailable,
    hasMore,
    emailCount: results?.emails?.length
  });

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
    if (!emailId) {
      console.warn('Attempted to select email without valid ID');
      return;
    }
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

  // Note: handleEmailDeleted function removed as it's not currently used
  // but kept for potential future implementation

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

  const handleLoadMoreEmails = async () => {
    if (loadingMoreEmails || !hasMore) return;
    
    try {
      setLoadingMoreEmails(true);
      
      const response = await fetch('http://localhost:5001/load_more_emails', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          thread_id: threadId,
          assistant_message_id: messageId,
        }),
      });
      
      if (!response.ok) {
        throw new Error(`Failed to load more emails: ${response.status}`);
      }
      
      const data = await response.json();
      
      if (data.new_emails && data.new_emails.length > 0) {
        // Update the results with new emails
        const updatedResults = {
          ...results,
          emails: [...(results.emails || []), ...data.new_emails]
        };
        
        if (onUpdate) {
          onUpdate(messageId, updatedResults, {
            currentOffset: data.current_offset,
            limitPerPage: data.limit_per_page,
            totalEmailsAvailable: data.total_emails_available,
            hasMore: data.has_more
          });
        }
        
        if (showSnackbar) {
          showSnackbar(`Loaded ${data.new_emails.length} more emails`, 'success');
        }
      } else {
        if (showSnackbar) {
          showSnackbar('No more emails to load', 'info');
        }
      }
    } catch (error) {
      console.error('[ToolResults] Error loading more emails:', error);
      if (showSnackbar) {
        showSnackbar(`Failed to load more emails: ${error.message}`, 'error');
      }
    } finally {
      setLoadingMoreEmails(false);
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

  // Note: totalSelected removed as it's not currently used
  // const totalSelected = selectedEmails.length + selectedEvents.length;

  // Helper function to handle anchor selection
  const handleAnchorSelect = (item, type) => {
    const itemId = type === 'email' ? (item.email_id || item._id || item.id) : item.id;
    const currentAnchoredId = anchoredItem?.id;
    
    if (currentAnchoredId === itemId) {
      // Deselect current anchor
      onAnchorChange(null);
    } else {
      // Select new anchor
      const anchorData = {
        id: itemId,
        type: type,
        data: item
      };
      onAnchorChange(anchorData);
    }
  };

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
              const uniqueKey = emailId ? `email-${emailId}` : `email-index-${index}`;
              const isSelected = selectedEmails.includes(emailId);
              const isHovered = hoveredEmailId === emailId;
              const isSummarizing = summarizingEmails.has(emailId);
              const fromName = email.from_email?.name || email.from?.name || 'Unknown Sender';
              const subject = email.subject || 'No Subject';
              const date = formatDate(email.date);
              
              // Skip this email if we don't have a valid emailId to prevent state confusion
              if (!emailId) {
                console.warn('Email without valid ID detected, skipping:', email);
                return null;
              }
              
              return (
                <div 
                  key={uniqueKey}
                  className={`email-row ${isSelected ? 'selected' : ''} ${anchoredItem?.id === emailId ? 'anchored' : ''}`}
                  onClick={() => handleEmailSelection(emailId)}
                  onMouseEnter={() => setHoveredEmailId(emailId)}
                  onMouseLeave={() => setHoveredEmailId(null)}
                >
                  <div className="email-checkbox-cell">
                    <input
                      type="checkbox"
                      className="email-checkbox"
                      checked={isSelected}
                      onChange={(e) => {
                        e.stopPropagation();
                        handleEmailSelection(emailId);
                      }}
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
                    {(isHovered || anchoredItem?.id === emailId) ? (
                      <div className="email-hover-icons">
                        <button 
                          className={`hover-icon-btn anchor-hover-btn ${anchoredItem?.id === emailId ? 'anchored' : ''}`}
                          onClick={(e) => {
                            e.stopPropagation();
                            handleAnchorSelect(email, 'email');
                          }}
                          title={anchoredItem?.id === emailId ? "Remove anchor" : "Anchor this email"}
                        >
                          <AnchorIcon />
                        </button>
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
                            if (onOpenEmail) {
                              onOpenEmail(email);
                            }
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
            
            {/* Load more emails row */}
            {hasMore && (
              <div className="email-row load-more-row">
                <div className="load-more-content">
                  <button 
                    onClick={handleLoadMoreEmails} 
                    disabled={loadingMoreEmails}
                    className="load-more-btn"
                  >
                    {loadingMoreEmails ? 'Loading more emails...' : 'Load more emails'}
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
        
        {calendar_events && calendar_events.length > 0 && (
          <div className="veyra-section">
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
                  isAnchored={anchoredItem?.id === event.id}
                  onAnchor={() => handleAnchorSelect(event, 'calendar_event')}
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