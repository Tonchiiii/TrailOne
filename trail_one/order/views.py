from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from order.models import Shipment,ShipmentItem  # Import Shipment model
from authentication.models import Users  # Import Users model
from django.template.loader import get_template
import csv
import re
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import HttpResponseRedirect
from django.http import HttpResponseNotFound
from django.http import HttpResponseForbidden
from django.http import Http404
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator
from django.contrib.auth.hashers import check_password,make_password
from django.core.exceptions import PermissionDenied
from django.template.loader import render_to_string
from django.http import HttpResponse
# from weasyprint import HTML
import tempfile
import io

def dashboard(request):
    if not request.session.get('user_id'):
        return redirect('login')

    # Fetch the user role and user_id from the session
    user_role = request.session.get('user_role', 'Guest')
    user_id = request.session.get('user_id')  # Assuming user_id is stored in the session

    # Fetch the 5 most recent completed deliveries (status = 'delivered')
    if user_role == 'CLIENT':
        completed_deliveries = Shipment.objects.filter(status='delivered', user_id=user_id).order_by('-created_at')[:4]
    else:
        completed_deliveries = Shipment.objects.filter(status='delivered').order_by('-created_at')[:4]

    # Fetch the 5 most recent pending deliveries (statuses could be 'shipped', 'arrived_at_destination', etc.)
    if user_role == 'CLIENT':
        pending_deliveries = Shipment.objects.filter(
            status__in=['shipped', 'arrived_at_destination', 'unloading_for_inspection', 'under_review'],
            user_id=user_id
        ).order_by('-created_at')[:5]
    else:
        pending_deliveries = Shipment.objects.filter(
            status__in=['shipped', 'arrived_at_destination', 'unloading_for_inspection', 'under_review']
        ).order_by('-created_at')[:5]

    def calculate_totals(shipments):
        for shipment in shipments:
            total_quantity = sum(item.quantity for item in shipment.items.all())
            total_missing = sum(item.missing for item in shipment.items.all())
            shipment.total_quantity = total_quantity
            shipment.total_missing = total_missing  # Add total missing quantity

        return shipments

    completed_deliveries = calculate_totals(completed_deliveries)
    pending_deliveries = calculate_totals(pending_deliveries)

    user_name = request.session.get('user_name', 'Guest')

    # Pass the data to the template
    return render(request, 'dashboard.html', {
        'completed_deliveries': completed_deliveries,
        'pending_deliveries': pending_deliveries,
        'user_name': user_name,
        'user_role': user_role,
    })

def view_create_orders(request):
    if not request.session.get('user_id'):
        return redirect('login')
    
    clients = Users.objects.filter(role='CLIENT')  # Fetch users with role 'CLIENT'

    return render(request, 'orders/view_create_orders.html', {
        'clients': clients
    })

def view_track_orders(request):
    # Get the status filter from the GET request, if provided
    status_filter = request.GET.get('status', None)

    # Start with all shipments or filter by user_id if CLIENT
    if request.session.get('user_role') == 'CLIENT':
        user_id = request.session.get('user_id')
        shipments = Shipment.objects.filter(user_id=user_id)
    else:
        shipments = Shipment.objects.all()

    if status_filter:
        shipments = shipments.filter(status=status_filter)

    shipments = shipments.order_by('-shipment_id', '-created_at')

    # Function to calculate total quantities for each shipment
    def calculate_totals(shipments):
        for shipment in shipments:
            total_quantity = sum(item.quantity for item in shipment.items.all())
            shipment.total_quantity = total_quantity
            total_missing = sum(item.missing for item in shipment.items.all())
            shipment.total_missing = total_missing
        return shipments

    shipments = calculate_totals(shipments)

    # Pagination
    paginator = Paginator(shipments, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Totals
    total_missing = sum(s.total_missing for s in page_obj.object_list if s.status == 'delivered')
    total_delivered = sum(s.total_quantity for s in page_obj.object_list if s.status == 'delivered')

    return render(request, 'orders/view_track_orders.html', {
        'page_obj': page_obj,
        'total_missing': total_missing,
        'total_delivered': total_delivered,
        'status_filter': status_filter,
    })

def create_order(request):
    if request.method == 'POST':
        csv_file = request.FILES.get('csv_file')

        if not csv_file:
            messages.error(request, "No CSV file uploaded.")
            return redirect('view_create_orders')

        if not csv_file.name.lower().endswith('.csv'):
            messages.error(request, "Please upload a CSV file.")
            return redirect('view_create_orders')

        if csv_file.size > 30 * 1024 * 1024:  # 30MB size limit
            messages.error(request, "File is too large. File should not exceed 30 MB.")

            return redirect('view_create_orders')

        try:
            # Use TextIOWrapper to stream the CSV
            file_wrapper = io.TextIOWrapper(csv_file.file, encoding='utf-8')
            reader = csv.reader(file_wrapper)

            # Skip header
            try:
                next(reader)
            except StopIteration:
                messages.error(request, "The CSV file is empty.")
                return redirect('view_create_orders')

            items = []
            for row in reader:
                if len(row) < 2:
                    continue
                desc = row[0].strip()
                qty = row[1].strip()

                if not desc or not qty:
                    continue
                if not qty.isdigit():
                    messages.error(request, f"Invalid quantity: {qty}")
                    return redirect('view_create_orders')
                if any(c in desc for c in ['<', '>', '"', "'"]):
                    messages.error(request, f"Invalid characters in description: {desc}")
                    return redirect('view_create_orders')

                items.append({
                    'description': desc,
                    'quantity': int(qty),
                })

            if not items:
                messages.error(request, "No valid items found in the CSV.")
                return redirect('view_create_orders')

            client_id = request.POST.get('client')
            try:
                client = Users.objects.get(pk=client_id)
            except Users.DoesNotExist:
                messages.error(request, "Invalid client selected.")
                return redirect('view_create_orders')

            shipment = Shipment.objects.create(user=client, status='shipped')
            ShipmentItem.objects.bulk_create([
                ShipmentItem(
                    shipment=shipment,
                    description=item['description'],
                    quantity=item['quantity'],
                    missing=0
                )
                for item in items
            ])

            messages.success(request, "Shipment created successfully.", extra_tags='shipment_created')
            return redirect('view_track_orders')

        except Exception as e:
            messages.error(request, f"Error processing CSV: {e}")
            return redirect('view_create_orders')

def view_track_order_detail(request, id):
    if not request.session.get('user_id'):
        return redirect('login')

    try:
        shipment = Shipment.objects.get(shipment_id=id)
    except Shipment.DoesNotExist:
        return HttpResponseNotFound("Http Response 404: Shipment not found.")

    # Restrict CLIENT users to only their own shipments
    if request.session.get('user_role') == 'CLIENT':
        if shipment.user_id != request.session.get('user_id'):
            raise PermissionDenied("You are not allowed to view this shipment.")

    STATUS_SEQUENCE = ['shipped', 'arrived_at_destination', 'unloading_for_inspection', 'under_review']
    
    # Calculate the next status
    if shipment.status != 'under_review':
        try:
            current_status_index = STATUS_SEQUENCE.index(shipment.status)
            next_status = STATUS_SEQUENCE[current_status_index + 1] if current_status_index + 1 < len(STATUS_SEQUENCE) else None
        except ValueError:
            next_status = None
    else:
        next_status = None

    total_missing = sum(item.missing for item in shipment.items.all())
    total_quantity = sum(item.quantity for item in shipment.items.all())

    return render(request, 'orders/view_track_order_detail.html', {
        'shipment': shipment,
        'next_status': next_status,
        'total_quantity': total_quantity,
        'missing_quantity': total_missing,
    })

def change_shipment_status(request, shipment_id):
    # Get the shipment
    shipment = get_object_or_404(Shipment, shipment_id=shipment_id)
    
    # Ensure that the user is logged in and has permission to change the status
    if not request.session.get('user_id'):
        return redirect('login')

    # Get the next status
    STATUS_SEQUENCE = ['shipped', 'arrived_at_destination', 'unloading_for_inspection', 'under_review']
    current_status_index = STATUS_SEQUENCE.index(shipment.status)

    if current_status_index + 1 < len(STATUS_SEQUENCE):
        next_status = STATUS_SEQUENCE[current_status_index + 1]
        shipment.status = next_status
        shipment.save()

        # Add a success message with shipment name or ID
        shipment_name = shipment.shipment_id  # You can replace this with any field like `shipment.name` if available
        messages.success(request, f"Shipment {shipment_name} status has been successfully updated to {next_status.replace('_', ' ').title()}.")

    return redirect('view_track_order_detail', id=shipment.shipment_id)

def submit_missing_items(request, shipment_id):
    if request.method == 'POST':
        shipment = get_object_or_404(Shipment, shipment_id=shipment_id)

        if request.session.get('user_role') == 'CLIENT':
            if shipment.user_id != request.session.get('user_id'):
                raise PermissionDenied("You are not allowed to view this shipment.")

        if request.session.get('user_role') != 'CLIENT' or shipment.status != 'under_review':
            raise PermissionDenied("You are not allowed to view this shipment.")

        has_error = False

        for item in shipment.items.all():
            missing_key = f'missing_qty_{item.id}'
            missing_value = request.POST.get(missing_key)

            if missing_value is not None and missing_value.strip() != '':
                try:
                    missing_int = int(missing_value)
                    if missing_int < 0:
                        messages.error(request, f"Missing quantity for item {item.description} cannot be less than 0.", extra_tags='missing_data_error')
                        has_error = True
                    elif missing_int > item.quantity:
                        messages.error(request, f"Missing quantity for item {item.description} cannot exceed its quantity ({item.quantity}).", extra_tags='missing_data_error')
                        has_error = True
                    else:
                        item.missing = missing_int
                        item.save()
                except ValueError:
                    messages.error(request, f"Invalid input for item {item.description}. Must be a number.", extra_tags='missing_data_error')
                    has_error = True

        if has_error:
            return redirect('view_track_order_detail', id=shipment.shipment_id)

        shipment.status = 'delivered'
        shipment.save()

        messages.success(request, "Status updated to delivered", extra_tags='status_to_delivered')
        return redirect('view_track_order_detail', id=shipment.shipment_id)

def view_edit_account(request):

    return render(request, 'account/view-edit-account.html')

# Custom 404 error handler
def custom_404(request, exception):
    return render(request, '404.html', status=404)

# Custom 403 error handler
def custom_403(request, exception):
    return render(request, '403.html', status=403)

# Custom 500 error handler
def custom_500(request):
    return render(request, '500.html', status=500)

def update_profile(request):
    session_email = request.session.get('user_email')
    if not session_email:
        messages.error(request, "You must be logged in to update your profile.")
        return redirect('login')

    try:
        user = Users.objects.get(email=session_email)
    except Users.DoesNotExist:
        messages.error(request, "User not found.")
        return redirect('login')

    if request.method == "POST":
        full_name = request.POST.get('full_name')
        email = request.POST.get('email')

        if not full_name:
            messages.error(request, "Full name cannot be empty.")

            return redirect('view_edit_account')
        else:
            email_validator = EmailValidator()
            try:
                email_validator(email)

                if not email.endswith('@trailone.com'):
                    messages.error(request, "Email must be a trailone.com address.")

                    return redirect('view_edit_account')
                elif email != user.email and Users.objects.filter(Q(email=email) & ~Q(user_id=user.user_id)).exists():
                    messages.error(request, "This email is already in use.")

                    return redirect('view_edit_account')
                else:
                    user.name = full_name  # Ensure correct field name
                    user.email = email
                    user.save()

                    request.session['user_id'] = user.user_id
                    request.session['user_name'] = user.name
                    request.session['user_role'] = user.role
                    request.session['user_email'] = user.email

                    messages.success(request, "Your profile has been updated.")

                    return redirect('view_edit_account')
            except ValidationError:
                messages.error(request, "Invalid email address.")

                return redirect('view_edit_account')

    return redirect('view_edit_account')

def view_users(request):
    # Check if user is logged in and is SUPER_ADMIN
    if request.session.get('user_role') != 'SUPER_ADMIN':
        raise PermissionDenied("You are not allowed to view this shipment.")

    # Get the current user's email
    current_user_email = request.session.get('user_email')

    # Get all users except the current one and exclude users without a role
    users_queryset = Users.objects.exclude(email=current_user_email).exclude(Q(role__isnull=True) | Q(role='')).order_by('user_id')

    # Paginate
    paginator = Paginator(users_queryset, 10)  # Show 10 users per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'users/users_list.html', {'page_obj': page_obj})

def user_detail(request, user_id):
    # Check if user is logged in and is SUPER_ADMIN
    if request.session.get('user_role') != 'SUPER_ADMIN':
        raise PermissionDenied("You are not allowed to view this shipment.")

    user = get_object_or_404(Users, user_id=user_id)
    return render(request, 'users/user_detail.html', {'user': user})

def change_password(request, user_email):
    user = get_object_or_404(Users, email=user_email)
    logged_in_email = request.session.get('user_email')
    logged_in_role = request.session.get('user_role')

    if logged_in_role != 'SUPER_ADMIN' and logged_in_email != user.email:
        raise PermissionDenied("You are not allowed to view this shipment.")

    if request.method == 'POST':
        current_password = request.POST.get('current_password', '').strip()
        new_password = request.POST.get('new_password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()

        # Validation
        if not new_password or not confirm_password:
            messages.error(request, "New password and confirmation are required.")
        elif logged_in_role != 'SUPER_ADMIN' and not current_password:
            messages.error(request, "Current password is required.")
        elif logged_in_role != 'SUPER_ADMIN' and not check_password(current_password, user.password_hash):
            messages.error(request, "Current password is incorrect.")
        elif new_password != confirm_password:
            messages.error(request, "New passwords do not match.")
        elif not re.match(r'^(?=.*[A-Z])(?=.*[^A-Za-z0-9])(?=.{8,})', new_password):
            messages.error(request, "Password must be at least 8 characters long, contain one uppercase letter and one special character.")
        else:
            user.password_hash = make_password(new_password)
            user.save()
            messages.success(request, "Password updated successfully.")

            if not current_password:
                return redirect('view_users')
            else:
                return redirect('view_edit_account')

    if not current_password:
        return redirect('view_users')
    else:
        return redirect('view_edit_account')

def add_user_view(request):
    # Only SUPER_ADMINs can access this view
    if request.session.get('user_role') != 'SUPER_ADMIN':
        raise PermissionDenied("You are not allowed to view this shipment.")

    # Handle only the GET request to display the form
    if request.method == 'GET':
        return render(request, 'users/add_users.html')

def add_user_save(request):
    session_email = request.session.get('user_email')
    if not session_email:
        messages.error(request, "You must be logged in to add a user.")
        return redirect('login')

    try:
        _ = Users.objects.get(email=session_email)
    except Users.DoesNotExist:
        messages.error(request, "User not found.")
        return redirect('login')

    if request.method == "POST":
        full_name = request.POST.get('full_name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        role = request.POST.get('role')

        # Required fields check
        if not full_name:
            messages.error(request, "Full name cannot be empty.")
            return redirect('add_user_view')
        if not email:
            messages.error(request, "Email cannot be empty.")
            return redirect('add_user_view')
        if not password:
            messages.error(request, "Password cannot be empty.")
            return redirect('add_user_view')
        if not confirm_password:
            messages.error(request, "Please confirm the password.")
            return redirect('add_user_view')
        if not role:
            messages.error(request, "Role cannot be empty.")
            return redirect('add_user_view')

        # Role validation
        if role not in ["CLIENT", "ADMIN"]:
            messages.error(request, "Invalid role. Only 'CLIENT' or 'ADMIN' are allowed.")
            return redirect('add_user_view')

        # Email format validation
        email_validator = EmailValidator()
        try:
            email_validator(email)
        except ValidationError:
            messages.error(request, "Invalid email address.")
            return redirect('add_user_view')

        # Domain check
        if not email.endswith('@trailone.com'):
            messages.error(request, "Email must be a trailone.com address.")
            return redirect('add_user_view')

        # Email uniqueness check
        if Users.objects.filter(email=email).exists():
            messages.error(request, "This email is already in use.")
            return redirect('add_user_view')

        # Password confirmation check
        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect('add_user_view')

        # Password format validation
        if not re.match(r'^(?=.*[A-Z])(?=.*[^A-Za-z0-9])(?=.{8,})', password):
            messages.error(request, "Password must be at least 8 characters long, contain one uppercase letter and one special character.")
            return redirect('add_user_view')

        # Save user (automatically hashes password)
        user = Users.objects.create_user(
            email=email,
            password_hash=make_password(password),
            name=full_name,
            role=role
        )

        messages.success(request, "User created successfully.")
        return redirect('view_users')

    messages.error(request, "Invalid request method.")
    return redirect('add_user_view')


# def generate_invoice_pdf(request, shipment_id):
#     from .models import Shipment  # Adjust import as needed
#     shipment = Shipment.objects.get(shipment_id=shipment_id)

#     total_quantity = sum(item.quantity for item in shipment.items.all())
#     missing_quantity = shipment.missing_items if shipment.status == "delivered" else 0

#     html_string = render_to_string('invoice.html', {
#         'shipment': shipment,
#         'total_quantity': total_quantity,
#         'missing_quantity': missing_quantity
#     })

#     html = HTML(string=html_string)
#     result = html.write_pdf()

#     response = HttpResponse(content_type='application/pdf')
#     response['Content-Disposition'] = f'inline; filename=invoice-order-{shipment_id}.pdf'
#     response.write(result)
#     return response