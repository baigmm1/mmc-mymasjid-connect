from src.models.company import CompanyModel
from src.models.donors import DonorsModel
from src.models.transaction import TransactionModel
from src.core.logging import get_logger
from src.core.date_utils import iso_to_short_date
from src.config import settings

logger = get_logger(__name__)



async def create_receipt_html(company: CompanyModel, transaction: TransactionModel) -> str | None:
    """
    Use the HTML template for Donation Receipt or Service and generate the email content.

    Templates are stored under data/templates/<companyid>/donation_receipt.html or service_receipt.html
    """
    
    try:
        template_type = "donation_receipt" if transaction.PurposeId == 1 else "service_receipt"
        template_path = f"{settings.EMAIL_TEMPLATE_PATH}/{company.CompanyId}/{template_type}.html"
        
        with open(template_path, 'r', encoding='utf-8') as file:
            template_content = file.read()
        
        if template_content:
            logger.info(f"Loaded email template from {template_path}")

            # Replace placeholders in the template
            if transaction.DonorDetails:
                donor = transaction.DonorDetails

                if donor.NamePrefix:
                    namewithPrefix = donor.NamePrefix + " " + (donor.CompleteName or "Valued Donor")
                else:
                    namewithPrefix = donor.CompleteName or "Valued Donor"
                address = donor.AddressLine1 or ""
                if donor.AddressLine2:
                    address += "<br />" + donor.AddressLine2
                address += f"<br />{donor.City}, {donor.State} {donor.PostalCode}"

            # Convert ISO date string to short date format (MM/DD/YYYY)
            transaction_date = iso_to_short_date(transaction.TransactionDate)
            
            #print(template_content)
            if transaction.DonorId:
                donor_id_str = str(donor.DonorId)
            else:
                donor_id_str = "N/A"
            html_content = template_content.replace("{{DonorFullName}}", donor.CompleteName or "Valued Donor")
            html_content = html_content.replace("{{ReceiptId}}", str(transaction.TransactionId))
            html_content = html_content.replace("{{TransactionDate}}", transaction_date)
            html_content = html_content.replace("{{DonorAddress}}", address)
            html_content = html_content.replace("{{NamewithPrefix}}", namewithPrefix)

            html_content = html_content.replace("{{TotalAmount}}", f"${transaction.TotalAmount:.2f}")
            html_content = html_content.replace("{{DonorID}}", donor_id_str)
            html_content = html_content.replace("{{TreasurerEMail}}", settings.SENDGRID_FROM_EMAIL or "")
            html_content = html_content.replace("{{TreasurerName}}", settings.SENDGRID_FROM_NAME or "")   

            # update the transaction details
            table_rows = ""
            if transaction.Details:
                for detail in transaction.Details:
                    table_rows += f"""
                    <tr>
                        <td style="border: 1px solid #dddddd; text-align: left; padding: 8px;">{detail.Description}</td>
                        <td style="border: 1px solid #dddddd; text-align: right; padding: 8px;">${detail.Amount:.2f}</td>
                    </tr>
                    """

            html_content = html_content.replace("<!--{DONATIONDETAILS}-->", table_rows)

            # Return the populated HTML content
            return html_content
        else:
            logger.error(f"Template content is empty for {template_path}")
            return None
    except Exception as e:
        logger.error(f"Error creating html content: {e}", exc_info=True)
        return None