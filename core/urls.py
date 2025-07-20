# core/urls.py
from django.urls import path
from .views import CheckEligibilityView, CreateLoanView, GetLoanByCustomerView, RegisterCustomerView, ViewLoanStatementView, ViewSingleLoanView

urlpatterns = [
    path('register', RegisterCustomerView.as_view(), name='register_customer'),
    path('check-eligibility', CheckEligibilityView.as_view(), name='check_eligibility'),
    path('create-loan', CreateLoanView.as_view(), name='create_loan'), # Add this lin
    path('view-loans/<int:customer_id>', GetLoanByCustomerView.as_view(), name='get_loan_by_customer'),
    path('view-statement/<int:customer_id>/<int:loan_id>', ViewLoanStatementView.as_view(), name='view_loan_statement'),
    path('view-loan/<int:loan_id>', ViewSingleLoanView.as_view(), name='view_single_loan'),

]
