# Gmail Classification Workflow Documentation

## Overview

This document describes the automated Gmail classification system built with n8n that processes incoming emails and categorizes them using AI. The workflow integrates with the Co-Pilot backend to store and manage classified emails.

## Workflow Architecture

### n8n Workflow: "Gmail Classification Workflow"
**Workflow ID:** `YMy28EC5W5a1MfhH`

The workflow consists of 5 sequential nodes that process incoming Gmail messages:

```
Gmail Trigger → Extract Email Data → Gemini Classification → Process Classification → Send to Backend
```

---

## Workflow Nodes Breakdown

### 1. Gmail Trigger
- **Type:** `n8n-nodes-base.gmailTrigger`
- **Purpose:** Monitors Gmail inbox for new incoming messages
- **Configuration:** 
  - Event: `messageReceived`
  - Filters: None (processes all incoming emails)

### 2. Extract Email Data (Code Node)
- **Purpose:** Processes raw Gmail API data into structured format
- **Key Functions:**
  - Extracts email headers (from, to, subject, date)
  - Decodes base64 email body content
  - Limits body text to 1000 characters (cost optimization)
  - Detects thread replies vs new conversations
  - Handles both simple and multipart email formats

**Output Structure:**
```javascript
{
  messageId: "gmail_message_id",
  threadId: "gmail_thread_id", 
  from: "sender@example.com",
  to: "recipient@example.com",
  subject: "Email Subject",
  date: "RFC2822_date_string",
  bodyText: "First 1000 chars of email body",
  snippet: "Gmail auto-generated snippet",
  isThreadReply: boolean, // true if part of existing conversation
  labelIds: ["INBOX", "UNREAD"]
}
```

### 3. Gemini Classification (AI Node)
- **Model:** `gemini-1.5-flash` (cost-optimized)
- **Temperature:** 0.1 (consistent classifications)
- **Max Tokens:** 200
- **Purpose:** Classifies emails into predefined categories

**Classification Categories:**

| Category | Description | Examples |
|----------|-------------|----------|
| **IMPORTANT** | Personal emails requiring response | Emails from known contacts, thread replies, urgent delivery notifications |
| **KNOWLEDGE** | Educational/Newsletter content | Business/tech/AI newsletters, educational content, industry updates |
| **TRANSACTIONAL** | Automated notifications | Order confirmations, status updates, receipts, account notifications |
| **OTHER** | Unclassified emails | Spam, promotional emails, unclear categorization |

**Prompt Structure:**
The AI receives structured email data and returns JSON classification with:
- Category (one of the 4 above)
- Confidence score (0.0 to 1.0)
- Reasoning (brief explanation)

### 4. Process Classification (Code Node)
- **Purpose:** Validates AI response and applies business rules
- **Key Functions:**
  - Parses Gemini JSON response
  - Applies 90% confidence threshold
  - Moves low-confidence classifications to "OTHER"
  - Combines email data with classification results
  - Adds processing timestamp

**Confidence Threshold Logic:**
```javascript
if (classification.confidence < 0.9) {
  classification.category = 'OTHER';
  classification.reasoning += ' (Low confidence, moved to OTHER)';
}
```

### 5. Send to Co-Pilot Backend (HTTP Request)
- **Method:** POST
- **Endpoint:** `http://localhost:5000/api/emails/classify`
- **Content-Type:** application/json
- **Retry Logic:** 3 attempts with 1-second delays
- **Timeout:** 10 seconds

---

## API Integration

### Expected Backend Endpoint
```
POST /api/emails/classify
Content-Type: application/json
```

### Request Payload Schema

The workflow sends the following JSON structure to the backend:

```json
{
  "email": {
    "messageId": "string",        // Gmail message ID (unique)
    "threadId": "string",         // Gmail thread ID (groups related emails)
    "from": "string",             // Sender email address
    "to": "string",               // Recipient email address  
    "subject": "string",          // Email subject line
    "date": "string",             // RFC2822 formatted date
    "snippet": "string",          // Gmail auto-generated preview text
    "isThreadReply": boolean      // True if email is part of existing conversation
  },
  "classification": {
    "category": "string",         // One of: IMPORTANT, KNOWLEDGE, TRANSACTIONAL, OTHER
    "confidence": number,         // Float between 0.0 and 1.0 (≥0.9 for non-OTHER)
    "reasoning": "string",        // AI explanation for classification
    "processedAt": "string"       // ISO 8601 timestamp of processing
  }
}
```

### Sample Payloads

#### Important Email (Thread Reply)
```json
{
  "email": {
    "messageId": "18d4c2f1a3b2e5f7",
    "threadId": "18d4c2f1a3b2e5f7",
    "from": "john.doe@company.com",
    "to": "michal.fiech@gmail.com",
    "subject": "Re: Q4 Planning Meeting",
    "date": "Fri, 11 Jan 2025 10:30:00 +0000",
    "snippet": "Thanks for sending the agenda. I have a few questions about...",
    "isThreadReply": true
  },
  "classification": {
    "category": "IMPORTANT",
    "confidence": 0.95,
    "reasoning": "Email is part of ongoing thread conversation requiring response",
    "processedAt": "2025-01-11T10:31:15.234Z"
  }
}
```

#### Knowledge Newsletter
```json
{
  "email": {
    "messageId": "19a5b3c2d4e6f8g0",
    "threadId": "19a5b3c2d4e6f8g0", 
    "from": "newsletter@techcrunch.com",
    "to": "michal.fiech@gmail.com",
    "subject": "Weekly AI & Startup Roundup",
    "date": "Fri, 11 Jan 2025 08:00:00 +0000",
    "snippet": "This week in AI: OpenAI releases new model, startup funding hits record...",
    "isThreadReply": false
  },
  "classification": {
    "category": "KNOWLEDGE", 
    "confidence": 0.92,
    "reasoning": "Newsletter containing business and AI industry content",
    "processedAt": "2025-01-11T08:01:20.456Z"
  }
}
```

#### Transactional Email
```json
{
  "email": {
    "messageId": "20b6c4d5e7f9g1h2",
    "threadId": "20b6c4d5e7f9g1h2",
    "from": "orders@amazon.com", 
    "to": "michal.fiech@gmail.com",
    "subject": "Your order has been shipped",
    "date": "Thu, 10 Jan 2025 16:45:00 +0000",
    "snippet": "Your order #123-456789 has been shipped and will arrive on Jan 12...",
    "isThreadReply": false
  },
  "classification": {
    "category": "TRANSACTIONAL",
    "confidence": 0.98,
    "reasoning": "Order shipment notification from e-commerce platform",
    "processedAt": "2025-01-10T16:46:03.789Z"
  }
}
```

#### Low Confidence (Moved to OTHER)
```json
{
  "email": {
    "messageId": "21c7d6e8f0g2h3i4",
    "threadId": "21c7d6e8f0g2h3i4",
    "from": "marketing@somecompany.com",
    "to": "michal.fiech@gmail.com", 
    "subject": "Special Offer Just for You!",
    "date": "Thu, 10 Jan 2025 14:20:00 +0000",
    "snippet": "Don't miss out on our limited time offer...",
    "isThreadReply": false
  },
  "classification": {
    "category": "OTHER",
    "confidence": 0.75,
    "reasoning": "Promotional email content unclear (Low confidence, moved to OTHER)",
    "processedAt": "2025-01-10T14:21:08.123Z"
  }
}
```

---

## Backend Implementation Requirements

### 1. Database Schema
The backend should store classified emails with:
- Email metadata (messageId, threadId, from, to, subject, date, snippet)
- Classification data (category, confidence, reasoning, processedAt)
- Processing status and timestamps
- User association (for multi-user support)

### 2. API Endpoint Requirements
- **Authentication:** Validate requests (API key or webhook signature)
- **Deduplication:** Handle duplicate messageIds gracefully
- **Validation:** Ensure required fields are present
- **Error Handling:** Return appropriate HTTP status codes
- **Logging:** Track processing for debugging

### 3. Suggested Response Format
```json
{
  "success": true,
  "messageId": "18d4c2f1a3b2e5f7",
  "status": "processed",
  "timestamp": "2025-01-11T10:31:15.500Z"
}
```

---

## Workflow Configuration

### Prerequisites
1. **Gmail API Access:** Configure Gmail OAuth credentials in n8n
2. **Google Cloud:** Set up Gemini API access with billing enabled
3. **Backend Endpoint:** Implement `/api/emails/classify` endpoint
4. **Network Access:** Ensure n8n can reach backend (localhost:5000)

### Activation Steps
1. Configure Gmail credentials in n8n workflow
2. Test Gemini API connection
3. Verify backend endpoint is running
4. Activate the workflow in n8n interface
5. Monitor initial test emails

### Cost Optimization
- **Email Content Limit:** 1000 characters max body text
- **Efficient Model:** Using gemini-1.5-flash (cheaper than GPT models)
- **Single API Call:** One classification per email
- **Confidence Threshold:** Reduces uncertain API calls

### Monitoring & Debugging
- **n8n Execution History:** View workflow runs and errors
- **Backend Logs:** Monitor API endpoint requests
- **Classification Accuracy:** Track confidence scores and categories
- **Cost Tracking:** Monitor Gemini API usage

---

## Future Enhancements

### Phase 2 Considerations
1. **Real-time Notifications:** Push important emails to frontend
2. **Learning System:** Incorporate user feedback for classification improvement
3. **Batch Processing:** Handle email backlogs efficiently
4. **Advanced Rules:** Custom classification rules per user
5. **Analytics Dashboard:** Classification accuracy and email volume metrics

### Security Considerations
1. **API Authentication:** Secure the classification endpoint
2. **Data Privacy:** Email content handling and storage policies
3. **Rate Limiting:** Prevent abuse of classification API
4. **Webhook Validation:** Verify requests from n8n workflow 