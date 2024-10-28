# PDF Bank Statement Parser

A command-line tool for extracting structured transaction data from PDF bank and credit card statements.

## The Challenge

Personal finance management often requires categorizing and analyzing credit card transactions. However, Indian banks and credit card providers typically only offer statements in PDF format, rather than machine-readable formats. This necessitates a solution for parsing PDF files to extract meaningful transaction data.

## Technical Approach

PDF parsing presents unique challenges since PDFs are optimized for printing rather than data extraction. A simple text extraction using tools like pdfcpu:

```bash
pdfcpu extract -mode=content hdfc_cc.pdf
```

produces an unstructured text stream that's difficult to parse meaningfully.

Our solution uses a two-step approach:
1. Crop PDF pages to isolate the transaction table area
2. Process the cropped PDF with specialized table extraction libraries

## Implementation

Currently implemented as a bash script that combines:
- pdfcpu for PDF cropping
- camelot for table extraction

A Python rewrite is in progress to enhance robustness and extensibility.

## Usage Example

```bash
./pdfstmt2csv.bash icici_cc.pdf icici mypassword
```

## Tool Evaluation

### PDF Processing Libraries

Go-based:
- pdfcpu: Versatile PDF processor with broad functionality
- PDF Reader: Lightweight library for PDF reading

C++/C-based:
- qpdf: Robust PDF transformer that handles corrupted files effectively

Python-based:
- Camelot: Specialized in table extraction
- pdfplumber: Detailed PDF content analysis and extraction
- PyMuPDF: Comprehensive PDF manipulation toolkit
- PyPDF: Pure Python library for basic PDF operations

### Key Findings

- qpdf excels at handling corrupted files that other tools fail to process
- pdfcpu offers a good balance of simplicity and versatility for general PDF processing tasks
