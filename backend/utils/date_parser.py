from email.utils import parsedate_to_datetime
from datetime import datetime, timezone

# A date in the distant past for sorting fallback
MIN_DATE = datetime.min.replace(tzinfo=timezone.utc)

def parse_email_date(date_str: str) -> datetime:
    """
    Parses an email date string into a timezone-aware datetime object.
    
    Args:
        date_str: The date string from the email (e.g., "Tue, 24 Jun 2025 11:52:24 GMT" or Unix timestamp).

    Returns:
        A datetime object. Returns a minimum default date if parsing fails.
    """
    if not date_str:
        return MIN_DATE
    
    # Try parsing as Unix timestamp first (Composio format)
    try:
        # Check if it's a numeric timestamp (string or number)
        if isinstance(date_str, (int, float)) or (isinstance(date_str, str) and date_str.isdigit()):
            timestamp = float(date_str)
            # Handle both seconds and milliseconds timestamps
            if timestamp > 1e10:  # Milliseconds timestamp
                timestamp = timestamp / 1000
            dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            return dt
    except (ValueError, TypeError, OSError):
        pass
    
    # Try parsing as RFC 2822 format (standard email date)
    try:
        dt = parsedate_to_datetime(date_str)
        # If the datetime object is naive, assume it's UTC, which is common for email headers.
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    except (TypeError, ValueError):
        pass
    
    # Try parsing as ISO format
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        pass
    
    print(f"[WARNING] Could not parse date string '{date_str}': trying all formats failed")
    return MIN_DATE 