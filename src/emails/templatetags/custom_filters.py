from django import template

register = template.Library()

@register.filter
def split(value, key):
    """
    Returns the first part of a string split by the key.
    Example: {{ "hello@example.com"|split:"@" }} returns "hello"
    """
    if value:
        parts = value.split(key)
        if parts:
            return parts[0]  # Return entire first part
    return value  # Return original if splitting fails

@register.filter
def multiply(value, arg):
    return value * arg