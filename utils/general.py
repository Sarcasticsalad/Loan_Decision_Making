import os
import json
import pandas as pd


# Benchmark standards for ratios
STANDARDS = {
    "EBITDA": {
        "positive": {"min": 0, "max": float('inf'), "message": "Positive EBITDA indicates the company is operationally profitable", "color": "green"},
        "negative": {"min": float('-inf'), "max": 0, "message": "Negative EBITDA indicates operational losses", "color": "red"}
    },
    "Leverage Ratio": {
        "strong": {"min": 0, "max": 4, "message": "Good leverage level (≤ 4)", "color": "green"},
        "high": {"min": 4, "max": float('inf'), "message": "High leverage level (> 4)", "color": "red"},
        "weak": {"min": float('-inf'), "max": 0, "message": "Negative leverage level", "color": "red"}
    },
    "Gear Ratio": {
        "strong": {"min": 0, "max": 0.5, "message": "Low gearing (≤ 0.5) – Strong financial structure", "color": "green"},
        "moderate": {"min": 0.5, "max": 1.0, "message": "Moderate gearing (0.5 – 1.0) – Acceptable leverage", "color": "yellow"},
        "high": {"min": 1.0, "max": float('inf'), "message": "High gearing (> 1.0) – Risk of over-leverage", "color": "red"},
        "invalid": {"min": float('-inf'),"max": 0, "message": "Negative gearing ratio – Check input values", "color": "red"}
    },
    "ICR": {
        "strong": {"min": 1.0, "max": float('inf'), "message": "Sufficient ability to cover interest expenses (> 1)", "color": "yellow"},
        "high": {"min": 1.5, "max": float('inf'), "message": "High ability to cover interest expenses (> 1.5)", "color": "green"},
        "weak": {"min": float('-inf'), "max": 1.0, "message": "Insufficient ability to cover interest expenses (< 1)", "color": "red"}
    },
    "DSCR": {
        "strong": {"min": 1.0, "max": float('inf'), "message": "Sufficient ability to service debt (> 1)", "color": "yellow"},
        "high": {"min": 1.5, "max": float('inf'), "message": "High ability to service debt (> 1.5)", "color": "green"},
        "weak": {"min": float('-inf'), "max": 1.0, "message": "Insufficient ability to service debt (< 1)", "color": "red"}
    },
    "CR": {
        "strong": {"min": 1.0, "max": 1.5, "message": "Good short-term liquidity (1-1.5)", "color": "yellow"},
        "high": {"min": 1.5, "max": float('inf'), "message": "High short-term liquidity (> 1.5)", "color": "green"},
        "weak": {"min": float('-inf'), "max": 1.0, "message": "Weak short-term liquidity (< 1)", "color": "red"}
    },
    "QR": {
        "strong": {"min": 1.0, "max": float('inf'), "message": "Good quick liquidity (> 1)", "color": "yellow"},
        "high": {"min": 1.5, "max": float('inf'), "message": "High quick liquidity (> 1.5)", "color": "green"},
        "weak": {"min": float('-inf'), "max": 1.0, "message": "Weak quick liquidity (< 1)", "color": "red"}
    }
}

# Load the config file
def load_config():
    config_path = "financial_mappings.json"  # Path JSON file
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            return json.load(f)["field_mappings"]
    else:
        return "Config file not found"

# Initialize field mappings
FIELD_MAPPINGS = load_config()    
    
def get_status(ratio_type, value):
    """Determine status of ratio based on standards with range support."""
    if pd.isna(value):
        return "Invalid", "Unable to calculate ratio", "red"
        # return "Invalid", "Unable to calculate ratio (division by zero or missing data)", "gray"
    
    # Get standards for this ratio type
    standards = STANDARDS[ratio_type]   # update with balancesheet and ratio formula.
    
    # Check each category's range
    for category, criteria in standards.items():
        if criteria["min"] <= value < criteria["max"]:
            return category, criteria["message"], criteria["color"]
    
    # Default case (should not reach here if standards are properly defined)
    return "Unknown", "Unable to determine status", "gray"


def find_value(data, field_options):
    """
    Find value in data using various possible field names, with case-insensitive matching.
    Prioritizes non-zero values when multiple field matches are found.
    """
    # Create a case-insensitive and whitespace-normalized version of the data keys
    normalized_data = {}
    for key, value in data.items():
        normalized_key = key.strip().lower()
        normalized_data[normalized_key] = value
    
    found_value = 0
    
    # Check for each field option with normalization
    for option in field_options:
        # Check direct match first
        if option in data:
            # If we find a non-zero value, return it immediately
            if data[option] != 0:
                return data[option]
            # Otherwise, record that we found a value (even if zero)
            found_value = data[option]
        
        # Check normalized match
        normalized_option = option.strip().lower()
        if normalized_option in normalized_data:
            # If we find a non-zero value, return it immediately
            if normalized_data[normalized_option] != 0:
                return normalized_data[normalized_option]
            # Otherwise, record that we found a value (even if zero)
            found_value = normalized_data[normalized_option]
    
    return found_value  # Return the found value (or 0 if nothing found)

# Function to format a float value as Nepali currency
def nepali_format(n):
    n = int(n)
    s = str(n)
    if len(s) <= 3:
        return float(s)
    else:
        last3 = s[-3:]
        rest = s[:-3]
        parts = []
        while len(rest) > 2:
            parts.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            parts.insert(0, rest)
        return ','.join(parts + [last3])
    
    