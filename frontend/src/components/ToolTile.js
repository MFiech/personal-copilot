import React from 'react';
import AnchorIcon from '@mui/icons-material/Anchor';
import DeleteOutlinedIcon from '@mui/icons-material/DeleteOutlined';
import './ToolTile.css';

const ToolTile = ({ 
  type, 
  data, 
  isSelected = false, 
  onSelect, 
  onDelete, 
  showCheckbox = false,
  isAnchored = false,
  onAnchor,
  onClick
}) => {
  console.log('ToolTile received:', { type, data, isSelected });

  const handleTileClick = (e) => {
    // Don't trigger selection if clicking on action buttons
    if (e.target.closest('.tile-actions') || e.target.closest('.tile-checkbox') || e.target.closest('.tile-anchor')) {
      return;
    }
    // Call onClick if provided (for calendar events), otherwise call onSelect
    if (onClick) {
      onClick();
    } else if (onSelect) {
      onSelect();
    }
  };

  const handleDeleteClick = (e) => {
    e.stopPropagation();
    if (onDelete && data) {
      const itemId = type === 'email' 
        ? (data.email_id || data._id) 
        : data.id;
      onDelete(itemId);
    }
  };

  const handleAnchorClick = (e) => {
    e.stopPropagation();
    if (onAnchor) {
      onAnchor();
    }
  };

  const renderEmailContent = () => {
    const subject = data.subject || 'No Subject';
    const sender = data.from?.name || data.from_email?.name || 'Unknown Sender';
    return (
      <>
        <div className="tile-subject" title={subject}>{subject}</div>
        <div className="tile-sender" title={sender}>{sender}</div>
      </>
    );
  };

  const renderCalendarContent = () => {
    const title = data.summary || 'Untitled Event';
    const startDateTime = data.start?.dateTime || data.start?.date;
    const endDateTime = data.end?.dateTime || data.end?.date;
    
    let timeDisplay = 'No Date';
    if (startDateTime && endDateTime) {
      const startDate = new Date(startDateTime);
      const endDate = new Date(endDateTime);
      const startTime = startDate.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: false });
      const endTime = endDate.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: false });
      const dateStr = startDate.toLocaleDateString('en-GB', { day: '2-digit', month: '2-digit', year: 'numeric' });
      timeDisplay = `${startTime}-${endTime}, ${dateStr}`;
    }
    
    return (
      <>
        <div className="calendar-top-row">
          <div className="calendar-time" title={timeDisplay}>{timeDisplay}</div>
          <div className="calendar-actions">
            {onAnchor && (
              <button 
                className={`calendar-anchor-btn ${isAnchored ? 'anchored' : ''}`}
                onClick={handleAnchorClick}
                title={isAnchored ? "Remove anchor" : "Anchor this event"}
              >
                <AnchorIcon />
              </button>
            )}
            {onDelete && (
              <button 
                className="calendar-delete-btn-icon"
                onClick={handleDeleteClick}
                title="Delete event"
              >
                <DeleteOutlinedIcon />
              </button>
            )}
          </div>
        </div>
        <div className="calendar-title" title={title}>{title}</div>
      </>
    );
  };

  return (
    <div 
      className={`veyra-tile ${type}-tile ${isSelected ? 'selected' : ''}`}
      onClick={handleTileClick}
    >
      {type === 'email' ? (
        <>
          {showCheckbox && (
            <div 
              className={`tile-checkbox ${isSelected ? 'selected' : ''}`}
              onClick={(e) => {
                e.stopPropagation();
                if (onSelect) onSelect();
              }}
            >
              {isSelected && <span>✓</span>}
            </div>
          )}
          
          <div style={{ paddingLeft: showCheckbox ? '30px' : '0px' }}>
            {renderEmailContent()}
          </div>

          <div className="tile-actions">
            {onAnchor && (
              <button 
                className={`tile-anchor-btn ${isAnchored ? 'anchored' : ''}`}
                onClick={handleAnchorClick}
                title={isAnchored ? "Remove anchor" : "Anchor this item"}
              >
                <AnchorIcon />
              </button>
            )}
            {onDelete && (
              <button 
                onClick={handleDeleteClick}
                title="Delete"
              >
                🗑️
              </button>
            )}
          </div>
        </>
      ) : (
        // Calendar tile layout
        renderCalendarContent()
      )}
    </div>
  );
};

export default ToolTile; 