from email.utils import parsedate_to_datetime
from datetime import datetime, timezone

# A date in the distant past for sorting fallback
MIN_DATE = datetime.min.replace(tzinfo=timezone.utc)

def parse_email_date(date_str: str) -> datetime:
    """
    Parses an email date string into a timezone-aware datetime object.
    
    Args:
        date_str: The date string from the email (e.g., "Tue, 24 Jun 2025 11:52:24 GMT").

    Returns:
        A datetime object. Returns a minimum default date if parsing fails.
    """
    if not date_str:
        return MIN_DATE
    try:
        # parsedate_to_datetime handles various email date formats
        dt = parsedate_to_datetime(date_str)
        # If the datetime object is naive, assume it's UTC, which is common for email headers.
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    except (TypeError, ValueError) as e:
        print(f"[WARNING] Could not parse date string '{date_str}': {e}")
        return MIN_DATE 