from docling.document_converter import DocumentConverter
from pdf2image import convert_from_path
import easyocr
from pathlib import Path
import re
import heapq
import numpy as np
import json
import os
from .logs import setup_logger

logger = setup_logger()

TEMP_FOLDER = "temp/"
MARKDOWN = ".md"
FINANCIAL_MAPPING = "financial_mappings.json"

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

def pdf_to_md(file_object, file_name:str):
    """
    Convert an uploaded PDF file (as BytesIO) into a markdown file using Docling.

    Args:
        file_object (BytesIO): The in-memory uploaded PDF file.
        file_name (str): The base filename (without extension) to use for saving.

    Creates:
        - A Markdown file saved as temp/<file_name>.md
    """
    try:
        # Ensure TEMP_FOLDER exists
        os.makedirs(TEMP_FOLDER, exist_ok=True)
        logger.info("Temp Folder exists.")

        # Build full path using original filename
        temp_pdf_path = os.path.join(TEMP_FOLDER, f"{file_name}.pdf")
        logger.info(temp_pdf_path)

        # Write the in-memory PDF to disk with original name
        with open(temp_pdf_path, "wb") as file:
            file.write(file_object.read())

        # Convert to markdown using Docling
        converter = DocumentConverter()
        doc = converter.convert(temp_pdf_path).document

        # Build markdown path
        md_path = os.path.join(TEMP_FOLDER, f"{file_name}.md")

        # Saving the markdown file 
        with open(md_path, "w", encoding="utf-8") as file:
            file.write(doc.export_to_markdown())

        # # Delete the Temporary PDF
        # os.remove(temp_pdf_path)

        logger.info(f"Markdown successfully saved to: {md_path}")
        logger.info("TODO: PDF removal pending!")

    except Exception as e:
        logger.error(f"Failed to convert PDF to Markdown!: {e}")


# === On plan using vision Language model ===

# def pdf_eocr(source):
# # Uncomment for only for GPU based systems

#     # print("Pytorch version:", torch.__version__)
#     # print("CUDA available:", torch.cuda.is_available())
#     # if torch.cuda.is_available():
#     #     print("GPU name:", torch.cuda.get_device_name(0))

# # Works for CPU based systems
#     # Convert PDF to list of images (each page = one image)
#     images = convert_from_path(source, poppler_path=r"C:\poppler-24.08.0\Library\bin")

#     # To use the gpu set gpu=True
#     reader = easyocr.Reader(['en'], gpu=True)

#     source = source.split("/")[-1].split(".")[0]

#     for i, img in enumerate(images):
#         print(f"Processing Page {1}")
#         result = reader.readtext(np.array(img))
#         with open(f"{source}.md", "w") as file:
#             for detection in result:
#                 bbox, text, confidence = detection
#                 file.write(text)
#                 print(f    """


def parse_markdown(file_path):
    try:
        path = Path(file_path)
        if not path.is_file():
            logger.warning(f"Markdown file not found: {file_path}")
            return []

        lines = path.read_text(encoding='utf-8').splitlines()
        table_lines = [line for line in lines if re.match(r'^\s*\|.*\|\s*$', line) and not re.match(r'^\s*\|?[\s\-|]+\|?\s*$', line)]
        logger.info(f"Parsed {len(table_lines)} table lines from markdown.")
        return table_lines
    
    except Exception as e:
        logger.error(f"[parse_markdown] Error parsing markdown file: {e}")
        return []


def check_years(header, year1, year2):
    """
    Identify the column indices of the two given years from the table header.
    Returns the years in chronological order and a mapping of year → column index.

    Args:
        header (list of str): List of header columns from the markdown table.
        year1 (int): First year to search for.
        year2 (int): Second year to search for.

    Returns:
        tuple: (current_year, projected_year, year_index)
            - current_year (int): The earlier year
            - projected_year (int): The later year
            - year_index (dict): Mapping of year → index in header

    Raises:
        ValueError: If one or both years are not found in the header
    """
    try:
        # Initialize year to column index mapping
        year_index = {}

        # Map each target year to its position in the header row
        for idx, col in enumerate(header):
            if str(year1) in col:
                year_index[year1] = idx
            elif str(year2) in col:
                year_index[year2] = idx 

        logger.info(f"Year index mapping found: {year_index}")

        # Handle missing years
        year_index_keys = list(year_index.keys())
        if len(year_index_keys) == 0:
            logger.error("Neither years were found in the header.")
            raise ValueError("No matching years found in header.")
        if len(year_index_keys) == 1:
            logger.error(f"Only one year found: {year_index_keys[0]}")
            raise ValueError("Only one year found in header.")
        
        # Return years in chronological order
        if len(year_index_keys) >=2:
            if year1 < year2:
                current_year , projected_year = year1, year2
            else:
                current_year, projected_year = year2, year1        

        logger.info(f"Years identified: Current = {current_year}, Projected = {projected_year}")

        return current_year, projected_year, year_index    
    
    except Exception as e:
        logger.error(f"Error processing years: {e}") 



def load_field_mappings():
    with open(f"{FINANCIAL_MAPPING}", "r") as file:
        mapping_data = json.load(file)
        
    
    logger.info("Field Mappings loaded!")
    return mapping_data["field_mappings"]

def create_alias_lookup(field_mappings):
    alias_lookup = {}
    for standard_field, aliases in field_mappings.items():
        for alias in aliases:
            alias_lookup[alias.strip().lower()] = standard_field

    logger.info("Aliases Created!")
    return alias_lookup


def extract_data_to_dict(file_name):
    
    parsed_data = parse_markdown(f"{TEMP_FOLDER}{file_name}{MARKDOWN}")

    # Stores the table data in a list where each row is a list
    table_data = [[cell.strip() for cell in re.findall(r'\|([^|]+)', data)] for data in parsed_data]

    # Assigns the first row of the table data as header
    header = table_data[0]

    # Using regex to only keep year values in a list
    years = re.findall(r'(\d{4})', ",".join(header))

    # Mapping the list values to integer
    years = list(map(int, years))

    # Assigning the largest and second largest value to year1 and year2
    year1, year2 = heapq.nlargest(2, years)

    FIELD_MAPPINGS = load_field_mappings()
    ALIAS_LOOKUP = create_alias_lookup(FIELD_MAPPINGS)

    current_year, projected_year, year_index = check_years(header, year1, year2)
    logger.info(f"Current: {current_year}, Projected: {projected_year}")

    # Creating the result dictionary
    result = {
        f"current_{current_year}": {
            #"year": current_year,
            # "data": {}
        },

        f"projected_{projected_year}": {
            # "year": projected_year,
            # "data": {}
        }
    }

    # Fill data for each year
    # Skips the header
    for row in table_data[1:]:
        if len(row) <= max(year_index.values()):
            continue

        raw_label = row[0].strip().lower()

        # First try exact match
        standard_field = ALIAS_LOOKUP.get(raw_label)

        # If no exact match, do partial match
        if not standard_field:
            for alias, field in ALIAS_LOOKUP.items():
                if alias in raw_label:
                    standard_field = field
                    break
        
        if not standard_field:
            logger.info(f"Unmatched label: '{raw_label}'")
            continue

        if standard_field.strip().lower() not in normalized_required:
            logger.info(f"Skipping non-required field: '{standard_field}'")
            continue

        current_value = row[year_index[current_year]]
        projected_value = row[year_index[projected_year]]

        try:
            # Clean and convert values
            if "(" in current_value or "(" in projected_value:
                current_value = float(current_value.replace('(', '').replace(')', '').replace('$', '').replace(',', '').strip())
                projected_value = float(projected_value.replace('(', '').replace(')', '').replace('$', '').replace(',', '').strip())

                result[f"current_{current_year}"][standard_field] = round(-current_value, 2)
                result[f"projected_{projected_year}"][standard_field] = round(-projected_value, 2)
            
            else:
                current_value = float(current_value.replace('(', '').replace(')', '').replace('$', '').replace(',', '').strip())
                projected_value = float(projected_value.replace('(', '').replace(')', '').replace('$', '').replace(',', '').strip())
                result[f"current_{current_year}"][standard_field] = round(current_value, 2)
                result[f"projected_{projected_year}"][standard_field] = round(projected_value, 2)
                        
        except ValueError:
            continue        
                    
    return result            
    # print(result)

def extract_dict_to_json(file_name):
    data = extract_data_to_dict(file_name)
    if data:
        json_path = os.path.join(TEMP_FOLDER, f"{file_name}.json")
        with open(json_path, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)


def extract_year_from_key(key):
    """Extract year from a key like 'audited-2023' or 'projected-2025'."""
    match = re.search(r'(\d{4})', key)
    if match:
        return int(match.group(1))
    return 0


def is_audited(key):
    """
    Check if a key represents audited data.
    AUDIT or Current
    """
    audited = key.lower().startswith('audit')
    if not audited:
        audited = key.lower().startswith('current')

    return audited


def is_projected(key):
    """Check if a key represents projected data. Project or Current """

    projected = key.lower().startswith('project')
    if not projected:
        projected = key.lower().startswith('previous')

    return projected


, line) and not re.match(r'^\s*\|?[\s\-|]+\|?\s*


def check_years(header, year1, year2):
    """
    Identify the column indices of the two given years from the table header.
    Returns the years in chronological order and a mapping of year → column index.

    Args:
        header (list of str): List of header columns from the markdown table.
        year1 (int): First year to search for.
        year2 (int): Second year to search for.

    Returns:
        tuple: (current_year, projected_year, year_index)
            - current_year (int): The earlier year
            - projected_year (int): The later year
            - year_index (dict): Mapping of year → index in header

    Raises:
        ValueError: If one or both years are not found in the header
    """
    try:
        # Initialize year to column index mapping
        year_index = {}

        # Map each target year to its position in the header row
        for idx, col in enumerate(header):
            if str(year1) in col:
                year_index[year1] = idx
            elif str(year2) in col:
                year_index[year2] = idx 

        logger.info(f"Year index mapping found: {year_index}")

        # Handle missing years
        year_index_keys = list(year_index.keys())
        if len(year_index_keys) == 0:
            logger.error("Neither years were found in the header.")
            raise ValueError("No matching years found in header.")
        if len(year_index_keys) == 1:
            logger.error(f"Only one year found: {year_index_keys[0]}")
            raise ValueError("Only one year found in header.")
        
        # Return years in chronological order
        if len(year_index_keys) >=2:
            if year1 < year2:
                current_year , projected_year = year1, year2
            else:
                current_year, projected_year = year2, year1        

        logger.info(f"Years identified: Current = {current_year}, Projected = {projected_year}")

        return current_year, projected_year, year_index    
    
    except Exception as e:
        logger.error(f"Error processing years: {e}") 



def load_field_mappings():
    with open(f"{FINANCIAL_MAPPING}", "r") as file:
        mapping_data = json.load(file)
        
    
    logger.info("Field Mappings loaded!")
    return mapping_data["field_mappings"]

def create_alias_lookup(field_mappings):
    alias_lookup = {}
    for standard_field, aliases in field_mappings.items():
        for alias in aliases:
            alias_lookup[alias.strip().lower()] = standard_field

    logger.info("Aliases Created!")
    return alias_lookup


def extract_data_to_dict(file_name):
    
    parsed_data = parse_markdown(f"{TEMP_FOLDER}{file_name}{MARKDOWN}")

    # Stores the table data in a list where each row is a list
    table_data = [[cell.strip() for cell in re.findall(r'\|([^|]+)', data)] for data in parsed_data]

    # Assigns the first row of the table data as header
    header = table_data[0]

    # Using regex to only keep year values in a list
    years = re.findall(r'(\d{4})', ",".join(header))

    # Mapping the list values to integer
    years = list(map(int, years))

    # Assigning the largest and second largest value to year1 and year2
    year1, year2 = heapq.nlargest(2, years)

    FIELD_MAPPINGS = load_field_mappings()
    ALIAS_LOOKUP = create_alias_lookup(FIELD_MAPPINGS)

    current_year, projected_year, year_index = check_years(header, year1, year2)
    logger.info(f"Current: {current_year}, Projected: {projected_year}")

    # Creating the result dictionary
    result = {
        f"current_{current_year}": {
            #"year": current_year,
            # "data": {}
        },

        f"projected_{projected_year}": {
            # "year": projected_year,
            # "data": {}
        }
    }

    # Fill data for each year
    # Skips the header
    for row in table_data[1:]:
        if len(row) <= max(year_index.values()):
            continue

        raw_label = row[0].strip().lower()

        # First try exact match
        standard_field = ALIAS_LOOKUP.get(raw_label)

        # If no exact match, do partial match
        if not standard_field:
            for alias, field in ALIAS_LOOKUP.items():
                if alias in raw_label:
                    standard_field = field
                    break
        
        if not standard_field:
            logger.info(f"Unmatched label: '{raw_label}'")
            continue

        if standard_field.strip().lower() not in normalized_required:
            logger.info(f"Skipping non-required field: '{standard_field}'")
            continue

        current_value = row[year_index[current_year]]
        projected_value = row[year_index[projected_year]]

        try:
            # Clean and convert values
            if "(" in current_value or "(" in projected_value:
                current_value = float(current_value.replace('(', '').replace(')', '').replace('$', '').replace(',', '').strip())
                projected_value = float(projected_value.replace('(', '').replace(')', '').replace('$', '').replace(',', '').strip())

                result[f"current_{current_year}"][standard_field] = round(-current_value, 2)
                result[f"projected_{projected_year}"][standard_field] = round(-projected_value, 2)
            
            else:
                current_value = float(current_value.replace('(', '').replace(')', '').replace('$', '').replace(',', '').strip())
                projected_value = float(projected_value.replace('(', '').replace(')', '').replace('$', '').replace(',', '').strip())
                result[f"current_{current_year}"][standard_field] = round(current_value, 2)
                result[f"projected_{projected_year}"][standard_field] = round(projected_value, 2)
                        
        except ValueError:
            continue        
                    
    return result            
    # print(result)

def extract_dict_to_json(file_name):
    data = extract_data_to_dict(file_name)
    if data:
        json_path = os.path.join(TEMP_FOLDER, f"{file_name}.json")
        with open(json_path, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)


def extract_year_from_key(key):
    """Extract year from a key like 'audited-2023' or 'projected-2025'."""
    match = re.search(r'(\d{4})', key)
    if match:
        return int(match.group(1))
    return 0


def is_audited(key):
    """
    Check if a key represents audited data.
    AUDIT or Current
    """
    audited = key.lower().startswith('audit')
    if not audited:
        audited = key.lower().startswith('current')

    return audited


def is_projected(key):
    """Check if a key represents projected data. Project or Current """

    projected = key.lower().startswith('project')
    if not projected:
        projected = key.lower().startswith('previous')

    return projected


, line)]
        logger.info(f"Parsed {len(table_lines)} table lines from markdown.")
        return table_lines

    except Exception as e:
        logger.error(f"Error parsing markdown file: {e}")
        return []


def check_years(header, year1, year2):
    """
    Identify the column indices of the two given years from the table header.
    Returns the years in chronological order and a mapping of year → column index.

    Args:
        header (list of str): List of header columns from the markdown table.
        year1 (int): First year to search for.
        year2 (int): Second year to search for.

    Returns:
        tuple: (current_year, projected_year, year_index)
            - current_year (int): The earlier year
            - projected_year (int): The later year
            - year_index (dict): Mapping of year → index in header

    Raises:
        ValueError: If one or both years are not found in the header
    """
    try:
        # Initialize year to column index mapping
        year_index = {}

        # Map each target year to its position in the header row
        for idx, col in enumerate(header):
            if str(year1) in col:
                year_index[year1] = idx
            elif str(year2) in col:
                year_index[year2] = idx 

        logger.info(f"Year index mapping found: {year_index}")

        # Handle missing years
        year_index_keys = list(year_index.keys())
        if len(year_index_keys) == 0:
            logger.error("Neither years were found in the header.")
            raise ValueError("No matching years found in header.")
        if len(year_index_keys) == 1:
            logger.error(f"Only one year found: {year_index_keys[0]}")
            raise ValueError("Only one year found in header.")
        
        # Return years in chronological order
        if len(year_index_keys) >=2:
            if year1 < year2:
                current_year , projected_year = year1, year2
            else:
                current_year, projected_year = year2, year1        

        logger.info(f"Years identified: Current = {current_year}, Projected = {projected_year}")

        return current_year, projected_year, year_index    
    
    except Exception as e:
        logger.error(f"Error processing years: {e}") 



def load_field_mappings():
    with open(f"{FINANCIAL_MAPPING}", "r") as file:
        mapping_data = json.load(file)
        
    
    logger.info("Field Mappings loaded!")
    return mapping_data["field_mappings"]

def create_alias_lookup(field_mappings):
    alias_lookup = {}
    for standard_field, aliases in field_mappings.items():
        for alias in aliases:
            alias_lookup[alias.strip().lower()] = standard_field

    logger.info("Aliases Created!")
    return alias_lookup


def extract_data_to_dict(file_name):
    
    parsed_data = parse_markdown(f"{TEMP_FOLDER}{file_name}{MARKDOWN}")

    # Stores the table data in a list where each row is a list
    table_data = [[cell.strip() for cell in re.findall(r'\|([^|]+)', data)] for data in parsed_data]

    # Assigns the first row of the table data as header
    header = table_data[0]

    # Using regex to only keep year values in a list
    years = re.findall(r'(\d{4})', ",".join(header))

    # Mapping the list values to integer
    years = list(map(int, years))

    # Assigning the largest and second largest value to year1 and year2
    year1, year2 = heapq.nlargest(2, years)

    FIELD_MAPPINGS = load_field_mappings()
    ALIAS_LOOKUP = create_alias_lookup(FIELD_MAPPINGS)

    current_year, projected_year, year_index = check_years(header, year1, year2)
    logger.info(f"Current: {current_year}, Projected: {projected_year}")

    # Creating the result dictionary
    result = {
        f"current_{current_year}": {
            #"year": current_year,
            # "data": {}
        },

        f"projected_{projected_year}": {
            # "year": projected_year,
            # "data": {}
        }
    }

    # Fill data for each year
    # Skips the header
    for row in table_data[1:]:
        if len(row) <= max(year_index.values()):
            continue

        raw_label = row[0].strip().lower()

        # First try exact match
        standard_field = ALIAS_LOOKUP.get(raw_label)

        # If no exact match, do partial match
        if not standard_field:
            for alias, field in ALIAS_LOOKUP.items():
                if alias in raw_label:
                    standard_field = field
                    break
        
        if not standard_field:
            logger.info(f"Unmatched label: '{raw_label}'")
            continue

        if standard_field.strip().lower() not in normalized_required:
            logger.info(f"Skipping non-required field: '{standard_field}'")
            continue

        current_value = row[year_index[current_year]]
        projected_value = row[year_index[projected_year]]

        try:
            # Clean and convert values
            if "(" in current_value or "(" in projected_value:
                current_value = float(current_value.replace('(', '').replace(')', '').replace('$', '').replace(',', '').strip())
                projected_value = float(projected_value.replace('(', '').replace(')', '').replace('$', '').replace(',', '').strip())

                result[f"current_{current_year}"][standard_field] = round(-current_value, 2)
                result[f"projected_{projected_year}"][standard_field] = round(-projected_value, 2)
            
            else:
                current_value = float(current_value.replace('(', '').replace(')', '').replace('$', '').replace(',', '').strip())
                projected_value = float(projected_value.replace('(', '').replace(')', '').replace('$', '').replace(',', '').strip())
                result[f"current_{current_year}"][standard_field] = round(current_value, 2)
                result[f"projected_{projected_year}"][standard_field] = round(projected_value, 2)
                        
        except ValueError:
            continue        
                    
    return result            
    # print(result)

def extract_dict_to_json(file_name):
    data = extract_data_to_dict(file_name)
    if data:
        json_path = os.path.join(TEMP_FOLDER, f"{file_name}.json")
        with open(json_path, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)


def extract_year_from_key(key):
    """Extract year from a key like 'audited-2023' or 'projected-2025'."""
    match = re.search(r'(\d{4})', key)
    if match:
        return int(match.group(1))
    return 0


def is_audited(key):
    """
    Check if a key represents audited data.
    AUDIT or Current
    """
    audited = key.lower().startswith('audit')
    if not audited:
        audited = key.lower().startswith('current')

    return audited


def is_projected(key):
    """Check if a key represents projected data. Project or Current """

    projected = key.lower().startswith('project')
    if not projected:
        projected = key.lower().startswith('previous')

    return projected


