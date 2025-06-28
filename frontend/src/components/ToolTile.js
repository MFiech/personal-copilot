import React from 'react';
import './ToolTile.css';

const ToolTile = ({ 
  type, 
  data, 
  isSelected = false, 
  onSelect, 
  onDelete, 
  showCheckbox = false 
}) => {
  console.log('ToolTile received:', { type, data, isSelected });

  const handleTileClick = (e) => {
    // Don't trigger selection if clicking on action buttons
    if (e.target.closest('.tile-actions') || e.target.closest('.tile-checkbox')) {
      return;
    }
    if (onSelect) {
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
    const start = data.start?.dateTime || data.start?.date || 'No Date';
    const date = new Date(start);
    const formattedDate = date.toLocaleDateString();
    return (
      <>
        <div className="tile-subject" title={title}>{title}</div>
        <div className="tile-date">{formattedDate}</div>
      </>
    );
  };

  return (
    <div 
      className={`veyra-tile ${type}-tile ${isSelected ? 'selected' : ''}`}
      onClick={handleTileClick}
    >
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
        {type === 'email' ? renderEmailContent() : renderCalendarContent()}
      </div>

      {onDelete && (
        <div className="tile-actions">
          <button 
            onClick={handleDeleteClick}
            title="Delete"
          >
            🗑️
          </button>
        </div>
      )}
    </div>
  );
};

export default ToolTile; 