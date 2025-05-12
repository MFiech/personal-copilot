import React from 'react';
import './VeyraTile.css';

const VeyraTile = ({ type, data }) => {
  console.log('VeyraTile received:', { type, data });

  const renderEmailContent = () => {
    const subject = data.subject || 'No Subject';
    const sender = data.from?.name || data.from_email?.name || 'Unknown Sender';
    return (
      <>
        <div className="tile-subject">{subject}</div>
        <div className="tile-sender">{sender}</div>
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
        <div className="tile-subject">{title}</div>
        <div className="tile-date">{formattedDate}</div>
      </>
    );
  };

  return (
    <div className="veyra-tile">
      {type === 'email' ? renderEmailContent() : renderCalendarContent()}
    </div>
  );
};

export default VeyraTile; 