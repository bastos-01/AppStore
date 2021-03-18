"""webproj URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf.urls import url
from django.contrib import admin
from django.urls import path
from app import views
from django.contrib.auth import views as auth_views
from app.forms import *

urlpatterns = [
    path('admin/django/', admin.site.urls),
    path('', views.indexView, name='index'),
    path('signup/',views.register,name='signup'),
    path('shop/product/<int:idprod>/', views.prodDetails, name='productdetails'),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),

    #Shop
    url(r'^shop$', views.shopView, name='shop'),

    #account
    path('account/', views.accountDetails, name="accountDetails"),


    #admin
    path('admin/purchases/', views.adminPurchases, name="adminPurchases"),
    path('admin/users/', views.adminUsers, name="adminUsers"),
    path('admin/apps/', views.adminApps, name="adminApps"),
    path('admin/devs/', views.adminDevs, name="adminDevs"),
    path('admin/cat/', views.adminCat, name="adminCat"),

    path('admin/apps/addApp', views.addApp, name='addApp'),

    path('404/', views.handler404, name="notfound"),

    path('about/', views.aboutus, name="aboutus"),



    #add/edit review

    path('shop/product/<int:idprod>/review', views.review_View, name='prodreview')


]
