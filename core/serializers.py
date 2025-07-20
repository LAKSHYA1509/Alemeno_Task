from rest_framework import serializers
from decimal import Decimal, ROUND_HALF_UP
from core.models import Customer, Loan
from datetime import date

class CheckEligibilityResponseSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField()
    approval = serializers.BooleanField()
    interest_rate = serializers.DecimalField(max_digits=5, decimal_places=2)  
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
            'name',             
            'monthly_income',
            'approved_limit',
            'phone_number'

        ]

    def get_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"

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

    monthly_income = serializers.DecimalField(max_digits=10, decimal_places=2)
    phone_number = serializers.CharField(max_length=20)

    def validate_phone_number(self, value):
        """
        Custom validation for phone number to ensure it's unique.
        """
        if Customer.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("A customer with this phone number already exists.")
        return value

    def validate_monthly_income(self, value):
        if value <= 0:
            raise serializers.ValidationError("Monthly income must be greater than zero.")
        return value

    def create(self, validated_data):
        """
        Create and return a new `Customer` instance, given the validated data.
        """
        monthly_salary_from_income = validated_data['monthly_income']

        print(f"\nDEBUG (Serializer Create): monthly_income = {monthly_salary_from_income} (type: {type(monthly_salary_from_income)})")

        calculated_approved_limit_raw = 36 * monthly_salary_from_income

        print(f"DEBUG (Serializer Create): raw_approved_limit = {calculated_approved_limit_raw}")

        temp_val_in_lakhs = calculated_approved_limit_raw / Decimal('100000')

        rounded_lakhs = temp_val_in_lakhs.quantize(Decimal('1'), rounding=ROUND_HALF_UP)

        approved_limit = rounded_lakhs * Decimal('100000')

        approved_limit = approved_limit.quantize(Decimal('0.01'))

        print(f"DEBUG (Serializer Create): rounded_approved_limit = {approved_limit}")

        customer = Customer.objects.create(
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],

            phone_number=validated_data['phone_number'],
            monthly_salary=monthly_salary_from_income, 
            approved_limit=approved_limit,
            current_debt=Decimal('0.00') 
        )
        return customer
        """
        Create and return a new `Customer` instance, given the validated data.
        """
        monthly_salary_from_income = validated_data['monthly_income']

        print(f"\nDEBUG (Serializer Create): monthly_income = {monthly_salary_from_income} (type: {type(monthly_salary_from_income)})")

        calculated_approved_limit_raw = 36 * monthly_salary_from_income
        print(f"DEBUG (Serializer Create): raw_approved_limit = {calculated_approved_limit_raw}")

        approved_limit = calculated_approved_limit_raw.quantize(Decimal('100000'), rounding=ROUND_HALF_UP)
        print(f"DEBUG (Serializer Create): rounded_approved_limit = {approved_limit}")

        customer = Customer.objects.create(
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],

            phone_number=validated_data['phone_number'],
            monthly_salary=monthly_salary_from_income, 
            approved_limit=approved_limit,
            current_debt=Decimal('0.00') 
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
    interest_rate = serializers.DecimalField(max_digits=5, decimal_places=2) 

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
            data['customer'] = customer 
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
    loan_approved = serializers.BooleanField(source='is_approved') 
    message = serializers.CharField() 

    class Meta:
        model = Loan
        fields = ['loan_id', 'customer_id', 'loan_approved', 'message', 'monthly_repayment_emi']

class LoanStatementSerializer(serializers.ModelSerializer):
    """
    Serializer for displaying a detailed loan statement.
    Used for /view-statement/{customer_id}/{loan_id} endpoint.
    """
    customer_id = serializers.IntegerField(source='customer.customer_id', read_only=True)

    remaining_emis = serializers.SerializerMethodField()

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
        from datetime import date 
        if obj.start_date is None:
            return 0
        today = date.today()

        months_passed = (today.year - obj.start_date.year) * 12 + (today.month - obj.start_date.month)

        return min(months_passed, obj.tenure)

    def get_remaining_emis(self, obj):
        """
        Calculates the remaining number of EMIs.
        """
        emis_due = self.get_emis_due(obj)
        return max(0, obj.tenure - obj.emis_paid_on_time) 

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
    customer = NestedCustomerSerializer(read_only=True) 

    loan_approved = serializers.SerializerMethodField()
    monthly_installment = serializers.DecimalField(source='monthly_repayment_emi', max_digits=10, decimal_places=2)

    class Meta:
        model = Loan
        fields = [
            'loan_id', 'customer', 'loan_amount', 'interest_rate',
            'monthly_installment', 'tenure', 'loan_approved'
        ]

    def get_loan_approved(self, obj):

        return obj.interest_rate > 0