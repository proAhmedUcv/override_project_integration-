"""
Security middleware for API endpoints
"""

import frappe
from frappe import _
import functools
import time
from override_project_integration.api.utils import api_response, get_client_ip


def before_request():
    """
    Global before request handler for security and logging
    """
    try:
        # Log all API requests to our endpoints
        if frappe.request.path and "/api/method/override_project_integration" in frappe.request.path:
            from override_project_integration.api.utils import log_api_request
            log_api_request(
                endpoint=frappe.request.path,
                method=frappe.request.method,
                data=frappe.local.form_dict
            )
    except Exception as e:
        frappe.log_error(f"Error in before_request: {str(e)}")


def after_request():
    """
    Global after request handler for cleanup and final logging
    """
    try:
        # Additional cleanup or logging can be added here
        pass
    except Exception as e:
        frappe.log_error(f"Error in after_request: {str(e)}")


def cors_handler(func):
    """
    Enhanced CORS middleware decorator for API endpoints
    
    Args:
        func: The API function to wrap
    
    Returns:
        function: Wrapped function with comprehensive CORS handling
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        from override_project_integration.config.cors import (
            get_cors_config, is_origin_allowed, log_cors_violation, get_security_headers
        )
        
        cors_config = get_cors_config()
        origin = frappe.get_request_header("Origin")
        
        # Handle preflight requests
        if frappe.request.method == "OPTIONS":
            frappe.local.response.http_status_code = 200
            
            # Validate origin for preflight requests
            is_allowed, reason = is_origin_allowed(origin)
            
            if not is_allowed and origin:
                log_cors_violation(origin, f"Preflight request blocked: {reason}")
                # Return 403 for blocked preflight requests
                frappe.local.response.http_status_code = 403
                return api_response(
                    success=False,
                    message=_("CORS preflight request not allowed"),
                    status_code=403
                )
            
            # Set CORS headers for preflight
            headers = {
                "Access-Control-Allow-Methods": ", ".join(cors_config["allowed_methods"]),
                "Access-Control-Allow-Headers": ", ".join(cors_config["allowed_headers"]),
                "Access-Control-Max-Age": str(cors_config["max_age"])
            }
            
            if cors_config["allow_credentials"]:
                headers["Access-Control-Allow-Credentials"] = "true"
            
            # Set expose headers
            if cors_config.get("expose_headers"):
                headers["Access-Control-Expose-Headers"] = ", ".join(cors_config["expose_headers"])
            
            # Set origin header
            if is_allowed and origin:
                headers["Access-Control-Allow-Origin"] = origin
            elif not origin:
                # No origin header in request
                headers["Access-Control-Allow-Origin"] = "*"
            
            # Apply security headers
            headers.update(get_security_headers())
            
            # Only set headers if response object exists (not in test environment)
            if hasattr(frappe.local, 'response') and frappe.local.response and hasattr(frappe.local.response, 'headers'):
                frappe.local.response.headers.update(headers)
            return {}
        
        # Validate origin for actual requests
        is_allowed, reason = is_origin_allowed(origin)
        
        if origin and not is_allowed:
            log_cors_violation(
                origin, 
                f"Request blocked: {reason}",
                {
                    "endpoint": frappe.request.path,
                    "method": frappe.request.method,
                    "referer": frappe.get_request_header("Referer", "")
                }
            )
            # For security, we still process the request but don't set CORS headers
            # This prevents the browser from accessing the response
        
        # Set CORS headers for actual requests
        headers = {}
        if is_allowed and origin:
            headers["Access-Control-Allow-Origin"] = origin
            if cors_config["allow_credentials"]:
                headers["Access-Control-Allow-Credentials"] = "true"
        elif not origin:
            # No origin header (direct API access)
            headers["Access-Control-Allow-Origin"] = "*"
        
        # Set expose headers
        if cors_config.get("expose_headers"):
            headers["Access-Control-Expose-Headers"] = ", ".join(cors_config["expose_headers"])
        
        # Apply comprehensive security headers
        headers.update(get_security_headers())
        
        # Add request tracking headers
        import uuid
        request_id = str(uuid.uuid4())
        headers["X-Request-ID"] = request_id
        
        # Only set headers if response object exists and has headers attribute
        if (hasattr(frappe.local, 'response') and 
            frappe.local.response and 
            hasattr(frappe.local.response, 'headers') and
            frappe.local.response.headers is not None):
            frappe.local.response.headers.update(headers)
        elif hasattr(frappe.local, 'response') and frappe.local.response:
            # Initialize headers if they don't exist
            if not hasattr(frappe.local.response, 'headers') or frappe.local.response.headers is None:
                frappe.local.response.headers = {}
            frappe.local.response.headers.update(headers)
        
        # Store request ID for logging
        frappe.local.request_id = request_id
        
        return func(*args, **kwargs)
    
    return wrapper


def rate_limit(limit=None, window=None, endpoint_name=None):
    """
    Enhanced rate limiting decorator with security event logging
    
    Args:
        limit (int): Number of requests allowed (optional, uses config if not provided)
        window (int): Time window in seconds (optional, uses config if not provided)
        endpoint_name (str): Endpoint name for configuration lookup
    
    Returns:
        function: Decorator function
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            from override_project_integration.config.api_settings import get_rate_limit_config
            
            # Get rate limit configuration
            if endpoint_name:
                config = get_rate_limit_config(endpoint_name)
                actual_limit = limit or config["limit"]
                actual_window = window or config["window"]
            else:
                actual_limit = limit or 60
                actual_window = window or 60
            
            client_ip = get_client_ip()
            user_agent = frappe.get_request_header("User-Agent", "")
            cache_key = f"rate_limit:{func.__name__}:{client_ip}"
            
            try:
                # Get current request count from cache
                current_requests = frappe.cache().get(cache_key) or 0
                
                if current_requests >= actual_limit:
                    # Log security event for rate limit violation
                    _log_security_event(
                        event_type="rate_limit_exceeded",
                        details={
                            "ip_address": client_ip,
                            "user_agent": user_agent,
                            "endpoint": func.__name__,
                            "limit": actual_limit,
                            "window": actual_window,
                            "current_requests": current_requests,
                            "timestamp": frappe.utils.now()
                        }
                    )
                    
                    # Add rate limit headers
                    if hasattr(frappe.local, 'response') and frappe.local.response and hasattr(frappe.local.response, 'headers'):
                        frappe.local.response.headers.update({
                            "X-Rate-Limit-Limit": str(actual_limit),
                            "X-Rate-Limit-Remaining": "0",
                            "X-Rate-Limit-Reset": str(int(time.time()) + actual_window),
                            "Retry-After": str(actual_window)
                        })
                    
                    return api_response(
                        success=False,
                        message=_("Rate limit exceeded. Please try again later."),
                        status_code=429,
                        errors={
                            "error_type": "rate_limit_exceeded",
                            "rate_limit": {
                                "limit": actual_limit,
                                "window": actual_window,
                                "retry_after": actual_window
                            },
                            "message": _("Too many requests. Limit: {} requests per {} seconds").format(
                                actual_limit, actual_window
                            )
                        }
                    )
                
                # Increment request count
                frappe.cache().set(cache_key, current_requests + 1, expires_in_sec=actual_window)
                
                # Add rate limit headers for successful requests
                remaining = max(0, actual_limit - current_requests - 1)
                if hasattr(frappe.local, 'response') and frappe.local.response and hasattr(frappe.local.response, 'headers'):
                    frappe.local.response.headers.update({
                        "X-Rate-Limit-Limit": str(actual_limit),
                        "X-Rate-Limit-Remaining": str(remaining),
                        "X-Rate-Limit-Reset": str(int(time.time()) + actual_window)
                    })
                
                return func(*args, **kwargs)
                
            except Exception as e:
                # Log error only if not in test environment
                if not frappe.flags.in_test:
                    frappe.log_error(f"Rate limiting error: {str(e)}")
                # If rate limiting fails, allow the request to proceed
                return func(*args, **kwargs)
        
        return wrapper
    return decorator


def _log_security_event(event_type, details=None):
    """
    Log security events for monitoring and analysis
    
    Args:
        event_type (str): Type of security event
        details (dict): Additional event details
    """
    try:
        event_data = {
            "event_type": event_type,
            "timestamp": frappe.utils.now(),
            "ip_address": frappe.local.request_ip,
            "user_agent": frappe.get_request_header("User-Agent", ""),
            "endpoint": frappe.request.path if hasattr(frappe, 'request') else None,
            "method": frappe.request.method if hasattr(frappe, 'request') else None,
            "user": frappe.session.user if hasattr(frappe, 'session') else None,
            "referer": frappe.get_request_header("Referer", "")
        }
        
        if details:
            event_data.update(details)
        
        # Log to Frappe's error log system
        frappe.log_error(
            f"Security Event: {event_type}\nDetails: {frappe.as_json(event_data, indent=2)}",
            f"Security Event: {event_type}"
        )
        
        # Also log to a separate security log if configured
        if frappe.get_site_config().get("enable_security_logging"):
            frappe.logger("security").info(frappe.as_json(event_data))
            
    except Exception as e:
        frappe.log_error(f"Error logging security event: {str(e)}")


def security_headers(func):
    """
    Decorator to add comprehensive security headers
    
    Args:
        func: The API function to wrap
    
    Returns:
        function: Wrapped function with security headers
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        from override_project_integration.config.cors import get_security_headers
        
        # Execute the function first
        result = func(*args, **kwargs)
        
        # Add security headers
        if hasattr(frappe.local, 'response') and frappe.local.response and hasattr(frappe.local.response, 'headers'):
            frappe.local.response.headers.update(get_security_headers())
        
        return result
    
    return wrapper


def ip_whitelist(allowed_ips=None):
    """
    IP whitelist decorator for sensitive endpoints
    
    Args:
        allowed_ips (list): List of allowed IP addresses
    
    Returns:
        function: Decorator function
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if allowed_ips is None:
                # If no whitelist specified, allow all IPs
                return func(*args, **kwargs)
            
            client_ip = get_client_ip()
            
            if client_ip not in allowed_ips:
                _log_security_event(
                    event_type="ip_whitelist_violation",
                    details={
                        "blocked_ip": client_ip,
                        "allowed_ips": allowed_ips,
                        "endpoint": func.__name__
                    }
                )
                
                return api_response(
                    success=False,
                    message=_("Access denied"),
                    status_code=403
                )
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def api_key_auth(func):
    """
    API key authentication decorator
    
    Args:
        func: The API function to wrap
    
    Returns:
        function: Wrapped function with API key authentication
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        api_key = frappe.get_request_header("X-API-Key") or frappe.local.form_dict.get("api_key")
        
        if not api_key:
            return api_response(
                success=False,
                message=_("API key is required"),
                status_code=401
            )
        
        # Validate API key (implementation will be added in later tasks)
        # For now, we'll skip validation and log the attempt
        frappe.logger().info(f"API key authentication attempted: {api_key[:8]}...")
        
        return func(*args, **kwargs)
    
    return wrapper


def validate_content_type(allowed_types=None):
    """
    Content type validation decorator
    
    Args:
        allowed_types (list): List of allowed content types
    
    Returns:
        function: Decorator function
    """
    if allowed_types is None:
        allowed_types = ["application/json", "application/x-www-form-urlencoded", "multipart/form-data"]
    
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            content_type = frappe.get_request_header("Content-Type", "")
            
            # Extract base content type (ignore charset and other parameters)
            base_content_type = content_type.split(";")[0].strip()
            
            if frappe.request.method in ["POST", "PUT", "PATCH"] and base_content_type not in allowed_types:
                return api_response(
                    success=False,
                    message=_("Unsupported content type"),
                    status_code=415
                )
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def token_based_auth(required=True):
    """
    Token-based authentication decorator for Vue.js users
    
    Args:
        required (bool): Whether token authentication is required
    
    Returns:
        function: Decorator function
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            from override_project_integration.api.user_session_manager import UserSessionManager
            
            # Get token from request
            token_id = (
                frappe.get_request_header("X-Token-ID") or 
                frappe.local.form_dict.get("token_id") or
                frappe.local.form_dict.get("token")
            )
            
            if not token_id and required:
                _log_security_event(
                    event_type="missing_token_auth",
                    details={
                        "endpoint": func.__name__,
                        "required": required
                    }
                )
                
                return api_response(
                    success=False,
                    message=_("Token authentication is required"),
                    status_code=401,
                    errors={
                        "error_type": "authentication_required",
                        "message": _("Please provide a valid token_id")
                    }
                )
            
            if token_id:
                # Validate session
                if not UserSessionManager.is_session_valid(token_id):
                    _log_security_event(
                        event_type="invalid_token_auth",
                        details={
                            "token_prefix": token_id[:8] if token_id else None,
                            "endpoint": func.__name__
                        }
                    )
                    
                    return api_response(
                        success=False,
                        message=_("Invalid or expired token"),
                        status_code=401,
                        errors={
                            "error_type": "invalid_token",
                            "message": _("Token is invalid or has expired")
                        }
                    )
                
                # Get user identity
                user_identity = UserSessionManager.get_user_identity(token_id)
                
                # Store user identity in frappe.local for use in the endpoint
                frappe.local.vue_user = user_identity
                
                # Update session activity
                UserSessionManager.update_session_activity(
                    token_id,
                    {
                        "last_endpoint": func.__name__,
                        "last_request_time": frappe.utils.now()
                    }
                )
                
                # Log successful authentication
                frappe.logger().info(
                    f"Token authentication successful for endpoint {func.__name__}: "
                    f"token={token_id[:8]}..., user={user_identity['identity']['name'] if user_identity.get('identity') else 'Unknown'}"
                )
            else:
                # No token provided, set anonymous user
                frappe.local.vue_user = {
                    "is_authenticated": False,
                    "user_type": "anonymous",
                    "identity": None
                }
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def require_vue_user(func):
    """
    Decorator that requires a valid Vue.js user session
    
    Args:
        func: The API function to wrap
    
    Returns:
        function: Wrapped function with Vue.js user requirement
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Check if Vue user is authenticated
        vue_user = getattr(frappe.local, 'vue_user', None)
        
        if not vue_user or not vue_user.get('is_authenticated'):
            return api_response(
                success=False,
                message=_("Vue.js user authentication required"),
                status_code=401,
                errors={
                    "error_type": "vue_user_required",
                    "message": _("This endpoint requires a valid Vue.js user session")
                }
            )
        
        return func(*args, **kwargs)
    
    return wrapper


def get_current_vue_user():
    """
    Get the current Vue.js user from the request context
    
    Returns:
        dict: Vue.js user identity or None
    """
    return getattr(frappe.local, 'vue_user', None)