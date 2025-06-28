import React, { useState } from 'react';
import ToolTile from './ToolTile';
import SelectionControlPanel from './SelectionControlPanel';
import TipsAndUpdatesOutlinedIcon from '@mui/icons-material/TipsAndUpdatesOutlined';
import OpenInFullOutlinedIcon from '@mui/icons-material/OpenInFullOutlined';
import DeleteOutlinedIcon from '@mui/icons-material/DeleteOutlined';
import './VeyraResults.css'; // Import the original styling

const ToolResults = ({ results, threadId, messageId, onUpdate, ...paginationProps }) => {
  const [selectedEmails, setSelectedEmails] = useState([]);
  const [selectedEvents, setSelectedEvents] = useState([]);
  const [hoveredEmailId, setHoveredEmailId] = useState(null);

  if (!results || (!results.emails && !results.calendar_events)) {
    console.log('[ToolResults] No results to display');
    return null;
  }

  const { emails, calendar_events } = results;

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

  const handleSummarizeEmails = () => {
    const selectedEmailData = emails.filter(email => 
      selectedEmails.includes(email.email_id || email._id)
    );
    console.log('Summarizing emails:', selectedEmailData);
    // TODO: Implement summarization functionality
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
                    <button onClick={handleSummarizeEmails} className="action-text-btn summarize-text-btn">
                      SUMMARIZE
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
                            console.log('Summarize single email:', emailId);
                            // TODO: Implement single email summarize
                          }}
                          title="Summarize"
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