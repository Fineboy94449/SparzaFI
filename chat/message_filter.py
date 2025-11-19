"""
Message Content Filter for SparzaFI Chat
Blocks phone numbers, email addresses, and URLs to ensure platform safety
"""

import re


class MessageFilter:
    """Filter messages for prohibited content"""

    # Regex patterns for blocked content
    PHONE_PATTERNS = [
        r'\+?\d{10,}',  # Any sequence of 10+ digits (with optional +)
        r'\+27\s?\d{9}',  # South African numbers (+27)
        r'0\d{9}',  # South African mobile (0xx xxx xxxx)
        r'\d{3}[-.\s]?\d{3}[-.\s]?\d{4}',  # xxx-xxx-xxxx format
        r'\(\d{3}\)\s?\d{3}[-.\s]?\d{4}',  # (xxx) xxx-xxxx format
    ]

    EMAIL_PATTERNS = [
        r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',  # email@domain.com
        r'\w+\s*@\s*\w+\s*\.\s*\w+',  # email @ domain . com (with spaces)
    ]

    URL_PATTERNS = [
        r'https?://[^\s]+',  # http:// or https://
        r'www\.[^\s]+',  # www.
        r'\w+\.\w{2,}\/[^\s]*',  # domain.com/path
    ]

    SOCIAL_MEDIA_PATTERNS = [
        r'@[a-zA-Z0-9_]+',  # @username (Twitter/Instagram handles)
        r'facebook\.com/[^\s]+',
        r'instagram\.com/[^\s]+',
        r'whatsapp\.me/[^\s]+',
        r'wa\.me/[^\s]+',
        r'telegram\.me/[^\s]+',
        r't\.me/[^\s]+',
    ]

    @classmethod
    def is_safe(cls, message: str) -> tuple[bool, str]:
        """
        Check if message is safe (doesn't contain prohibited content)

        Args:
            message: The message text to check

        Returns:
            tuple: (is_safe: bool, reason: str)
        """
        if not message or not message.strip():
            return False, "Message cannot be empty"

        # Check for phone numbers
        for pattern in cls.PHONE_PATTERNS:
            if re.search(pattern, message):
                return False, "Phone numbers are not allowed. Please use the platform's messaging system only."

        # Check for emails
        for pattern in cls.EMAIL_PATTERNS:
            if re.search(pattern, message):
                return False, "Email addresses are not allowed. Please use the platform's messaging system only."

        # Check for URLs
        for pattern in cls.URL_PATTERNS:
            if re.search(pattern, message):
                return False, "Links are not allowed for security reasons."

        # Check for social media handles
        for pattern in cls.SOCIAL_MEDIA_PATTERNS:
            if re.search(pattern, message):
                return False, "Social media links/handles are not allowed."

        # Message is safe
        return True, ""

    @classmethod
    def sanitize(cls, message: str) -> str:
        """
        Remove/replace prohibited content from message
        (Alternative to blocking - can be used for auto-sanitization)

        Args:
            message: The message text to sanitize

        Returns:
            Sanitized message
        """
        sanitized = message

        # Replace phone numbers
        for pattern in cls.PHONE_PATTERNS:
            sanitized = re.sub(pattern, '[PHONE NUMBER REMOVED]', sanitized)

        # Replace emails
        for pattern in cls.EMAIL_PATTERNS:
            sanitized = re.sub(pattern, '[EMAIL REMOVED]', sanitized)

        # Replace URLs
        for pattern in cls.URL_PATTERNS:
            sanitized = re.sub(pattern, '[LINK REMOVED]', sanitized)

        # Replace social media
        for pattern in cls.SOCIAL_MEDIA_PATTERNS:
            sanitized = re.sub(pattern, '[SOCIAL MEDIA REMOVED]', sanitized)

        return sanitized

    @classmethod
    def validate_message_length(cls, message: str, min_length: int = 1, max_length: int = 1000) -> tuple[bool, str]:
        """
        Validate message length

        Args:
            message: The message text
            min_length: Minimum allowed length
            max_length: Maximum allowed length

        Returns:
            tuple: (is_valid: bool, reason: str)
        """
        if len(message) < min_length:
            return False, f"Message must be at least {min_length} character(s)"

        if len(message) > max_length:
            return False, f"Message cannot exceed {max_length} characters"

        return True, ""


# Helper functions for easy import
def is_message_safe(message: str) -> tuple[bool, str]:
    """Quick check if message is safe"""
    return MessageFilter.is_safe(message)


def sanitize_message(message: str) -> str:
    """Quick sanitize message"""
    return MessageFilter.sanitize(message)


def validate_message(message: str) -> tuple[bool, str]:
    """
    Complete message validation (safety + length)

    Returns:
        tuple: (is_valid: bool, error_message: str)
    """
    # Check length
    is_valid, reason = MessageFilter.validate_message_length(message)
    if not is_valid:
        return False, reason

    # Check safety
    is_safe, reason = MessageFilter.is_safe(message)
    if not is_safe:
        return False, reason

    return True, ""
