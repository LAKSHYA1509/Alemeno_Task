from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import Customer, Loan
from .serializers import (
    CustomerRegistrationRequestSerializer,
    CustomerRegistrationResponseSerializer,
    CheckEligibilityRequestSerializer,
    CheckEligibilityResponseSerializer,
    CreateLoanRequestSerializer, # Import new serializer
    CreateLoanResponseSerializer,
    LoanDetailSerializer,
    NestedCustomerSerializer, # Import new serializer
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
        serializer = CustomerRegistrationRequestSerializer(data=request.data) # Use the correct serializer name
        if serializer.is_valid():
            customer = serializer.save() # This calls the create method in the serializer
            response_serializer = CustomerRegistrationResponseSerializer(customer)
             # --- DEBUG PRINT START ---
            print(f"DEBUG (View Post): Response Data being sent = {response_serializer.data}")
            # --- DEBUG PRINT END ---

            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        
        # --- DEBUG PRINT START ---
        print(f"DEBUG (View Post): Serializer Errors = {serializer.errors}")
        # --- DEBUG PRINT END ---
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

            # 🔧 FIXED: interest_rate was incorrectly using `approved_limit` before
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
            requested_interest_rate = serializer.validated_data['interest_rate'] # Original rate requested

            # Fetch all loans related to this customer for credit score and EMI calculation
            customer_loans = Loan.objects.filter(customer=customer)

            # Calculate credit score
            credit_score = calculate_credit_score(customer, customer_loans)

            # Determine loan eligibility and corrected interest rate
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
                # Use a database transaction to ensure atomicity
                try:
                    with transaction.atomic():
                        # Create the new loan record
                        loan = Loan.objects.create(
                            customer=customer,
                            loan_amount=loan_amount,
                            tenure=tenure,
                            interest_rate=corrected_interest_rate, # Use corrected rate for the loan
                            monthly_repayment_emi=monthly_installment,
                            emis_paid_on_time=0, # New loan starts with 0 EMIs paid
                            start_date=date.today(),
                            end_date=date.today().replace(month=date.today().month + tenure) # Simple end date calc
                        )

                        # Update customer's current debt
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
                    # Log the error for debugging
                    print(f"Error creating loan or updating customer debt: {e}")
                    return Response(
                        {"message": "An internal error occurred during loan creation."},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
            else:
                # Loan not approved, return appropriate response
                response_data = {
                    "loan_id": None,
                    "customer_id": customer.customer_id,
                    "loan_approved": False,
                    "message": "Loan not approved",
                    "monthly_repayment_emi": 0.0,
                    "corrected_interest_rate": corrected_interest_rate # Show the corrected rate even if not approved
                }
                # If the assignment requires specific reasons for rejection, add them here.
                return Response(response_data, status=status.HTTP_200_OK) # Return 200 OK for rejection, as it's a valid outcome of the check

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
        serializer = LoanDetailSerializer(loans, many=True) # `many=True` because it's a list of objects

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
            # Ensure the loan belongs to the specified customer
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