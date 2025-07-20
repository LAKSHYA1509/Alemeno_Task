# core/utils.py
from decimal import Decimal
from datetime import date

def calculate_credit_score(customer, loan_data):
    """
    Calculates the credit score for a given customer.
    """
    credit_score = 0

    total_active_loans_amount = Decimal('0.00')
    total_on_time_payment_ratio_sum = Decimal('0.00')
    num_loans_considered_for_ratio = 0
    has_past_loan_delay = False
    
    # Check for any active loans and calculate on-time payment ratio
    for loan in loan_data:
        # Check if loan is active
        if loan.end_date is None or loan.end_date > date.today():
            total_active_loans_amount += loan.loan_amount

        # For credit score, consider all loans (past and current) for on-time payment history
        if loan.tenure > 0:
            total_on_time_payment_ratio_sum += (Decimal(loan.emis_paid_on_time) / Decimal(loan.tenure))
            num_loans_considered_for_ratio += 1

        # Check for any loan that has had EMIs paid on time less than its tenure
        # This is a simple indicator of potential past delays.
        if loan.emis_paid_on_time < loan.tenure:
            has_past_loan_delay = True


    # Base Credit Score Logic
    if num_loans_considered_for_ratio == 0: # No past or current loans
        credit_score = 100 # Default score for customers with no loan history
    else:
        credit_score = 50 # Base score for customers with loan history

        # Positive impact from on-time payments
        if num_loans_considered_for_ratio > 0:
            avg_on_time_ratio = total_on_time_payment_ratio_sum / num_loans_considered_for_ratio
            credit_score += min(50, int(avg_on_time_ratio * 50)) # Max 50 points from this part

        # Negative impact from high current debt relative to approved limit
        if customer.current_debt > customer.approved_limit:
            credit_score -= 20 # Significant penalty

        # Negative impact from sum of active loans relative to approved limit
        if total_active_loans_amount > customer.approved_limit:
            credit_score -= 10 # Penalty if active loan amount is too high

        # Negative impact from past loan delays
        if has_past_loan_delay:
            credit_score -= 10 # Penalty for any past delays

    # Ensure score is within 0-100 range
    credit_score = max(0, min(100, credit_score))
    return credit_score

def check_loan_eligibility(customer, requested_loan_amount, requested_tenure, credit_score, loan_data):
    """
    Checks loan eligibility and calculates corrected interest rate and EMI.
    """
    # Get total current EMIs
    total_current_emis = Decimal('0.00')
    for loan in loan_data:
        if loan.customer == customer and (loan.end_date is None or loan.end_date > date.today()): # Active loan
            total_current_emis += loan.monthly_repayment_emi

    # Rule 1: Credit Score based approval and interest rate
    approved = False
    corrected_interest_rate = 0.0

    if credit_score > 70:
        approved = True
        corrected_interest_rate = 10.0 # 10%
    elif credit_score > 50:
        approved = True
        corrected_interest_rate = 12.0 # 12%
    elif credit_score > 30:
        approved = True
        corrected_interest_rate = 16.0 # 16%
    else:
        approved = False # Credit score too low

    # Rule 2: Sum of current EMIs + requested EMI should not exceed 50% of monthly income
    # Calculate EMI for requested loan *with* the corrected interest rate
    # Using a simplified EMI formula for now (Principal * (rate/12) / (1 - (1 + rate/12)^-tenure))
    # This is a common approximation. For exact, use proper financial formula.
    if approved:
        monthly_interest_rate = Decimal(corrected_interest_rate / 100 / 12)
        if monthly_interest_rate > 0:
            requested_emi = (requested_loan_amount * monthly_interest_rate) / (1 - (1 + monthly_interest_rate)**-requested_tenure)
        else:
            requested_emi = requested_loan_amount / requested_tenure # If interest rate is 0

        if (total_current_emis + requested_emi) > (customer.monthly_salary * Decimal('0.50')):
            approved = False # EMI burden too high

    # Rule 3: Requested loan amount + current debt must not exceed approved limit
    if approved and (customer.current_debt + requested_loan_amount) > customer.approved_limit:
        approved = False

    monthly_installment = Decimal('0.00')
    if approved:
        monthly_installment = requested_emi.quantize(Decimal('0.01')) # Round to 2 decimal places

    return {
    "approved": approved,
    "interest_rate": corrected_interest_rate,  # ✅ Add this line
    "corrected_interest_rate": float(corrected_interest_rate) if approved else 0.0,
    "monthly_installment": float(monthly_installment) if approved else 0.0,
}
