"""
API configuration settings
"""

import frappe

# Default API configuration
DEFAULT_API_CONFIG = {
    "rate_limits": {
        "submit_form": {"limit": 10, "window": 60},                     # 10 form submissions per minute
        "create_project_application": {"limit": 10, "window": 60},      # 10 requests per minute
        "get_application_status": {"limit": 20, "window": 60},          # 20 requests per minute
        "upload_document": {"limit": 5, "window": 60},                  # 5 uploads per minute
        "get_form_schema": {"limit": 30, "window": 60},                 # 30 schema requests per minute
        "get_supported_forms": {"limit": 30, "window": 60},             # 30 requests per minute
        "default": {"limit": 60, "window": 60}                          # Default rate limit
    },
    "file_upload": {
        "max_file_size": 10 * 1024 * 1024,  # 10MB
        "allowed_extensions": [".jpg", ".jpeg", ".png", ".pdf", ".doc", ".docx"],
        "upload_path": "files/project_applications"
    },
    "token": {
        "length": 32,
        "expires_in_days": 365  # Tokens expire after 1 year
    },
    "logging": {
        "log_requests": True,
        "log_responses": True,
        "log_errors": True
    }
}

def get_api_config():
    """
    Get API configuration from site config or return defaults
    
    Returns:
        dict: API configuration
    """
    site_config = frappe.get_site_config()
    
    config = DEFAULT_API_CONFIG.copy()
    
    # Override with site-specific settings if available
    if "api_config" in site_config:
        site_api_config = site_config["api_config"]
        
        # Merge rate limits
        if "rate_limits" in site_api_config:
            config["rate_limits"].update(site_api_config["rate_limits"])
        
        # Merge file upload settings
        if "file_upload" in site_api_config:
            config["file_upload"].update(site_api_config["file_upload"])
        
        # Merge token settings
        if "token" in site_api_config:
            config["token"].update(site_api_config["token"])
        
        # Merge logging settings
        if "logging" in site_api_config:
            config["logging"].update(site_api_config["logging"])
    
    return config

def get_rate_limit_config(endpoint_name):
    """
    Get rate limit configuration for a specific endpoint
    
    Args:
        endpoint_name (str): Name of the endpoint
    
    Returns:
        dict: Rate limit configuration with 'limit' and 'window' keys
    """
    config = get_api_config()
    rate_limits = config["rate_limits"]
    
    return rate_limits.get(endpoint_name, rate_limits["default"])

def get_file_upload_config():
    """
    Get file upload configuration
    
    Returns:
        dict: File upload configuration
    """
    config = get_api_config()
    return config["file_upload"]

def get_token_config():
    """
    Get token configuration
    
    Returns:
        dict: Token configuration
    """
    config = get_api_config()
    return config["token"]

def is_logging_enabled(log_type):
    """
    Check if a specific type of logging is enabled
    
    Args:
        log_type (str): Type of logging ('requests', 'responses', 'errors')
    
    Returns:
        bool: True if logging is enabled for the specified type
    """
    config = get_api_config()
    logging_config = config["logging"]
    
    log_key = f"log_{log_type}"
    return logging_config.get(log_key, True)