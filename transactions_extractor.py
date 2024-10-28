import pikepdf
import sys
from dataclasses import dataclass
from typing import Optional
from pypdf import PdfReader
import pandas as pd
import re
import argparse
import tempfile
import os

@dataclass
class BankPattern:
    """Bank specific patterns and formats"""
    name: str
    pattern: str
    date_format: str
    date_out_format: str = '%d %b %y'  # Standard output format
    credit_identifier: str = 'C'
    debit_identifier: str = 'D'
    amount_group: int = 3
    date_group: int = 1
    desc_group: int = 2
    type_group: Optional[int] = 4  # None if type is determined by credit_suffix
    credit_suffix: Optional[str] = None  # e.g., 'Cr' for HDFC

# Predefined bank patterns
BANK_PATTERNS = {
    'sbi': BankPattern(
        name='SBI',
        pattern=r'(\d{2} \w{3} \d{2}) (.*?) (\d{1,3}(?:,\d{3})*\.?\d{0,2}) ([CD])',
        date_format='%d %b %y'
    ),
    'hdfc': BankPattern(
        name='HDFC',
        pattern=r'(\d{2}/\d{2}/\d{4})\s+(.*?)\s+((?:\d{1,3}(?:,\d{3})*\.?\d{0,2})(?:\s*Cr)?)\s*$',
        date_format='%d/%m/%Y',
        credit_suffix='Cr',
        type_group=None
    )
}

def parse_cropbox(cropbox_str):
    """
    Parse cropbox string into tuple of integers
    Args:
        cropbox_str (str): Comma-separated string of coordinates
    Returns:
        tuple: (x0, top, x1, bottom)
    """
    try:
        coords = [int(x.strip()) for x in cropbox_str.split(',')]
        if len(coords) != 4:
            raise ValueError("Cropbox must have exactly 4 values")
        return tuple(coords)
    except ValueError as e:
        raise argparse.ArgumentTypeError(f"Invalid cropbox format: {str(e)}")

def parse_arguments():
    """
    Parse command line arguments
    """
    parser = argparse.ArgumentParser(
        description='Extract transactions from bank statement PDF',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s input.pdf
  %(prog)s --password=123456 input.pdf
  %(prog)s --cropbox "10,422,430,675" input.pdf
  %(prog)s --output transactions.csv input.pdf
  %(prog)s --bank hdfc input.pdf
        '''
    )
    parser.add_argument('input_pdf', 
                       help='Input PDF file')
    parser.add_argument('--password', 
                       help='PDF password',
                       default=None)
    parser.add_argument('--cropbox', 
                       type=parse_cropbox,
                       help='Cropbox coordinates as "x0,top,x1,bottom"',
                       default=(10, 422, 430, 675))
    parser.add_argument('--output', '-o',
                       help='Output CSV file (default: transactions.csv)',
                       default='transactions.csv')
    parser.add_argument('--bank',
                       choices=['sbi', 'hdfc'],
                       help='Force bank type (override auto-detection)')
    
    return parser.parse_args()

def identify_bank(pdf_path, password=None):
    """
    Identify bank from PDF content
    Args:
        pdf_path (str): Path to PDF file
        password (str): PDF password if encrypted
    Returns:
        str: Bank identifier ('hdfc', 'sbi', or None)
    """
    try:
        reader = PdfReader(pdf_path, password=password)
        text = reader.pages[0].extract_text()
        
        # Define bank identifiers
        bank_identifiers = {
            'hdfc': 'HDFC Bank Credit Cards GSTIN',
            'sbi': 'GSTIN of SBI Card'
        }
        
        # Check for each bank's identifier
        for bank_id, identifier in bank_identifiers.items():
            if identifier in text:
                print(f"Detected {bank_id.upper()} Bank statement")
                return bank_id
        
        print("Warning: Could not identify bank type from statement content")
        return None
        
    except Exception as e:
        print(f"Error identifying bank: {str(e)}")
        return None

def preprocess_pdf(input_path, output_path, password=None):
    """
    Preprocess PDF: decrypt, keep first page, uncompress streams and remove restrictions
    """
    try:
        # Open PDF with password if provided
        pdf = pikepdf.open(input_path, password=password)
        
        # Create new PDF with just the first page
        new_pdf = pikepdf.Pdf.new()
        new_pdf.pages.append(pdf.pages[0])
        
        # Save with uncompressed streams and no encryption
        new_pdf.save(output_path, 
                    compress_streams=False,
                    object_stream_mode=pikepdf.ObjectStreamMode.disable,
                    encryption=False)
        
        print("Successfully preprocessed PDF")
        return True
        
    except Exception as e:
        print(f"Error preprocessing PDF: {str(e)}")
        return False
    finally:
        if 'pdf' in locals():
            pdf.close()
        if 'new_pdf' in locals():
            new_pdf.close()

def extract_transactions_from_region(input_path, crop_box, bank_pattern='sbi'):
    """
    Extract transactions directly from specified region of PDF
    """
    try:
        # Get bank pattern
        if isinstance(bank_pattern, str):
            pattern = BANK_PATTERNS.get(bank_pattern.lower())
            if not pattern:
                raise ValueError(f"Unknown bank pattern: {bank_pattern}")
        elif isinstance(bank_pattern, BankPattern):
            pattern = bank_pattern
        else:
            raise ValueError("bank_pattern must be string key or BankPattern object")

        # Read and crop PDF
        reader = PdfReader(input_path)
        page = reader.pages[0]
        page_height = float(page.mediabox.height)
        page.cropbox.lower_left = (crop_box[0], page_height - crop_box[3])
        page.cropbox.upper_right = (crop_box[2], page_height - crop_box[1])
        
        # Extract and process text
        text = page.extract_text()
        lines = text.split('\n')
        transactions = []
        
        print(f"\nProcessing {len(lines)} lines...")
        
        for i, line in enumerate(lines):
            try:
                match = re.search(pattern.pattern, line)
                if match:
                    groups = match.groups()
                    
                    # Debug print
                    print(f"\nMatched line {i+1}: {line}")
                    print(f"Groups: {groups}")
                    
                    # Validate all required groups are present
                    if any(g is None for g in groups):
                        print(f"Warning: Missing data in line {i+1}: {groups}")
                        continue
                    
                    # Extract date and convert format if needed
                    date_str = groups[pattern.date_group - 1]
                    date_obj = pd.to_datetime(date_str, format=pattern.date_format)
                    std_date = date_obj.strftime(pattern.date_out_format)
                    
                    # Extract description
                    description = groups[pattern.desc_group - 1].strip()
                    
                    # Extract and process amount
                    amount_str = groups[pattern.amount_group - 1]
                    if amount_str is None:
                        print(f"Warning: No amount found in line {i+1}")
                        continue
                        
                    # Clean amount string
                    amount_str = amount_str.replace(',', '')
                    if pattern.credit_suffix:
                        amount_str = amount_str.replace(pattern.credit_suffix, '')
                    amount_str = amount_str.strip()
                    
                    try:
                        amount = float(amount_str)
                    except ValueError:
                        print(f"Warning: Invalid amount format in line {i+1}: {amount_str}")
                        continue
                    
                    # Determine transaction type
                    if pattern.type_group:
                        # Type is explicitly specified (e.g., SBI's C/D)
                        txn_type = groups[pattern.type_group - 1]
                        is_credit = txn_type == pattern.credit_identifier
                    else:
                        # Type is determined by suffix (e.g., HDFC's Cr)
                        is_credit = pattern.credit_suffix and pattern.credit_suffix in groups[pattern.amount_group - 1]
                    
                    # Make amount negative for debits
                    if not is_credit:
                        amount = -amount
                    
                    transactions.append({
                        'Date': std_date,
                        'Description': description,
                        'Amount': amount,
                        'Type': pattern.credit_identifier if is_credit else pattern.debit_identifier
                    })
                    print(f"Successfully processed transaction: {std_date} - {description} - {amount}")
                    
            except Exception as e:
                print(f"Warning: Error processing line {i+1}: {str(e)}")
                continue
        
        print(f"\nFound {len(transactions)} valid transactions")
        
        # Convert to DataFrame and sort
        df = pd.DataFrame(transactions)
        if not df.empty:
            df['Date'] = pd.to_datetime(df['Date'], format=pattern.date_out_format)
            df = df.sort_values('Date')
        
        return df
    
    except Exception as e:
        print(f"Error extracting transactions: {str(e)}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()

def process_pdf(input_path, output_csv, password, crop_box, bank=None):
    """
    Complete PDF processing pipeline with bank auto-detection
    """
    # Create temporary file
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
        tmp_path = tmp_file.name
        
        try:
            # Step 1: Preprocess (decrypt and sanitize)
            if not preprocess_pdf(input_path, tmp_path, password):
                print("Preprocessing failed, stopping.")
                return
            
            # Step 2: Identify bank type if not specified
            if not bank:
                bank = identify_bank(tmp_path)
                if not bank:
                    print("Could not identify bank type. Please specify using --bank option.")
                    return
            
            # Step 3: Extract transactions using identified pattern
            df = extract_transactions_from_region(tmp_path, crop_box, bank)
            
            # Display and save results
            if not df.empty:
                print(f"\nExtracted {len(df)} transactions:")
                print(df)
                
                df.to_csv(output_csv, index=False)
                print(f"\nSaved transactions to {output_csv}")
            else:
                print("No transactions found in the PDF")
                
        except Exception as e:
            print(f"Error processing PDF: {str(e)}")
        finally:
            # Clean up temporary file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
                print("Cleaned up temporary files")

def main():
    # Parse command line arguments
    args = parse_arguments()
    
    # Process PDF
    process_pdf(
        input_path=args.input_pdf,
        output_csv=args.output,
        password=args.password,
        crop_box=args.cropbox,
        bank=args.bank
    )

if __name__ == "__main__":
    main()