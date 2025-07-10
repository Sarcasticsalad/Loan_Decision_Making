from utils.logs import setup_logger
from .general import find_value, get_status, FIELD_MAPPINGS



logger = setup_logger()         

def safe_division(numerator, denominator):
    """Safely divide two numbers, handling zero division."""
    if denominator == 0:
        return float('nan')
    return numerator / denominator

# TODO: -ve EBITDA: do not proceed with calculations
# TODO: Total Assets is not equal to Total Liabilities + Equity: do not proceed with calculations
def calculate_ebitda(operating_profit, interest_expense, depreciation, amortization, taxation,profit_after_tax, administration_expense):
    """
    Calculate EBITDA (Earnings Before Interest, Taxes, Depreciation, and Amortization)
    """
    
    # CASE 1:
    operating_profit = abs(operating_profit) # profit/loss (Before)
    interest_expense = abs(interest_expense)
    depreciation = abs(depreciation)
    amortization = abs(amortization)
    taxation = abs(taxation)
    administration_expense = abs(administration_expense)

    # return operating_profit + interest_expense + depreciation + amortization
    return profit_after_tax + taxation + interest_expense + depreciation + administration_expense

def calculate_leverage_ratio(total_liabilities, total_equity):
    """Calculate Leverage Ratio (Total Liabilities / Total Equity)."""
    return safe_division(total_liabilities, total_equity)

def calculate_gear_ratio(term_loan, total_equity):
    """Calculate Gear Ratio (Term Loan and Finance / Total Equity)."""
    total_equity = abs(total_equity)
    if not isinstance(total_equity,(int,float)):
        return "Data is not complete (total_equity is missing)"
    
    return safe_division(term_loan, total_equity)

# TODO: ICR
def calculate_icr(interest_expense, depreciation, amortization, operating_profit):
    """Calculate Interest Coverage Ratio (EBIT / Interest Expense)."""
    # ebitda = calculate_ebitda(data)
    # if not isinstance(ebitda,(int,float)):
    #     return st.error("Could not proceed with ICR calculation (EBITDA is missing)")
    
    if not isinstance(interest_expense,(int,float)):
        return "Could not proceed with ICR calculation (Interest Expense is missing)"
    abs_interest_expense = abs(interest_expense)
    # Case: 1
    # return safe_division(ebitda, interest_expense)

    # Case: 2
    val = abs(operating_profit)-(abs_interest_expense+abs(amortization)+abs(depreciation))

    return safe_division(val, interest_expense)

def calculate_dscr(interest_expense, depreciation, amortization, operating_profit, principal_repayment=0):
    """Calculate Debt Service Coverage Ratio (EBITDA / (Interest Expense + Principal Repayment))."""

    # Case 1:
    # ebitda = calculate_ebitda(data)
    debt_service = interest_expense + principal_repayment
    # return safe_division(ebitda, debt_service)

    # Case: 2
    abs_interest_expense = abs(interest_expense)
    val = abs(operating_profit)-(abs_interest_expense+abs(amortization)+abs(depreciation))

    return safe_division(val,debt_service)

def calculate_cr(current_assets, current_liabilities):
    """Calculate Current Ratio (Current Assets / Current Liabilities)."""

    return safe_division(current_assets, current_liabilities)

def calculate_qr(current_assets, current_liabilities, inventory=0):
    """Calculate Quick Ratio ((Current Assets - Inventory) / Current Liabilities)."""
    if not isinstance(inventory,(int,float)):
        inventory = 0
    
    return safe_division((current_assets - inventory), current_liabilities)


def calculate_ratios_for_data(data, principal_repayment=0):
    """Calculate all financial ratios for a given data set."""

    # print(f"calculate_ratios_for_data - {principal_repayment}")
    logger.info(f"Data :{data}")
    # PL
    operating_profit = find_value(data, FIELD_MAPPINGS["Net Operating Profit"])
    interest_expense = find_value(data, FIELD_MAPPINGS["Interest Expense"])
    depreciation = find_value(data, FIELD_MAPPINGS["Depreciation"])
    amortization = find_value(data, FIELD_MAPPINGS["Amortization"])
    taxation = find_value(data, FIELD_MAPPINGS["Taxation"])
    administration_expense = find_value(data, FIELD_MAPPINGS["Administration Expenses"])
    profit_after_tax = find_value(data,FIELD_MAPPINGS["Profit After Tax"])

    #BS
    total_liabilities = find_value(data, FIELD_MAPPINGS["Total Liabilities"])
    current_liabilities = find_value(data, FIELD_MAPPINGS["Total Current Liabilities"])
    total_equity = find_value(data, FIELD_MAPPINGS["Total Equity"])
    current_assets = find_value(data, FIELD_MAPPINGS["Total Current Assets"])

    # total_liabilities_equity = find_value(data, FIELD_MAPPINGS["total_liabilities_equity"]) # Can be removed
    # non_current_liabilities = find_value(data, FIELD_MAPPINGS["total_non_current_liabilities"]) # Can be removed
    
    # if total_liabilities == 0:
    #     total_liabilities = current_liabilities + non_current_liabilities

    # if total_liabilities == 0:
    #     total_liabilities = total_liabilities_equity - total_equity
    
    # if total_equity == 0:
    #     total_equity = total_liabilities_equity - total_liabilities

    term_loan = find_value(data, FIELD_MAPPINGS["Term Loan"]) # Long term Debt
    inventory = find_value(data, FIELD_MAPPINGS["Inventory"])


    ratios = {
        "EBITDA": {"value": calculate_ebitda(operating_profit, interest_expense, depreciation, amortization, taxation, profit_after_tax, administration_expense)},
        "Leverage Ratio": {"value": calculate_leverage_ratio(total_liabilities, total_equity)},
        "Gear Ratio": {"value": calculate_gear_ratio(term_loan, total_equity)},
        "ICR": {"value": calculate_icr(interest_expense, depreciation, amortization, operating_profit)},
        "DSCR": {"value": calculate_dscr(interest_expense, depreciation, amortization, operating_profit, principal_repayment)},
        "CR": {"value": calculate_cr(current_assets, current_liabilities)},
        "QR": {"value": calculate_qr(current_assets, current_liabilities, inventory)}
    }
    
    # Determine status for each ratio
    for ratio_name in ratios:
        ratios[ratio_name]["status"], ratios[ratio_name]["message"], ratios[ratio_name]["color"] = get_status(
            ratio_name, ratios[ratio_name]["value"]
        )
    
    # print(f"calculate_ratios_for_data - Ratios: {[(ratio_name,ratios[ratio_name]['value']) for ratio_name in ratios]}")
    # print(f"{'***********'*2}")
    logger.info(f"Ratios: {ratios}")
    return ratios
