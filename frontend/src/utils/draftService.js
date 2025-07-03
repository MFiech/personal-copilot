/**
 * Frontend service for handling draft operations
 */

const API_BASE = 'http://localhost:5001';

export class DraftService {
  
  /**
   * Create a new draft
   */
  static async createDraft(draftType, threadId, messageId, initialData = {}) {
    try {
      const response = await fetch(`${API_BASE}/drafts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          draft_type: draftType,
          thread_id: threadId,
          message_id: messageId,
          initial_data: initialData
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('[DraftService] Create draft error:', error);
      throw error;
    }
  }

  /**
   * Get draft by ID
   */
  static async getDraft(draftId) {
    try {
      const response = await fetch(`${API_BASE}/drafts/${draftId}`);
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('[DraftService] Get draft error:', error);
      throw error;
    }
  }

  /**
   * Update draft
   */
  static async updateDraft(draftId, updates) {
    try {
      const response = await fetch(`${API_BASE}/drafts/${draftId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ updates })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('[DraftService] Update draft error:', error);
      throw error;
    }
  }

  /**
   * Validate draft completeness
   */
  static async validateDraft(draftId) {
    try {
      const response = await fetch(`${API_BASE}/drafts/${draftId}/validate`);
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('[DraftService] Validate draft error:', error);
      throw error;
    }
  }

  /**
   * Send/Execute draft
   */
  static async sendDraft(draftId) {
    try {
      const response = await fetch(`${API_BASE}/drafts/${draftId}/send`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('[DraftService] Send draft error:', error);
      throw error;
    }
  }

  /**
   * Get drafts by thread
   */
  static async getDraftsByThread(threadId) {
    try {
      const response = await fetch(`${API_BASE}/drafts/thread/${threadId}`);
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('[DraftService] Get drafts by thread error:', error);
      throw error;
    }
  }

  /**
   * Get draft by message ID
   */
  static async getDraftByMessage(messageId) {
    try {
      const response = await fetch(`${API_BASE}/drafts/message/${messageId}`);
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('[DraftService] Get draft by message error:', error);
      throw error;
    }
  }

  /**
   * Close a draft
   */
  static async closeDraft(draftId, status = 'closed') {
    try {
      const response = await fetch(`${API_BASE}/drafts/${draftId}/close`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('[DraftService] Close draft error:', error);
      throw error;
    }
  }
}

/**
 * Helper function to format draft display text
 */
export const formatDraftDisplayText = (draft) => {
  if (!draft) return '';

  const type = draft.draft_type;

  if (type === 'email') {
    const subject = draft.subject || 'No Subject';
    const to = draft.to_emails || [];
    const toText = to.length > 0 ? to.map(email => email.name || email.email).join(', ') : 'No Recipients';
    return `Email: ${subject} → ${toText}`;
  } else if (type === 'calendar_event') {
    const summary = draft.summary || 'Untitled Event';
    const startTime = draft.start_time || 'No Start Time';
    // Format time nicely if it's a full datetime string
    let displayTime = startTime;
    if (startTime && startTime !== 'No Start Time') {
      try {
        const date = new Date(startTime);
        displayTime = date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
      } catch (e) {
        displayTime = startTime;
      }
    }
    return `Event: ${summary} at ${displayTime}`;
  }

  return `${type.replace('_', ' ').toUpperCase()} Draft`;
};

/**
 * Helper function to get missing fields for display
 */
export const getMissingFieldsText = (validation) => {
  if (!validation || validation.is_complete) return '';
  
  const missing = validation.missing_fields || [];
  if (missing.length === 0) return '';
  
  // Map technical field names to user-friendly names
  const fieldNameMap = {
    'to_emails': 'Recipients',
    'subject': 'Subject',
    'body': 'Message Body',
    'summary': 'Event Title', 
    'start_time': 'Start Time',
    'end_time': 'End Time',
    'attendees': 'Attendees',
    'location': 'Location',
    'description': 'Description',
    'cc_emails': 'CC Recipients',
    'bcc_emails': 'BCC Recipients'
  };
  
  const friendlyNames = missing.map(field => fieldNameMap[field] || field);
  return `Missing: ${friendlyNames.join(', ')}`;
}; 