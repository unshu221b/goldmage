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
from django.urls import path, include, re_path
from django.conf.urls.static import static
from django.http import HttpResponse
from django.views.generic.base import RedirectView
from django.views.generic import TemplateView
from . import views, webhooks
from courses import views as course_views


def health_check(request):
    return HttpResponse("OK")

urlpatterns = [
    # Home page (Django template)
    path('', views.home_view, name='home'),
    # API endpoints
    path('api/analyze/', views.analyze_view, name='analyze'),
    path('webhook/', webhooks.stripe_webhook, name='stripe-webhook'),
    path('payment/checkout/', views.payment_checkout, name='payment_checkout'),
    path('payment/return/', views.payment_return, name='payment_return'),
    path('create-customer-portal-session', views.create_portal_session, name='create-portal-session'),
    path('create-checkout-session/', views.create_checkout_session, name='create-checkout-session'),
    # Admin, static, etc.
    path("admin/", admin.site.urls),
    path('favicon.ico', RedirectView.as_view(url='/static/img/favicon.ico', permanent=True)),
    # Catch-all for React frontend (must be last!)
    re_path(r'^(?!api/|admin/|static/|media/|webhook/|create-customer-portal-session|create-checkout-session|payment/|search/|help/|history/|product/|dashboard/|settings/|favicon\.ico).*$', TemplateView.as_view(template_name='index.html')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += [
        path("__reload__/", include("django_browser_reload.urls")),
    ]

# Add these lines at the bottom of the file
handler404 = 'cfehome.views.handler404'
handler500 = 'cfehome.views.handler500'
