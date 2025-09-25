/**
 * Shared draft validation utility
 * Provides consistent validation logic for email and calendar drafts across all components
 */

/**
 * Validate an email draft
 * @param {Object} draft - Email draft object
 * @returns {Object} - { isComplete: boolean, reason: string, missingFields: array }
 */
export const validateEmailDraft = (draft) => {
  if (!draft) return { isComplete: false, reason: 'No draft', missingFields: [] };
  
  const missingFields = [];
  
  // Check to_emails (always required)
  if (!draft.to_emails || draft.to_emails.length === 0) {
    missingFields.push('recipients');
  }
  
  // Check subject (required unless it's a reply with gmail_thread_id)
  const hasSubject = Boolean(draft.subject?.trim());
  const isReply = Boolean(draft.gmail_thread_id);
  if (!hasSubject && !isReply) {
    missingFields.push('subject');
  }
  
  // Check body (always required)
  if (!draft.body?.trim()) {
    missingFields.push('body');
  }
  
  const isComplete = missingFields.length === 0;
  let reason;
  if (isComplete) {
    reason = 'Ready to send';
  } else if (missingFields.length === 1) {
    reason = `Missing ${missingFields[0]}`;
  } else {
    reason = `Missing ${missingFields.slice(0, -1).join(', ')} and ${missingFields.slice(-1)}`;
  }
  
  return { isComplete, reason, missingFields };
};

/**
 * Validate a calendar event draft
 * @param {Object} draft - Calendar draft object
 * @returns {Object} - { isComplete: boolean, reason: string, missingFields: array }
 */
export const validateCalendarDraft = (draft) => {
  if (!draft) return { isComplete: false, reason: 'No draft', missingFields: [] };
  
  const missingFields = [];
  
  if (!draft.summary?.trim()) missingFields.push('title');
  if (!draft.start_time) missingFields.push('start time');
  if (!draft.end_time) missingFields.push('end time');
  
  const isComplete = missingFields.length === 0;
  let reason;
  if (isComplete) {
    reason = 'Ready to create';
  } else if (missingFields.length === 1) {
    reason = `Missing ${missingFields[0]}`;
  } else {
    reason = `Missing ${missingFields.slice(0, -1).join(', ')} and ${missingFields.slice(-1)}`;
  }
  
  return { isComplete, reason, missingFields };
};

/**
 * Universal draft validator that handles both email and calendar drafts
 * @param {Object} draft - Draft object with draft_type field
 * @returns {Object} - { isComplete: boolean, reason: string, missingFields: array }
 */
export const validateDraft = (draft) => {
  if (!draft) return { isComplete: false, reason: 'No draft', missingFields: [] };
  
  if (draft.draft_type === 'email') {
    return validateEmailDraft(draft);
  }
  
  if (draft.draft_type === 'calendar_event') {
    return validateCalendarDraft(draft);
  }
  
  return { isComplete: false, reason: 'Unknown draft type', missingFields: [] };
};

/**
 * Get color for draft status
 * @param {string} status - Draft status ('active', 'closed', 'composio_error')
 * @returns {string} - Color code
 */
export const getDraftStatusColor = (status) => {
  switch (status) {
    case 'active': return '#1976d2';
    case 'closed': return '#4caf50';
    case 'composio_error': return '#f44336';
    default: return '#757575';
  }
};

/**
 * Get label for draft status
 * @param {string} status - Draft status
 * @returns {string} - Human readable label
 */
export const getDraftStatusLabel = (status) => {
  switch (status) {
    case 'active': return 'Draft';
    case 'closed': return 'Sent';
    case 'composio_error': return 'Error';
    default: return 'Draft';
  }
};

/**
 * Format recipients for display
 * @param {Array} recipients - Array of recipient objects
 * @returns {string} - Formatted recipient string
 */
export const formatRecipients = (recipients) => {
  if (!recipients || recipients.length === 0) return 'Not specified';
  return recipients.map(recipient => {
    if (typeof recipient === 'string') return recipient;
    if (recipient.name && recipient.email) return `${recipient.name} <${recipient.email}>`;
    return recipient.email || recipient.name || 'Unknown';
  }).join(', ');
};

/**
 * Check if a draft is a reply
 * @param {Object} draft - Draft object
 * @returns {boolean} - True if draft is a reply
 */
export const isDraftReply = (draft) => {
  return Boolean(draft?.gmail_thread_id);
};