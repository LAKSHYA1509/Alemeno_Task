# core/serializers.py
from rest_framework import serializers
from .models import Customer
from decimal import Decimal, ROUND_HALF_UP

class CustomerRegistrationSerializer(serializers.Serializer):
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

    def create(self, validated_data):
        """
        Create and return a new `Customer` instance, given the validated data.
        """
        monthly_salary = validated_data['monthly_income']
        # Calculate approved_limit: 36 * monthly_salary, rounded to nearest lakh (100,000)
        approved_limit = (36 * monthly_salary).quantize(Decimal('100000'), rounding=ROUND_HALF_UP)

        customer = Customer.objects.create(
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            # Age is not in the Customer model, so we won't save it directly.
            # If you want to store age, you'd need to add it to the Customer model.
            phone_number=validated_data['phone_number'],
            monthly_salary=monthly_salary,
            approved_limit=approved_limit,
            current_debt=Decimal('0.00') # New customers start with 0 debt
        )
        return customer

class CustomerRegistrationResponseSerializer(serializers.ModelSerializer):
    """
    Serializer for the response of customer registration.
    Output fields for the API response.
    """
    name = serializers.SerializerMethodField()
    monthly_income = serializers.DecimalField(source='monthly_salary', max_digits=10, decimal_places=2)
    # Age is not in the model, so we can't directly serialize it from the model instance.
    # If age needs to be returned, it should either be stored in the model or passed through context.
    # For now, we'll omit it from the response unless explicitly stored.

    class Meta:
        model = Customer
        fields = ['customer_id', 'name', 'monthly_income', 'approved_limit', 'phone_number']

    def get_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"