import os
import pandas as pd
from celery import shared_task
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from .models import Customer, Loan

def normalize_headers(df):
    """
    Normalize column headers to lowercase with underscores and no leading/trailing spaces.
    """
    df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
    return df

@shared_task
def import_customer_data_task():
    """
    Celery task to import customer data from customer_data.xlsx.
    Assumes headers: customer_id, first_name, last_name, age, phone_number, monthly_salary, approved_limit, current_debt
    """
    file_path = os.path.join(os.getcwd(), 'data', 'customer_data.xlsx')

    try:
        df = pd.read_excel(file_path)
        df = normalize_headers(df)
        print("Normalized columns:", df.columns.tolist())

        for index, row in df.iterrows():
            try:
                customer_id = row['customer_id']
                first_name = row['first_name']
                last_name = row['last_name']
                phone_number = str(int(row['phone_number']))  
                monthly_salary = Decimal(str(row['monthly_salary']))

                approved_limit = (36 * monthly_salary).quantize(Decimal('100000'), rounding=ROUND_HALF_UP)

                current_debt = Decimal(str(row['current_debt'])) if 'current_debt' in row and not pd.isnull(row['current_debt']) else Decimal('0.00')

                customer, created = Customer.objects.update_or_create(
                    customer_id=customer_id,
                    defaults={
                        'first_name': first_name,
                        'last_name': last_name,
                        'phone_number': phone_number,
                        'monthly_salary': monthly_salary,
                        'approved_limit': approved_limit,
                        'current_debt': current_debt,
                    }
                )

                print(f"{'Created' if created else 'Updated'} customer: {customer.first_name} {customer.last_name} (ID: {customer.customer_id})")

            except Exception as row_error:
                print(f"[Customer Row Error] {row_error}. Row data: {row.to_dict()}")

    except FileNotFoundError:
        print(f"[Error] File not found: {file_path}")
    except Exception as e:
        print(f"[Import Error] {e}")

@shared_task
def import_loan_data_task():
    """
    Celery task to import loan data from loan_data.xlsx.
    Assumes headers: customer_id, loan_id, loan_amount, tenure, interest_rate, monthly_payment, emis_paid_on_time, date_of_approval, end_date
    """
    file_path = os.path.join(os.getcwd(), 'data', 'loan_data.xlsx')

    try:
        df = pd.read_excel(file_path)
        df = normalize_headers(df)

        for index, row in df.iterrows():
            try:
                customer_id = row['customer_id']
                try:
                    customer = Customer.objects.get(customer_id=customer_id)
                except Customer.DoesNotExist:
                    print(f"[Skip] Loan {row['loan_id']} skipped: Customer {customer_id} not found.")
                    continue

                start_date = pd.to_datetime(row['date_of_approval']).date()
                end_date = pd.to_datetime(row['end_date']).date()

                loan, created = Loan.objects.update_or_create(
                    loan_id=row['loan_id'],
                    defaults={
                        'customer': customer,
                        'loan_amount': Decimal(str(row['loan_amount'])),
                        'tenure': int(row['tenure']),
                        'interest_rate': Decimal(str(row['interest_rate'])),
                        'monthly_repayment_emi': Decimal(str(row['monthly_payment'])),
                        'emis_paid_on_time': int(row['emis_paid_on_time']),
                        'start_date': start_date,
                        'end_date': end_date,
                    }
                )

                print(f"{'Created' if created else 'Updated'} loan: {loan.loan_id} for customer {customer.customer_id}")

            except Exception as row_error:
                print(f"[Loan Row Error] {row_error}. Row data: {row.to_dict()}")

    except FileNotFoundError:
        print(f"[Error] File not found: {file_path}")
    except Exception as e:
        print(f"[Import Error] {e}")