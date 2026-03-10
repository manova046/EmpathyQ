# accounts/decorators.py
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages

def role_required(allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            print(f"\n{'='*50}")
            print(f"ROLE REQUIRED DECORATOR CHECK")
            print(f"{'='*50}")
            
            if not request.user.is_authenticated:
                print(f"User not authenticated")
                messages.error(request, "Please login first.")
                return redirect('login')
            
            print(f"User: {request.user.username}")
            print(f"User role from DB: '{request.user.role}'")
            print(f"User is_superuser: {request.user.is_superuser}")
            print(f"View function name: {view_func.__name__}")
            print(f"Allowed roles parameter: {allowed_roles}")
            
            # Check each condition
            condition1 = request.user.role in allowed_roles
            condition2 = request.user.is_superuser
            
            print(f"Condition 1 (role in allowed_roles): {condition1}")
            print(f"Condition 2 (is_superuser): {condition2}")
            
            if condition1 or condition2:
                print(f"✓ ACCESS GRANTED")
                return view_func(request, *args, **kwargs)
            else:
                print(f"✗ ACCESS DENIED")
                print(f"  User role '{request.user.role}' not in {allowed_roles}")
                messages.error(request, f"You don't have permission to access this page. Your role: {request.user.role}")
                return redirect('login')
        return wrapper
    return decorator