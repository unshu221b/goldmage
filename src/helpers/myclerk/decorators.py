from functools import wraps

from django.http import JsonResponse


def api_login_required(view_function):
    @wraps(view_function)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"detail": "Auth required"}, status=401)
        return view_function(request, *args, **kwargs)
    return _wrapped_view

def check_credits(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Check if user has credits
        if not request.user.use_credit():
            return JsonResponse({
                'error': 'Insufficient credits',
                'remaining_credits': request.user.get_remaining_credits(),
                'upgrade_url': '/dashboard/upgrade'
            }, status=402)  # 402 Payment Required
            
        return view_func(request, *args, **kwargs)
    return _wrapped_view