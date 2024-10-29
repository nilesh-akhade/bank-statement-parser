
# How to create a Profile

A profile is a JSON file that contains the information required to extract transactions from a PDF file. The profile contains the following information:

- `name`: Name of the profile
- `identifier`: Unique text associated with the statement type, found on first page of the PDF file, which will help in identifying the profile.
- `cropbox`: Coordinates of the cropbox
- `pattern`: Regular expression pattern and some metadata to extract transactions

```bash
# Step 1:Identify cropbox for a PDF file
python3 cropbox_locator.py input/8799314479959121_03102024.pdf --password=<password> --cropbox "10,422,430,675"
# Step 2: Keep on changing cropbox coordinates until you get the desired output, the format is "x0,y0,x1,y1"
# x0,x1 -> horizontal offsets from the left edge of the page
# y0,y1 -> vertical offsets from the top edge of the page

# Step 3: Identify Regex
python3 cropbox_locator.py input/8799314479959121_03102024.pdf --password=<password> --cropbox "10,422,430,675" --show-content
# This will show the content of the cropbox, which will help in identifying the regex pattern
# Ask chatgpt to construct a pattern to extract transactions from these lines

# Step 4: Identify identifier
python3 cropbox_locator.py input/8799314479959121_03102024.pdf --password=<password> --show-content
# Identify unique text, for example bank name, which will help in identifying the profile.
# TransactionExtractor will match this text to identify the profile to use.

# Step 5: Update the profile.json file
```

# Use profile to extract transactions

The profiles are stored in the `profiles.json`. The profile will be selected based on the identifier. The transactions will be extracted using the pattern and cropbox coordinates.

```bash
python3 transactions_extractor.py --password=<password> --output results.csv input/8799314479959121_03102024.pdf
```
