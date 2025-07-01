from django.contrib.auth.hashers import check_password
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Users
from django.http import HttpResponseForbidden

def userLogin(request):
    if request.method == "POST":
        username = request.POST.get("username")  # this is the email
        password = request.POST.get("password")

        if not username or not password:
            messages.error(request, "Please enter both email and password")
            return loginView(request)

        try:
            # Fetch user by email
            user = Users.objects.get(email=username)
        except Users.DoesNotExist:
            messages.error(request, "Invalid email or password")
            return loginView(request)

        # Check if the provided password matches the stored hash
        if check_password(password, user.password_hash):
            # Store user info in session, including user_id
            request.session['user_id'] = user.user_id
            request.session['user_name'] = user.name
            request.session['user_role'] = user.role
            request.session['user_email'] = user.email
            
            return redirect("dashboard")  # Redirect to dashboard or home page
        else:
            messages.error(request, "Invalid email or password")
            return loginView(request)

    # If not POST, redirect to login
    return loginView(request)

def loginView(request):
    if request.session.get('user_id') and request.session.get('user_email'):
        return redirect("dashboard")

    return render(request, 'login.html')

def logout_view(request):
    request.session.flush()  # Clears all session data

    return redirect('login')