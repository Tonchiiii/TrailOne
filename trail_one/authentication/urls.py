from django.urls import path
from . import views

urlpatterns = [
    path("login", views.loginView, name='login'),
    path('authenticate', views.userLogin, name='userLogin'),
    path('logout/', views.logout_view, name='logout'),
]