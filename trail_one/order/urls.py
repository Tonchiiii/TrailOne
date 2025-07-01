# urls.pys
from django.urls import path
from . import views

# Set the custom 404 handler at the module level
handler404 = 'order.views.custom_404'
handler403 = 'order.views.custom_403'
handler500 = 'order.views.custom_500'

urlpatterns = [
    path("dashboard", views.dashboard, name='dashboard'),
    path('orders/create', views.view_create_orders, name='view_create_orders'),
    path('orders/create-order', views.create_order, name='create_order'),
    path('orders/track', views.view_track_orders, name='view_track_orders'),
    path('orders/track/<int:id>/', views.view_track_order_detail, name='view_track_order_detail'),
    path('orders/track/<int:shipment_id>/change_status/', views.change_shipment_status, name='change_shipment_status'),
    path('orders/track/<int:shipment_id>/submit_missing/', views.submit_missing_items, name='submit_missing_items'),
    # path('orders/invoice/<int:shipment_id>/', generate_invoice_pdf, name='generate_invoice_pdf'),
    path('account/view-edit', views.view_edit_account, name='view_edit_account'),
    path('profile/update/', views.update_profile, name='update_profile'),
    path('users/', views.view_users, name='view_users'),
    path('users/<int:user_id>/', views.user_detail, name='user_detail'),
    path('users/add/', views.add_user_view, name='add_user_view'),
    path('users/save/', views.add_user_save, name='add_user_save'),
    path('users/<str:user_email>/change-password/', views.change_password, name='change_password'),
]
