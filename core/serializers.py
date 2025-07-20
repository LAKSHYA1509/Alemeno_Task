from rest_framework import serializers
from decimal import Decimal, ROUND_HALF_UP
from core.models import Customer, Loan
from datetime import date

# -------------------------------
# Customer Registration Serializers
# -------------------------------

class CheckEligibilityResponseSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField()
    approval = serializers.BooleanField()
    interest_rate = serializers.DecimalField(max_digits=5, decimal_places=2)  # ✅ NEW FIELD
    corrected_interest_rate = serializers.DecimalField(max_digits=5, decimal_places=2)
    tenure = serializers.IntegerField()
    monthly_installment = serializers.DecimalField(max_digits=10, decimal_places=2)
    
class NestedCustomerSerializer(serializers.ModelSerializer):
    """
    Serializer for embedding customer details within other responses.
    Includes: id, first_name, last_name, phone_number.
    NOTE: 'age' is requested but not in your Customer model.
        If you need 'age', please add it to core/models.py and run migrations.
    """
    class Meta:
        model = Customer
        fields = ['customer_id', 'first_name', 'last_name', 'phone_number']
        # If 'age' is added to Customer model, uncomment the line below:
        # fields = ['customer_id', 'first_name', 'last_name', 'phone_number', 'age']


class CustomerRegistrationResponseSerializer(serializers.ModelSerializer):
    """
    Serializer for the response of customer registration.
    Output fields for the API response.
    """
    name = serializers.SerializerMethodField()
    monthly_income = serializers.DecimalField(source='monthly_salary', max_digits=10, decimal_places=2)

    class Meta:
        model = Customer
        fields = [
            'customer_id',
            'name',             # 🐛 CRITICAL FIX: Ensure 'name' is in the fields list
            'monthly_income',
            'approved_limit',
            'phone_number'
            # If 'age' is in your Customer model and you want it in response:
            # 'age'
        ]

    def get_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"


# -------------------------------
# Eligibility Check Serializers
# -------------------------------

class CheckEligibilityRequestSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField()
    loan_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    tenure = serializers.IntegerField()

    def validate(self, data):
        customer_id = data.get('customer_id')
        loan_amount = data.get('loan_amount')
        tenure = data.get('tenure')

        if not Customer.objects.filter(customer_id=customer_id).exists():
            raise serializers.ValidationError({"customer_id": "Customer with this ID does not exist."})

        if loan_amount <= 0:
            raise serializers.ValidationError({"loan_amount": "Loan amount must be positive."})

        if tenure <= 0:
            raise serializers.ValidationError({"tenure": "Tenure must be positive."})

        return data


class CustomerRegistrationRequestSerializer(serializers.Serializer):
    """
    Serializer for handling customer registration requests.
    Input fields from the API request.
    """
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    age = serializers.IntegerField()
    # 🐛 FIX: Ensure this field name is 'monthly_income'
    monthly_income = serializers.DecimalField(max_digits=10, decimal_places=2)
    phone_number = serializers.CharField(max_length=20)

    def validate_phone_number(self, value):
        """
        Custom validation for phone number to ensure it's unique.
        """
        if Customer.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("A customer with this phone number already exists.")
        return value

    # 🐛 FIX: Ensure this validation method is for 'monthly_income'
    def validate_monthly_income(self, value):
        if value <= 0:
            raise serializers.ValidationError("Monthly income must be greater than zero.")
        return value

    def create(self, validated_data):
        """
        Create and return a new `Customer` instance, given the validated data.
        """
        monthly_salary_from_income = validated_data['monthly_income']
        
        # --- DEBUG PRINTS START ---
        print(f"\nDEBUG (Serializer Create): monthly_income = {monthly_salary_from_income} (type: {type(monthly_salary_from_income)})")
        # --- DEBUG PRINTS END ---

        calculated_approved_limit_raw = 36 * monthly_salary_from_income
        
        # --- DEBUG PRINTS START ---
        print(f"DEBUG (Serializer Create): raw_approved_limit = {calculated_approved_limit_raw}")
        # --- DEBUG PRINTS END ---

        # 🐛 FIX: More robust rounding to nearest lakh (100,000)
        # Step 1: Divide by 100,000 to get the number in "lakhs"
        temp_val_in_lakhs = calculated_approved_limit_raw / Decimal('100000')
        
        # Step 2: Round this number to the nearest whole integer (e.g., 28.8 becomes 29)
        # We use quantize with Decimal('1') to round to zero decimal places
        rounded_lakhs = temp_val_in_lakhs.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        
        # Step 3: Multiply back by 100,000 to get the final approved_limit
        approved_limit = rounded_lakhs * Decimal('100000')
        
        # Ensure the final result has 2 decimal places for consistency with the model field
        approved_limit = approved_limit.quantize(Decimal('0.01'))

        # --- DEBUG PRINTS START ---
        print(f"DEBUG (Serializer Create): rounded_approved_limit = {approved_limit}")
        # --- DEBUG PRINTS END ---

        customer = Customer.objects.create(
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            # age=validated_data['age'], # Uncomment if you added 'age' field to Customer model
            phone_number=validated_data['phone_number'],
            monthly_salary=monthly_salary_from_income, # Store as monthly_salary in model
            approved_limit=approved_limit,
            current_debt=Decimal('0.00') # New customers start with 0 debt
        )
        return customer
        """
        Create and return a new `Customer` instance, given the validated data.
        """
        monthly_salary_from_income = validated_data['monthly_income']
        
        # --- DEBUG PRINTS START ---
        print(f"\nDEBUG (Serializer Create): monthly_income = {monthly_salary_from_income} (type: {type(monthly_salary_from_income)})")
        
        calculated_approved_limit_raw = 36 * monthly_salary_from_income
        print(f"DEBUG (Serializer Create): raw_approved_limit = {calculated_approved_limit_raw}")
        
        # This is the line that performs the rounding to nearest lakh
        approved_limit = calculated_approved_limit_raw.quantize(Decimal('100000'), rounding=ROUND_HALF_UP)
        print(f"DEBUG (Serializer Create): rounded_approved_limit = {approved_limit}")
        # --- DEBUG PRINTS END ---

        customer = Customer.objects.create(
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            # age=validated_data['age'], # Uncomment if you added 'age' field to Customer model
            phone_number=validated_data['phone_number'],
            monthly_salary=monthly_salary_from_income, # Store as monthly_salary in model
            approved_limit=approved_limit,
            current_debt=Decimal('0.00') # New customers start with 0 debt
        )
        return customer

class CreateLoanRequestSerializer(serializers.Serializer):
    """
    Serializer for handling /create-loan API requests.
    Input fields: customer_id, loan_amount, tenure, interest_rate.
    """
    customer_id = serializers.IntegerField()
    loan_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    tenure = serializers.IntegerField()
    interest_rate = serializers.DecimalField(max_digits=5, decimal_places=2) # The original interest rate requested by customer

    def validate(self, data):
        """
        Performs basic validation for loan creation request.
        """
        customer_id = data.get('customer_id')
        loan_amount = data.get('loan_amount')
        tenure = data.get('tenure')
        interest_rate = data.get('interest_rate')

        try:
            customer = Customer.objects.get(customer_id=customer_id)
            data['customer'] = customer # Attach customer object for easier access in view
        except Customer.DoesNotExist:
            raise serializers.ValidationError({"customer_id": "Customer with this ID does not exist."})

        if loan_amount <= 0:
            raise serializers.ValidationError({"loan_amount": "Loan amount must be positive."})

        if tenure <= 0:
            raise serializers.ValidationError({"tenure": "Tenure must be positive."})

        if interest_rate <= 0:
            raise serializers.ValidationError({"interest_rate": "Interest rate must be positive."})

        return data

class CreateLoanResponseSerializer(serializers.ModelSerializer):
    """
    Serializer for the response of /create-loan API.
    Output fields for the API response.
    """
    loan_id = serializers.IntegerField()
    customer_id = serializers.IntegerField(source='customer.customer_id')
    loan_approved = serializers.BooleanField(source='is_approved') # Assuming you'll add an 'is_approved' field to Loan model or handle this in view
    message = serializers.CharField() # Custom message for approval/rejection

    class Meta:
        model = Loan
        fields = ['loan_id', 'customer_id', 'loan_approved', 'message', 'monthly_repayment_emi']
        # You might want to add other fields like loan_amount, tenure, interest_rate if needed in response
        
class LoanStatementSerializer(serializers.ModelSerializer):
    """
    Serializer for displaying a detailed loan statement.
    Used for /view-statement/{customer_id}/{loan_id} endpoint.
    """
    customer_id = serializers.IntegerField(source='customer.customer_id', read_only=True)
    # Calculate remaining EMIs based on current date
    remaining_emis = serializers.SerializerMethodField()
    # Calculate EMIs due (simple calculation based on start_date and current date)
    emis_due = serializers.SerializerMethodField()

    class Meta:
        model = Loan
        fields = [
            'loan_id', 'customer_id', 'loan_amount', 'tenure', 'interest_rate',
            'monthly_repayment_emi', 'emis_paid_on_time', 'start_date', 'end_date',
            'emis_due', 'remaining_emis'
        ]

    def get_emis_due(self, obj):
        """
        Calculates the number of EMIs due up to the current date.
        """
        from datetime import date # Import here to avoid circular dependency if models.py imports serializers
        if obj.start_date is None:
            return 0
        today = date.today()
        # Calculate months passed since start_date
        months_passed = (today.year - obj.start_date.year) * 12 + (today.month - obj.start_date.month)
        # Ensure emis_due doesn't exceed total tenure
        return min(months_passed, obj.tenure)

    def get_remaining_emis(self, obj):
        """
        Calculates the remaining number of EMIs.
        """
        emis_due = self.get_emis_due(obj)
        return max(0, obj.tenure - obj.emis_paid_on_time) # Simple calculation: total tenure - paid

# (Ensure SingleLoanViewSerializer and any other serializers come after this)

class LoanDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for detailed loan information.
    Used in /create-loan response to provide full loan details.
    """
    customer_id = serializers.IntegerField(source='customer.customer_id', read_only=True)
    loan_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Loan
        fields = [
            'loan_id', 'customer_id', 'loan_amount', 'tenure', 'interest_rate',
            'monthly_repayment_emi', 'emis_paid_on_time', 'start_date', 'end_date'
        ]
        
class SingleLoanViewSerializer(serializers.ModelSerializer):
    """
    Serializer for /view-loan/{loan_id} endpoint.
    Includes loan details and nested customer details.
    """
    customer = NestedCustomerSerializer(read_only=True) # Nested serializer for customer details
    # loan_approved is a boolean indicating if the loan was approved.
    # Assuming 'is_approved' field on Loan model, or derive it.
    # For now, we'll derive it from interest_rate > 0.
    loan_approved = serializers.SerializerMethodField()
    monthly_installment = serializers.DecimalField(source='monthly_repayment_emi', max_digits=10, decimal_places=2)


    class Meta:
        model = Loan
        fields = [
            'loan_id', 'customer', 'loan_amount', 'interest_rate',
            'monthly_installment', 'tenure', 'loan_approved'
        ]

    def get_loan_approved(self, obj):
        # A simple way to determine if loan was approved: if interest_rate > 0
        # You might have a specific 'is_approved' field in your Loan model if needed.
        return obj.interest_rate > 0