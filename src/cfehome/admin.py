from django.contrib import admin
from django.contrib.admin import AdminSite
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator

class RateLimitedAdminSite(AdminSite):
    @method_decorator(ratelimit(key='ip', rate='5/m', method=['POST']))
    def login(self, request, extra_context=None):
        return super().login(request, extra_context)

# Replace the default admin site with our rate-limited version
admin.site = RateLimitedAdminSite() 