"""
CORS Fix for Vue.js Integration
This module ensures CORS headers are properly applied
"""

import frappe
from frappe import _


def apply_cors_headers():
    """
    Apply CORS headers to all API responses
    """
    try:
        # Get the current response
        if not hasattr(frappe.local, 'response'):
            return
        
        # Initialize headers if they don't exist
        if not hasattr(frappe.local.response, 'headers') or frappe.local.response.headers is None:
            frappe.local.response.headers = {}
        
        # Get origin from request
        origin = frappe.get_request_header("Origin")
        
        # List of allowed origins
        allowed_origins = [
            "http://localhost:3000",
            "http://localhost:5173", 
            "http://localhost:8080",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8080",
            "http://127.0.0.1:8007",
            "https://graduation-project-delta-green.netlify.app"
        ]
        
        # Apply CORS headers
        cors_headers = {
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With, X-API-Key, X-CSRF-Token, X-Token-ID",
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Max-Age": "86400"
        }
        
        # Set origin header
        if origin and origin in allowed_origins:
            cors_headers["Access-Control-Allow-Origin"] = origin
        elif not origin:
            cors_headers["Access-Control-Allow-Origin"] = "*"
        else:
            # For development, allow localhost origins
            if "localhost" in origin or "127.0.0.1" in origin:
                cors_headers["Access-Control-Allow-Origin"] = origin
        
        # Apply headers
        frappe.local.response.headers.update(cors_headers)
        
    except Exception as e:
        frappe.log_error(f"Error applying CORS headers: {str(e)}")


def handle_preflight_request():
    """
    Handle OPTIONS preflight requests
    """
    try:
        if frappe.request.method == "OPTIONS":
            # Set response status
            frappe.local.response.http_status_code = 200
            
            # Apply CORS headers
            apply_cors_headers()
            
            # Return empty response for preflight
            return {}
            
    except Exception as e:
        frappe.log_error(f"Error handling preflight request: {str(e)}")
        return {}


@frappe.whitelist(allow_guest=True, methods=["OPTIONS", "POST", "GET"])
def cors_test():
    """
    Test endpoint for CORS functionality
    """
    # Handle preflight
    if frappe.request.method == "OPTIONS":
        return handle_preflight_request()
    
    # Apply CORS headers
    apply_cors_headers()
    
    return {
        "success": True,
        "message": "CORS test successful",
        "method": frappe.request.method,
        "origin": frappe.get_request_header("Origin"),
        "headers": dict(frappe.request.headers) if hasattr(frappe.request, 'headers') else {}
    }