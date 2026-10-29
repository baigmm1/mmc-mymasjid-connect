"""
Utility functions for payment processing.

Provides helper functions for payment descriptions, formatting, and validation.
"""

from enum import IntEnum
from typing import Optional

from src.core.logging import get_logger
from src.models.transaction import TransactionModel

logger = get_logger(__name__)


class PurposeTypeConstants(IntEnum):
    """Purpose type constants for transactions."""
    DONATE = 1
    SERVICE = 2
    OTHER = 3


def get_payment_description(company_short_name: str, purpose: int) -> str:
    """
    Generate a payment statement descriptor for credit card statements.
    
    Creates a formatted descriptor that appears on customer credit card statements
    to identify the transaction. The descriptor follows payment processor requirements:
    - Company name/DBA section: 7 characters (padded with spaces if shorter, trimmed if longer)
    - Separator: * (asterisk)
    - Product descriptor: varies by purpose type
    - Maximum total length: 22 characters
    
    Args:
        company_short_name: Company short name or DBA to appear on statement
        purpose: Purpose type constant (1=Donate, 2=Service, 3=Other)
        
    Returns:
        Formatted statement descriptor string (max 22 characters)
        
    Example:
        >>> get_payment_description("ACME", PurposeTypeConstants.DONATE)
        'ACME   *Donation'
        
        >>> get_payment_description("Very Long Company Name", PurposeTypeConstants.SERVICE)
        'Very Lo*Payment'
        
        >>> get_payment_description("ABC", PurposeTypeConstants.OTHER)
        'ABC    *Online Transactio'
    """
    # Process company short name - pad or trim to 7 characters
    if len(company_short_name) <= 7:
        descriptor_value = company_short_name.ljust(7)[:7]
    else:
        descriptor_value = company_short_name[:7]
    
    # Append purpose-specific suffix
    if purpose == PurposeTypeConstants.DONATE:
        descriptor_value = descriptor_value + "*Donation"
    elif purpose == PurposeTypeConstants.SERVICE:
        descriptor_value = descriptor_value + "*Payment"
    else:
        descriptor_value = descriptor_value + "*Online Transaction"
    
    # Ensure maximum length of 22 characters
    if len(descriptor_value) > 22:
        descriptor_value = descriptor_value[:22]
    
    logger.debug(
        f"Generated payment descriptor: {descriptor_value}",
        extra={"company": company_short_name, "purpose": purpose}
    )
    
    return descriptor_value

def get_transaction_description(transaction : TransactionModel) -> str:
    """
    Generate a transaction description for payment intents.
    
    Creates a description that provides context about the transaction, which can be useful
    for both customers and merchants when reviewing transactions. The description includes
    the company name and the purpose of the transaction.
    
    Args:
        company_short_name: Company short name or DBA to include in description
        transaction: Transaction object containing details about the transaction        
    Returns:
        Formatted transaction description string
    Example:
        >>> get_transaction_description("ACME", transaction_object) 
        'ACME - Donation for Ramadan Food Drive'    
    """

    # get the first record of detail if present
    detail = transaction.Details[0] if transaction.Details else None

    if transaction.PurposeId == PurposeTypeConstants.DONATE:
        purpose_desc = "Donation"
    elif transaction.PurposeId == PurposeTypeConstants.SERVICE:
        purpose_desc = "Payment for Service"
    else:
        purpose_desc = "Online Transaction"
    
    detail_desc = f"{detail.Description}" if detail and detail.Description else "NA"
    if transaction.Recurring:
        if transaction.RecurringFrequency == 1:
            detail_desc += " (Monthly)"
        elif transaction.RecurringFrequency == 2:
            detail_desc += " (Annually)"
        elif transaction.RecurringFrequency == 3:
            detail_desc += " (Daily)"
        elif transaction.RecurringFrequency == 4:
            detail_desc += " (Weekly)"
            
    description = f"{purpose_desc}: {detail_desc}"
    
    logger.debug(
        f"Generated transaction description: {description}",
        extra={"company": transaction.CompanyId, "transaction_id": transaction.TransactionId}
    )
    
    return description

def get_statement_descriptor_suffix(transaction : TransactionModel) -> str:
    """
    Generate a statement descriptor suffix for credit card statements.
    
    Creates a formatted suffix that appears on customer credit card statements
    to identify the transaction. The suffix follows payment processor requirements:
    - Maximum length: 22 characters
    
    Args:
        company_short_name: Company short name or DBA to appear on statement
        purpose: Purpose type constant (1=Donate, 2=Service, 3=Other)
    Returns:
        Formatted statement descriptor suffix string
    """
    detail = transaction.Details[0] if transaction.Details else None
    detail_desc = f"{detail.Description}" if detail and detail.Description else "NA"

    descriptor_value = f"{detail_desc}"
    if len(descriptor_value) > 22:
        descriptor_value = descriptor_value[:22]

    return descriptor_value 