from docling.document_converter import DocumentConverter
# from img2table.ocr import TesseractOCR
# from img2table.document import PDF, Image
from pdf2image import convert_from_path
import easyocr
from pathlib import Path
import re
import heapq
import numpy as np
import torch
import json

REQUIRED = [ 
    "Total Current Assets",
            "Total Non-Current Assets",
            "Total Assets",
            "Inventory",
            "Total Current Liabilities",
            "Total Non-Current Liabilities",
            "Total Liabilities",
            "Term Loan",
            "Total Equity",
            "Total Liabilities and Equity",
            "Operating Income",
            "Interest Expense",
            "Net Operating Profit",
            "Profit After Tax",
            "Depreciation",
            "Amortization",
            "Taxation",
            "Administration Expenses"
            ]

normalized_required = {x.strip().lower() for x in REQUIRED}

def pdf_to_md(source):
    converter = DocumentConverter()
    doc = converter.convert(source).document

    # Splitting the path to extract only file name
    source = source.split("/")[-1].split(".")[0]
    
    # Saving the markdown file 
    with open(f"{source}.md", "w") as file:
        file.write(doc.export_to_markdown())
        file.close()


# pdf_to_md("pdfs/Shivam.pdf")

# img2table gives no results: {0: []}

# def pdf_ocr(source):
#     # Instantiation of OCR
#     ocr = TesseractOCR(n_threads=2, lang='eng')

#     # Instantiation of document, either an image or a PDF
#     doc = PDF(source)

#     # Table extraction
#     extracted_tables = doc.extract_tables(ocr=ocr,
#                                       implicit_rows=True,
#                                       implicit_columns=True,
#                                       borderless_tables=True,
#                                       min_confidence=40)

#     print(extracted_tables)

# pdf_ocr("pdfs/Shivam.pdf")  

def pdf_eocr(source):

# Uncomment for only for GPU based systems

    # print("Pytorch version:", torch.__version__)
    # print("CUDA available:", torch.cuda.is_available())
    # if torch.cuda.is_available():
    #     print("GPU name:", torch.cuda.get_device_name(0))

# Works for CPU based systems
    # Convert PDF to list of images (each page = one image)
    images = convert_from_path(source, poppler_path=r"C:\poppler-24.08.0\Library\bin")

    # To use the gpu set gpu=True
    reader = easyocr.Reader(['en'], gpu=True)

    source = source.split("/")[-1].split(".")[0]

    for i, img in enumerate(images):
        print(f"Processing Page {1}")
        result = reader.readtext(np.array(img))
        with open(f"{source}.md", "w") as file:
            for detection in result:
                bbox, text, confidence = detection
                file.write(text)
                print(f"Text: {text} | Confidence: {confidence}")

# pdf_eocr("pdfs/Shivam.pdf")

def parse_markdown(file_path):
    path = Path(file_path)
    if path.is_file():
        # print("File exists.")

        # Read Lines
        lines = Path(file_path).read_text(encoding='utf-8').splitlines()
        # print(lines)
        # Select only table lines
        # table_lines = [line for line in lines if re.match(r'^\s*\|.*\|\s*$', line) and not re.match(r'^\s*\|?[\s\-|]+\|?\s*$', line) and not re.match(r'^\s*\|[^|]*\s*\|\s*\|\s*\|$', line)]
        table_lines = [line for line in lines if re.match(r'^\s*\|.*\|\s*$', line) and not re.match(r'^\s*\|?[\s\-|]+\|?\s*$', line)]
        # print(table_lines)
        
        return table_lines

    else:
        print("File doesn't exist.")

# parse_markdown("tech_innovator.md")

def check_years(header, year1, year2):
    # Mapping years to the column index
    year_index = {}

    for idx, col in enumerate(header):
        if str(year1) in col:
            year_index[year1] = idx
        elif str(year2) in col:
            year_index[year2] = idx 

    year_index_keys = list(year_index.keys())
    print(year_index_keys)
    if len(year_index_keys) == 0:
        print("Cannot move forward. No years found.")
    if len(year_index_keys) == 1:
        print("Cannot move forward. Only one year found")
    
    if len(year_index_keys) >=2:
        if year1 < year2:
            current_year , projected_year = year1, year2
        else:
            current_year, projected_year = year2, year1        

    return current_year, projected_year, year_index    


def extract_data_to_dict():

    parsed_data = parse_markdown("tech_innovator.md")

    # Stores the table data in a list where each row is a list
    table_data = [[cell.strip() for cell in re.findall(r'\|([^|]+)', data)] for data in parsed_data]
    # print(table_data)

    # Assigns the first row of the table data as header
    header = table_data[0]
    # print(header)
    # Using regex to only keep year values in a list
    years = re.findall(r'(\d{4})', ",".join(header))
    # Mapping the list values to integer
    years = list(map(int, years))
    # print(years)
    # Assigning the largest and second largest value to year1 and year2
    year1, year2 = heapq.nlargest(2, years)
    # print(year1)
    # print(year2)

    # if year1 < year2:
    #     result = {"Current": {"year": year1}, "Projected": {"year": year2}}
    # else:
    #     result = {"Current": {"year": year2}, "Projected": {"year": year1}}

    # print(result)

    current_year, projected_year, year_index = check_years(header, year1, year2)
    print(f"Current: {current_year}, Projected: {projected_year}")

    # Creating the result dictionary
    result = {
        "Current": {
            "year": current_year,
            "data": {}
        },

        "Projected": {
            "year": projected_year,
            "data": {}
        }
    }

    # Fill data for each year
    # print(table_data)

    # Skips the header
    for row in table_data[1:]:
        if len(row) <= max(year_index.values()):
            continue

        item = row[0]
        current_value = row[year_index[current_year]]
        projected_value = row[year_index[projected_year]]

        normalized_item = item.strip().lower()
    
        if normalized_item in normalized_required:
            try:
                    # Clean and convert values
                    if "(" in current_value or "(" in projected_value:
                        current_value = float(current_value.replace('(', '').replace(')', '').replace('$', '').replace(',', '').strip())
                        projected_value = float(projected_value.replace('(', '').replace(')', '').replace('$', '').replace(',', '').strip())

                        result["Current"]["data"][item] = round(-current_value, 2)
                        result["Projected"]["data"][item] = round(-projected_value, 2)
                    else:
                        current_value = float(current_value.replace('(', '').replace(')', '').replace('$', '').replace(',', '').strip())
                        projected_value = float(projected_value.replace('(', '').replace(')', '').replace('$', '').replace(',', '').strip())
                        result["Current"]["data"][item] = round(current_value, 2)
                        result["Projected"]["data"][item] = round(projected_value, 2)
                        
            except ValueError:
                    continue        
                    
    return result            
    # print(result)

def extract_dict_to_json():
    data = extract_data_to_dict()
    if data:
        with open("output_filtered.json", "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)

extract_dict_to_json()    

