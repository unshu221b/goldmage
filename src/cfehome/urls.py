
from django.conf import settings
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf.urls.static import static
from django.http import HttpResponse
from django.views.generic.base import RedirectView
from django.views.generic import TemplateView
from . import views, webhooks
from .api import user_summary

def health_check(request):
    return HttpResponse("OK")

urlpatterns = [
    # Home page (Django template)
    path('', views.home_view, name='home'),
    # API endpoints
    path('api/accounts/', include('accounts.urls')),
    path('api/analyze/', views.analyze_view, name='analyze'),
    path('webhook/', webhooks.stripe_webhook, name='stripe-webhook'),
    path('webhook/clerk/', webhooks.clerk_webhook, name='clerk-webhook'),
    path('api/create-customer-portal-session/', views.create_portal_session, name='create-portal-session'),
    path('api/create-checkout-session/', views.create_checkout_session, name='create-checkout-session'),
    path('api/user/summary/', user_summary, name='user-summary'),
    path('cors-test/', views.cors_test, name='cors-test'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += [
        path("__reload__/", include("django_browser_reload.urls")),
    ]