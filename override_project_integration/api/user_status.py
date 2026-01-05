"""
User status API endpoints for Vue.js token-based authentication
"""

import frappe
from frappe import _
from override_project_integration.api.utils import api_response
from override_project_integration.api.middleware import (
    cors_handler, rate_limit, token_based_auth, require_vue_user, get_current_vue_user
)
from override_project_integration.api.user_session_manager import UserSessionManager


@frappe.whitelist(allow_guest=True)
@cors_handler
@rate_limit(limit=20, window=60, endpoint_name="get_user_status")
@token_based_auth(required=True)
def get_user_status():
    """
    Get current user status based on token authentication
    
    Returns:
        dict: User status information
    """
    try:
        # Get current Vue user from middleware
        vue_user = get_current_vue_user()
        
        if not vue_user or not vue_user.get('is_authenticated'):
            return api_response(
                success=False,
                message=_("User not authenticated"),
                status_code=401
            )
        
        # Get detailed user identity
        identity = vue_user.get('identity', {})
        
        return api_response(
            success=True,
            message=_("User status retrieved successfully"),
            data={
                "user_type": vue_user.get('user_type'),
                "is_authenticated": vue_user.get('is_authenticated'),
                "token_id": identity.get('token_id'),
                "name": identity.get('name'),
                "document_name": identity.get('document_name'),
                "project_name": identity.get('project_name'),
                "status": identity.get('status'),
                "session_created": identity.get('session_created'),
                "last_accessed": identity.get('last_accessed')
            }
        )
        
    except Exception as e:
        frappe.log_error(f"Error getting user status: {str(e)}")
        return api_response(
            success=False,
            message=_("Error retrieving user status"),
            status_code=500
        )


@frappe.whitelist(allow_guest=True)
@cors_handler
@rate_limit(limit=10, window=60, endpoint_name="validate_token")
def validate_token():
    """
    Validate a token without creating a session
    
    Returns:
        dict: Token validation result
    """
    try:
        # Get token from request
        token_id = (
            frappe.get_request_header("X-Token-ID") or 
            frappe.local.form_dict.get("token_id") or
            frappe.local.form_dict.get("token")
        )
        
        if not token_id:
            return api_response(
                success=False,
                message=_("Token ID is required"),
                status_code=400
            )
        
        # Validate token using UserSessionManager
        is_valid = UserSessionManager.is_session_valid(token_id)
        
        if is_valid:
            # Get user identity without creating session
            identity = UserSessionManager.get_user_identity(token_id)
            
            return api_response(
                success=True,
                message=_("Token is valid"),
                data={
                    "is_valid": True,
                    "is_authenticated": identity.get('is_authenticated', False),
                    "user_type": identity.get('user_type'),
                    "user_name": identity.get('identity', {}).get('name') if identity.get('identity') else None
                }
            )
        else:
            return api_response(
                success=False,
                message=_("Token is invalid or expired"),
                data={
                    "is_valid": False,
                    "is_authenticated": False
                }
            )
            
    except Exception as e:
        frappe.log_error(f"Error validating token: {str(e)}")
        return api_response(
            success=False,
            message=_("Error validating token"),
            status_code=500
        )


@frappe.whitelist(allow_guest=True)
@cors_handler
@rate_limit(limit=5, window=60, endpoint_name="invalidate_session")
@token_based_auth(required=True)
@require_vue_user
def invalidate_session():
    """
    Invalidate current user session
    
    Returns:
        dict: Session invalidation result
    """
    try:
        # Get current Vue user
        vue_user = get_current_vue_user()
        
        if not vue_user or not vue_user.get('identity'):
            return api_response(
                success=False,
                message=_("No active session found"),
                status_code=400
            )
        
        token_id = vue_user['identity'].get('token_id')
        
        if not token_id:
            return api_response(
                success=False,
                message=_("No token found in session"),
                status_code=400
            )
        
        # Invalidate session
        success = UserSessionManager.invalidate_session(token_id)
        
        if success:
            return api_response(
                success=True,
                message=_("Session invalidated successfully"),
                data={
                    "invalidated": True,
                    "token_id": token_id[:8] + "..."  # Only show first 8 characters
                }
            )
        else:
            return api_response(
                success=False,
                message=_("Failed to invalidate session"),
                status_code=500
            )
            
    except Exception as e:
        frappe.log_error(f"Error invalidating session: {str(e)}")
        return api_response(
            success=False,
            message=_("Error invalidating session"),
            status_code=500
        )


@frappe.whitelist(allow_guest=True)
@cors_handler
@rate_limit(limit=30, window=60, endpoint_name="get_session_stats")
def get_session_statistics():
    """
    Get session statistics (admin endpoint)
    
    Returns:
        dict: Session statistics
    """
    try:
        stats = UserSessionManager.get_session_statistics()
        
        return api_response(
            success=True,
            message=_("Session statistics retrieved successfully"),
            data=stats
        )
        
    except Exception as e:
        frappe.log_error(f"Error getting session statistics: {str(e)}")
        return api_response(
            success=False,
            message=_("Error retrieving session statistics"),
            status_code=500
        )