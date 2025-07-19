from django.shortcuts import render

# Create your views here.
# core/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .serializers import CustomerRegistrationSerializer, CustomerRegistrationResponseSerializer

class RegisterCustomerView(APIView):
    """
    API endpoint for registering new customers.
    """
    def post(self, request, *args, **kwargs):
        serializer = CustomerRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            customer = serializer.save() # This calls the create method in the serializer
            response_serializer = CustomerRegistrationResponseSerializer(customer)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)