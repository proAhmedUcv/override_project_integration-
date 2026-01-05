"""
API documentation endpoints
"""

import frappe
from frappe import _
from override_project_integration.api.utils import api_response
from override_project_integration.api.middleware import cors_handler


@frappe.whitelist(allow_guest=True)
@cors_handler
def get_api_documentation():
    """
    Provide interactive API documentation
    
    Returns:
        dict: API documentation structure
    """
    try:
        # Implementation will be added in later tasks
        return api_response(
            success=False,
            message=_("Documentation endpoint not yet implemented"),
            status_code=501
        )
    except Exception as e:
        frappe.log_error(f"Error in get_api_documentation: {str(e)}")
        return api_response(
            success=False,
            message=_("Internal server error"),
            status_code=500
        )