# Email Reply Feature Implementation Plan

## Overview
Implement email reply functionality using Composio's `GMAIL_REPLY_TO_THREAD` action, reusing existing draft system infrastructure.

## Decision Summary
- **Subject**: Read-only display with "Re: [original subject]" prefix
- **Recipients**: Auto-populate "To" with original sender, CC with original recipients
- **Thread Context**: Pass ALL email text content to LLM
- **UI Position**: Draft appears after all thread emails with divider, below last email

---

## Phase 1: Backend - Data Model & Storage

### Tasks:
- [x] **1.1** Add new fields to Draft model (`backend/models/draft.py`):
  - [x] `gmail_thread_id` (string, optional) - Gmail thread ID for replies
  - [x] `reply_to_email_id` (string, optional) - Email ID being replied to
  - [x] Ensure `cc_emails` and `bcc_emails` exist and are properly used

- [x] **1.2** Update Draft Service (`backend/services/draft_service.py`):
  - [x] Modify `create_draft()` to accept `gmail_thread_id` and `reply_to_email_id` in `initial_data`
  - [x] Update `convert_draft_to_composio_params()` to handle thread context for replies

---

## Phase 2: Backend - Reply Detection & Execution

### Tasks:
- [x] **2.1** Add reply method to Composio Service (`backend/services/composio_service.py`):
  - [x] Create `reply_to_thread()` method using `GMAIL_REPLY_TO_THREAD` action
  - [x] Handle parameters: thread_id, recipient_email, message_body, cc, bcc, extra_recipients

- [x] **2.2** Update Draft Send Endpoint (`backend/app.py` - `/drafts/<draft_id>/send`):
  - [x] Check if draft has `gmail_thread_id`
  - [x] If yes → call `reply_to_thread()`
  - [x] If no → use existing `send_email()` (current behavior)

- [x] **2.3** Modify Draft Creation Logic (`backend/app.py` - chat endpoint):
  - [x] Check if `anchored_item` exists and type is 'email'
  - [x] Extract `gmail_thread_id` from anchored email
  - [x] Pass email thread context to LLM for reply generation
  - [x] Auto-populate recipients (To: original sender, CC: original recipients)

---

## Phase 3: Frontend - UI Integration

### Tasks:
- [x] **3.1** Pass thread context to draft creation (`frontend/src/App.js`):
  - [x] When email is anchored, include `gmail_thread_id` in draft creation
  - [x] Pass anchored email data to backend via `anchored_item`
  - [x] Update draft validation to make subject optional for replies

- [x] **3.2** Update Email Sidebar UI (`frontend/src/components/ResizableEmailSidebar.js`):
  - [x] Show draft box after all thread emails with divider
  - [x] Reuse existing draft UI (bordered box with chip and Send button)
  - [x] Keep all email expand/collapse functionality intact
  - [x] Show subject as read-only for reply drafts
  - [x] Update chip text to "Reply Draft" / "Reply Sent" for replies

- [x] **3.3** Update Draft Tile (`frontend/src/components/SimplifiedDraftCard.js`):
  - [x] Show "Reply Draft" / "Reply Sent" text for reply drafts
  - [x] Detect reply via `gmail_thread_id` field

---

## Phase 4: Backend - LLM Prompt Enhancement

### Tasks:
- [ ] **4.1** Create thread context builder helper:
  - [ ] Format email thread for LLM (sender, date, subject, body text-only)
  - [ ] Include ALL emails in thread
  - [ ] Return formatted conversation history

- [ ] **4.2** Update Draft Detection Prompts (`backend/prompts.py`):
  - [ ] Modify `draft_information_extraction_prompt` to accept thread context
  - [ ] Instruct LLM to consider thread history when generating reply
  - [ ] Extract reply-specific information

---

## Phase 5: Integration & Polish

### Tasks:
- [x] **5.1** Update Draft Validation:
  - [x] For reply drafts (has `gmail_thread_id`), make subject optional
  - [x] Subject is inherited from thread by Gmail

- [x] **5.2** Frontend Visual Indicators:
  - [x] Draft tile shows "Reply to [Subject]" when it's a reply
  - [x] Sidebar chip shows "Reply Draft" or "Reply Sent" (green)
  - [x] Optional: Show small thread icon in draft tile

- [ ] **5.3** Testing & Edge Cases:
  - [ ] Test reply with single email vs multi-email thread
  - [ ] Test reply with CC/BCC
  - [ ] Test switching between new email and reply modes
  - [ ] Test thread context passing to LLM
  - [ ] Test subject display (read-only)
  - [ ] Test recipient auto-population

---

## Implementation Notes

### Draft Creation Flow (Reply):
```
1. User anchors email in thread
2. User types "reply to this email saying..."
3. Backend detects draft intent
4. Backend checks anchored_item → type='email', has gmail_thread_id
5. Backend fetches thread emails for context
6. Backend auto-populates: To=original_sender, CC=original_recipients
7. LLM generates reply with full thread context
8. Draft created with gmail_thread_id set
9. Frontend shows draft in thread after emails with divider
10. Subject shown as read-only "Re: [Original Subject]"
11. User clicks Send → Backend uses GMAIL_REPLY_TO_THREAD
```

### Draft Creation Flow (New Email - Existing):
```
1. No email anchored OR only draft anchored
2. User types "send email to..."
3. Backend detects draft intent
4. LLM generates email
5. Draft created without gmail_thread_id
6. Frontend shows draft tile
7. User clicks Send → Backend uses GMAIL_SEND_EMAIL (existing)
```

---

## Future Enhancements (Not in Current Scope)
- Allow LLM to modify recipients in reply drafts
- Thread context optimization (limit to last N emails)
- Forward functionality
- Draft templates for common replies