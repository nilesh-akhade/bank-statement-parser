
```bash
# Step 1:Identify cropbox for a PDF file
python3 cropbox_locator.py input/8799314479959121_03102024.pdf --password=<password> --cropbox "10,422,430,675"
# Step 2: Keep on changing cropbox coordinates until you get the desired output

# Step 3: Extract transactions from the PDF file
python3 transactions_extractor.py --password=<password> --cropbox "10,422,430,675" --output results.csv input/8799314479959121_03102024.pdf
```

With HDFC:

```bash

python3 cropbox_locator.py input/5181XXXXXXXXXX07_15-10-2024.PDF --password=<password> --cropbox "5,428,592,675"
python3 transactions_extractor.py --password=<password> --cropbox "5,428,592,675" --output results.csv input/5181XXXXXXXXXX07_15-10-2024.PDF
```