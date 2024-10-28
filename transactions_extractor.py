import pikepdf
import sys
from pypdf import PdfReader
import pandas as pd
import re
import argparse
import tempfile
import os

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
    
    return parser.parse_args()

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
        
        print("Successfully preprocessed PDF: ", output_path)
        return True
        
    except Exception as e:
        print(f"Error preprocessing PDF: {str(e)}")
        return False
    finally:
        if 'pdf' in locals():
            pdf.close()
        if 'new_pdf' in locals():
            new_pdf.close()

def extract_transactions_from_region(input_path, crop_box):
    """
    Extract transactions directly from specified region of PDF
    """
    try:
        reader = PdfReader(input_path)
        page = reader.pages[0]
        
        # Get page dimensions
        page_height = float(page.mediabox.height)
        
        # Apply crop box
        page.cropbox.lower_left = (crop_box[0], page_height - crop_box[3])
        page.cropbox.upper_right = (crop_box[2], page_height - crop_box[1])
        
        # Extract text from cropped region
        text = page.extract_text()
        
        # Split into lines
        lines = text.split('\n')
        
        # Initialize lists to store transaction data
        transactions = []
        
        # Regular expression to match transaction lines
        # SBI Bank pattern
        transaction_pattern = r'(\d{2} \w{3} \d{2}) (.*?) (\d{1,3}(?:,\d{3})*\.?\d{0,2}) ([CD])'
        # HDFC Bank pattern
        # transaction_pattern = r'(\d{2}/\d{2}/\d{4})\s+(.*?)\s+((?:\d{1,3}(?:,\d{3})*\.?\d{0,2})(?:\s*Cr)?)\s*$'
        for line in lines:
            # print(line)
            match = re.search(transaction_pattern, line)
            if match:
                date, description, amount, txn_type = match.groups()
                
                # Clean up amount - remove commas
                amount = float(amount.replace(',', ''))
                
                # Make amount negative for debits
                if txn_type == 'D':
                    amount = -amount
                
                transactions.append({
                    'Date': date,
                    'Description': description.strip(),
                    'Amount': amount,
                    'Type': txn_type
                })
        
        # Convert to DataFrame
        df = pd.DataFrame(transactions)
        
        if not df.empty:
            # Sort by date
            df['Date'] = pd.to_datetime(df['Date'], format='%d %b %y')
            df = df.sort_values('Date')
        
        return df
    
    except Exception as e:
        print(f"Error extracting transactions: {str(e)}")
        return pd.DataFrame()

def process_pdf(input_path, output_csv, password, crop_box):
    """
    Complete PDF processing pipeline
    """
    # Create temporary file
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
        tmp_path = tmp_file.name
        
        try:
            # Step 1: Preprocess (decrypt and sanitize)
            if not preprocess_pdf(input_path, tmp_path, password):
                print("Preprocessing failed, stopping.")
                return
            
            # Step 2: Extract transactions
            df = extract_transactions_from_region(tmp_path, crop_box)
            
            # Display and save results
            if not df.empty:
                print("\nExtracted Transactions:")
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

def main():
    # Parse command line arguments
    args = parse_arguments()
    
    # Process PDF
    process_pdf(
        input_path=args.input_pdf,
        output_csv=args.output,
        password=args.password,
        crop_box=args.cropbox
    )

if __name__ == "__main__":
    main()