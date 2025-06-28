import React from 'react';

const SelectionControlPanel = ({
  selectedCount,
  onSelectAll,
  onDeselectAll,
  onSummarize,
  onDelete,
}) => {
  return (
    <div
      style={{
        padding: '8px 16px',
        backgroundColor: '#f0f2f5',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-around',
        borderTop: '1px solid #e0e0e0',
        position: 'fixed',
        bottom: '60px', // Assuming chat input is around 60px high
        left: '0',
        right: '0',
        zIndex: '1000', // Ensure it's above other elements
      }}
    >
      <span>{selectedCount} selected</span>
      <button onClick={onSelectAll} style={{ marginLeft: '10px', padding: '5px 10px' }}>
        Select All
      </button>
      <button onClick={onDeselectAll} style={{ marginLeft: '10px', padding: '5px 10px' }}>
        Deselect All
      </button>
      <button onClick={onSummarize} style={{ marginLeft: '10px', padding: '5px 10px' }}>
        Summarize
      </button>
      <button onClick={onDelete} style={{ marginLeft: '10px', padding: '5px 10px' }}>
        Delete
      </button>
    </div>
  );
};

export default SelectionControlPanel; 