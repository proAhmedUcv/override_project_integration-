"""
Simple CORS test endpoint
"""

import frappe
from frappe import _


@frappe.whitelist(allow_guest=True, methods=["GET", "POST", "OPTIONS"])
def test_cors():
    """
    Simple CORS test endpoint
    """
    # Get origin for CORS
    origin = frappe.get_request_header("Origin") or "*"
    
    try:
        # Handle preflight requests
        if frappe.request.method == "OPTIONS":
            # Set CORS headers for preflight
            frappe.local.response.headers = frappe.local.response.headers or {}
            frappe.local.response.headers.update({
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With, X-API-Key, X-CSRF-Token, X-Token-ID",
                "Access-Control-Allow-Credentials": "true",
                "Access-Control-Max-Age": "86400"
            })
            frappe.local.response.http_status_code = 200
            return {}
        
        # Handle actual requests
        frappe.local.response.headers = frappe.local.response.headers or {}
        frappe.local.response.headers.update({
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With, X-API-Key, X-CSRF-Token, X-Token-ID",
            "Access-Control-Allow-Credentials": "true"
        })
        
        return {
            "success": True,
            "message": _("CORS test successful"),
            "method": frappe.request.method,
            "origin": origin,
            "timestamp": frappe.utils.now(),
            "headers_set": bool(frappe.local.response.headers)
        }
        
    except Exception as e:
        frappe.log_error(f"CORS test error: {str(e)}", "test_cors")
        return {
            "success": False,
            "message": _("CORS test failed"),
            "error": str(e),
            "method": frappe.request.method,
            "timestamp": frappe.utils.now()
        }