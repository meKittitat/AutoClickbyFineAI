"""
Permission handling utilities for the Auto Click application.
"""

def has_permission(permissions, required_permission):
    """Check if the user has the required permission."""
    return required_permission in permissions

def check_permissions(permissions, required_permissions):
    """Check if the user has all the required permissions."""
    return all(perm in permissions for perm in required_permissions)