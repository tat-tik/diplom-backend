from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    path('users/', views.users_get, name='users-list'),
    path('users/reg/', views.user_reg, name='user-reg'),
    path('users/<int:id>/', views.user_api, name='user-detail'),
   path('users/login/', views.UsersLogin.as_view(), name='user-login'),
    path('users/logout/', views.UsersLogin.as_view(), name='user-logout'),
]