from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from decimal import Decimal
from datetime import date

from .models import Customer, Loan
from .utils import calculate_credit_score, check_loan_eligibility
from .serializers import CustomerRegistrationRequestSerializer

class CustomerModelTests(TestCase):
    """
    Tests for the Customer model.
    """
    def test_create_customer(self):
        customer = Customer.objects.create(
            first_name="Test",
            last_name="User",
            phone_number="1234567890",
            monthly_salary=Decimal("50000.00"),
            approved_limit=Decimal("1800000.00"),
            current_debt=Decimal("0.00")
        )
        self.assertIsInstance(customer, Customer)
        self.assertEqual(customer.first_name, "Test")
        self.assertEqual(customer.approved_limit, Decimal("1800000.00"))

    def test_phone_number_uniqueness(self):
        Customer.objects.create(
            first_name="Test", last_name="User", phone_number="1112223333",
            monthly_salary=Decimal("50000.00"), approved_limit=Decimal("1800000.00")
        )
        with self.assertRaises(Exception): 
            Customer.objects.create(
                first_name="Another", last_name="User", phone_number="1112223333",
                monthly_salary=Decimal("60000.00"), approved_limit=Decimal("2160000.00")
            )

class LoanModelTests(TestCase):
    """
    Tests for the Loan model.
    """
    def setUp(self):
        self.customer = Customer.objects.create(
            first_name="Loan", last_name="Customer", phone_number="9998887777",
            monthly_salary=Decimal("100000.00"), approved_limit=Decimal("3600000.00"),
            current_debt=Decimal("0.00")
        )

    def test_create_loan(self):
        loan = Loan.objects.create(
            customer=self.customer,
            loan_amount=Decimal("500000.00"),
            tenure=12,
            interest_rate=Decimal("10.00"),
            monthly_repayment_emi=Decimal("45000.00"),
            emis_paid_on_time=0,
            start_date=date(2025, 1, 1),
            end_date=date(2026, 1, 1)
        )
        self.assertIsInstance(loan, Loan)
        self.assertEqual(loan.customer, self.customer)
        self.assertEqual(loan.loan_amount, Decimal("500000.00"))

class UtilityFunctionTests(TestCase):
    """
    Tests for utility functions in core/utils.py.
    """
    def setUp(self):

        self.customer1 = Customer.objects.create(
            first_name="Eligible", last_name="Customer", phone_number="1111111111",
            monthly_salary=Decimal("100000.00"), approved_limit=Decimal("3600000.00"),
            current_debt=Decimal("0.00")
        )
        self.customer2 = Customer.objects.create(
            first_name="HighDebt", last_name="Customer", phone_number="2222222222",
            monthly_salary=Decimal("50000.00"), approved_limit=Decimal("1800000.00"),
            current_debt=Decimal("2000000.00") 
        )
        self.customer3 = Customer.objects.create(
            first_name="LowIncome", last_name="Customer", phone_number="3333333333",
            monthly_salary=Decimal("10000.00"), approved_limit=Decimal("360000.00"),
            current_debt=Decimal("0.00")
        )

        self.loan1_c1 = Loan.objects.create(
            customer=self.customer1, loan_amount=Decimal("100000.00"), tenure=12,
            interest_rate=Decimal("10.00"), monthly_repayment_emi=Decimal("9000.00"),
            emis_paid_on_time=12, start_date=date(2024, 1, 1), end_date=date(2025, 1, 1)
        )
        self.loan2_c1 = Loan.objects.create(
            customer=self.customer1, loan_amount=Decimal("50000.00"), tenure=6,
            interest_rate=Decimal("12.00"), monthly_repayment_emi=Decimal("8500.00"),
            emis_paid_on_time=3, start_date=date(2025, 3, 1), end_date=date(2025, 9, 1)
        )
        self.loan3_c2 = Loan.objects.create(
            customer=self.customer2, loan_amount=Decimal("1000000.00"), tenure=60,
            interest_rate=Decimal("15.00"), monthly_repayment_emi=Decimal("23790.00"),
            emis_paid_on_time=50, start_date=date(2023, 1, 1), end_date=date(2028, 1, 1)
        )

    def test_calculate_credit_score_no_loans(self):
        customer = Customer.objects.create(
            first_name="New", last_name="Guy", phone_number="4444444444",
            monthly_salary=Decimal("70000.00"), approved_limit=Decimal("2520000.00"),
            current_debt=Decimal("0.00")
        )
        score = calculate_credit_score(customer, [])
        self.assertEqual(score, 100) 

    def test_calculate_credit_score_good_history(self):

        score = calculate_credit_score(self.customer1, [self.loan1_c1, self.loan2_c1])
        self.assertEqual(score, 77) 

    def test_calculate_credit_score_high_debt(self):

        score = calculate_credit_score(self.customer2, [self.loan3_c2])
        self.assertEqual(score, 61) 

    def test_check_loan_eligibility_approved_high_score(self):
        eligibility = check_loan_eligibility(
            self.customer1, Decimal("100000.00"), 12, 80, [self.loan1_c1, self.loan2_c1]
        )
        self.assertTrue(eligibility["approved"])
        self.assertEqual(eligibility["corrected_interest_rate"], 10.0)
        self.assertGreater(eligibility["monthly_installment"], 0)

    def test_check_loan_eligibility_approved_medium_score(self):

        eligibility = check_loan_eligibility(
            self.customer1, Decimal("100000.00"), 12, 60, [self.loan1_c1, self.loan2_c1]
        )
        self.assertTrue(eligibility["approved"])
        self.assertEqual(eligibility["corrected_interest_rate"], 12.0)

    def test_check_loan_eligibility_rejected_low_score(self):

        eligibility = check_loan_eligibility(
            self.customer1, Decimal("100000.00"), 12, 20, [self.loan1_c1, self.loan2_c1]
        )
        self.assertFalse(eligibility["approved"])
        self.assertEqual(eligibility["corrected_interest_rate"], 0.0)
        self.assertEqual(eligibility["monthly_installment"], 0.0)

    def test_check_loan_eligibility_rejected_high_emi_burden(self):

        customer = Customer.objects.create(
            first_name="Emi", last_name="Burden", phone_number="5555555555",
            monthly_salary=Decimal("10000.00"), approved_limit=Decimal("360000.00"),
            current_debt=Decimal("0.00")
        )

        Loan.objects.create(
            customer=customer, loan_amount=Decimal("100000.00"), tenure=12,
            interest_rate=Decimal("10.00"), monthly_repayment_emi=Decimal("4500.00"), 
            emis_paid_on_time=0, start_date=date(2025, 1, 1), end_date=date(2026, 1, 1)
        )

        eligibility = check_loan_eligibility(
            customer, Decimal("10000.00"), 12, 80, Loan.objects.filter(customer=customer)
        )
        self.assertFalse(eligibility["approved"])

class RegisterAPITests(APITestCase):
    """
    Tests for the /api/register API endpoint.
    """
    def test_register_new_customer_success(self):
        url = reverse('register_customer')
        data = {
            "first_name": "Api",
            "last_name": "Test",
            "age": 25,
            "monthly_income": 80000.00, 
            "phone_number": "9999999999"
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('customer_id', response.data)
        self.assertEqual(response.data['name'], "Api Test")
        self.assertEqual(response.data['monthly_income'], "80000.00") 
        self.assertEqual(response.data['approved_limit'], "2900000.00") 

    def test_register_customer_duplicate_phone_number(self):
        url = reverse('register_customer')
        Customer.objects.create(
            first_name="Existing", last_name="User", phone_number="1231231234",
            monthly_salary=Decimal("50000.00"), approved_limit=Decimal("1800000.00")
        )
        data = {
            "first_name": "Another",
            "last_name": "One",
            "age": 30,
            "monthly_income": 70000.00, 
            "phone_number": "1231231234" 
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('phone_number', response.data)
        self.assertEqual(response.data['phone_number'][0], "A customer with this phone number already exists.")

    def test_register_customer_invalid_monthly_salary(self): 
        url = reverse('register_customer')
        data = {
            "first_name": "Invalid",
            "last_name": "Salary",
            "age": 25,
            "monthly_income": 0.00, 
            "phone_number": "8888888888"
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('monthly_income', response.data) 
        self.assertEqual(response.data['monthly_income'][0], "Monthly income must be greater than zero.") 

