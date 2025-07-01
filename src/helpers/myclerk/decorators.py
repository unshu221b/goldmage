from functools import wraps

from django.http import JsonResponse


def api_login_required(view_function):
    @wraps(view_function)
    def _wrapped_view(request, *args, **kwargs):
        print(f"=== DECORATOR DEBUG ===")
        print(f"User: {request.user}")
        print(f"User type: {type(request.user)}")
        print(f"Is authenticated: {getattr(request.user, 'is_authenticated', 'NO PROPERTY')}")
        print(f"=======================")
        
        if not request.user.is_authenticated:
            return JsonResponse({"detail": "Auth required"}, status=401)
        return view_function(request, *args, **kwargs)
    return _wrapped_view
