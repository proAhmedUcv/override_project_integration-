"""
Input validation utilities for API endpoints
"""

import frappe
from frappe import _
import re
from datetime import datetime
from override_project_integration.api.token_manager import TokenManager
from override_project_integration.api.errors import ValidationError, TokenError


class InputValidator:
    """
    Comprehensive input validation for API requests
    """
    
    @staticmethod
    def validate_email(email):
        """
        Validate email address format
        
        Args:
            email (str): Email address to validate
            
        Returns:
            tuple: (is_valid, error_message)
        """
        if not email:
            return True, None  # Email is optional in most cases
        
        if not isinstance(email, str):
            return False, _("Email must be a string")
        
        # Basic email regex pattern
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not re.match(pattern, email):
            return False, _("Invalid email format")
        
        # Additional checks
        if len(email) > 254:  # RFC 5321 limit
            return False, _("Email address too long")
        
        local_part, domain = email.rsplit('@', 1)
        if len(local_part) > 64:  # RFC 5321 limit
            return False, _("Email local part too long")
        
        return True, None
    
    @staticmethod
    def validate_phone_number(phone):
        """
        Validate and format phone number
        
        Args:
            phone (str): Phone number to validate
            
        Returns:
            tuple: (is_valid, formatted_phone, error_message)
        """
        if not phone:
            return False, None, _("Phone number is required")
        
        if not isinstance(phone, str):
            return False, None, _("Phone number must be a string")
        
        # Remove all non-digit characters for validation
        digits_only = re.sub(r'\D', '', phone)
        
        # Check length (assuming international format)
        if len(digits_only) < 7 or len(digits_only) > 15:
            return False, None, _("Phone number must be between 7 and 15 digits")
        
        # Format phone number (basic formatting)
        if len(digits_only) == 10:  # Domestic format
            formatted = f"({digits_only[:3]}) {digits_only[3:6]}-{digits_only[6:]}"
        elif len(digits_only) == 11 and digits_only.startswith('1'):  # US format with country code
            formatted = f"+1 ({digits_only[1:4]}) {digits_only[4:7]}-{digits_only[7:]}"
        else:  # International format
            formatted = f"+{digits_only}"
        
        return True, formatted, None
    
    @staticmethod
    def validate_date_format(date_str, field_name="date"):
        """
        Validate date format and convert to standard format
        
        Args:
            date_str (str): Date string to validate
            field_name (str): Field name for error messages
            
        Returns:
            tuple: (is_valid, formatted_date, error_message)
        """
        if not date_str:
            return False, None, _(f"{field_name} is required")
        
        if not isinstance(date_str, str):
            return False, None, _(f"{field_name} must be a string")
        
        # Common date formats to try
        formats = [
            '%Y-%m-%d',      # 2024-01-01
            '%d/%m/%Y',      # 01/01/2024
            '%m/%d/%Y',      # 01/01/2024
            '%d-%m-%Y',      # 01-01-2024
            '%Y/%m/%d',      # 2024/01/01
            '%d.%m.%Y',      # 01.01.2024
        ]
        
        for fmt in formats:
            try:
                parsed_date = datetime.strptime(date_str, fmt)
                # Return in standard format
                return True, parsed_date.strftime('%Y-%m-%d'), None
            except ValueError:
                continue
        
        return False, None, _(f"Invalid {field_name} format. Use YYYY-MM-DD format")
    
    @staticmethod
    def validate_required_fields(data, required_fields):
        """
        Validate that all required fields are present and not empty
        
        Args:
            data (dict): Data to validate
            required_fields (list): List of required field names
            
        Returns:
            tuple: (is_valid, field_errors)
        """
        field_errors = {}
        
        for field in required_fields:
            if field not in data:
                field_errors[field] = [_(f"{field} is required")]
            elif not data[field] or (isinstance(data[field], str) and not data[field].strip()):
                field_errors[field] = [_(f"{field} cannot be empty")]
        
        return len(field_errors) == 0, field_errors
    
    @staticmethod
    def validate_text_length(text, field_name, min_length=0, max_length=None):
        """
        Validate text length
        
        Args:
            text (str): Text to validate
            field_name (str): Field name for error messages
            min_length (int): Minimum length
            max_length (int): Maximum length
            
        Returns:
            tuple: (is_valid, error_message)
        """
        if not text:
            if min_length > 0:
                return False, _(f"{field_name} is required")
            return True, None
        
        if not isinstance(text, str):
            return False, _(f"{field_name} must be text")
        
        text_length = len(text.strip())
        
        if text_length < min_length:
            return False, _(f"{field_name} must be at least {min_length} characters")
        
        if max_length and text_length > max_length:
            return False, _(f"{field_name} must not exceed {max_length} characters")
        
        return True, None
    
    @staticmethod
    def validate_numeric_field(value, field_name, min_value=None, max_value=None, allow_decimal=True):
        """
        Validate numeric field
        
        Args:
            value: Value to validate
            field_name (str): Field name for error messages
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            allow_decimal (bool): Whether decimal values are allowed
            
        Returns:
            tuple: (is_valid, converted_value, error_message)
        """
        if value is None or value == "":
            return False, None, _(f"{field_name} is required")
        
        try:
            if allow_decimal:
                numeric_value = float(value)
            else:
                numeric_value = int(value)
        except (ValueError, TypeError):
            return False, None, _(f"{field_name} must be a valid number")
        
        if min_value is not None and numeric_value < min_value:
            return False, None, _(f"{field_name} must be at least {min_value}")
        
        if max_value is not None and numeric_value > max_value:
            return False, None, _(f"{field_name} must not exceed {max_value}")
        
        return True, numeric_value, None


class TokenValidator:
    """
    Token-specific validation utilities
    """
    
    @staticmethod
    def validate_token_for_lookup(token):
        """
        Validate token for document lookup operations
        
        Args:
            token (str): Token to validate
            
        Returns:
            tuple: (is_valid, document_data, error_message)
            
        Raises:
            TokenError: If token validation fails
        """
        if not token:
            raise TokenError(_("Token is required"))
        
        # Validate token format
        if not TokenManager.validate_token_format(token):
            raise TokenError(_("Invalid token format"))
        
        # Check if token exists and get document
        try:
            document_data = TokenManager.get_document_by_token(token)
            return True, document_data, None
        except TokenError as e:
            raise e
        except Exception as e:
            frappe.log_error(f"Token validation error: {str(e)}")
            raise TokenError(_("Error validating token"))
    
    @staticmethod
    def validate_token_format_only(token):
        """
        Validate only the token format without checking existence
        
        Args:
            token (str): Token to validate
            
        Returns:
            tuple: (is_valid, error_message)
        """
        if not token:
            return False, _("Token is required")
        
        if not isinstance(token, str):
            return False, _("Token must be a string")
        
        if not TokenManager.validate_token_format(token):
            return False, _("Invalid token format. Expected format: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX")
        
        return True, None


# Convenience functions for common validations
def validate_project_registration_data(data):
    """
    Validate project registration form data
    
    Args:
        data (dict): Form data to validate
        
    Returns:
        tuple: (is_valid, validated_data, field_errors)
    """
    validator = InputValidator()
    field_errors = {}
    validated_data = {}
    
    # Required fields
    required_fields = [
        'ownerFullName', 'governorate', 'district', 'neighborhood', 'street',
        'age', 'primaryPhone', 'projectName', 'projectStatus', 'capital',
        'workersCount', 'startDate', 'products', 'projectDescription'
    ]
    
    # Check required fields
    is_valid, req_errors = validator.validate_required_fields(data, required_fields)
    if req_errors:
        field_errors.update(req_errors)
    
    # Validate specific fields
    for field, value in data.items():
        if field == 'email' and value:
            is_valid_email, email_error = validator.validate_email(value)
            if not is_valid_email:
                field_errors[field] = [email_error]
            else:
                validated_data[field] = value
        
        elif field in ['primaryPhone', 'secondaryPhone']:
            if field == 'primaryPhone' or (field == 'secondaryPhone' and value):
                is_valid_phone, formatted_phone, phone_error = validator.validate_phone_number(value)
                if not is_valid_phone:
                    field_errors[field] = [phone_error]
                else:
                    validated_data[field] = formatted_phone
        
        elif field == 'startDate':
            is_valid_date, formatted_date, date_error = validator.validate_date_format(value, "start date")
            if not is_valid_date:
                field_errors[field] = [date_error]
            else:
                validated_data[field] = formatted_date
        
        elif field in ['capital', 'workersCount']:
            is_valid_num, num_value, num_error = validator.validate_numeric_field(
                value, field, min_value=0, allow_decimal=(field == 'capital')
            )
            if not is_valid_num:
                field_errors[field] = [num_error]
            else:
                validated_data[field] = num_value
        
        elif field in required_fields:
            # Basic text validation for other required fields
            is_valid_text, text_error = validator.validate_text_length(value, field, min_length=1, max_length=500)
            if not is_valid_text:
                field_errors[field] = [text_error]
            else:
                validated_data[field] = value.strip()
    
    return len(field_errors) == 0, validated_data, field_errors


def validate_status_check_request(data):
    """
    Validate status check request data
    
    Args:
        data (dict): Request data to validate
        
    Returns:
        tuple: (is_valid, validated_token, error_message)
    """
    token = data.get('token')
    
    try:
        is_valid, document_data, error = TokenValidator.validate_token_for_lookup(token)
        return is_valid, token, error
    except TokenError as e:
        return False, None, str(e)