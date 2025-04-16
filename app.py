import streamlit as st
import json
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import copy
import numpy as np
import re
import base64
from datetime import datetime


# Set page configuration
st.set_page_config(
    page_title="Preliminary Decision Making",
    page_icon="💰",
    layout="wide"
)

ACCEPT_RATIO_PARAM = 2 # 6
DESIRABLE_RATIO_PARAM = (ACCEPT_RATIO_PARAM/2) # 3
REJECT_RATIO_PARAM = DESIRABLE_RATIO_PARAM # 3

APPROVED_GREEN = ":green[**GREEN : In principal approval subject to approve from concerned authority**]"
CONSIDERABLE_AMBER= ":orange[**AMBER: In principal approval subject to aligning ratios ( highlighted in red) to acceptable level.**]"
REJECTED_RED = ":red[**RED: REJECTED**]"

# Check Field 'balance.json' , update ratio function, add standards for ratios

# def notes():
#     operating_profit = find_value(data, FIELD_MAPPINGS["net_operating_profit"])
#     interest = abs(find_value(data, FIELD_MAPPINGS["interest_expense"]))
#     depreciation = abs(find_value(data, FIELD_MAPPINGS["depreciation"]))
#     amortization = abs(find_value(data, FIELD_MAPPINGS["amortization"]))
#     current_assets = find_value(data, FIELD_MAPPINGS["total_current_assets"])
#     total_current_liabilities = find_value(data, FIELD_MAPPINGS["total_current_liabilities"])
#     total_liabilities = find_value(data, FIELD_MAPPINGS["total_liabilities"])
#     total_equity = find_value(data, FIELD_MAPPINGS["total_equity"])
#     inventory = find_value(data, FIELD_MAPPINGS["inventory"])
#     Principal_Repayment


# Config for field mappings (handles different naming conventions)
FIELD_MAPPINGS_old = {
    "inventory": ["Inventory", "stocks-trading", "Stocks Trading", "stocks trading", "stock_trading", "Stock Trading", "Stocks-Trading"],
    "total_current_assets": ["Total Current Assets", "current assets", "current_assets", "total current assets"],
    "total_current_liabilities": ["Total Current Liabilities", "current liabilities", "current_liabilities", "total current liabilities"],
    "long_term_debt": ["Long-term Debt", "Long term Debt", "long_term_debt", "LTD", "long term debt"],
    "total_liabilities": ["Total Liabilities", "liabilities", "total liabilities"],
    "total_equity": ["Total Equity", "equity", "shareholders equity", "Shareholders' Equity", "total equity"],
    "interest_expense": ["Interest Expense", "interest expense", "interest_expense"],
    "net_operating_profit": ["Net Operating Profit", "operating profit", "operating_profit", "EBIT", "net operating profit"],
    "depreciation": ["Depreciation", "depreciation"],
    "amortization": ["Amortization", "amortization"]
}

# Benchmark standards for ratios
STANDARDS_old= {
    "EBITDA": {
        "positive": {"threshold": 0, "message": "Positive EBITDA indicates the company is operationally profitable", "color": "green"},
        "negative": {"threshold": float('-inf'), "message": "Negative EBITDA indicates operational losses", "color": "red"}
    },
    "Leverage Ratio": {
        "good": {"threshold": 4, "message": "Good leverage level (≤ 4)", "color": "green"},
        "moderate": {"threshold": float('-inf'), "message": "High leverage level (> 4)", "color": "red"}
    },
    "ICR": {
        "strong": {"threshold": 1.0, "message": "Sufficient ability to cover interest expenses (> 1)", "color": "green"},
        "weak": {"threshold": float('-inf'), "message": "Insufficient ability to cover interest expenses (< 1)", "color": "red"}
    },
    "DSCR": {
        "strong": {"threshold": 1.0, "message": "Sufficient ability to service debt (> 1)", "color": "green"},
        "high": {"threshold": 1.5, "message": "High ability to service debt (> 1.5)", "color": "yellow"},
        "weak": {"threshold": float('-inf'), "message": "Insufficient ability to service debt (< 1)", "color": "red"}
    },
    "CR": {
        "strong": {"threshold": 1.0, "message": "Good short-term liquidity (1-1.5)", "color": "green"},
        "high": {"threshold": 1.5, "message": "High short-term liquidity (> 1.5)", "color": "amber"},
        "weak": {"threshold": float('-inf'), "message": "Weak short-term liquidity (< 1)", "color": "red"}
    },
    "QR": {
        "strong": {"threshold": 1.0, "message": "Good quick liquidity (> 1)", "color": "green"},
        "weak": {"threshold": float('-inf'), "message": "Weak quick liquidity (< 1)", "color": "red"}
    }
}
STANDARDS = {
    "EBITDA": {
        "positive": {"min": 0, "max": float('inf'), "message": "Positive EBITDA indicates the company is operationally profitable", "color": "green"},
        "negative": {"min": float('-inf'), "max": 0, "message": "Negative EBITDA indicates operational losses", "color": "red"}
    },
    "Leverage Ratio": {
        "strong": {"min": 0, "max": 4, "message": "Good leverage level (≤ 4)", "color": "green"},
        "high": {"min": 4, "max": float('inf'), "message": "High leverage level (> 4)", "color": "red"},
        # "weak": {"min": float('-inf'), "max": 0, "message": "Negative leverage level", "color": "gray"}
    },
    "Gear Ratio": {
        "strong": {"min": 0, "max": 0.5, "message": "Low gearing (≤ 0.5) – Strong financial structure", "color": "green"},
        "moderate": {"min": 0.5, "max": 1.0, "message": "Moderate gearing (0.5 – 1.0) – Acceptable leverage", "color": "yellow"},
        "high": {"min": 1.0, "max": float('inf'), "message": "High gearing (> 1.0) – Risk of over-leverage", "color": "red"},
        "invalid": {"min": float('-inf'),"max": 0, "message": "Negative gearing ratio – Check input values", "color": "gray"}
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
        st.error("Config file not found")
        return None

# Initialize field mappings
FIELD_MAPPINGS = load_config()

def find_value(data, field_options):
    """Find value in data using various possible field names, with case-insensitive matching.
    Prioritizes non-zero values when multiple field matches are found."""
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

def safe_division(numerator, denominator):
    """Safely divide two numbers, handling zero division."""
    if denominator == 0:
        return float('nan')
    return numerator / denominator

def normal_page():
    # Balance Sheet: Statement of Financial Position
    # Profit and Loss account: Statement of Profit and Loss Account

    st.info("Please upload a JSON file with financial data to begin analysis.")
    st.write("The expected JSON structure should contain multiple years of audited and projected financial data.")
        
    # Show sample data structure
    st.subheader("Expected JSON Structure")
    sample_structure = """
        {
            "audited-2023": {
                "Total Current Assets": 179411,
                "Inventory": 0,
                "Total Current Liabilities": 155900,
                ...
            },
            "audited-2024": {
                "Total Current Assets": 185000,
                "Inventory": 0,
                "Total Current Liabilities": 152000,
                ...
            },
            "projected-2025": {
                "Total Current Assets": 195000,
                "Inventory": 0,
                "Total Current Liabilities": 150000,
                ...
            },
            "projected-2026": {
                "Total Current Assets": 210000,
                "Inventory": 0,
                "Total Current Liabilities": 145000,
                ...
            }
        }
        """
    
    calculations="""
        {
            "EBITDA-1":["net_operating_profit","interest_expense","depreciation","amortization"],
            "EBITDA-2":["profit_after_tax", "taxation", "interest_expense", "depreciation", "administration_expense"],
            "Leverage":["total liabilities (total_current_liabilities + total_non_current_liabilities)","total equity"],
            "Gear":["long_term_debt (term loan)", "total equity"],
            "ICR-1":["EBITDA-1","interest_expense"],
            "ICR-2":["net_operating_profit","interest_expense","depreciation","amortization"],
            "DSCR-1":["EBITDA-1","interest_expense","principal repayment"],
            "DSCR-2":["net_operating_profit","depreciation","amortization","interest_expense","principal repayment"],
            "CR":["total_current_assets","total_current_liabilities"],
            "QR":["total_current_assets","inventory","total_current_liabilities"]
        }
        """
    
    required_fields="""
        {
        "BalanceSheet":[
            "total_current_assets", "total_current_liabilities", "total_non_current_liabilities",
            "total liabilities", "total equity", "Stocks - Trading | Inventory", "long_term_debt | term loan"
        ],
        "PL":["interest_expense", "depreciation | depreciation expenses", "amortization | amortization expenses",
            "net_operating_profit | net income | profit_after_tax", "administration_expenses", "taxation"]
        }
        """
    # Finance Cost
    # Financial Charges: Int Exp
    # # Financing Charge, Borrowing Cost
    # Profit from Operation/; net op

    with st.expander("Sample Structure"):
        st.code(sample_structure, language="json")
    with st.expander("Balance Sheet and PL"):
        st.code(calculations,language="json")
        st.code(required_fields,language="json")
    
# TODO: -ve EBITDA: do not proceed with calculations
# TODO: Total Assets is not equal to Total Liabilities + Equity: do not proceed with calculations
def calculate_ebitda(data):
    """Calculate EBITDA (Earnings Before Interest, Taxes, Depreciation, and Amortization)."""
    # CASE 1:
    operating_profit = abs(find_value(data, FIELD_MAPPINGS["net_operating_profit"])) # shivam" profit/loss (Before)
    interest = abs(find_value(data, FIELD_MAPPINGS["interest_expense"]))
    depreciation = abs(find_value(data, FIELD_MAPPINGS["depreciation"]))
    amortization = abs(find_value(data, FIELD_MAPPINGS["amortization"]))
    taxation = abs(find_value(data, FIELD_MAPPINGS["taxation"]))
    administration_expense = abs(find_value(data, FIELD_MAPPINGS["administration_expense"]))

    # print(f"EBITDA1: {operating_profit} {interest} {depreciation} {amortization}")
    # For financial analysis, we make interest, depreciation, and amortization positive
    # as we're adding them back to the operating profit
    # return operating_profit + interest + depreciation + amortization

    # CASE 2: Profit after tax: was inside net_operating_profit
    # "net_operating_profit": [
    #     "Net Operating Profit", 
    #     "operating profit", "operating_profit", "net operating profit", "Net Income", "net income", 
    #     "Net Operating Income", "net operating income", "PAT", "Net Profit", 
    #     "Profit for the Year"
    #   ],
    
    # Profit After Tax + Taxation + Interest Expense + Depreciation + Administration Expense
    profit_after_tax = abs(find_value(data,FIELD_MAPPINGS["profit_after_tax"]))
    
    print(f"EBITDA2--: {operating_profit} -- {taxation} - {interest} - {depreciation} -- {administration_expense}")
    # return operating_profit + taxation + interest + depreciation + administration_expense
    return profit_after_tax + taxation + interest + depreciation + administration_expense

    # return operating_profit + taxation + interest + depreciation + administration_expense

def calculate_leverage_ratio(data):
    """Calculate Leverage Ratio (Total Liabilities / Total Equity)."""
    total_liabilities = find_value(data, FIELD_MAPPINGS["total_liabilities"])
    
    # If total liabilities is not found or is zero, calculate from current and non-current liabilities
    if total_liabilities == 0:
        total_current_liabilities = find_value(data, FIELD_MAPPINGS["total_current_liabilities"])
        if "Total Non-Current Liabilities" in data:
            total_non_current_liabilities = data["Total Non-Current Liabilities"]
        else:
            total_non_current_liabilities = 0
        total_liabilities = total_current_liabilities + total_non_current_liabilities
    
    if total_liabilities == 0:
        return st.error("Data is not complete (total_liabilities is missing)")
    
    total_equity = find_value(data, FIELD_MAPPINGS["total_equity"])
    if total_equity == 0:
        return st.error("Data is not complete (total_equity is missing)")
    
    return safe_division(total_liabilities, total_equity)

def calculate_gear_ratio(data):
    """Calculate Gear Ratio (Term Loan and Finance / Ttoal Equity)."""
    term_loan = find_value(data, FIELD_MAPPINGS["long_term_debt"]) # Long term Debt
    total_equity = abs(find_value(data, FIELD_MAPPINGS["total_equity"]))
    if not isinstance(total_equity,(int,float)):
        return st.error("Data is not complete (total_equity is missing)")
    
    # print(f"Term Loan {term_loan} - {total_equity}")
    return safe_division(term_loan, total_equity)

# TODO: ICR
def calculate_icr(data):
    """Calculate Interest Coverage Ratio (EBIT / Interest Expense)."""
    ebitda = calculate_ebitda(data)
    if not isinstance(ebitda,(int,float)):
        return st.error("Could not proceed with ICR calculation (EBITDA is missing)")
    
    interest_expense = find_value(data, FIELD_MAPPINGS["interest_expense"])
    if not isinstance(interest_expense,(int,float)):
        return st.error("Could not proceed with ICR calculation (Interest Expense is missing)")
    abs_interest_expense = abs(interest_expense)
    # Case: 1
    # return safe_division(ebitda, interest_expense)

    # Case: 2
    depreciation = find_value(data, FIELD_MAPPINGS["depreciation"])
    amortization = find_value(data, FIELD_MAPPINGS["amortization"])
    operating_profit = find_value(data, FIELD_MAPPINGS["net_operating_profit"])
    val = abs(operating_profit)-(abs_interest_expense+abs(amortization)+abs(depreciation))
    return safe_division(val,interest_expense)

def calculate_dscr(data, principal_repayment=0):
    """Calculate Debt Service Coverage Ratio (EBITDA / (Interest Expense + Principal Repayment))."""
    # ebitda = calculate_ebitda(data)
    interest_expense = find_value(data, FIELD_MAPPINGS["interest_expense"])
    debt_service = interest_expense + principal_repayment
    # return safe_division(ebitda, debt_service)

    # Case: 2
    abs_interest_expense = abs(interest_expense)
    depreciation = abs(find_value(data, FIELD_MAPPINGS["depreciation"]))
    amortization = abs(find_value(data, FIELD_MAPPINGS["amortization"]))
    operating_profit = abs(find_value(data, FIELD_MAPPINGS["net_operating_profit"]))
    # val = operating_profit-(interest_expense+amortization+depreciation)
    val = abs(operating_profit)-(abs_interest_expense+abs(amortization)+abs(depreciation))

    return safe_division(val,(interest_expense+principal_repayment))

def calculate_cr(data):
    """Calculate Current Ratio (Current Assets / Current Liabilities)."""
    current_assets = find_value(data, FIELD_MAPPINGS["total_current_assets"])
    current_liabilities = find_value(data, FIELD_MAPPINGS["total_current_liabilities"])
    return safe_division(current_assets, current_liabilities)

def calculate_qr(data):
    """Calculate Quick Ratio ((Current Assets - Inventory) / Current Liabilities)."""
    current_assets = find_value(data, FIELD_MAPPINGS["total_current_assets"])
    inventory = find_value(data, FIELD_MAPPINGS["inventory"])
    current_liabilities = find_value(data, FIELD_MAPPINGS["total_current_liabilities"])
    return safe_division(current_assets - inventory, current_liabilities)

def get_status(ratio_type, value):
    """Determine status of ratio based on standards with range support."""
    if pd.isna(value):
        return "Invalid", "Unable to calculate ratio (division by zero or missing data)", "gray"
    
    # Get standards for this ratio type
    standards = STANDARDS[ratio_type]   # update with balancesheet and ratio formula.
    
    # Check each category's range
    for category, criteria in standards.items():
        if criteria["min"] <= value < criteria["max"]:
            return category, criteria["message"], criteria["color"]
    
    # Default case (should not reach here if standards are properly defined)
    return "Unknown", "Unable to determine status", "gray"

def display_metric(label, value, status, message, color):
    """Display a metric with appropriate color and message."""

    if pd.isna(value):
        formatted_value = "N/A"
    else:
        formatted_value = f"{value:.2f}"
    
    if color == "green":
        st.success(f"**{label}:** {formatted_value} | **Status:** {status.capitalize()} | ***{message}***")
    elif color == "yellow":
        st.warning(f"**{label}:** {formatted_value} | **Status:** {status.capitalize()} | ***{message}***")
    elif color == "red":
        st.error(f"**{label}:** {formatted_value} | **Status:** {status.capitalize()} | ***{message}***")
    else:
        st.write(f"**{label}:** {formatted_value} | **Status:** {status.capitalize()} | ***{message}***")

def extract_year_from_key(key):
    """Extract year from a key like 'audited-2023' or 'projected-2025'."""
    match = re.search(r'(\d{4})', key)
    if match:
        return int(match.group(1))
    return 0

def is_audited(key):
    """Check if a key represents audited data."""
    return key.lower().startswith('audit')

def is_projected(key):
    """Check if a key represents projected data."""
    return key.lower().startswith('project')

def calculate_ratios_for_data(data, principal_repayment=0):
    """Calculate all financial ratios for a given data set."""
    # print(f"calculate_ratios_for_data - {principal_repayment}")
    # print(f"Data :{data}")
    ratios = {
        "EBITDA": {"value": calculate_ebitda(data)},
        "Leverage Ratio": {"value": calculate_leverage_ratio(data)},
        "Gear Ratio": {"value": calculate_gear_ratio(data)},
        "ICR": {"value": calculate_icr(data)},
        "DSCR": {"value": calculate_dscr(data, principal_repayment)},
        "CR": {"value": calculate_cr(data)},
        "QR": {"value": calculate_qr(data)}
    }
    
    # Determine status for each ratio
    for ratio_name in ratios:
        ratios[ratio_name]["status"], ratios[ratio_name]["message"], ratios[ratio_name]["color"] = get_status(
            ratio_name, ratios[ratio_name]["value"]
        )
    
    # print(f"calculate_ratios_for_data - Ratios: {[(ratio_name,ratios[ratio_name]['value']) for ratio_name in ratios]}")
    # print(f"{'***********'*2}")
    
    return ratios

def create_multi_year_chart(years_data, ratio_name):
    """Create a chart showing a specific ratio across multiple years."""
    # print(f"Creating chart for {ratio_name}..")
    years = list(years_data.keys())
    years.sort(key=extract_year_from_key)
    
    # Separate audited and projected data
    audited_years = [y for y in years if is_audited(y)]
    projected_years = [y for y in years if is_projected(y)]

    # TODO: Audited Years
    # Extract values for the specified ratio
    audited_values = [years_data[y][ratio_name]["value"] for y in audited_years]
    projected_values = [years_data[y][ratio_name]["value"] for y in projected_years]
    
    # print("create_multi_year_chart Years:", years)
    # print("Year Data:", years_data)
    # print("create_multi_year_chart Audited Years:", audited_years)
    # print("Audited Values:", audited_values)
    # print("create_multi_year_chart Projected Years:", projected_years)
    # color_continuous_scale=["red", "yellow", "green"],

    # Create the figure
    fig = go.Figure()
    if audited_years:
        # fig.add_trace(go.Scatter(
        #     x=audited_years,
        #     y=audited_values,
        #     mode='lines+markers',
        #     name='Audited',
        #     line=dict(color='blue', width=2, dash='dash'),
        #     marker=dict(size=8)
        # ))
        fig.add_trace(go.Scatter(
            x=audited_years,
            y=audited_values,
            mode='lines+markers',
            name='Audited',
            line=dict(color='#1f77b4', width=3),  # Deeper blue, thicker line
            marker=dict(size=10, symbol='circle', color='#1f77b4', line=dict(width=2, color='#000')),  # Larger markers with outline
            hovertemplate='%{x}: %{y:.2f}<extra></extra>'
        ))
        
        
    
    if projected_years:
        # fig.add_trace(go.Scatter(
        #     x=projected_years,
        #     y=projected_values,
        #     mode='lines+markers',
        #     name='Projected',
        #     line=dict(color='orange', width=2, dash='dash'),
        #     marker=dict(size=8)
        # ))
        fig.add_trace(go.Scatter(
            x=projected_years,
            y=projected_values,
            mode='lines+markers',
            name='Projected',
            line=dict(color='#ff7f0e', width=3, dash='dot'),  # Orange color, thicker dotted line
            marker=dict(size=10, symbol='circle', color='#ff7f0e', line=dict(width=2, color='#000')),  # Diamond markers with outline
            hovertemplate='%{x}: %{y:.2f}<extra></extra>'
        ))
    
    # Add threshold lines based on ratio type
    standards = STANDARDS[ratio_name]
    
    # Add lines for key thresholds
    if ratio_name == "EBITDA":
        # Zero line for EBITDA
        fig.add_shape(
            type="line", line=dict(color="green", width=2, dash="dot"),
            y0=0, y1=0, x0=years[0], x1=years[-1]
        )
    elif ratio_name == "Gear Ratio":
        # Upper threshold for Gear Ratio
        threshold = standards["strong"]["max"] # strong, high, weak
        fig.add_shape(
            type="line", line=dict(color="red", width=2, dash="dot"),
            y0=threshold, y1=threshold, x0=years[0], x1=years[-1]
        )
    elif ratio_name == "Leverage Ratio":
        # Upper threshold for Leverage Ratio
        threshold = standards["strong"]["max"] # strong, high, weak
        fig.add_shape(
            type="line", line=dict(color="red", width=2, dash="dot"),
            y0=threshold, y1=threshold, x0=years[0], x1=years[-1]
        )
    elif ratio_name == "ICR" or ratio_name == "DSCR" or ratio_name == "QR":
        # Lower threshold for ICR, DSCR, QR
        threshold = standards["strong"]["min"]
        fig.add_shape(
            type="line", line=dict(color="red", width=2, dash="dot"),
            y0=threshold, y1=threshold, x0=years[0], x1=years[-1]
        )
    elif ratio_name == "CR":
        # Lower threshold for CR
        lower_threshold = standards["strong"]["min"]
        fig.add_shape(
            type="line", line=dict(color="red", width=2, dash="dot"),
            y0=lower_threshold, y1=lower_threshold, x0=years[0], x1=years[-1]
        )
        # Upper threshold for CR
        upper_threshold = standards["strong"]["max"]
        fig.add_shape(
            type="line", line=dict(color="green", width=2, dash="dot"),
            y0=upper_threshold, y1=upper_threshold, x0=years[0], x1=years[-1]
        )
    
    # Update layout
    fig.update_layout(
        title=f"{ratio_name} Trend Over Time",
        xaxis_title="Year",
        yaxis_title=f"{ratio_name} Value",
        legend_title="Data Type",
        hovermode="x unified"
    )
    
    return fig

def perform_stress_test(data, stress_factors):
    """
    Perform stress testing on financial data with various stress factors.
    
    Args:
        data: Financial data dictionary
        stress_factors: Dictionary of stress factors (percentage change) to apply
        
    Returns:
        Dictionary with original and stressed ratios
    """
    # Create a copy of data to avoid modifying the original
    stressed_data = data.copy()
    
    # Apply stress factors to the relevant fields
    for field, factor in stress_factors.items():
        # Get the original value using our mapping function
        original_value = None
        for mapping_key, field_options in FIELD_MAPPINGS.items():
            if any(f.lower() == field.lower() for f in field_options):
                original_value = find_value(data, field_options)
                break
        
        if original_value is not None:
            # Calculate the stressed value
            stressed_value = original_value * (1 + factor/100)
            
            # Update the field in stressed data
            # We need to find which key in the data corresponds to this field
            field_key = None
            for key in data.keys():
                if key.lower().strip() == field.lower().strip():
                    field_key = key
                    break
            
            if field_key:
                stressed_data[field_key] = stressed_value
    
    # Calculate ratios for original and stressed data
    original_ratios = {
        "EBITDA": calculate_ebitda(data),
        "Leverage Ratio": calculate_leverage_ratio(data),
        "ICR": calculate_icr(data),
        "DSCR": calculate_dscr(data),
        "CR": calculate_cr(data),
        "QR": calculate_qr(data)
    }
    
    stressed_ratios = {
        "EBITDA": calculate_ebitda(stressed_data),
        "Leverage Ratio": calculate_leverage_ratio(stressed_data),
        "ICR": calculate_icr(stressed_data),
        "DSCR": calculate_dscr(stressed_data),
        "CR": calculate_cr(stressed_data),
        "QR": calculate_qr(stressed_data)
    }
    
    return {
        "original": original_ratios,
        "stressed": stressed_ratios,
        "stress_factors": stress_factors
    }

def create_gauge_chart(ratio_name, original_value, stressed_value):
    """Create a gauge chart for stress test visualization using range-based standards."""
    if pd.isna(original_value) or pd.isna(stressed_value):
        return None
    
    # Get standards for this ratio type
    standards = STANDARDS[ratio_name]
    
    # Define thresholds and value ranges based on standards
    if ratio_name == "EBITDA":
        threshold = standards["positive"]["min"]  # 0
        max_value = max(abs(original_value), abs(stressed_value)) * 1.5
        min_value = min(min(original_value, stressed_value), 0) * 1.5
    elif ratio_name == "Leverage Ratio":
        threshold = standards["high"]["max"]  # 4
        max_value = max(original_value, stressed_value, threshold * 1.5)
        min_value = 0
    elif ratio_name == "ICR" or ratio_name == "DSCR":
        threshold = standards["strong"]["min"]  # 1
        max_value = max(original_value, stressed_value, threshold * 2)
        min_value = min(min(original_value, stressed_value), 0)
    elif ratio_name == "CR":
        threshold_low = standards["strong"]["min"]  # 1
        threshold_high = standards["strong"]["max"]  # 1.5
        max_value = max(original_value, stressed_value, threshold_high * 1.5)
        min_value = 0
    elif ratio_name == "QR":
        threshold = standards["strong"]["min"]  # 1
        max_value = max(original_value, stressed_value, threshold * 1.5)
        min_value = 0
    else:
        max_value = max(original_value, stressed_value) * 1.5
        min_value = min(original_value, stressed_value) * 0.5
        threshold = (max_value + min_value) / 2
    
    # Create a gauge chart
    fig = go.Figure()
    
    # Steps for color zones
    if ratio_name == "CR":
        # Special case for Current Ratio
        steps = [
            {'range': [min_value, threshold_low], 'color': 'red'},
            {'range': [threshold_low, threshold_high], 'color': 'green'},
            {'range': [threshold_high, max_value], 'color': 'yellow'}
        ]
    elif ratio_name == "Leverage Ratio":
        # For Leverage Ratio, lower is better (reverse color scale)
        steps = [
            {'range': [min_value, threshold], 'color': 'green'},
            {'range': [threshold, max_value], 'color': 'red'}
        ]
    elif ratio_name == "EBITDA":
        steps = [
            {'range': [min_value, threshold], 'color': 'red'},
            {'range': [threshold, max_value], 'color': 'green'}
        ]
    else:
        # Default case
        steps = [
            {'range': [min_value, threshold], 'color': 'red'},
            {'range': [threshold, max_value], 'color': 'green'}
        ]
    
    # Add gauge trace for original value
    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=original_value,
        title={'text': f"{ratio_name} (Original)"},
        gauge={
            'axis': {'range': [min_value, max_value]},
            'bar': {'color': "blue"},
            'steps': steps,
            'threshold': {
                'line': {'color': "black", 'width': 4},
                'thickness': 0.75,
                'value': original_value
            }
        },
        domain={'row': 0, 'column': 0}
    ))
    
    # Add gauge trace for stressed value
    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=stressed_value,
        title={'text': f"{ratio_name} (Stressed)"},
        gauge={
            'axis': {'range': [min_value, max_value]},
            'bar': {'color': "orange"},
            'steps': steps,
            'threshold': {
                'line': {'color': "black", 'width': 4},
                'thickness': 0.75,
                'value': stressed_value
            }
        },
        domain={'row': 0, 'column': 1}
    ))
    
    # Update layout
    fig.update_layout(
        grid={'rows': 1, 'columns': 2, 'pattern': "independent"},
        height=400,
        margin=dict(l=40, r=40, t=80, b=40)  # Adjust margins for better spacing
    )
    
    return fig

def display_stress_test_results(data, stress_factors):
    """
    Display stress test results visualization and analysis.
    
    Args:
        data: Dictionary containing financial data
        stress_factors: Dictionary of stress factors to apply
    
    Returns:
        Dictionary with stress test results
    """
    # Perform stress test on data
    stress_test_results = perform_stress_test(data, stress_factors)
    
    # Create stress test summary
    st.subheader("Stress Test Summary")
    
    # Display the applied stress factors
    st.write("**Applied Stress Factors:**")
    col1, col2 = st.columns(2)
    with col1:
        stress_factors_df = pd.DataFrame({
            "Financial Metric": list(stress_factors.keys()),
            "Applied Change (%)": [f"{factor}%" for factor in stress_factors.values()]
        })
        st.dataframe(stress_factors_df, use_container_width=True)
    
    with col2:
        # Create and display ratio summary
        stress_summary = pd.DataFrame({
            "Ratio": list(stress_test_results["original"].keys()),
            "Original Value": [stress_test_results["original"][r] for r in stress_test_results["original"]],
            "Stressed Value": [stress_test_results["stressed"][r] for r in stress_test_results["original"]],
            "Change (%)": [(stress_test_results["stressed"][r] / stress_test_results["original"][r] - 1) * 100 
                        if stress_test_results["original"][r] != 0 else float('nan') 
                        for r in stress_test_results["original"]]
        })
    
        # Format the summary table
        formatted_summary = stress_summary.copy()
        formatted_summary["Original Value"] = formatted_summary["Original Value"].apply(lambda x: f"{x:.2f}" if not pd.isna(x) else "N/A")
        formatted_summary["Stressed Value"] = formatted_summary["Stressed Value"].apply(lambda x: f"{x:.2f}" if not pd.isna(x) else "N/A")
        formatted_summary["Change (%)"] = formatted_summary["Change (%)"].apply(lambda x: f"{x:.2f}%" if not pd.isna(x) else "N/A")
        
        st.dataframe(formatted_summary, use_container_width=True)
    
    # Create gauge charts for each ratio
    st.subheader("Stress Test Visualization")
    
    # Use tabs for displaying gauge charts
    tabs = st.tabs(list(stress_test_results["original"].keys()))
    
    for i, ratio_name in enumerate(stress_test_results["original"]):
        with tabs[i]:
            original_value = stress_test_results["original"][ratio_name]
            stressed_value = stress_test_results["stressed"][ratio_name]
            
            gauge_chart = create_gauge_chart(ratio_name, original_value, stressed_value)
            if gauge_chart:
                st.plotly_chart(gauge_chart, use_container_width=True)
                
                # Add interpretation
                original_status, original_message, _ = get_status(ratio_name, original_value)
                stressed_status, stressed_message, _ = get_status(ratio_name, stressed_value)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Original Status:** {original_status.capitalize()}")
                    st.write(f"**Original Value:** {original_value:.2f}")
                    st.write(original_message)
                
                with col2:
                    st.write(f"**Stressed Status:** {stressed_status.capitalize()}")
                    st.write(f"**Stressed Value:** {stressed_value:.2f}")
                    st.write(stressed_message)
                    
                # Calculate and display impact
                if not pd.isna(original_value) and not pd.isna(stressed_value) and original_value != 0:
                    change_pct = (stressed_value / original_value - 1) * 100
                    impact = "positive" if (change_pct > 0 and ratio_name != "Leverage Ratio") or (change_pct < 0 and ratio_name == "Leverage Ratio") else "negative"
                    
                    if impact == "positive":
                        st.success(f"**Impact:** The stress test shows a **{abs(change_pct):.2f}% {impact}** change in this ratio.")
                    else:
                        st.error(f"**Impact:** The stress test shows a **{abs(change_pct):.2f}% {impact}** change in this ratio.")
            else:
                st.error("Unable to create gauge chart due to invalid values.")
    
    # Add overall stress test conclusion
    st.subheader("Stress Test Conclusion")
    
    # Count ratios that remain in good standing after stress
    good_ratios_after_stress = 0
    changed_status_ratios = []
    
    for ratio_name in stress_test_results["original"]:
        original_status, _, original_color = get_status(ratio_name, stress_test_results["original"][ratio_name])
        stressed_status, _, stressed_color = get_status(ratio_name, stress_test_results["stressed"][ratio_name])
        
        if stressed_color == "green":
            good_ratios_after_stress += 1
        
        if original_color != stressed_color:
            status_change = "improved" if stressed_color == "green" and original_color != "green" else "deteriorated"
            changed_status_ratios.append((ratio_name, status_change))
    
    # Display overall resilience assessment
    resilience_threshold = len(stress_test_results["original"]) / 2
    
    if good_ratios_after_stress >= resilience_threshold:
        st.success(f"**Overall Assessment:** The company shows good resilience to the applied stress factors, with {good_ratios_after_stress} out of {len(stress_test_results['original'])} ratios remaining in good standing.")
    else:
        st.error(f"**Overall Assessment:** The company shows vulnerability to the applied stress factors, with only {good_ratios_after_stress} out of {len(stress_test_results['original'])} ratios remaining in good standing.")
    
    # Display changed status ratios
    if changed_status_ratios:
        st.write("**Ratios with Changed Status:**")
        for ratio, change in changed_status_ratios:
            if change == "improved":
                st.success(f"- {ratio}: {change}")
            else:
                st.error(f"- {ratio}: {change}")
    
    return stress_test_results

def create_financial_ratios_dataframe(data):
    """
    Create a DataFrame with financial ratios and trend indicators
    
    Parameters:
    - data: List of dictionaries with ratio_name, year, and value
    
    Returns:
    - DataFrame with trend indicators
    """
    # Convert to DataFrame
    df = pd.DataFrame(data)
    
    # Create pivot table with ratios as rows and years as columns
    pivot_df = df.pivot(index='ratio_name', columns='year', values='value')
    
    # Sort columns in chronological order
    year_order = ['audited-2079', 'audited-2080', 'projected-2081', 'projected-2082', 'projected-2083']
    pivot_df = pivot_df[year_order]
    
    # Create a DataFrame to store trend indicators
    trend_df = pd.DataFrame(index=pivot_df.index, columns=pivot_df.columns)
    
    # Fill first column with neutral indicator
    trend_df.iloc[:, 0] = '—'
    
    # For remaining columns, compare with previous column and add trend indicators
    for i in range(1, len(pivot_df.columns)):
        for j in range(len(pivot_df.index)):
            ratio = pivot_df.index[j]
            current = pivot_df.iloc[j, i]
            previous = pivot_df.iloc[j, i-1]
            
            # For Leverage Ratio, lower is better (↑ for decrease, ↓ for increase)
            if ratio == 'Leverage Ratio':
                trend_df.iloc[j, i] = '↑' if current < previous else '↓'
            else:
                # For all other metrics, higher is better (↑ for increase, ↓ for decrease)
                trend_df.iloc[j, i] = '↑' if current > previous else '↓'
    
    # Format the values based on ratio type
    formatted_pivot = pivot_df.copy()
    
    for idx in formatted_pivot.index:
        for col in formatted_pivot.columns:
            value = formatted_pivot.loc[idx, col]
            
            if idx == 'EBITDA':
                formatted_pivot.loc[idx, col] = f"{value:,.0f}"
            else:
                formatted_pivot.loc[idx, col] = f"{value:.2f}"
    
    # Combine formatted values with trend indicators
    result_df = formatted_pivot.copy()
    
    for idx in result_df.index:
        for col in result_df.columns:
            value = formatted_pivot.loc[idx, col]
            trend = trend_df.loc[idx, col]
            result_df.loc[idx, col] = f"{value} {trend}"
    
    # Reset index to make ratio_name a column
    result_df = result_df.reset_index()
    
    return result_df

def collect_financial_data(years_ratios):
    """
    Collects financial data from a nested dictionary structure
    
    Parameters:
    - years_ratios: Dictionary with year keys and ratio dictionaries as values
    
    Returns:
    - List of dictionaries with ratio_name, year, and value
    """
    all_years_trend = {}
    ratios = list(list(years_ratios.values())[0].keys())
    years = list(years_ratios.keys())
    all_years_trend['ratio_name'] = ratios

    for year in years:
        values = [years_ratios[year][ratio]["value"] for ratio in ratios]
        all_years_trend[year] = values
    
    return pd.DataFrame(all_years_trend)

# Function to add trend indicators to the DataFrame
def add_trend_indicators(df):
    # Make a copy to avoid modifying the original
    result_df = df.copy()
    
    # Sort year columns chronologically
    year_columns = [col for col in df.columns if col != 'ratio_name']
    sorted_years = sorted(year_columns)
    
    # Process each ratio row
    for i, row in df.iterrows():
        ratio = row['ratio_name']
        
        # Loop through years and compare with previous
        for j in range(1, len(sorted_years)):
            current_year = sorted_years[j]
            prev_year = sorted_years[j-1]
            
            current_value = row[current_year]
            prev_value = row[prev_year]
            
            # Determine trend direction (for Leverage Ratio, lower is better)
            # if ratio == 'Leverage Ratio':
            #     trend = ' ▲ ' if current_value < prev_value else ' ▼ '
            # else:
            #     trend = ' ▲ ' if current_value > prev_value else ' ▼ '
            # trend = ""
            # if current_value > prev_value:
            #     trend = st.markdown("<span style='color:green; font-size:12px'> ▲ </span>")
            # else:
            #     trend = st.markdown("<span style='color:red; font-size:12px'> ▼ </span>")

            # trend = " ▲ " if current_value > prev_value else ' ▼ ' # ADD
            trend=''
            
            # Format the value based on ratio type
            if ratio == 'EBITDA':
                formatted_value = f"{current_value:,.2f}"
            else:
                formatted_value = f"{current_value:.2f}"
            
            # Add trend indicator
            result_df.at[i, current_year] = f"{formatted_value} {trend}"
        
        # Format the first year (no trend comparison)
        first_year = sorted_years[0]
        if ratio == 'EBITDA':
            result_df.at[i, first_year] = f"{row[first_year]:,.2f}" #  ➖"
        else:
            result_df.at[i, first_year] = f"{row[first_year]:.2f}" #  ➖"
    
    result_df = result_df.style.applymap(style_symbols)

    return result_df

def year_wise_financial_statements(all_years_data, years_ratios):
    """Display financial statements for each year and calculate ratios."""
    audited_years, projected_years = return_auditednprojected_years(years_ratios)
   
    latest_audited = audited_years[-1]
    first_projected = projected_years[0]

    all_years_data_keys = all_years_data.keys()
    selected_ratios = []

    with st.expander("Select Year to Analyze", expanded=False):
        selected_year = st.radio(  # selected_year = st.selectbox(
            "**Choose year:**",
            options=list(all_years_data_keys),
            index=0,
            help="Select the year for which you want to analyze financial ratios.",
            horizontal=True
        )
        
        # Display selected year analysis
        selected_ratios = years_ratios[selected_year]

        # print(f"Selected ratios: {selected_ratios}")
        num_columns = 3  # Display and adjust column numbers
        columns = st.columns(num_columns)
        count_green, count_yellow, count_red = 0,0,0

        for i, (ratio_name, ratio_data) in enumerate(selected_ratios.items()):
            if ratio_name == 'EBITDA':
                display_metric(
                        ratio_name,
                        ratio_data["value"],
                        ratio_data["status"],
                        ratio_data["message"],
                        ''
                )
            else:
                with columns[i % num_columns]:
                    display_metric(
                        ratio_name,
                        ratio_data["value"],
                        ratio_data["status"],
                        ratio_data["message"],
                        ratio_data["color"]
                    )
                    if selected_ratios[ratio_name]["color"] == "green":
                        count_green += 1
                    if selected_ratios[ratio_name]["color"] == "yellow":
                        count_yellow += 1
                    if selected_ratios[ratio_name]["color"] == "red":
                        count_red += 1

        if count_green or count_yellow or count_red:
            # st.write(f"Green {count_green} - Red {count_red} - Yellow {count_yellow}")
            if ACCEPT_RATIO_PARAM == 0:
                st.warning("**Overview: No financial ratios were calculated for the selected year.**")
            if selected_year == latest_audited or selected_year == first_projected:
                st.divider()
                if count_green == ACCEPT_RATIO_PARAM: # 6
                    st.subheader(APPROVED_GREEN) 
                    # st.write(":green[**APPROVED]: The company is in -EXCELLENT- standing based onthe selected financial ratios.**")
                if count_green == REJECT_RATIO_PARAM: # 3
                    st.subheader(CONSIDERABLE_AMBER) 
                    # st.success("**: The company is in -GOOD- standing based on the selected financial ratios.**")        
                if count_green < REJECT_RATIO_PARAM: # 3
                    st.subheader(REJECTED_RED)
                    # st.error(":red[**DENY**]:**The company is in -POOR- standing based on the selected financial ratios.**")
                # else:
                #     st.error("**Overview: No financial ratios were calculated for the selected year.**")

    return selected_ratios

# 2
def all_trends_dataframe(years_ratios):
    financial_df = collect_financial_data(years_ratios)
    data_with_trend = add_trend_indicators(financial_df)
    st.dataframe(data_with_trend, use_container_width=True)

def visualize_trends(selected_ratios, years_ratios):
    ratio_keys = selected_ratios.keys()
    ratio_tabs = st.tabs(list(ratio_keys))
    
    audited_years, projected_years = return_auditednprojected_years(years_ratios
                                                                    )
    print(f"Trend: {ratio_keys}")
    for i, ratio_name in enumerate(ratio_keys):
        with ratio_tabs[i]:
            chart = create_multi_year_chart(years_ratios, ratio_name)
            st.plotly_chart(chart, use_container_width=True)

            # Only show trend analysis if we have multiple years
            col1, col2 = st.columns(2)
            with col1:
                if len(audited_years) >= 1:
                    st.write("**Audited Data Trend:**")
                    first_year = audited_years[0]
                    last_year = audited_years[-1]
                    first_value = years_ratios[first_year][ratio_name]["value"]
                    last_value = years_ratios[last_year][ratio_name]["value"]
                    
                    if not pd.isna(first_value) and not pd.isna(last_value) and first_value != 0:
                        change_pct = (last_value - first_value) / abs(first_value) * 100
                        trend = "increasing" if change_pct > 0 else "decreasing"
                        
                        # For leverage ratio, decreasing is good
                        is_positive = (change_pct > 0 and ratio_name != "Leverage Ratio") or (change_pct < 0 and ratio_name == "Leverage Ratio")
                        
                        if is_positive:
                            st.success(f"The **{ratio_name}** has been **{trend}** by **{abs(change_pct):.2f}%** from **{first_year}** to **{last_year}**, which is positive.")
                        else:
                            st.error(f"The **{ratio_name}** has been **{trend}** by **{abs(change_pct):.2f}%** from **{first_year}** to **{last_year}**, which needs attention.")
                    else:
                        st.info(f"The **{ratio_name}** has no noticable changes from **{first_year}** to **{last_year}**.")

            with col2:
                if len(projected_years) >= 1:
                    st.write("**Projected Data Trend:**")
                    first_year = projected_years[0]
                    last_year = projected_years[-1]
                    first_value = years_ratios[first_year][ratio_name]["value"]
                    last_value = years_ratios[last_year][ratio_name]["value"]
                    
                    if not pd.isna(first_value) and not pd.isna(last_value) and first_value != 0:
                        change_pct = (last_value - first_value) / abs(first_value) * 100
                        trend = "increase" if change_pct > 0 else "decrease"
                        
                        # For leverage ratio, decreasing is good
                        is_positive = (change_pct > 0 and ratio_name != "Leverage Ratio") or (change_pct < 0 and ratio_name == "Leverage Ratio")
                        
                        if is_positive:
                            st.success(f"The **{ratio_name}** is projected to **{trend}** by **{abs(change_pct):.2f}%** from **{first_year}** to **{last_year}**, which is positive.")
                        else:
                            st.warning(f"The **{ratio_name}** is projected to **{trend}** by **{abs(change_pct):.2f}%** from **{first_year}** to **{last_year}**, which may need attention.")
                    else:
                        
                        st.info(f"The **{ratio_name}** has no noticable changes from **{first_year}** to **{last_year}**.")

# Function to get repayment values for each year
def get_repayment_values(all_years_data_keys):
    """
    Create an organized UI for setting principal repayment values for each year.
    Returns a dictionary with repayment values for each year.
    
    Args:
        all_years_data_keys: List of year keys from the financial data
        Example: ['audited-2023', 'projected-2024', ...]
        
    Returns:
        Dictionary mapping each year to its repayment value
    """
    repayment_values = {}
    
    with st.sidebar:
        # st.header("DSCR Configuration")
        
        # Create an expander for repayment settings
        with st.expander("**Principal Repayment by Year**", expanded=False):
            # Option to set all years at once
            apply_to_all = st.checkbox("Set same value for all years")
            
            if apply_to_all:
                # Single input for all years
                all_years_value = st.number_input(
                    "Principal Repayment (All Years)",
                    min_value=0.0,
                    value=0.0,
                    step=1000.0,
                    help="This value will be applied to all years"
                )
                
                # Apply to all years
                repayment_values = {year: all_years_value for year in all_years_data_keys}
            else:
                # Group years by type (audited vs projected)
                audited_years = sorted([y for y in all_years_data_keys if is_audited(y)], key=extract_year_from_key)
                projected_years = sorted([y for y in all_years_data_keys if is_projected(y)], key=extract_year_from_key)
                other_years = [y for y in all_years_data_keys if not is_audited(y) and not is_projected(y)]
                
                # Show projected years first (most likely to need repayment values)
                if projected_years:
                    st.subheader("Projected Years")
                    cols = st.columns(min(3, len(projected_years)))
                    for i, year in enumerate(projected_years):
                        with cols[i % len(cols)]:
                            repayment_values[year] = st.number_input(
                                f"{year}",
                                min_value=0.0,
                                value=0.0,
                                step=1000.0,
                                key=f"repayment_{year}"
                            )
                
                # Then show audited years (might be historical)
                if audited_years:
                    st.subheader("Audited Years")
                    cols = st.columns(min(3, len(audited_years)))
                    for i, year in enumerate(audited_years):
                        with cols[i % len(cols)]:
                            repayment_values[year] = st.number_input(
                                f"{year}",
                                min_value=0.0,
                                value=0.0,
                                step=1000.0,
                                key=f"repayment_{year}"
                            )
                
                # Finally, any other years that don't match patterns
                if other_years:
                    st.subheader("Other Years")
                    cols = st.columns(min(3, len(other_years)))
                    for i, year in enumerate(other_years):
                        with cols[i % len(cols)]:
                            repayment_values[year] = st.number_input(
                                f"{year}",
                                min_value=0.0,
                                value=0.0,
                                step=1000.0,
                                key=f"repayment_{year}"
                            )
    
    return repayment_values

# 3
def complete_stress_test(all_years_data, projected_years):
    stress_year = st.radio(
        "**Select Projected Years for Stress Testing:**",
        options=projected_years,
        index=0 if projected_years else 0,
        horizontal=True,
        help="Select the year for which you want to perform stress testing.",
        )

    # Add preset scenarios
    st.subheader("Stress Test Presets")
    preset_col1, preset_col2, preset_col3 = st.columns(3)
    
    with preset_col1:
        mild_recession = st.button("Mild Recession", help="Current Assets: -10%, Liabilities: +5%, Interest: +10%, Operating Profit: -15%")
    
    with preset_col2:
        severe_recession = st.button("Severe Recession", help="Current Assets: -25%, Liabilities: +15%, Interest: +25%, Operating Profit: -35%")
    
    with preset_col3:
        optimistic = st.button("Optimistic Scenario", help="Current Assets: +10%, Liabilities: -5%, Interest: -10%, Operating Profit: +20%")
    
    # Custom sliders
    st.subheader("Custom Stress Parameters")
    st.write("Enter percentage change for stress testing (negative for decrease)")
    
    col1, col2 = st.columns(2)
    
    # Initialize session state for sliders if not already present
    if 'stress_current_assets' not in st.session_state:
        st.session_state.stress_current_assets = 0
    if 'stress_current_liabilities' not in st.session_state:
        st.session_state.stress_current_liabilities = 0
    if 'stress_interest_expense' not in st.session_state:
        st.session_state.stress_interest_expense = 0
    if 'stress_net_operating_profit' not in st.session_state:
        st.session_state.stress_net_operating_profit = 0
    
    # Apply presets if buttons are clicked
    if mild_recession:
        st.session_state.stress_current_assets = -10
        st.session_state.stress_current_liabilities = 5
        st.session_state.stress_interest_expense = 10
        st.session_state.stress_net_operating_profit = -15
    
    if severe_recession:
        st.session_state.stress_current_assets = -25
        st.session_state.stress_current_liabilities = 15
        st.session_state.stress_interest_expense = 25
        st.session_state.stress_net_operating_profit = -35
    
    if optimistic:
        st.session_state.stress_current_assets = 10
        st.session_state.stress_current_liabilities = -5
        st.session_state.stress_interest_expense = -10
        st.session_state.stress_net_operating_profit = 20
    
    with col1:
        stress_current_assets = st.slider("Current Assets Stress (%)", -50, 50, st.session_state.stress_current_assets, 5)
        st.session_state.stress_current_assets = stress_current_assets
        
        stress_current_liabilities = st.slider("Current Liabilities Stress (%)", -50, 50, st.session_state.stress_current_liabilities, 5)
        st.session_state.stress_current_liabilities = stress_current_liabilities
    
    with col2:
        stress_interest_expense = st.slider("Interest Expense Stress (%)", -50, 50, st.session_state.stress_interest_expense, 5)
        st.session_state.stress_interest_expense = stress_interest_expense
        
        stress_net_operating_profit = st.slider("Operating Profit Stress (%)", -50, 50, st.session_state.stress_net_operating_profit, 5)
        st.session_state.stress_net_operating_profit = stress_net_operating_profit
    
    # # Add a run button to trigger stress test calculation
    # run_stress_test = st.button("Run Stress Test")
    # # Only perform stress test if the button is clicked
    # if run_stress_test:
    #     # Define stress factors from user inputs
    stress_factors = {
        "Total Current Assets": stress_current_assets,
        "Total Current Liabilities": stress_current_liabilities,
        "Interest Expense": stress_interest_expense,
        "Net Operating Profit": stress_net_operating_profit
    }
            
    # Call the stress test display function
    display_stress_test_results(all_years_data[stress_year], stress_factors)
    
# 4
def audited_to_projected_trend(years_ratios):

    audited_years, projected_years = return_auditednprojected_years(years_ratios)
    latest_audited = audited_years[-1] if audited_years else None  # TODO: Handle case with no audited : data audited_years[-1]
    
    # latest_projected = projected_years[-1] if projected_years else None #TODO: Handle case with no projected : data projected_years[-1]
    latest_projected = projected_years[0] if projected_years else None # NEW
    
    print(f"Audited Years: {audited_years} -- {projected_years}")
                
    if latest_projected:
        
        # Count how many ratios are in good standing for projected data
        # projected_good_count = sum(1 for ratio in years_ratios[latest_projected].values() if ratio["color"] == "green")
        # # Loan recommendation based on proportion of good ratios in projected data
        # good_ratio_threshold = len(years_ratios[latest_projected]) / 2  # At least half of ratios should be good
        
        # if projected_good_count >= good_ratio_threshold:
        #     st.success("✅ **Loan Recommendation: APPROVE**")
        #     st.write(f"The company shows positive financial health in {projected_good_count} out of {len(years_ratios[latest_projected])} key metrics for the latest projected data ({latest_projected}).")
            
        #     # Highlight areas of improvement if any
        #     areas_to_monitor = [name for name, data in years_ratios[latest_projected].items() if data["color"] != "green"]
        #     if areas_to_monitor:
        #         st.info(f"**Areas to Monitor:** {', '.join(areas_to_monitor)}")
        # else:
        #     st.error("⚠️ **Loan Recommendation: CAUTION**")
        #     st.write(f"The company shows challenges in {len(years_ratios[latest_projected]) - projected_good_count} out of {len(years_ratios[latest_projected])} key metrics for the latest projected data ({latest_projected}).")
            
        #     # Highlight strong areas if any
        #     strong_areas = [name for name, data in years_ratios[latest_projected].items() if data["color"] == "green"]
        #     if strong_areas:
        #         st.info(f"**Strong Areas:** {', '.join(strong_areas)}")
        
        # # Show trend analysis between latest audited and projected
        # st.divider()
        

        if latest_audited:
            # st.subheader("Audited to Projected Trend Analysis")
        
            # Create a DataFrame to show the change from audited to projected
            trend_data = []
            for ratio_name in years_ratios[latest_audited]:
                audited_value = years_ratios[latest_audited][ratio_name]["value"]
                projected_value = years_ratios[latest_projected][ratio_name]["value"]
                
                if not pd.isna(audited_value) and not pd.isna(projected_value):
                    change = projected_value - audited_value
                    change_percent = safe_division(change, abs(audited_value)) * 100
                    
                    trend_data.append({
                        "Ratio": ratio_name,
                        f"Audited: {latest_audited}": audited_value,
                        f"Projected: {latest_projected}": projected_value,
                        "Change": change,
                        "Change %": change_percent
                    })
            
            if trend_data:
                trend_df = pd.DataFrame(trend_data)
                
                # Create a visualization for trend
                fig = px.bar(
                    trend_df,
                    x="Ratio",
                    y="Change %",
                    title=f"Change from: '{latest_audited}' to '{latest_projected}' (% change)",
                    color="Change %",
                    color_continuous_scale=["red", "yellow", "green"],
                    labels={"Change %": "Change (%)", "Ratio": "Financial Ratio"}
                )
                
                st.plotly_chart(fig, use_container_width=True)
                
                # Display the trend table
                st.write(f"**Detailed Trend Analysis** - from: **{latest_audited}** to **{latest_projected}** (% change)")
                
                # Format the DataFrame for display
                formatted_df = trend_df.copy()
                for col in [f"Audited: {latest_audited}", f"Projected: {latest_projected}", "Change"]:
                    formatted_df[col] = formatted_df[col].map(lambda x: f"{x:.2f}")
                formatted_df["Change %"] = formatted_df["Change %"].map(lambda x: f"{x:.2f}%")
                
                st.dataframe(formatted_df, use_container_width=True)
                
                # Key insights
                st.write(f"**Key Insights** - from: {latest_audited} to {latest_projected} (% change)")
                
                improvements = trend_df[trend_df["Change"] > 0]["Ratio"].tolist()
                declines = trend_df[trend_df["Change"] < 0]["Ratio"].tolist()

                col1, col2 = st.columns(2)
                with col1:
                    if improvements:
                        st.success(f"**Improvements Expected:** {', '.join(improvements)}")
                    
                    if declines:
                        st.warning(f"**Declining Metrics:** {', '.join(declines)}")
                with col2:
                # Best and worst performing metrics
                    if not trend_df.empty:
                        best_metric = trend_df.loc[trend_df["Change %"].idxmax()]["Ratio"]
                        worst_metric = trend_df.loc[trend_df["Change %"].idxmin()]["Ratio"]
                        
                        st.success(f"**Best Performing Metric:** {best_metric}")
                        st.error(f"**Metric Requiring Most Attention:** {worst_metric}")
        else:
            st.warning("No audited data available for trend analysis.")
        
        # st.divider() 
        # # Count how many ratios are in good standing for projected data
        # projected_good_count = sum(1 for ratio in years_ratios[latest_projected].values() if ratio["color"] == "green")
        # # Loan recommendation based on proportion of good ratios in projected data
        # good_ratio_threshold = len(years_ratios[latest_projected]) / 2  # At least half of ratios should be good
        
        # if projected_good_count >= good_ratio_threshold:
        #     st.success("✅ **Loan Recommendation: APPROVE**")
        #     st.write(f"The company shows positive financial health in {projected_good_count} out of {len(years_ratios[latest_projected])} key metrics for the latest projected data ({latest_projected}).")
            
        #     # Highlight areas of improvement if any
        #     areas_to_monitor = [name for name, data in years_ratios[latest_projected].items() if data["color"] != "green"]
        #     if areas_to_monitor:
        #         st.info(f"**Areas to Monitor:** {', '.join(areas_to_monitor)}")
        # else:
        #     st.error("⚠️ **Loan Recommendation: CAUTION**")
        #     st.write(f"The company shows challenges in {len(years_ratios[latest_projected]) - projected_good_count} out of {len(years_ratios[latest_projected])} key metrics for the latest projected data ({latest_projected}).")
            
        #     # Highlight strong areas if any
        #     strong_areas = [name for name, data in years_ratios[latest_projected].items() if data["color"] == "green"]
        #     if strong_areas:
        #         st.info(f"**Strong Areas:** {', '.join(strong_areas)}")
        
        # Show trend analysis between latest audited and projected
        
    else:
        st.warning("No projected data available for loan recommendation.")

# Value in '000
def convert_to_thousands(all_years_data):
    scaled_data = {}
    for year_key, data in all_years_data.items():
        scaled_data[year_key] = {}
        for key, value in data.items():
            # Only scale numeric values
            if isinstance(value, (int, float)):
                scaled_data[year_key][key] = value * 1000
            else:
                scaled_data[year_key][key] = value

    return scaled_data

def edit_financial_data_for_year(year_key, financial_data):
    """
    Load and display financial data for a specific year/period for editing.
    Requires explicit confirmation before saving changes.
    
    Args:
        year_key (str): The period key (e.g., 'audited-2023')
        financial_data (dict): Dictionary containing all financial data
        
    Returns:
        tuple: (bool, dict) - (Whether changes were confirmed, Updated data for the year)
    """
    st.subheader(f"Edit Financial Data for {year_key}")
    
    # Create a copy of the data to avoid modifying the original until confirmed
    if year_key in financial_data:
        year_data = financial_data[year_key].copy()
    else:
        st.error(f"No data found for {year_key}")
        return False, {}
    
    # Display editable fields
    st.write("Please review and edit the financial data below:")
    
    # Create columns for better layout
    col1, col2 = st.columns(2)
    
    # Track if any values were changed
    original_data = year_data.copy()
    has_changes = False
    
    # Display input fields for all financial metrics in two columns
    metrics = list(year_data.keys())
    midpoint = len(metrics) // 2
    
    for i, metric in enumerate(metrics):
        # Determine which column to place this field in
        column = col1 if i < midpoint else col2
        
        with column:
            # Get current value with proper type handling
            current_value = year_data.get(metric, 0)
            if isinstance(current_value, (int, float)):
                value_type = type(current_value)
            else:
                value_type = float
                
            # Create input field
            new_value = st.number_input(
                metric,
                value=float(current_value),
                key=f"edit_{year_key}_{metric}"
            )
            
            # Update the data and track changes
            year_data[metric] = new_value
            if abs(float(original_data.get(metric, 0)) - new_value) > 0.001:  # Using a small epsilon for float comparison
                has_changes = True
    
    # Add confirmation buttons
    st.write("---")
    if has_changes:
        st.warning("You have made changes to the financial data. Please confirm to save these changes.")
    
    col_cancel, col_confirm = st.columns(2)
    
    with col_cancel:
        if st.button("Cancel Changes", key=f"cancel_{year_key}"):
            st.info("Changes have been discarded.")
            return False, original_data
    
    with col_confirm:
        confirm_button = st.button("Confirm Changes", key=f"confirm_{year_key}", 
                                  type="primary" if has_changes else "secondary")
        if confirm_button:
            st.success("Changes have been saved successfully!")
            return True, year_data
    
    # If neither button was pressed, return not confirmed
    return False, year_data

# Define a styling function
def style_symbols(val):
    if "➖" in str(val):
        return 'color: black'  # Or whatever your default text color is
    elif "▲" in str(val):
        return 'color: green'
    elif "▼" in str(val):
        return 'color: red'
    return ''

# Function to handle customer information
def collect_customer_information():
    st.header("Customer Information")
    customer_info = {}
    with st.expander("Collect Customer Details", expanded=False):
        # Create columns for a cleaner layout
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # 1. Name of the Customer: Input Box
            customer_name = st.text_input("Name of the Customer")
            
           # 4. Consolidated/Unconsolidated: Dropdown
            consolidation = st.selectbox("Consolidated/Unconsolidated", options=["--","Consolidated", "Unconsolidated"])

            branches = ["--","Branch-001", "Branch-002", "Branch-003","Branch-004"]
            branch = st.selectbox("Select Branch", options=branches, help="Branch Code")
        
        with col2:
            # 2. Customer Group: Input Box
            customer_group = st.text_input("Customer Group", help="Group Name?")

            # Amount
            loan_amount = st.number_input("Loan Amount", min_value=100000, value=1000000, step=100000, help="Total Loan Amount")

            # 6. Auditor Class: Dropdown
            auditor_classes = ["--","Registered", "Registered Auditor A", "Registered Auditor B", "Registered Auditor C"]
            auditor_class = st.selectbox("Auditor Class", options=auditor_classes)
        
        with col3:
            # 5. Auditor Name: Input Box
            auditor_name = st.text_input("Auditor Name")

            # years
            loan_years = st.number_input("Total Years", min_value=1, value=1, step=1, help="Estimated Years for Loan")

            # 3. Business Type: DropDown
            business_types = ["--","Trading", "Project Loan", "New Project", "Contractor", "Service", "Manufacturing", "Other"]
            business_type = st.selectbox("Business Type", options=business_types)

            # Auditor Requirement by ICAN
        
        # Return customer information as a dictionary
        # if len(customer_name) < 6:
        #     st.error("Please re-enter Customer Name")
        # if consolidation not in ["Consolidated", "Unconsolidated"]:
        #     st.error("Please select Consolidation")
        # if auditor_class not in auditor_classes[1:]:
        #     st.error("Please select Auditor Class")
        # if business_type not in business_types[1:]:
        #     st.error("Please select Business Type")

        customer_info = {
            "customer_name": customer_name,
            "customer_group": customer_group,
            "business_type": business_type,
            "branch": branch,
            "consolidation": consolidation,
            "auditor_name": auditor_name,
            "auditor_class": auditor_class
        }
    
    return customer_info

# Function to create a printable report
def create_printable_report(customer_info, financial_data, data_type):
    # Create HTML for the report
    html = f"""
    <html>
    <head>
        <title>Financial Report</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1 {{ color: #2c3e50; }}
            h2 {{ color: #3498db; margin-top: 20px; }}
            .customer-info {{ border: 1px solid #ddd; padding: 15px; margin-bottom: 20px; background-color: #f9f9f9; }}
            .financial-data {{ margin-top: 30px; }}
            table {{ border-collapse: collapse; width: 100%; margin-top: 10px; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            .print-header {{ display: flex; justify-content: space-between; }}
            .print-date {{ text-align: right; font-size: 0.9em; color: #777; }}
            .category {{ margin-top: 20px; margin-bottom: 10px; font-weight: bold; color: #2c3e50; }}
            @media print {{
                button {{ display: none; }}
            }}
        </style>
    </head>
    <body>
        <div class="print-header">
            <h1>Financial Report</h1>
            <div class="print-date">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
        </div>
        
        <h2>Customer Information</h2>
        <div class="customer-info">
            <table>
                <tr><th>Field</th><th>Value</th></tr>
                <tr><td>Customer Name</td><td>{customer_info['customer_name']}</td></tr>
                <tr><td>Customer Group</td><td>{customer_info['customer_group']}</td></tr>
                <tr><td>Business Type</td><td>{customer_info['business_type']}</td></tr>
                <tr><td>Consolidation</td><td>{customer_info['consolidation']}</td></tr>
                <tr><td>Auditor Name</td><td>{customer_info['auditor_name']}</td></tr>
                <tr><td>Auditor Class</td><td>{customer_info['auditor_class']}</td></tr>
            </table>
        </div>
        
        <h2>{data_type.title()} Financial Data</h2>
        <div class="financial-data">
    """
    
    # Group data into categories for better organization
    categories = {
        "Assets": ["Total Current Assets", "Total Non-Current Assets", "Total Assets"],
        "Liabilities": ["Total Current Liabilities", "Total Non-Current Liabilities", "Total Liabilities", "Long-term Debt"],
        "Equity": ["Total Equity", "Total Liabilities and Equity"],
        "Income": ["Operating Income", "Gross Profit", "Total Operating Expenses", "Interest Expense", "Net Operating Profit"],
        "Other": ["Depreciation", "Amortization", "Stocks Trading", "Inventory"]
    }
    
    # Add each category of financial data
    for category, fields in categories.items():
        html += f"<div class='category'>{category}</div>"
        html += "<table>"
        html += "<tr><th>Metric</th><th>Value</th></tr>"
        
        for field in fields:
            if field in financial_data:
                value = financial_data[field]
                html += f"<tr><td>{field}</td><td>{value:,}</td></tr>"
        
        html += "</table>"
    
    # Close the HTML
    html += """
        </div>
        
        <script>
            // Auto-print when the page loads
            window.onload = function() {
                // Add a print button
                var printButton = document.createElement('button');
                printButton.innerHTML = 'Print Report';
                printButton.style.margin = '20px 0';
                printButton.style.padding = '10px 15px';
                printButton.style.backgroundColor = '#3498db';
                printButton.style.color = 'white';
                printButton.style.border = 'none';
                printButton.style.borderRadius = '4px';
                printButton.style.cursor = 'pointer';
                printButton.onclick = function() { window.print(); };
                document.body.insertBefore(printButton, document.body.firstChild);
            };
        </script>
    </body>
    </html>
    """
    
    return html

def load_and_edit_yearly_data(all_years_data):
    """
    Loads financial data for a selected year and allows editing with multi-column layout.
    
    Parameters:
    all_years_data (dict): Dictionary containing data for all years with keys like 
                           'audited-2079', 'projected-2081', etc.
    
    Returns:
    tuple: (selected_year, edited_data)
    """
    # Define available years
    all_years_data_keys = list(all_years_data.keys())
    
    # Create a radio button for year selection
    selected_year = st.radio(
        "**Choose year:**",
        options=all_years_data_keys,
        index=0,
        help="Select the year for which you want to analyze financial ratios.",
        horizontal=True
    )
    
    # Get data for the selected year
    current_data = copy.deepcopy(all_years_data[selected_year])
    
    # Create a container for edited data
    edited_data = {}
    
    # Display editable fields
    st.subheader(f"Edit {selected_year} Data")
    
    # Create a form for editing
    with st.form(key=f"edit_form_{selected_year}"):
        # Get all field names
        all_fields = list(current_data.keys())
        
        # Calculate number of columns and rows
        num_columns = 3  # You can adjust this number
        num_fields = len(all_fields)
        fields_per_column = (num_fields + num_columns - 1) // num_columns
        
        # Create columns
        cols = st.columns(num_columns)
        
        # Distribute fields across columns
        for i, field in enumerate(all_fields):
            col_index = i // fields_per_column
            
            # Ensure we don't exceed the number of columns
            if col_index >= num_columns:
                col_index = num_columns - 1
                
            with cols[col_index]:
                value = current_data[field]
                field_key = f"{selected_year}_{field}"
                
                # Show the field name and an editable number input
                new_value = st.number_input(
                    label=field,
                    value=float(value) if value is not None else 0.0,
                    key=field_key,
                    format="%.2f"  # Format to 2 decimal places for cleaner display
                )
                
                # Store the edited value
                edited_data[field] = new_value
        
        # Submit button for the form - centered at the bottom
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            submit_button = st.form_submit_button(label="Save Changes")
    
    # If form was submitted
    if submit_button:
        st.success(f"Changes for {selected_year} saved successfully!")
        
        # Here you would typically save the edited data somewhere
        # all_years_data[selected_year] = edited_data
    
    return selected_year, edited_data

def return_auditednprojected_years(years_ratios):
    years_ratios_keys = years_ratios.keys()
    audited_years = [y for y in years_ratios_keys if is_audited(y)]
    projected_years = [y for y in years_ratios_keys if is_projected(y)]
    audited_years.sort(key=extract_year_from_key)
    projected_years.sort(key=extract_year_from_key)
    if not audited_years:
        st.error("Please verify the docs uploaded to the system")
    if not audited_years:
        st.error("Please verify the docs uploaded to the system")
    return audited_years, projected_years


def main():
    st.title("Decision Making") 
    # print(FIELD_MAPPINGS)

    # Sidebar for file upload
    with st.sidebar:
        st.header("Upload Financial Data")
        uploaded_file = st.file_uploader("Upload JSON file", type=["json"])

        # Add checkbox for scaling values
        values_in_thousands = st.checkbox(
            "**Values in thousands: '000**", 
            help="Check this if the values in your JSON file are in thousands"
        )
        
    if uploaded_file is not None:
        try:
            # Load the financial data
            financial_data = json.load(uploaded_file)
            
            # Extract all years of data
            all_years_data = {}
            if isinstance(financial_data, list):
                # Handle list structure
                for item in financial_data:
                    for key, data in item.items():
                        all_years_data[key] = data
            elif isinstance(financial_data, dict):
                all_years_data = financial_data
            else:
                st.error("Invalid JSON format. Expected a list or dictionary structure.")
                return

            # Metadata for the app
            all_years_data_keys = all_years_data.keys()

            # print("All Years Data:", all_years_data)

            # Display the customer information form and save the results
            customer_info = collect_customer_information()
            print(f"\n Customer Data: {customer_info}")

            st.divider()
            
            # If len(all_years_data)
            if values_in_thousands:
                all_years_data = convert_to_thousands(all_years_data)
                # st.info("Values have been multiplied by 1,000 as specified.")

            # print("All Years Data:", all_years_data)

            repayment_values = get_repayment_values(all_years_data_keys)
            print(f"Repayment {repayment_values}")
           


            # Calculate ratios for all years # TODO Repayment
            # TODO: CHECK EBITDA
            years_ratios = {}
            for year_key, data in all_years_data.items():
                year_repayment = repayment_values.get(year_key, 0)    # # Calculate DSCR with the specific repayment value
                years_ratios[year_key] = calculate_ratios_for_data(data, year_repayment) # TODO: CHECK EBITDA
                # calculate_ratios_for_data(data, principal_repayment=0):
                # years_ratios[year_key] = calculate_ratios_for_data(data, principal_repayment if is_projected(year_key) else 0)   # TODO ORIG
            # print(f"Years Ratios: {years_ratios}")
            

            # Metadata for the app
            audited_years, projected_years = return_auditednprojected_years(years_ratios)
            # years_ratios_keys = years_ratios.keys()
            # audited_years = [y for y in years_ratios_keys if is_audited(y)]
            # projected_years = [y for y in years_ratios_keys if is_projected(y)]
            # audited_years.sort(key=extract_year_from_key)
            # projected_years.sort(key=extract_year_from_key)

            # TODO: CHECK balance sheet for all years do some debugging
            # 1: total assest == total liabilities + equity
            # Net Operating profit & Interest expense is available
            # Inventory is there

            print(f" -- All years data keys: {list(all_years_data_keys)}")
            # print(f" -- Years ratio keys: {years_ratios_keys}")
            # print(f" -- Audited years: {audited_years}")
            # print(f" -- Projected years: {projected_years}")
            
            # # 0. Edit Data from Selected Years.
            # with st.expander("Edit data", expanded=False):
            #     load_and_edit_yearly_data(all_years_data)

            # 1. Select Financial Statements to Analyze
            st.subheader("Select Financial Statements to Analyze")
            selected_ratios = year_wise_financial_statements(all_years_data, years_ratios)
            st.button("Generate Printable Report")
            st.divider()

            # 2. Multi-year trend analysis
            st.subheader("All Actual & Projected - Trend Analysis")
            with st.expander("Numerical Trend Analysis (Comparable..)", expanded=False):
                all_trends_dataframe(years_ratios)

            # with st.expander("Trends Visualization", expanded=False):
            #     visualize_trends(selected_ratios, years_ratios)
                
            # st.divider()

            # # 3. Stress Testing Section
            # st.subheader("Stress Testing Analysis (projected)", help="Analyze how changes in key financial metrics would affect the company's financial ratios.")
            # with st.expander("Select Year for Stress Testing", expanded=False):
            #     complete_stress_test(all_years_data, projected_years)
            
            st.divider()
            
            # 4. Audited to Projected Trend Analysis
            st.subheader("Audited to Projected Trend Analysis")
            with st.expander("Audited (recent) to Projected (final)", expanded=False):
                audited_to_projected_trend(years_ratios)
                
        except Exception as e:
            st.error(f"An error occurred: {e}") # TODO
            st.error("Please check the JSON format and try again.")
            normal_page()
    else:
        # Display instructions when no file is uploaded
        normal_page()

if __name__ == "__main__":
    main()