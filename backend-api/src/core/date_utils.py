"""
Date utility functions for formatting and parsing dates.
"""
from datetime import datetime
from typing import Union
from src.core.logging import get_logger

logger = get_logger(__name__)


def iso_to_short_date(date_input: Union[str, datetime], date_format: str = "%m/%d/%Y") -> str:
    """
    Convert ISO date string or datetime object to short date format.
    
    Args:
        date_input: ISO date string (e.g., "2025-01-27T14:30:00.000000") or datetime object
        date_format: Output format string (default: "%m/%d/%Y")
    
    Returns:
        Formatted date string (e.g., "01/27/2025")
        Returns original string if parsing fails
    
    Examples:
        >>> iso_to_short_date("2025-01-27T14:30:00.000000")
        "01/27/2025"
        >>> iso_to_short_date(datetime(2025, 1, 27))
        "01/27/2025"
        >>> iso_to_short_date("2025-01-27T14:30:00Z")
        "01/27/2025"
    """
    try:
        if isinstance(date_input, str):
            # Handle ISO string with 'Z' timezone indicator
            dt = datetime.fromisoformat(date_input.replace('Z', '+00:00'))
            return dt.strftime(date_format)
        elif isinstance(date_input, datetime):
            return date_input.strftime(date_format)
        else:
            logger.warning(f"Unexpected date type: {type(date_input)}")
            return str(date_input)
    except Exception as e:
        logger.warning(f"Could not parse date '{date_input}': {e}")
        return str(date_input)


def short_date_to_iso(date_string: str, date_format: str = "%m/%d/%Y") -> str:
    """
    Convert short date format to ISO date string.
    
    Args:
        date_string: Date string in specified format (e.g., "01/27/2025")
        date_format: Input format string (default: "%m/%d/%Y")
    
    Returns:
        ISO formatted date string (e.g., "2025-01-27T00:00:00")
        Returns original string if parsing fails
    
    Examples:
        >>> short_date_to_iso("01/27/2025")
        "2025-01-27T00:00:00"
        >>> short_date_to_iso("27/01/2025", "%d/%m/%Y")
        "2025-01-27T00:00:00"
    """
    try:
        dt = datetime.strptime(date_string, date_format)
        return dt.isoformat()
    except Exception as e:
        logger.warning(f"Could not parse date string '{date_string}': {e}")
        return date_string


def format_date(date_input: Union[str, datetime], output_format: str = "%m/%d/%Y") -> str:
    """
    General purpose date formatter that handles multiple input types.
    
    Args:
        date_input: ISO string, datetime object, or formatted date string
        output_format: Desired output format (default: "%m/%d/%Y")
    
    Returns:
        Formatted date string
    
    Examples:
        >>> format_date("2025-01-27T14:30:00", "%B %d, %Y")
        "January 27, 2025"
        >>> format_date(datetime(2025, 1, 27), "%Y-%m-%d")
        "2025-01-27"
    """
    return iso_to_short_date(date_input, output_format)
