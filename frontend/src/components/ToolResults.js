import React, { useState } from 'react';
import ToolTile from './ToolTile';
import SelectionControlPanel from './SelectionControlPanel';
import './VeyraResults.css'; // Import the original styling

const ToolResults = ({ results, threadId, messageId, onUpdate, ...paginationProps }) => {
  const [selectedEmails, setSelectedEmails] = useState([]);
  const [selectedEvents, setSelectedEvents] = useState([]);

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

  const totalSelected = selectedEmails.length + selectedEvents.length;

  return (
    <>
      <div className="veyra-results">
        {emails && emails.length > 0 && (
          <div className="veyra-section">
            <h2>Emails ({emails.length})</h2>
            <div className="veyra-grid">
              {emails.map((email, index) => (
                <ToolTile 
                  key={email.email_id || email._id || index}
                  type="email"
                  data={email} 
                  threadId={threadId}
                  messageId={messageId}
                  onDelete={handleEmailDeleted}
                  isSelected={selectedEmails.includes(email.email_id || email._id)}
                  onSelect={() => handleEmailSelection(email.email_id || email._id)}
                  showCheckbox={true}
                />
              ))}
            </div>
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

      {totalSelected > 0 && (
        <SelectionControlPanel
          selectedCount={totalSelected}
          onSelectAll={handleSelectAllEmails}
          onDeselectAll={() => {
            handleDeselectAllEmails();
            setSelectedEvents([]);
          }}
          onSummarize={handleSummarizeEmails}
          onDelete={handleBulkDeleteEmails}
        />
      )}
    </>
  );
};

export default ToolResults;