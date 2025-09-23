# Email Draft Click Fix - Test Instructions

## What was fixed:
The issue where clicking on an email draft tile in the conversation incorrectly triggered `/thread/{id}/combined` instead of the proper endpoint.

## How it now works:

### For Reply Drafts (with gmail_thread_id):
1. Click on email draft tile → calls `/resolve-thread/{gmail_thread_id}?pm_thread_id={thread_id}`
2. Shows Gmail thread emails + drafts in right sidebar 
3. Uses `contentType: 'combined'` → reply functionality via Composio
4. Send button uses Composio reply method

### For New Email Drafts (without gmail_thread_id):
1. Click on email draft tile → shows draft-only sidebar
2. Shows only the single draft in right sidebar
3. Uses `contentType: 'draft'` → send email functionality
4. Send button uses Composio send email method

## Test Steps:

1. **Test Reply Draft:**
   - Find a draft with `gmail_thread_id` 
   - Click the draft tile
   - Verify right sidebar shows Gmail thread emails
   - Verify network calls `/resolve-thread/` not `/thread/.../combined`

2. **Test New Email Draft:**
   - Find a draft without `gmail_thread_id` 
   - Click the draft tile  
   - Verify right sidebar shows only the draft
   - Verify no network calls to `/thread/.../combined`

## Key Changes:
- Modified `handleDraftClick` in `App.js` 
- Proper `if/else` logic for gmail_thread_id presence
- Reuses existing working functionality
- No duplication of features