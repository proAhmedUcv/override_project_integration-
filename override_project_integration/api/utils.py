"""
API utility functions and response handlers
"""

import frappe
from frappe import _
import json
from datetime import datetime
import uuid
import re


def create_api_response(success=True, message="", data=None, status_code=200, errors=None):
    """
    Create standardized API response format
    
    Args:
        success (bool): Whether the operation was successful
        message (str): Human-readable message
        data (dict): Response data
        status_code (int): HTTP status code
        errors (dict): Error details
    
    Returns:
        dict: Formatted API response
    """
    response = {
        "success": success,
        "message": message,
        "timestamp": datetime.now().isoformat(),
        "status_code": status_code
    }
    
    if success and data is not None:
        response["data"] = data
    elif not success:
        error_info = {
            "code": f"ERROR_{status_code}",
            "message": message,
            "request_id": str(uuid.uuid4())
        }
        
        if errors is not None:
            error_info.update(errors)
        
        response["error"] = error_info
    
    # Set HTTP status code
    if hasattr(frappe, 'local') and hasattr(frappe.local, 'response'):
        frappe.local.response.http_status_code = status_code
    
    return response


def validate_token_id(token_id):
    """
    Validate token_id and get associated user information
    
    Args:
        token_id (str): Token ID from better-auth
        
    Returns:
        dict: User information if valid, None if invalid
    """
    try:
        if not token_id:
            return None
        
        # Check if Micro Enterprise Request exists with this token_id
        micro_enterprise_requests = frappe.get_all(
            "Micro Enterprise Request",
            filters={"token_id": token_id},
            fields=["name", "family_name", "first_name", "last_name", "creation"]
        )
        
        if micro_enterprise_requests:
            return {
                "token_id": token_id,
                "micro_enterprise_requests": micro_enterprise_requests,
                "is_valid": True
            }
        
        return None
        
    except Exception as e:
        frappe.log_error(f"Error validating token_id: {str(e)}", "Token Validation")
        return None


def log_api_call(endpoint, data=None):
    """
    Log API call for monitoring and debugging
    
    Args:
        endpoint (str): API endpoint called
        data (dict): Request data (sanitized)
    """
    try:
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "endpoint": endpoint,
            "method": frappe.request.method if hasattr(frappe, 'request') else 'Unknown',
            "ip_address": getattr(frappe.local, 'request_ip', 'Unknown'),
            "user_agent": frappe.get_request_header("User-Agent", "") if hasattr(frappe, 'get_request_header') else "",
            "request_id": str(uuid.uuid4())
        }
        
        if data:
            # Sanitize sensitive data before logging
            sanitized_data = {k: v for k, v in data.items() 
                            if k not in ["password", "token", "api_key", "token_id"]}
            log_data["request_data"] = sanitized_data
        
        # Log at info level
        frappe.logger().info(json.dumps(log_data, indent=2))
            
    except Exception as e:
        frappe.log_error(f"Error logging API call: {str(e)}")


def api_response(success=True, message="", data=None, status_code=200, errors=None):
    """
    Enhanced standardized API response format
    
    Args:
        success (bool): Whether the operation was successful
        message (str): Human-readable message
        data (dict): Response data
        status_code (int): HTTP status code
        errors (dict): Error details
    
    Returns:
        dict: Formatted API response
    """
    response = {
        "success": success,
        "message": message,
        "timestamp": datetime.now().isoformat(),
        "status_code": status_code
    }
    
    if success and data is not None:
        response["data"] = data
    elif not success:
        error_info = {
            "code": f"ERROR_{status_code}",
            "message": message,
            "request_id": str(uuid.uuid4())
        }
        
        if errors is not None:
            error_info.update(errors)
        
        response["error"] = error_info
    
    # Set HTTP status code
    if hasattr(frappe, 'local') and hasattr(frappe.local, 'response'):
        frappe.local.response.http_status_code = status_code
        
        # Add CORS headers for cross-origin requests (only if headers exist)
        if hasattr(frappe.local.response, 'headers') and frappe.local.response.headers is not None:
            frappe.local.response.headers.update({
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With"
            })
    
    return response


def validate_request(required_fields=None, optional_fields=None):
    """
    Enhanced request validation with comprehensive error reporting
    
    Args:
        required_fields (list): List of required field names
        optional_fields (list): List of optional field names
    
    Returns:
        tuple: (is_valid, data, errors)
    """
    if required_fields is None:
        required_fields = []
    if optional_fields is None:
        optional_fields = []
    
    try:
        # Get request data
        if frappe.request.method == "POST":
            data = frappe.local.form_dict
        else:
            data = frappe.local.form_dict
        
        errors = {}
        field_errors = {}
        
        # Check required fields
        for field in required_fields:
            value = data.get(field)
            if not value or (isinstance(value, str) and not value.strip()):
                field_errors[field] = [_("This field is required")]
        
        # Validate field formats if values are provided
        for field in required_fields + optional_fields:
            value = data.get(field)
            if value:
                # Email validation
                if 'email' in field.lower() and value:
                    if not re.match(r'^[^@]+@[^@]+\.[^@]+$', value):
                        if field not in field_errors:
                            field_errors[field] = []
                        field_errors[field].append(_("Invalid email format"))
                
                # Phone validation
                if 'phone' in field.lower() and value:
                    phone_clean = re.sub(r'[^\d+]', '', value)
                    if len(phone_clean) < 9:
                        if field not in field_errors:
                            field_errors[field] = []
                        field_errors[field].append(_("Phone number must be at least 9 digits"))
                
                # Sanitize text inputs
                if isinstance(value, str):
                    data[field] = sanitize_input(value)
        
        # If there are field validation errors, return them
        if field_errors:
            errors["field_errors"] = field_errors
            return False, None, errors
        
        # Extract only the fields we care about
        validated_data = {}
        all_fields = required_fields + optional_fields
        
        for field in all_fields:
            if field in data:
                validated_data[field] = data[field]
        
        return True, validated_data, None
        
    except Exception as e:
        frappe.log_error(f"Request validation error: {str(e)}")
        return False, None, {"general": [_("Invalid request format")]}


def validate_file_upload(file_data, allowed_types=None, max_size_mb=10):
    """
    Validate uploaded file data
    
    Args:
        file_data (dict): File data with filename, content, content_type
        allowed_types (list): List of allowed file extensions
        max_size_mb (int): Maximum file size in MB
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not file_data:
        return False, _("No file data provided")
    
    filename = file_data.get("filename", "")
    content = file_data.get("content", b"")
    content_type = file_data.get("content_type", "")
    
    # Check if file has a name
    if not filename:
        return False, _("File must have a name")
    
    # Check file extension
    if allowed_types:
        file_ext = filename.lower().split('.')[-1] if '.' in filename else ""
        if file_ext not in [ext.lower().lstrip('.') for ext in allowed_types]:
            return False, _("File type '{0}' is not allowed. Allowed types: {1}").format(
                file_ext, ", ".join(allowed_types)
            )
    
    # Check file size
    if content:
        file_size_mb = len(content) / (1024 * 1024)
        if file_size_mb > max_size_mb:
            return False, _("File size ({0:.1f}MB) exceeds maximum allowed size ({1}MB)").format(
                file_size_mb, max_size_mb
            )
    
    # Check for potentially dangerous file types
    dangerous_extensions = ['exe', 'bat', 'cmd', 'scr', 'pif', 'vbs', 'js', 'jar']
    file_ext = filename.lower().split('.')[-1] if '.' in filename else ""
    if file_ext in dangerous_extensions:
        return False, _("File type '{0}' is not allowed for security reasons").format(file_ext)
    
    return True, None


def sanitize_input(text):
    """
    Sanitize text input to prevent XSS and injection attacks
    
    Args:
        text (str): Input text to sanitize
    
    Returns:
        str: Sanitized text
    """
    if not isinstance(text, str):
        return text
    
    # First remove potential script tags and javascript before encoding
    import re
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)
    text = re.sub(r'on\w+\s*=', '', text, flags=re.IGNORECASE)
    text = re.sub(r'alert\s*\(', '', text, flags=re.IGNORECASE)  # Remove alert calls
    
    # Then HTML entity encoding for XSS prevention
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    text = text.replace('"', "&quot;")
    text = text.replace("'", "&#x27;")
    text = text.replace("/", "&#x2F;")
    
    return text.strip()


def log_api_request(endpoint, method, data=None, response=None, error=None):
    """
    Log API request details for monitoring and debugging
    
    Args:
        endpoint (str): API endpoint called
        method (str): HTTP method
        data (dict): Request data (sanitized)
        response (dict): Response data
        error (str): Error message if any
    """
    try:
        log_data = {
            "timestamp": datetime.now().isoformat(),
            "endpoint": endpoint,
            "method": method,
            "ip_address": getattr(frappe.local, 'request_ip', 'Unknown'),
            "user_agent": frappe.get_request_header("User-Agent", "") if hasattr(frappe, 'get_request_header') else "",
            "request_id": str(uuid.uuid4())
        }
        
        if data:
            # Sanitize sensitive data before logging
            sanitized_data = {k: v for k, v in data.items() 
                            if k not in ["password", "token", "api_key"]}
            log_data["request_data"] = sanitized_data
        
        if response:
            log_data["response_status"] = response.get("success", False)
        
        if error:
            log_data["error"] = error
            frappe.log_error(json.dumps(log_data, indent=2), "API Request Error")
        else:
            # Log successful requests at info level
            frappe.logger().info(json.dumps(log_data, indent=2))
            
    except Exception as e:
        frappe.log_error(f"Error logging API request: {str(e)}")


def get_client_ip():
    """
    Get client IP address from request headers
    
    Returns:
        str: Client IP address
    """
    # Check for forwarded IP first (in case of proxy/load balancer)
    forwarded_for = frappe.get_request_header("X-Forwarded-For") if hasattr(frappe, 'get_request_header') else None
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    real_ip = frappe.get_request_header("X-Real-IP") if hasattr(frappe, 'get_request_header') else None
    if real_ip:
        return real_ip
    
    return getattr(frappe.local, 'request_ip', 'unknown')


def validate_token_request(token):
    """
    Validate token from request parameters
    
    Args:
        token (str): Token to validate
        
    Returns:
        tuple: (is_valid, error_response)
    """
    try:
        if not token:
            return False, api_response(
                success=False,
                message=_("Token is required"),
                status_code=400,
                errors={"token": [_("Token parameter is missing")]}
            )
        
        # Basic token format validation
        if len(token) < 10:
            return False, api_response(
                success=False,
                message=_("Invalid token format"),
                status_code=400,
                errors={"token": [_("Token format is invalid")]}
            )
        
        return True, None
        
    except Exception as e:
        frappe.log_error(f"Token validation error: {str(e)}")
        return False, api_response(
            success=False,
            message=_("Error validating token"),
            status_code=500
        )


def extract_token_from_request():
    """
    Extract token from request parameters (query string or form data)
    
    Returns:
        str: Token value or None if not found
    """
    # Try to get token from query parameters first
    token = frappe.local.form_dict.get('token')
    
    # If not found, try common alternative parameter names
    if not token:
        token = frappe.local.form_dict.get('application_token')
    
    if not token:
        token = frappe.local.form_dict.get('tracking_token')
    
    if not token:
        token = frappe.local.form_dict.get('token_id')
    
    return token


def format_application_response(doc_data):
    """
    Format application data for API response
    
    Args:
        doc_data (dict): Document data from token lookup
        
    Returns:
        dict: Formatted response data
    """
    return {
        "token": doc_data.get("token"),
        "application_id": doc_data.get("name"),
        "status": doc_data.get("status", "Open"),
        "applicant_name": doc_data.get("applicant_name", _("Unknown")),
        "project_name": doc_data.get("project_name", _("Unknown Project")),
        "submitted_date": doc_data.get("submitted_date"),
        "last_updated": doc_data.get("last_updated"),
        "notes": doc_data.get("notes", "")
    }