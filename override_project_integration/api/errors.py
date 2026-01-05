"""
Custom error classes and error handling utilities
"""

import frappe
from frappe import _
import traceback
import json
from datetime import datetime
import uuid


class APIError(Exception):
    """Base API error class"""
    
    def __init__(self, message, status_code=400, error_code=None, details=None):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or f"ERROR_{status_code}"
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(APIError):
    """Validation error for invalid input data"""
    
    def __init__(self, message=None, field_errors=None):
        message = message or _("Validation failed")
        details = {"field_errors": field_errors} if field_errors else {}
        super().__init__(message, status_code=400, error_code="VALIDATION_ERROR", details=details)


class AuthenticationError(APIError):
    """Authentication error for invalid credentials"""
    
    def __init__(self, message=None):
        message = message or _("Authentication failed")
        super().__init__(message, status_code=401, error_code="AUTH_ERROR")


class AuthorizationError(APIError):
    """Authorization error for insufficient permissions"""
    
    def __init__(self, message=None):
        message = message or _("Insufficient permissions")
        super().__init__(message, status_code=403, error_code="PERMISSION_ERROR")


class NotFoundError(APIError):
    """Error for resource not found"""
    
    def __init__(self, message=None, resource=None):
        if resource:
            message = message or _("Resource not found: {0}").format(resource)
        else:
            message = message or _("Resource not found")
        super().__init__(message, status_code=404, error_code="NOT_FOUND")


class RateLimitError(APIError):
    """Error for rate limit exceeded"""
    
    def __init__(self, message=None, retry_after=None):
        message = message or _("Rate limit exceeded")
        details = {"retry_after": retry_after} if retry_after else {}
        super().__init__(message, status_code=429, error_code="RATE_LIMIT_EXCEEDED", details=details)


class FileUploadError(APIError):
    """Error for file upload issues"""
    
    def __init__(self, message=None, file_errors=None):
        message = message or _("File upload failed")
        details = {"file_errors": file_errors} if file_errors else {}
        super().__init__(message, status_code=400, error_code="FILE_UPLOAD_ERROR", details=details)


class TokenError(APIError):
    """Error for token-related issues"""
    
    def __init__(self, message=None, token_details=None):
        message = message or _("Invalid or expired token")
        details = {"token_details": token_details} if token_details else {}
        super().__init__(message, status_code=400, error_code="TOKEN_ERROR", details=details)


class DatabaseError(APIError):
    """Error for database-related issues"""
    
    def __init__(self, message=None):
        message = message or _("Database operation failed")
        super().__init__(message, status_code=500, error_code="DATABASE_ERROR")


class ConfigurationError(APIError):
    """Error for configuration-related issues"""
    
    def __init__(self, message=None):
        message = message or _("System configuration error")
        super().__init__(message, status_code=500, error_code="CONFIG_ERROR")


class ErrorLogger:
    """
    Enhanced error logging utility
    """
    
    @staticmethod
    def log_error(error, context=None, request_data=None, user_id=None):
        """
        Log error with comprehensive context information
        
        Args:
            error (Exception): The error to log
            context (dict): Additional context information
            request_data (dict): Request data (will be sanitized)
            user_id (str): User ID if available
        """
        try:
            error_data = {
                "timestamp": datetime.now().isoformat(),
                "error_type": type(error).__name__,
                "error_message": str(error),
                "request_id": str(uuid.uuid4()),
                "user_id": user_id or frappe.session.user,
                "ip_address": frappe.local.request_ip,
                "user_agent": frappe.get_request_header("User-Agent", ""),
                "endpoint": frappe.request.path if hasattr(frappe, 'request') else None,
                "method": frappe.request.method if hasattr(frappe, 'request') else None
            }
            
            # Add context if provided
            if context:
                error_data["context"] = context
            
            # Add sanitized request data
            if request_data:
                error_data["request_data"] = ErrorLogger._sanitize_request_data(request_data)
            
            # Add stack trace for debugging
            if hasattr(error, '__traceback__'):
                error_data["stack_trace"] = traceback.format_exception(
                    type(error), error, error.__traceback__
                )
            
            # Log to Frappe's error log
            frappe.log_error(
                json.dumps(error_data, indent=2, default=str),
                f"API Error: {type(error).__name__}"
            )
            
        except Exception as logging_error:
            # Fallback logging if main logging fails
            frappe.log_error(f"Error logging failed: {str(logging_error)}")
            frappe.log_error(f"Original error: {str(error)}")
    
    @staticmethod
    def _sanitize_request_data(data):
        """
        Sanitize request data by removing sensitive information
        
        Args:
            data (dict): Request data to sanitize
            
        Returns:
            dict: Sanitized data
        """
        if not isinstance(data, dict):
            return data
        
        sensitive_fields = [
            'password', 'token', 'api_key', 'secret', 'private_key',
            'access_token', 'refresh_token', 'authorization'
        ]
        
        sanitized = {}
        for key, value in data.items():
            if key.lower() in sensitive_fields:
                sanitized[key] = "[REDACTED]"
            elif isinstance(value, dict):
                sanitized[key] = ErrorLogger._sanitize_request_data(value)
            else:
                sanitized[key] = value
        
        return sanitized


class ErrorResponseFormatter:
    """
    Standardized error response formatting
    """
    
    @staticmethod
    def format_validation_error(field_errors, general_message=None):
        """
        Format validation errors with field-specific details
        
        Args:
            field_errors (dict): Dictionary of field errors
            general_message (str): General error message
            
        Returns:
            dict: Formatted error response
        """
        from override_project_integration.api.utils import api_response
        
        message = general_message or _("Form validation failed")
        
        # Ensure field_errors is properly structured
        if isinstance(field_errors, dict):
            formatted_errors = {}
            for field, errors in field_errors.items():
                if isinstance(errors, list):
                    formatted_errors[field] = errors
                else:
                    formatted_errors[field] = [str(errors)]
        else:
            formatted_errors = {"general": [str(field_errors)]}
        
        return api_response(
            success=False,
            message=message,
            status_code=400,
            errors={
                "error_type": "validation_error",
                "field_errors": formatted_errors,
                "error_count": sum(len(errors) for errors in formatted_errors.values())
            }
        )
    
    @staticmethod
    def format_file_upload_error(file_errors, general_message=None):
        """
        Format file upload errors
        
        Args:
            file_errors (list): List of file upload errors
            general_message (str): General error message
            
        Returns:
            dict: Formatted error response
        """
        from override_project_integration.api.utils import api_response
        
        message = general_message or _("File upload failed")
        
        return api_response(
            success=False,
            message=message,
            status_code=400,
            errors={
                "error_type": "file_upload_error",
                "file_errors": file_errors,
                "error_count": len(file_errors) if file_errors else 0
            }
        )
    
    @staticmethod
    def format_server_error(error_message=None, error_id=None):
        """
        Format server errors with user-friendly messages
        
        Args:
            error_message (str): Technical error message
            error_id (str): Error tracking ID
            
        Returns:
            dict: Formatted error response
        """
        from override_project_integration.api.utils import api_response
        
        user_message = _("An internal server error occurred. Please try again later.")
        
        error_details = {
            "error_type": "server_error",
            "user_message": user_message
        }
        
        if error_id:
            error_details["error_id"] = error_id
            user_message += f" (Error ID: {error_id})"
        
        return api_response(
            success=False,
            message=user_message,
            status_code=500,
            errors=error_details
        )


def handle_api_error(func):
    """
    Enhanced decorator to handle API errors and return standardized responses
    
    Args:
        func: The API function to wrap
    
    Returns:
        function: Wrapped function with comprehensive error handling
    """
    import functools
    from override_project_integration.api.utils import api_response
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        error_id = str(uuid.uuid4())
        
        try:
            return func(*args, **kwargs)
            
        except ValidationError as e:
            ErrorLogger.log_error(e, context={"function": func.__name__})
            return ErrorResponseFormatter.format_validation_error(
                e.details.get("field_errors", {}),
                e.message
            )
            
        except FileUploadError as e:
            ErrorLogger.log_error(e, context={"function": func.__name__})
            return ErrorResponseFormatter.format_file_upload_error(
                e.details.get("file_errors", []),
                e.message
            )
            
        except APIError as e:
            ErrorLogger.log_error(e, context={"function": func.__name__})
            return api_response(
                success=False,
                message=e.message,
                status_code=e.status_code,
                errors={
                    "error_type": e.error_code.lower(),
                    "details": e.details,
                    "error_id": error_id
                }
            )
            
        except frappe.ValidationError as e:
            ErrorLogger.log_error(e, context={"function": func.__name__})
            return ErrorResponseFormatter.format_validation_error(
                {"general": [str(e)]},
                _("Data validation failed")
            )
            
        except frappe.PermissionError as e:
            ErrorLogger.log_error(e, context={"function": func.__name__})
            return api_response(
                success=False,
                message=_("You don't have permission to perform this action"),
                status_code=403,
                errors={
                    "error_type": "permission_error",
                    "error_id": error_id
                }
            )
            
        except frappe.DoesNotExistError as e:
            ErrorLogger.log_error(e, context={"function": func.__name__})
            return api_response(
                success=False,
                message=_("The requested resource was not found"),
                status_code=404,
                errors={
                    "error_type": "not_found_error",
                    "error_id": error_id
                }
            )
            
        except Exception as e:
            ErrorLogger.log_error(
                e, 
                context={
                    "function": func.__name__,
                    "error_id": error_id
                }
            )
            return ErrorResponseFormatter.format_server_error(
                str(e),
                error_id
            )
    
    return wrapper


def validate_and_handle_errors(required_fields=None, optional_fields=None):
    """
    Decorator that combines request validation with error handling
    
    Args:
        required_fields (list): List of required field names
        optional_fields (list): List of optional field names
    
    Returns:
        function: Decorator function
    """
    def decorator(func):
        @functools.wraps(func)
        @handle_api_error
        def wrapper(*args, **kwargs):
            from override_project_integration.api.utils import validate_request
            
            # Validate request
            is_valid, data, errors = validate_request(required_fields, optional_fields)
            
            if not is_valid:
                raise ValidationError(field_errors=errors.get("field_errors", {}))
            
            # Add validated data to kwargs
            kwargs['validated_data'] = data
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator