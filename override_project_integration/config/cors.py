"""
CORS configuration for the integration API
"""

import frappe
import re
from urllib.parse import urlparse

# Default CORS configuration
DEFAULT_CORS_CONFIG = {
    "allowed_origins": [
        "http://localhost:3000",
        "http://localhost:5173", 
        "http://localhost:8080",
        "https://graduation-project-delta-green.netlify.app"
    ],
    "allowed_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    "allowed_headers": [
        "Content-Type", 
        "Authorization", 
        "X-Requested-With",
        "X-API-Key",
        "X-CSRF-Token"
    ],
    "allow_credentials": True,
    "max_age": 86400,  # 24 hours
    "expose_headers": ["X-Request-ID", "X-Rate-Limit-Remaining"],
    "strict_origin_validation": True
}

def get_cors_config():
    """
    Get CORS configuration from site config or return defaults
    
    Returns:
        dict: CORS configuration
    """
    site_config = frappe.get_site_config()
    
    return {
        "allowed_origins": site_config.get("cors_allowed_origins", DEFAULT_CORS_CONFIG["allowed_origins"]),
        "allowed_methods": site_config.get("cors_allowed_methods", DEFAULT_CORS_CONFIG["allowed_methods"]),
        "allowed_headers": site_config.get("cors_allowed_headers", DEFAULT_CORS_CONFIG["allowed_headers"]),
        "allow_credentials": site_config.get("cors_allow_credentials", DEFAULT_CORS_CONFIG["allow_credentials"]),
        "max_age": site_config.get("cors_max_age", DEFAULT_CORS_CONFIG["max_age"]),
        "expose_headers": site_config.get("cors_expose_headers", DEFAULT_CORS_CONFIG["expose_headers"]),
        "strict_origin_validation": site_config.get("cors_strict_origin_validation", DEFAULT_CORS_CONFIG["strict_origin_validation"])
    }

def is_origin_allowed(origin):
    """
    Enhanced origin validation with security checks
    
    Args:
        origin (str): The origin to check
    
    Returns:
        tuple: (is_allowed, reason) - bool and string explaining the decision
    """
    if not origin:
        return False, "No origin provided"
    
    config = get_cors_config()
    allowed_origins = config["allowed_origins"]
    strict_validation = config["strict_origin_validation"]
    
    # Security check: validate origin format
    if not _is_valid_origin_format(origin):
        return False, "Invalid origin format"
    
    # Security check: block suspicious origins
    if _is_suspicious_origin(origin):
        return False, "Suspicious origin detected"
    
    # Check for exact match
    if origin in allowed_origins:
        return True, "Exact match"
    
    # Check for wildcard patterns
    for allowed_origin in allowed_origins:
        if allowed_origin == "*":
            if strict_validation:
                # In strict mode, wildcard is only allowed for development
                parsed = urlparse(origin)
                if parsed.hostname in ['localhost', '127.0.0.1'] or parsed.hostname.endswith('.local'):
                    return True, "Wildcard match (development)"
                else:
                    return False, "Wildcard not allowed in strict mode for production origins"
            return True, "Wildcard match"
        
        if allowed_origin.endswith("*"):
            base_origin = allowed_origin[:-1]
            if origin.startswith(base_origin):
                return True, f"Pattern match: {allowed_origin}"
    
    # Check for subdomain patterns (e.g., *.example.com)
    for allowed_origin in allowed_origins:
        if allowed_origin.startswith("*."):
            domain = allowed_origin[2:]  # Remove *.
            parsed_origin = urlparse(origin)
            if parsed_origin.hostname and (
                parsed_origin.hostname == domain or 
                parsed_origin.hostname.endswith(f".{domain}")
            ):
                return True, f"Subdomain match: {allowed_origin}"
    
    return False, "Origin not in allowed list"

def _is_valid_origin_format(origin):
    """
    Validate origin format according to RFC 6454
    
    Args:
        origin (str): Origin to validate
    
    Returns:
        bool: True if format is valid
    """
    try:
        parsed = urlparse(origin)
        
        # Must have scheme and netloc
        if not parsed.scheme or not parsed.netloc:
            return False
        
        # Scheme must be http or https
        if parsed.scheme not in ['http', 'https']:
            return False
        
        # Must not have path, query, or fragment
        if parsed.path not in ['', '/'] or parsed.query or parsed.fragment:
            return False
        
        # Hostname validation
        if not parsed.hostname:
            return False
        
        # Basic hostname format check
        hostname_pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
        if not re.match(hostname_pattern, parsed.hostname):
            # Allow localhost and IP addresses
            if parsed.hostname not in ['localhost', '127.0.0.1'] and not _is_valid_ip(parsed.hostname):
                return False
        
        return True
        
    except Exception:
        return False

def _is_valid_ip(hostname):
    """
    Check if hostname is a valid IP address
    
    Args:
        hostname (str): Hostname to check
    
    Returns:
        bool: True if valid IP address
    """
    import ipaddress
    try:
        ipaddress.ip_address(hostname)
        return True
    except ValueError:
        return False

def _is_suspicious_origin(origin):
    """
    Check for suspicious origin patterns that might indicate attacks
    
    Args:
        origin (str): Origin to check
    
    Returns:
        bool: True if origin appears suspicious
    """
    suspicious_patterns = [
        r'javascript:',
        r'data:',
        r'file:',
        r'ftp:',
        r'<script',
        r'%3Cscript',
        r'vbscript:',
        r'about:',
        r'chrome:',
        r'chrome-extension:',
        r'moz-extension:',
        r'safari-extension:',
        r'ms-browser-extension:'
    ]
    
    origin_lower = origin.lower()
    for pattern in suspicious_patterns:
        if re.search(pattern, origin_lower):
            return True
    
    return False

def log_cors_violation(origin, reason, request_info=None):
    """
    Log CORS violation attempts for security monitoring
    
    Args:
        origin (str): The blocked origin
        reason (str): Reason for blocking
        request_info (dict): Additional request information
    """
    try:
        violation_data = {
            "origin": origin,
            "reason": reason,
            "timestamp": frappe.utils.now(),
            "ip_address": frappe.local.request_ip,
            "user_agent": frappe.get_request_header("User-Agent", ""),
            "endpoint": frappe.request.path if hasattr(frappe, 'request') else None,
            "method": frappe.request.method if hasattr(frappe, 'request') else None
        }
        
        if request_info:
            violation_data.update(request_info)
        
        frappe.log_error(
            f"CORS Violation: {reason}\nOrigin: {origin}\nDetails: {violation_data}",
            "CORS Security Violation"
        )
        
    except Exception as e:
        frappe.log_error(f"Error logging CORS violation: {str(e)}")

def get_security_headers():
    """
    Get comprehensive security headers
    
    Returns:
        dict: Security headers to apply
    """
    return {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
        "Content-Security-Policy": (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self'; "
            "media-src 'self'; "
            "object-src 'none'; "
            "child-src 'none'; "
            "worker-src 'self'; "
            "frame-ancestors 'none'; "
            "form-action 'self'; "
            "base-uri 'self'; "
            "manifest-src 'self'"
        ),
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "accelerometer=(), "
            "gyroscope=(), "
            "speaker=(), "
            "vibrate=(), "
            "fullscreen=(self), "
            "sync-xhr=()"
        ),
        "Cross-Origin-Embedder-Policy": "require-corp",
        "Cross-Origin-Opener-Policy": "same-origin",
        "Cross-Origin-Resource-Policy": "cross-origin"
    }