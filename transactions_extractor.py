import pikepdf
import sys
from dataclasses import dataclass
from typing import Optional, List
from pypdf import PdfReader
import pandas as pd
import re
import argparse
import tempfile
import os
import json
from pathlib import Path

@dataclass
class BankPattern:
    """Bank specific patterns and formats"""
    name: str
    regex: str
    date_format: str
    date_out_format: str = '%d %b %y'
    credit_identifier: str = 'C'
    debit_identifier: str = 'D'
    amount_group: int = 3
    date_group: int = 1
    desc_group: int = 2
    type_group: Optional[int] = None
    credit_suffix: Optional[str] = None

@dataclass
class BankProfile:
    """Complete bank profile including pattern and cropbox"""
    name: str
    identifier: str
    crop_box: List[int]
    pattern: BankPattern

def load_bank_profiles(profile_path='profiles.json'):
    """
    Load bank profiles from JSON configuration
    """
    try:
        if not os.path.exists(profile_path):
            print(f"Error: Bank profiles file '{profile_path}' not found.")
            print("Please create profiles.json in the current directory.")
            sys.exit(1)
            
        with open(profile_path, 'r') as f:
            config = json.load(f)
        
        profiles = {}
        for bank_id, profile in config.items():
            pattern = BankPattern(
                name=profile['name'],
                regex=profile['pattern']['regex'],
                date_format=profile['pattern']['date_format'],
                date_group=profile['pattern']['date_group'],
                desc_group=profile['pattern']['desc_group'],
                amount_group=profile['pattern']['amount_group'],
                type_group=profile['pattern']['type_group'],
                credit_identifier=profile['pattern']['credit_identifier'],
                debit_identifier=profile['pattern']['debit_identifier'],
                credit_suffix=profile['pattern']['credit_suffix']
            )
            
            profiles[bank_id] = BankProfile(
                name=profile['name'],
                identifier=profile['identifier'],
                crop_box=profile['crop_box'],
                pattern=pattern
            )
        
        return profiles
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in bank profiles file: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"Error loading bank profiles: {str(e)}")
        sys.exit(1)

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Extract transactions from bank statement PDF',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s --password=123456 input.pdf
  %(prog)s --output transactions.csv --password=123456 input.pdf
        '''
    )
    parser.add_argument('input_pdf', help='Input PDF file')
    parser.add_argument('--password', required=True, help='PDF password')
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
        
        return True
        
    except Exception as e:
        print(f"Error preprocessing PDF: {str(e)}")
        return False
    finally:
        if 'pdf' in locals():
            pdf.close()
        if 'new_pdf' in locals():
            new_pdf.close()

def identify_bank(pdf_path, profiles, password=None):
    """Identify bank from PDF content using profiles"""
    try:
        reader = PdfReader(pdf_path, password=password)
        text = reader.pages[0].extract_text()
        
        for bank_id, profile in profiles.items():
            if profile.identifier in text:
                print(f"\nDetected {profile.name} Bank statement")
                return profile
        
        print("\nError: Unsupported bank statement format")
        print("This PDF doesn't match any supported bank profile")
        print("Please verify profiles.json contains the correct identifier")
        return None
        
    except Exception as e:
        print(f"Error identifying bank: {str(e)}")
        return None

def extract_transactions_from_region(input_path, profile):
    """Extract transactions using bank profile"""
    try:
        reader = PdfReader(input_path)
        page = reader.pages[0]
        page_height = float(page.mediabox.height)
        
        # Apply crop box from profile
        crop_box = profile.crop_box
        page.cropbox.lower_left = (crop_box[0], page_height - crop_box[3])
        page.cropbox.upper_right = (crop_box[2], page_height - crop_box[1])
        
        # Extract and process text
        text = page.extract_text()
        lines = text.split('\n')
        transactions = []
        pattern = profile.pattern
        
        for i, line in enumerate(lines, 1):
            try:
                # print(line)
                match = re.search(pattern.regex, line)
                if match:
                    groups = match.groups()
                    
                    if any(g is None for g in groups):
                        continue
                    
                    # Process transaction data
                    date_str = groups[pattern.date_group - 1]
                    description = groups[pattern.desc_group - 1].strip()
                    amount_str = groups[pattern.amount_group - 1]
                    
                    # Convert date
                    date_obj = pd.to_datetime(date_str, format=pattern.date_format)
                    std_date = date_obj.strftime(pattern.date_out_format)
                    
                    # Process amount
                    amount_str = amount_str.replace(',', '')
                    if pattern.credit_suffix:
                        amount_str = amount_str.replace(pattern.credit_suffix, '')
                    amount = float(amount_str.strip())
                    
                    # Determine transaction type
                    if pattern.type_group:
                        txn_type = groups[pattern.type_group - 1]
                        is_credit = txn_type == pattern.credit_identifier
                    else:
                        is_credit = pattern.credit_suffix and pattern.credit_suffix in groups[pattern.amount_group - 1]
                    
                    if not is_credit:
                        amount = -amount
                    
                    transactions.append({
                        'Date': std_date,
                        'Description': description,
                        'Amount': amount,
                        'Type': pattern.credit_identifier if is_credit else pattern.debit_identifier
                    })
                    
            except Exception as e:
                continue
        
        # Convert to DataFrame
        df = pd.DataFrame(transactions)
        if not df.empty:
            df['Date'] = pd.to_datetime(df['Date'], format=pattern.date_out_format)
            df = df.sort_values('Date')
        
        return df
    
    except Exception as e:
        print(f"Error extracting transactions: {str(e)}")
        return pd.DataFrame()

def process_pdf(input_path, output_csv, password):
    """Process PDF with bank profile"""
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
        tmp_path = tmp_file.name
        
        try:
            # Load bank profiles
            profiles = load_bank_profiles()
            
            # Decrypt and extract first page
            if not preprocess_pdf(input_path, tmp_path, password):
                print("Error: PDF preprocessing failed")
                return
            
            # Identify bank and get profile
            profile = identify_bank(tmp_path, profiles)
            if not profile:
                return
            
            # Extract transactions
            print(f"Extracting transactions using {profile.name} profile...")
            df = extract_transactions_from_region(tmp_path, profile)
            
            # Save results
            if not df.empty:
                print(f"\nExtracted {len(df)} transactions")
                print(df)
                df.to_csv(output_csv, index=False)
                print(f"Saved transactions to {output_csv}")
            else:
                print("No transactions found in the PDF")
                
        except Exception as e:
            print(f"Error processing PDF: {str(e)}")
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

def main():
    args = parse_arguments()
    process_pdf(
        input_path=args.input_pdf,
        output_csv=args.output,
        password=args.password
    )

if __name__ == "__main__":
    main()