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

    for loan in loan_data:

        if loan.end_date is None or loan.end_date > date.today():
            total_active_loans_amount += loan.loan_amount

        if loan.tenure > 0:
            total_on_time_payment_ratio_sum += (Decimal(loan.emis_paid_on_time) / Decimal(loan.tenure))
            num_loans_considered_for_ratio += 1

        if loan.emis_paid_on_time < loan.tenure:
            has_past_loan_delay = True

    if num_loans_considered_for_ratio == 0: 
        credit_score = 100 
    else:
        credit_score = 50 

        if num_loans_considered_for_ratio > 0:
            avg_on_time_ratio = total_on_time_payment_ratio_sum / num_loans_considered_for_ratio
            credit_score += min(50, int(avg_on_time_ratio * 50)) 

        if customer.current_debt > customer.approved_limit:
            credit_score -= 20 

        if total_active_loans_amount > customer.approved_limit:
            credit_score -= 10 

        if has_past_loan_delay:
            credit_score -= 10 

    credit_score = max(0, min(100, credit_score))
    return credit_score

def check_loan_eligibility(customer, requested_loan_amount, requested_tenure, credit_score, loan_data):
    """
    Checks loan eligibility and calculates corrected interest rate and EMI.
    """

    total_current_emis = Decimal('0.00')
    for loan in loan_data:
        if loan.customer == customer and (loan.end_date is None or loan.end_date > date.today()): 
            total_current_emis += loan.monthly_repayment_emi

    approved = False
    corrected_interest_rate = 0.0

    if credit_score > 70:
        approved = True
        corrected_interest_rate = 10.0 
    elif credit_score > 50:
        approved = True
        corrected_interest_rate = 12.0 
    elif credit_score > 30:
        approved = True
        corrected_interest_rate = 16.0 
    else:
        approved = False 

    if approved:
        monthly_interest_rate = Decimal(corrected_interest_rate / 100 / 12)
        if monthly_interest_rate > 0:
            requested_emi = (requested_loan_amount * monthly_interest_rate) / (1 - (1 + monthly_interest_rate)**-requested_tenure)
        else:
            requested_emi = requested_loan_amount / requested_tenure 

        if (total_current_emis + requested_emi) > (customer.monthly_salary * Decimal('0.50')):
            approved = False 

    if approved and (customer.current_debt + requested_loan_amount) > customer.approved_limit:
        approved = False

    monthly_installment = Decimal('0.00')
    if approved:
        monthly_installment = requested_emi.quantize(Decimal('0.01')) 

    return {
    "approved": approved,
    "interest_rate": corrected_interest_rate,  
    "corrected_interest_rate": float(corrected_interest_rate) if approved else 0.0,
    "monthly_installment": float(monthly_installment) if approved else 0.0,
}