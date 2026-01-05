"""
Token management utilities for project application tracking
"""

import frappe
from frappe import _
import uuid
import secrets
import hashlib
import re
from datetime import datetime, timedelta
from override_project_integration.config.api_settings import get_token_config
from override_project_integration.api.errors import TokenError


class TokenManager:
    """
    Manages token generation, validation, and lookup for project applications
    """
    
    @staticmethod
    def generate_token():
        """
        Generate a cryptographically secure unique token
        
        Returns:
            str: Generated token
            
        Raises:
            TokenError: If token generation fails after retries
        """
        config = get_token_config()
        max_retries = 5
        
        for attempt in range(max_retries):
            try:
                # Generate base token using UUID4 and secrets
                base_uuid = str(uuid.uuid4())
                random_bytes = secrets.token_hex(16)
                timestamp = str(int(datetime.now().timestamp()))
                
                # Combine components
                token_data = f"{base_uuid}-{random_bytes}-{timestamp}"
                
                # Create hash for additional security and consistent length
                token_hash = hashlib.sha256(token_data.encode()).hexdigest()
                
                # Format as readable token (first 32 characters)
                token = token_hash[:32].upper()
                
                # Add hyphens for readability: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
                formatted_token = f"{token[:8]}-{token[8:12]}-{token[12:16]}-{token[16:20]}-{token[20:32]}"
                
                # Check for uniqueness
                if TokenManager._is_token_unique(formatted_token):
                    return formatted_token
                    
            except Exception as e:
                frappe.log_error(f"Token generation attempt {attempt + 1} failed: {str(e)}")
                
        # If we get here, all retries failed
        raise TokenError(_("Failed to generate unique token after multiple attempts"))
    
    @staticmethod
    def _is_token_unique(token):
        """
        Check if token is unique across all applications
        
        Args:
            token (str): Token to check
            
        Returns:
            bool: True if token is unique, False otherwise
        """
        try:
            # Check if token exists in Micro Enterprise Request documents
            existing = frappe.db.exists("Micro Enterprise Request", {"token_id": token})
            return not existing
            
        except Exception as e:
            frappe.log_error(f"Error checking token uniqueness: {str(e)}")
            return False
    
    @staticmethod
    def validate_token_format(token):
        """
        Validate token format
        
        Args:
            token (str): Token to validate
            
        Returns:
            bool: True if format is valid, False otherwise
        """
        if not token or not isinstance(token, str):
            return False
        
        # Expected format: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
        # Total length: 36 characters (32 hex + 4 hyphens)
        pattern = r'^[A-F0-9]{8}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{12}$'
        
        return bool(re.match(pattern, token))
    
    @staticmethod
    def token_exists(token):
        """
        Check if token exists in the system
        
        Args:
            token (str): Token to check
            
        Returns:
            bool: True if token exists, False otherwise
        """
        if not TokenManager.validate_token_format(token):
            return False
            
        try:
            return frappe.db.exists("Micro Enterprise Request", {"token_id": token})
        except Exception as e:
            frappe.log_error(f"Error checking token existence: {str(e)}")
            return False
    
    @staticmethod
    def get_document_by_token(token):
        """
        Retrieve document associated with token
        
        Args:
            token (str): Token to lookup
            
        Returns:
            dict: Document data or None if not found
            
        Raises:
            TokenError: If token is invalid or not found
        """
        if not TokenManager.validate_token_format(token):
            raise TokenError(_("Invalid token format"))
        
        try:
            # Get document name by token
            doc_name = frappe.db.get_value("Micro Enterprise Request", {"token_id": token}, "name")
            
            if not doc_name:
                raise TokenError(_("Token not found"))
            
            # Get full document
            doc = frappe.get_doc("Micro Enterprise Request", doc_name)
            
            return {
                "name": doc.name,
                "token": doc.token_id,
                "status": doc.status,
                "applicant_name": TokenManager._get_full_name(doc),
                "project_name": TokenManager._get_project_name(doc),
                "submitted_date": doc.creation,
                "last_updated": doc.modified,
                "notes": getattr(doc, 'notes', '')
            }
            
        except TokenError:
            raise
        except Exception as e:
            frappe.log_error(f"Error retrieving document by token: {str(e)}")
            raise TokenError(_("Error retrieving application data"))
    
    @staticmethod
    def _get_full_name(doc):
        """
        Get full name from document
        
        Args:
            doc: Frappe document
            
        Returns:
            str: Full name
        """
        try:
            parts = []
            if hasattr(doc, 'first_name') and doc.first_name:
                parts.append(doc.first_name)
            if hasattr(doc, 'middle_name') and doc.middle_name:
                parts.append(doc.middle_name)
            if hasattr(doc, 'last_name') and doc.last_name:
                parts.append(doc.last_name)
            
            return " ".join(parts) if parts else _("Unknown")
        except:
            return _("Unknown")
    
    @staticmethod
    def _get_project_name(doc):
        """
        Get project name from document
        
        Args:
            doc: Frappe document
            
        Returns:
            str: Project name
        """
        try:
            # Check if project data is in child table
            if hasattr(doc, 'project') and doc.project:
                for project in doc.project:
                    if hasattr(project, 'project_name') and project.project_name:
                        return project.project_name
            
            # Check if project name is a direct field
            if hasattr(doc, 'project_name') and doc.project_name:
                return doc.project_name
                
            return _("Unknown Project")
        except:
            return _("Unknown Project")
    
    @staticmethod
    def is_token_expired(token):
        """
        Check if token is expired (if expiration is implemented)
        
        Args:
            token (str): Token to check
            
        Returns:
            bool: True if expired, False otherwise
        """
        # For now, tokens don't expire, but this method is ready for future implementation
        config = get_token_config()
        expires_in_days = config.get('expires_in_days', 0)
        
        if expires_in_days <= 0:
            return False  # No expiration
        
        try:
            doc_name = frappe.db.get_value("Micro Enterprise Request", {"token_id": token}, "name")
            if not doc_name:
                return True  # Token doesn't exist, consider it expired
            
            doc = frappe.get_doc("Micro Enterprise Request", doc_name)
            creation_date = doc.creation
            
            if isinstance(creation_date, str):
                creation_date = datetime.fromisoformat(creation_date.replace('Z', '+00:00'))
            
            expiry_date = creation_date + timedelta(days=expires_in_days)
            return datetime.now() > expiry_date
            
        except Exception as e:
            frappe.log_error(f"Error checking token expiration: {str(e)}")
            return True  # Consider expired on error for security
    
    @staticmethod
    def validate_token(token):
        """
        Comprehensive token validation
        
        Args:
            token (str): Token to validate
            
        Returns:
            tuple: (is_valid, error_message)
        """
        if not token:
            return False, _("Token is required")
        
        if not TokenManager.validate_token_format(token):
            return False, _("Invalid token format")
        
        if not TokenManager.token_exists(token):
            return False, _("Token not found")
        
        if TokenManager.is_token_expired(token):
            return False, _("Token has expired")
        
        return True, None


# Convenience functions for backward compatibility and ease of use
def generate_unique_token():
    """Generate a unique token"""
    return TokenManager.generate_token()


def validate_token_format(token):
    """Validate token format"""
    return TokenManager.validate_token_format(token)


def get_application_by_token(token):
    """Get application data by token"""
    return TokenManager.get_document_by_token(token)


def is_valid_token(token):
    """Check if token is valid"""
    is_valid, _ = TokenManager.validate_token(token)
    return is_valid