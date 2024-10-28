import sys
import pikepdf
import pdfplumber
import matplotlib.pyplot as plt
import matplotlib.patches as patches
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
    parser = argparse.ArgumentParser(description='PDF Cropbox Locator')
    parser.add_argument('input_pdf', help='Input PDF file')
    parser.add_argument('--password', 
                      help='PDF password',
                      default=None)
    parser.add_argument('--cropbox', 
                      type=parse_cropbox,
                      help='Cropbox coordinates as "x0,top,x1,bottom"',
                      default=(10, 422, 430, 675))
    
    return parser.parse_args()

def preprocess_pdf(input_path, output_path, password=None):
    """
    Preprocess PDF: decrypt, keep first page, uncompress streams and remove restrictions
    Args:
        input_path (str): Input PDF path
        output_path (str): Output PDF path
        password (str): PDF password (optional)
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
        
        print(f"Successfully preprocessed PDF")
        return True
        
    except Exception as e:
        print(f"Error preprocessing PDF: {str(e)}")
        return False
    finally:
        if 'pdf' in locals():
            pdf.close()
        if 'new_pdf' in locals():
            new_pdf.close()

def visualize_cropbox(pdf_path, crop_box):
    """
    Visualize PDF page with crop box overlay
    Args:
        pdf_path (str): Path to PDF file
        crop_box (tuple): (x0, top, x1, bottom) coordinates
    """
    with pdfplumber.open(pdf_path) as pdf:
        # Get first page
        page = pdf.pages[0]
        
        # Convert page to image
        img = page.to_image()
        
        # Create figure and axis with appropriate size
        fig, ax = plt.subplots(figsize=(15, 20))
        
        # Display the page
        ax.imshow(img.annotated)
        
        # Create rectangle patch for crop box
        left, top, right, bottom = crop_box
        width = right - left
        height = bottom - top
        
        rect = patches.Rectangle(
            (left, top),           # (x,y) of lower left corner
            width,                 # width
            height,                # height
            linewidth=2,
            edgecolor='red',
            facecolor='none'
        )
        
        # Add the rectangle to the plot
        ax.add_patch(rect)
        
        # Remove axes
        plt.axis('off')
        
        # Print dimensions for reference
        print(f"Page dimensions: width={page.width}, height={page.height}")
        print(f"Crop box coordinates: {crop_box}")
        print("Red rectangle shows the area that will be extracted")
        
        plt.show()

def main():
    # Parse command line arguments
    args = parse_arguments()
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
        tmp_path = tmp_file.name
        
        try:
            # Step 1: Preprocess (decrypt and sanitize)
            if not preprocess_pdf(args.input_pdf, tmp_path, args.password):
                print("Preprocessing failed, stopping.")
                return
            
            # Step 2: Show page with crop box overlay
            visualize_cropbox(tmp_path, args.cropbox)
            
        finally:
            # Clean up temporary file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

if __name__ == "__main__":
    main()