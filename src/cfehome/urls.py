"""
URL configuration for cfehome project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
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
from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static
from django.http import HttpResponse

from emails.views import verify_email_token_view, resend_verification_email
from . import views, webhooks



def health_check(request):
    return HttpResponse("OK")

urlpatterns = [
    path("", views.home_view, name="home"),
    path("dashboard/", views.dashboard_view, name="dashboard"),
    path("settings/", views.settings_view, name="settings"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("signup/", views.signup_view, name="signup"),
    path('verify/<uuid:token>/', verify_email_token_view),
    path('resend-verification/', resend_verification_email, name='resend_verification'),
    path("courses/", include("courses.urls")),
    path("admin/", admin.site.urls),
    path('health/', health_check, name='health_check'),
    path('payment/checkout/', views.payment_checkout, name='payment_checkout'),
    path('payment/return/', views.payment_return, name='payment_return'),
    path('webhook/', webhooks.stripe_webhook, name='stripe-webhook'),
    path('create-customer-portal-session', views.create_portal_session, name='create-portal-session'),
    path('create-checkout-session/', views.create_checkout_session, name='create-checkout-session'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += [
        path("__reload__/", include("django_browser_reload.urls")),
    ]
