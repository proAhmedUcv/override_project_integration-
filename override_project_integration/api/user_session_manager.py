"""
User session management for token-based identification
"""

import frappe
from frappe import _
import json
from datetime import datetime, timedelta
from override_project_integration.api.token_manager import TokenManager
from override_project_integration.api.errors import TokenError


class UserSessionManager:
    """
    Manages user sessions based on token_id from Vue.js frontend
    """
    
    @staticmethod
    def create_session_from_token(token_id, request_info=None):
        """
        Create a user session based on token_id
        
        Args:
            token_id (str): Token ID from Vue.js frontend
            request_info (dict): Additional request information
            
        Returns:
            dict: Session information
            
        Raises:
            TokenError: If token is invalid or session creation fails
        """
        if not token_id:
            raise TokenError(_("Token ID is required for session creation"))
        
        # Validate token
        is_valid, error_message = TokenManager.validate_token(token_id)
        if not is_valid:
            raise TokenError(error_message)
        
        try:
            # Get document associated with token
            doc_data = TokenManager.get_document_by_token(token_id)
            
            # Create session data
            session_data = {
                "token_id": token_id,
                "user_type": "vue_js_user",
                "document_name": doc_data["name"],
                "applicant_name": doc_data["applicant_name"],
                "project_name": doc_data["project_name"],
                "status": doc_data["status"],
                "created_at": datetime.now().isoformat(),
                "last_accessed": datetime.now().isoformat(),
                "is_active": True
            }
            
            # Add request information if provided
            if request_info:
                session_data.update({
                    "ip_address": request_info.get("ip_address"),
                    "user_agent": request_info.get("user_agent"),
                    "origin": request_info.get("origin")
                })
            
            # Store session in cache for quick access
            cache_key = f"vue_session:{token_id}"
            frappe.cache().set(cache_key, json.dumps(session_data), expires_in_sec=3600)  # 1 hour
            
            return session_data
            
        except TokenError:
            raise
        except Exception as e:
            frappe.log_error(f"Error creating session from token: {str(e)}")
            raise TokenError(_("Failed to create user session"))
    
    @staticmethod
    def get_session_by_token(token_id):
        """
        Get existing session by token_id
        
        Args:
            token_id (str): Token ID to lookup
            
        Returns:
            dict: Session data or None if not found
        """
        if not token_id:
            return None
        
        try:
            # Try to get from cache first
            cache_key = f"vue_session:{token_id}"
            cached_session = frappe.cache().get(cache_key)
            
            if cached_session:
                session_data = json.loads(cached_session)
                # Update last accessed time
                session_data["last_accessed"] = datetime.now().isoformat()
                frappe.cache().set(cache_key, json.dumps(session_data), expires_in_sec=3600)
                return session_data
            
            # If not in cache, try to recreate from token
            if TokenManager.token_exists(token_id):
                return UserSessionManager.create_session_from_token(token_id)
            
            return None
            
        except Exception as e:
            frappe.log_error(f"Error getting session by token: {str(e)}")
            return None
    
    @staticmethod
    def update_session_activity(token_id, activity_data=None):
        """
        Update session activity information
        
        Args:
            token_id (str): Token ID of the session
            activity_data (dict): Additional activity information
            
        Returns:
            bool: True if updated successfully, False otherwise
        """
        if not token_id:
            return False
        
        try:
            session_data = UserSessionManager.get_session_by_token(token_id)
            if not session_data:
                return False
            
            # Update activity information
            session_data["last_accessed"] = datetime.now().isoformat()
            
            if activity_data:
                session_data.update(activity_data)
            
            # Save back to cache
            cache_key = f"vue_session:{token_id}"
            frappe.cache().set(cache_key, json.dumps(session_data), expires_in_sec=3600)
            
            return True
            
        except Exception as e:
            frappe.log_error(f"Error updating session activity: {str(e)}")
            return False
    
    @staticmethod
    def invalidate_session(token_id):
        """
        Invalidate a user session
        
        Args:
            token_id (str): Token ID of the session to invalidate
            
        Returns:
            bool: True if invalidated successfully, False otherwise
        """
        if not token_id:
            return False
        
        try:
            cache_key = f"vue_session:{token_id}"
            frappe.cache().delete(cache_key)
            
            # Log session invalidation
            frappe.logger().info(f"Session invalidated for token: {token_id[:8]}...")
            
            return True
            
        except Exception as e:
            frappe.log_error(f"Error invalidating session: {str(e)}")
            return False
    
    @staticmethod
    def get_user_identity(token_id):
        """
        Get user identity information based on token_id
        
        Args:
            token_id (str): Token ID to get identity for
            
        Returns:
            dict: User identity information
        """
        if not token_id:
            return {
                "is_authenticated": False,
                "user_type": "anonymous",
                "identity": None
            }
        
        try:
            session_data = UserSessionManager.get_session_by_token(token_id)
            
            if not session_data:
                return {
                    "is_authenticated": False,
                    "user_type": "invalid_token",
                    "identity": None
                }
            
            return {
                "is_authenticated": True,
                "user_type": "vue_js_user",
                "identity": {
                    "token_id": token_id,
                    "name": session_data.get("applicant_name"),
                    "document_name": session_data.get("document_name"),
                    "project_name": session_data.get("project_name"),
                    "status": session_data.get("status"),
                    "session_created": session_data.get("created_at"),
                    "last_accessed": session_data.get("last_accessed")
                }
            }
            
        except Exception as e:
            frappe.log_error(f"Error getting user identity: {str(e)}")
            return {
                "is_authenticated": False,
                "user_type": "error",
                "identity": None
            }
    
    @staticmethod
    def is_session_valid(token_id):
        """
        Check if a session is valid and active
        
        Args:
            token_id (str): Token ID to check
            
        Returns:
            bool: True if session is valid, False otherwise
        """
        if not token_id:
            return False
        
        try:
            session_data = UserSessionManager.get_session_by_token(token_id)
            
            if not session_data:
                return False
            
            # Check if session is marked as active
            if not session_data.get("is_active", False):
                return False
            
            # Check if token still exists in the system
            if not TokenManager.token_exists(token_id):
                # Token no longer exists, invalidate session
                UserSessionManager.invalidate_session(token_id)
                return False
            
            # Check if token is expired
            if TokenManager.is_token_expired(token_id):
                # Token is expired, invalidate session
                UserSessionManager.invalidate_session(token_id)
                return False
            
            return True
            
        except Exception as e:
            frappe.log_error(f"Error checking session validity: {str(e)}")
            return False
    
    @staticmethod
    def get_session_statistics():
        """
        Get statistics about active sessions
        
        Returns:
            dict: Session statistics
        """
        try:
            # This is a simplified implementation
            # In a production system, you might want to track sessions more comprehensively
            
            return {
                "total_active_sessions": 0,  # Would need to implement session tracking
                "session_cache_enabled": bool(frappe.cache()),
                "cache_backend": frappe.cache().__class__.__name__ if frappe.cache() else None,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            frappe.log_error(f"Error getting session statistics: {str(e)}")
            return {
                "error": "Failed to get session statistics",
                "timestamp": datetime.now().isoformat()
            }


# Convenience functions for easier usage
def create_vue_session(token_id, request_info=None):
    """Create a Vue.js user session"""
    return UserSessionManager.create_session_from_token(token_id, request_info)


def get_vue_session(token_id):
    """Get Vue.js user session"""
    return UserSessionManager.get_session_by_token(token_id)


def get_vue_user_identity(token_id):
    """Get Vue.js user identity"""
    return UserSessionManager.get_user_identity(token_id)


def is_vue_session_valid(token_id):
    """Check if Vue.js session is valid"""
    return UserSessionManager.is_session_valid(token_id)