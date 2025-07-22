from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from datetime import date
from dateutil.relativedelta import relativedelta

from .models import Customer, Loan
from .serializers import (
    CustomerRegistrationRequestSerializer,
    CustomerRegistrationResponseSerializer,
    CheckEligibilityRequestSerializer,
    CheckEligibilityResponseSerializer,
    CreateLoanRequestSerializer, 
    CreateLoanResponseSerializer,
    LoanDetailSerializer,
    NestedCustomerSerializer, 
    SingleLoanViewSerializer,
    LoanStatementSerializer
)
from .utils import calculate_credit_score, check_loan_eligibility
from decimal import Decimal

class RegisterCustomerView(APIView):
    """
    API endpoint for registering new customers.
    """
    def post(self, request, *args, **kwargs):
        serializer = CustomerRegistrationRequestSerializer(data=request.data) 
        if serializer.is_valid():
            customer = serializer.save() 
            response_serializer = CustomerRegistrationResponseSerializer(customer)

            print(f"DEBUG (View Post): Response Data being sent = {response_serializer.data}")

            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        print(f"DEBUG (View Post): Serializer Errors = {serializer.errors}")

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CheckEligibilityView(APIView):
    """
    API endpoint for checking loan eligibility of a customer.
    """
    def post(self, request, *args, **kwargs):
        serializer = CheckEligibilityRequestSerializer(data=request.data)
        if serializer.is_valid():
            customer_id = serializer.validated_data['customer_id']
            loan_amount = serializer.validated_data['loan_amount']
            tenure = serializer.validated_data['tenure']

            try:
                customer = Customer.objects.get(customer_id=customer_id)
            except Customer.DoesNotExist:
                return Response(
                    {"customer_id": "Customer with this ID does not exist."},
                    status=status.HTTP_404_NOT_FOUND
                )

            customer_loans = Loan.objects.filter(customer=customer)

            credit_score = calculate_credit_score(customer, customer_loans)

            eligibility_result = check_loan_eligibility(
                customer,
                loan_amount,
                tenure,
                credit_score,
                customer_loans
            )

            response_data = {
    "customer_id": customer.customer_id,
    "approval": eligibility_result["approved"],
    "interest_rate": Decimal(str(eligibility_result["interest_rate"])).quantize(Decimal("1.00")),
    "corrected_interest_rate": Decimal(str(eligibility_result["corrected_interest_rate"])).quantize(Decimal("1.00")),
    "tenure": tenure,
    "monthly_installment": Decimal(str(eligibility_result["monthly_installment"])).quantize(Decimal("1.00")),
}

            response_serializer = CheckEligibilityResponseSerializer(response_data)
            return Response(response_serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class CreateLoanView(APIView):
    """
    API endpoint for creating a new loan for a customer.
    Performs eligibility check before creating the loan.
    """
    def post(self, request, *args, **kwargs):
        serializer = CreateLoanRequestSerializer(data=request.data)
        if serializer.is_valid():
            customer = serializer.validated_data['customer']
            loan_amount = serializer.validated_data['loan_amount']
            tenure = serializer.validated_data['tenure']
            requested_interest_rate = serializer.validated_data['interest_rate'] 

            customer_loans = Loan.objects.filter(customer=customer)

            credit_score = calculate_credit_score(customer, customer_loans)

            eligibility_result = check_loan_eligibility(
                customer,
                loan_amount,
                tenure,
                credit_score,
                customer_loans
            )

            approved = eligibility_result["approved"]
            corrected_interest_rate = eligibility_result["corrected_interest_rate"]
            monthly_installment = eligibility_result["monthly_installment"]

            if approved:

                try:
                    with transaction.atomic():

                        loan = Loan.objects.create(
                            customer=customer,
                            loan_amount=loan_amount,
                            tenure=tenure,
                            interest_rate=corrected_interest_rate, 
                            monthly_repayment_emi=monthly_installment,
                            emis_paid_on_time=0, 
                            start_date=date.today(),
                            end_date=date.today() + relativedelta(months=+tenure)
                        )

                        customer.current_debt += loan_amount
                        customer.save()

                        response_data = {
                            "loan_id": loan.loan_id,
                            "customer_id": customer.customer_id,
                            "loan_approved": True,
                            "message": "Loan approved",
                            "monthly_repayment_emi": monthly_installment,
                        }
                        return Response(response_data, status=status.HTTP_201_CREATED)
                except Exception as e:

                    print(f"Error creating loan or updating customer debt: {e}")
                    return Response(
                        {"message": "An internal error occurred during loan creation."},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
            else:

                response_data = {
                    "loan_id": None,
                    "customer_id": customer.customer_id,
                    "loan_approved": False,
                    "message": "Loan not approved",
                    "monthly_repayment_emi": 0.0,
                    "corrected_interest_rate": corrected_interest_rate 
                }

                return Response(response_data, status=status.HTTP_200_OK) 

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class GetLoanByCustomerView(APIView):
    """
    API endpoint for retrieving all loans for a given customer_id.
    """
    def get(self, request, customer_id, *args, **kwargs):
        try:
            customer = Customer.objects.get(customer_id=customer_id)
        except Customer.DoesNotExist:
            return Response(
                {"customer_id": "Customer with this ID does not exist."},
                status=status.HTTP_404_NOT_FOUND
            )

        loans = Loan.objects.filter(customer=customer)
        serializer = LoanDetailSerializer(loans, many=True) 

        return Response(serializer.data, status=status.HTTP_200_OK)

class ViewLoanStatementView(APIView):
    """
    API endpoint for retrieving a detailed statement for a specific loan.
    """
    def get(self, request, customer_id, loan_id, *args, **kwargs):
        try:
            customer = Customer.objects.get(customer_id=customer_id)
        except Customer.DoesNotExist:
            return Response(
                {"customer_id": "Customer with this ID does not exist."},
                status=status.HTTP_404_NOT_FOUND
            )

        try:

            loan = Loan.objects.get(loan_id=loan_id, customer=customer)
        except Loan.DoesNotExist:
            return Response(
                {"loan_id": "Loan with this ID not found for the given customer."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = LoanStatementSerializer(loan)
        return Response(serializer.data, status=status.HTTP_200_OK)

class ViewSingleLoanView(APIView):
    """
    API endpoint for retrieving details of a single loan and its associated customer.
    """
    def get(self, request, loan_id, *args, **kwargs):
        try:
            loan = Loan.objects.get(loan_id=loan_id)
        except Loan.DoesNotExist:
            return Response(
                {"loan_id": "Loan with this ID does not exist."},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = SingleLoanViewSerializer(loan)
        return Response(serializer.data, status=status.HTTP_200_OK)