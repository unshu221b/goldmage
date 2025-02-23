from django.contrib import admin
from django.utils.safestring import mark_safe

# Register your models here.
from .models import Email, EmailVerificationEvent, LoginAttempt

admin.site.register(Email)
admin.site.register(EmailVerificationEvent)

@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    list_display = ('email', 'ip_address', 'timestamp', 'was_successful')
    list_filter = ('timestamp', 'was_successful')
    search_fields = ('email', 'ip_address')
    readonly_fields = ('timestamp',)
    ordering = ('-timestamp',)
    
    def get_suspicious_status(self, obj):
        is_suspicious, reasons = obj.is_suspicious
        if is_suspicious:
            return "🚨 Suspicious"
        return "✅ Normal"
    get_suspicious_status.short_description = "Status"
    
    def get_pattern_analysis(self, obj):
        patterns = obj.get_pattern_data()
        is_suspicious, reasons = obj.is_suspicious
        
        html = "<h3>Pattern Analysis:</h3>"
        html += "<ul>"
        for key, value in patterns.items():
            html += f"<li><strong>{key}:</strong> {value}</li>"
        html += "</ul>"
        
        if reasons:
            html += "<h3>Suspicious Patterns:</h3>"
            html += "<ul style='color: red;'>"
            for reason in reasons:
                html += f"<li>{reason}</li>"
            html += "</ul>"
        
        return mark_safe(html)
    get_pattern_analysis.short_description = "Login Pattern Analysis"