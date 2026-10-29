"""
Document endpoints for PDF downloads.

Provides endpoints for generating and downloading PDF documents:
- Transaction receipts
- Tax receipts
- Other document types

Endpoints:
    GET /api/v1/documents/pdf/{document_type}/{transaction_id} - Download PDF document
"""

from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Literal

from src.config import settings
from src.core.dependencies import User, get_current_user_required
from src.core.donors_utils import get_donor_by_user_id
from src.core.logging import get_logger
from src.database import get_session
from src.database.models.transaction_header import TransactionHeader
from src.database.models.donors import Donors
from src.core.stored_procedure_utils import execute_stored_procedure

router = APIRouter(prefix="/documents", tags=["documents"])
logger = get_logger(__name__, level=settings.LOG_LEVEL)

# Supported document types
DocumentType = Literal["transaction-receipt", "tax-receipt", "donation-summary"]


@router.get(
    "/pdf/{company_id}/{document_type}/{transaction_id}",
    status_code=status.HTTP_200_OK,
    summary="Download PDF document",
    description="""
    Download a PDF document for an authenticated user.
    
    Supported document types:
    - transaction-receipt: Receipt for a specific donation transaction
    - tax-receipt: Tax receipt for a specific transaction or year
    - donation-summary: Summary of donations for a period
    
    Returns binary PDF data.
    """,
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "PDF document downloaded successfully",
        },
        403: {"description": "User does not have access to this document"},
        404: {"description": "Document not found"},
    },
)
async def download_pdf_document(
    company_id: int = Path(..., description="Company ID"),
    document_type: DocumentType = Path(..., description="Type of document to download"),
    transaction_id: int = Path(..., description="Transaction or document ID"),
    current_user: User = Depends(get_current_user_required),
    session: AsyncSession = Depends(get_session),    
) -> Response:
    """
    Download a PDF document for the authenticated user.
    
    Args:
        document_type: Type of document (transaction-receipt, tax-receipt, etc.)
        transaction_id: ID of the transaction or document
        current_user: Authenticated user
        session: Database session
        company_id: Company ID
        
    Returns:
        Response with PDF binary data
        
    Raises:
        HTTPException: If document not found or user doesn't have access
    """
    logger.info(
        f"User {current_user.id} requesting {document_type} PDF for transaction {transaction_id}"
    )
    
    try:
        # Find the donor record for the current user
        donor = await _get_donor_for_user(session, current_user)
        
        if not donor:
            logger.warning(f"No donor record found for user: {current_user.id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User does not have a donor account",
            )
        
        # Verify the transaction belongs to this donor
        if document_type in ["transaction-receipt", "tax-receipt"]:
            await _verify_transaction_access(session, document_type, transaction_id, donor.DonorId, company_id)
        
        # Generate PDF based on document type
        pdf_data = await _generate_pdf(
            session=session,
            document_type=document_type,
            transaction_id=transaction_id,
            donor_id=donor.DonorId,
            company_id=company_id,
        )
        
        # Determine filename based on document type
        filename = _get_pdf_filename(document_type, transaction_id)
        
        logger.info(f"Successfully generated {document_type} PDF for user {current_user.id}")
        
        # Return PDF as response
        return Response(
            content=pdf_data,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating PDF: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate PDF document",
        )


async def _get_donor_for_user(session: AsyncSession, user: User) -> Donors | None:
    """Get donor record for user."""
    return await get_donor_by_user_id(session, user.id)


async def _verify_transaction_access(
    session: AsyncSession,
    document_type: DocumentType,
    transaction_id: int,
    donor_id: int,
    company_id: int,
) -> None:
    """
    Verify that the donor has access to the transaction.
    
    Raises:
        HTTPException: If transaction not found or access denied
    """
    parameters = {
        "DataType": 1,            
        "CompanyId": company_id,
        "DonorId": donor_id,
        "TransactionId": transaction_id,
        "TaxYear": str(transaction_id) if document_type == "tax-receipt" else None,
    }

    if document_type == "tax-receipt":
        parameters["DataType"] = 11  # Different DataType for tax receipt

     # Remove None values
    parameters = {k: v for k, v in parameters.items() if v is not None}

    result = await execute_stored_procedure(
            session=session,
            procedure_name="[dbo].[UIQueryGetDocuments]",
            parameters=parameters,
            fetch_results=True,
            fetch_multiple=False
        )
    
    if not result or len(result) == 0:
        logger.warning(
            f"Transaction {transaction_id} not found or access denied for donor {donor_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found or you do not have access to this document",
        )


async def _generate_pdf(
    session: AsyncSession,
    document_type: DocumentType,
    transaction_id: int,
    donor_id: int,
    company_id: int,
) -> bytes:
    """
    Generate PDF document based on type.
    
    Args:
        session: Database session
        document_type: Type of document to generate
        transaction_id: Transaction or document ID
        donor: Donor record
        company_id: Company ID
        
    Returns:
        Binary PDF data
    """
    
    if document_type == "transaction-receipt":
        return await _generate_transaction_receipt_pdf(
            session, transaction_id,  donor_id, company_id
        )
    elif document_type == "tax-receipt":
        return await _generate_tax_receipt_pdf(session, transaction_id, donor_id, company_id)
    elif document_type == "donation-summary":
        return await _generate_donation_summary_pdf(session, transaction_id, donor_id, company_id)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported document type: {document_type}",
        )


async def _generate_transaction_receipt_pdf(
    session: AsyncSession,
    transaction_id: int,
    donor_id: int,
    company_id: int,
) -> bytes:
    """Generate transaction receipt PDF."""
    # Prepare parameters for stored procedure
    parameters = {
        "DataType": 2,            
        "CompanyId": company_id,
        "DonorId": donor_id,
        "TransactionId": transaction_id,
    }

     # Remove None values
    parameters = {k: v for k, v in parameters.items() if v is not None}

    result = await execute_stored_procedure(
            session=session,
            procedure_name="[dbo].[UIQueryGetDocuments]",
            parameters=parameters,
            fetch_results=True,
            fetch_multiple=False
        )

    if not result or len(result) == 0:
        logger.warning(
            f"Transaction {transaction_id} not found or access denied for donor {donor_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found or you do not have access to this document",
        )

    row: dict = result[0] # type: ignore    
    pdf_content: bytes = row.get("DocumentFileImage", b"")
    return pdf_content


async def _generate_tax_receipt_pdf(
    session: AsyncSession,
    transaction_id: int,
    donor_id: int,
    company_id: int,
) -> bytes:
    """Generate tax receipt PDF."""
    # Prepare parameters for stored procedure
    parameters = {
        "DataType": 12,            
        "CompanyId": company_id,
        "DonorId": donor_id,
        "TaxYear": str(transaction_id),
    }

     # Remove None values
    parameters = {k: v for k, v in parameters.items() if v is not None}

    result = await execute_stored_procedure(
            session=session,
            procedure_name="[dbo].[UIQueryGetDocuments]",
            parameters=parameters,
            fetch_results=True,
            fetch_multiple=False
        )

    if not result or len(result) == 0:
        logger.warning(
            f"Transaction {transaction_id} not found or access denied for donor {donor_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found or you do not have access to this document",
        )

    row: dict = result[0] # type: ignore    
    pdf_content: bytes = row.get("DocumentFileImage", b"")
    return pdf_content


async def _generate_donation_summary_pdf(
    session: AsyncSession,
    period_id: int,
    donor: Donors,
    company_id: int,
) -> bytes:
    """Generate donation summary PDF."""
    # TODO: Implement actual donation summary PDF generation
    pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    pdf_content += b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    pdf_content += b"3 0 obj\n<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> "
    pdf_content += b"/MediaBox [0 0 612 792] /Contents 5 0 R >>\nendobj\n"
    pdf_content += b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
    pdf_content += b"5 0 obj\n<< /Length 48 >>\nstream\nBT\n/F1 12 Tf\n100 700 Td\n"
    pdf_content += b"(Donation Summary) Tj\nET\nendstream\nendobj\n"
    pdf_content += b"xref\n0 6\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n"
    pdf_content += b"0000000115 00000 n\n0000000261 00000 n\n0000000339 00000 n\n"
    pdf_content += b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n445\n%%EOF"
    
    logger.info(f"Generated donation summary PDF for period {period_id}")
    return pdf_content


def _get_pdf_filename(document_type: DocumentType, transaction_id: int) -> str:
    """Generate appropriate filename for PDF."""
    if document_type == "transaction-receipt":
        return f"receipt_{transaction_id}.pdf"
    elif document_type == "tax-receipt":
        return f"tax_receipt_{transaction_id}.pdf"
    elif document_type == "donation-summary":
        return f"donation_summary_{transaction_id}.pdf"
    else:
        return f"document_{transaction_id}.pdf"
