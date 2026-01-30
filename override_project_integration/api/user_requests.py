"""
User Requests API
Handles fetching technical support requests for users based on token_id
"""

import frappe
from frappe import _
import json
from typing import Dict, List, Any, Optional
from .utils import validate_token_id, create_api_response, log_api_call
from .errors import APIError, ValidationError, NotFoundError


@frappe.whitelist(allow_guest=True)
def get_user_technical_support_requests(token_id: str) -> Dict[str, Any]:
    """
    Get technical support requests for a user based on their token_id
    
    Args:
        token_id: User's token ID from better-auth
        
    Returns:
        Dict containing user's technical support requests and statistics
    """
    try:
        # Log API call
        log_api_call("get_user_technical_support_requests", {"token_id": token_id})
        
        # Validate token_id
        if not token_id:
            raise ValidationError(_("Token ID is required"))
        
        # Validate token_id format and get user info
        user_info = validate_token_id(token_id)
        if not user_info:
            raise NotFoundError(_("Invalid token ID or user not found"))
        
        # Get user's micro enterprises
        micro_enterprises = get_user_micro_enterprises(token_id)
        if not micro_enterprises:
            # Return empty data if user has no micro enterprises
            return create_api_response(
                success=True,
                data={
                    "total_requests": 0,
                    "approved_requests": 0,
                    "pending_requests": 0,
                    "rejected_requests": 0,
                    "requests": []
                },
                message=_("No micro enterprises found for this user")
            )
        
        # Get technical support requests for user's micro enterprises
        requests_data = get_technical_support_requests_for_enterprises(micro_enterprises)
        
        return create_api_response(
            success=True,
            data=requests_data,
            message=_("Technical support requests retrieved successfully")
        )
        
    except (ValidationError, NotFoundError) as e:
        frappe.log_error(f"User requests validation error: {str(e)}", "User Requests API")
        return create_api_response(
            success=False,
            message=str(e)
        )
    except Exception as e:
        frappe.log_error(f"Error in get_user_technical_support_requests: {str(e)}", "User Requests API")
        return create_api_response(
            success=False,
            message=_("An error occurred while fetching technical support requests")
        )


def get_user_micro_enterprises(token_id: str) -> List[str]:
    """
    Get list of micro enterprise names for a user based on token_id
    
    Args:
        token_id: User's token ID
        
    Returns:
        List of micro enterprise names (actual Micro Enterprise document names)
    """
    try:
        # First, find the Micro Enterprise Request with this token_id
        micro_enterprise_requests = frappe.get_all(
            "Micro Enterprise Request",
            filters={"token_id": token_id},
            fields=["name", "family_name"]
        )
        
        if not micro_enterprise_requests:
            return []
        
        # Get the actual Micro Enterprise documents linked to these requests
        micro_enterprises = frappe.get_all(
            "Micro Enterprise",
            filters={"micro_enterprise_request": ["in", [req.name for req in micro_enterprise_requests]]},
            fields=["name", "micro_enterprise_name"]
        )
        
        # Return the actual Micro Enterprise document names (not family_name)
        micro_enterprise_names = [enterprise.name for enterprise in micro_enterprises]
        
        return micro_enterprise_names
        
    except Exception as e:
        frappe.log_error(f"Error getting user micro enterprises: {str(e)}", "User Requests API")
        return []


def get_technical_support_requests_for_enterprises(micro_enterprises: List[str]) -> Dict[str, Any]:
    """
    Get technical support requests for given micro enterprises
    
    Args:
        micro_enterprises: List of micro enterprise names
        
    Returns:
        Dict containing requests data and statistics
    """
    try:
        if not micro_enterprises:
            return {
                "total_requests": 0,
                "approved_requests": 0,
                "pending_requests": 0,
                "rejected_requests": 0,
                "requests": []
            }
        
        # Get technical support requests
        requests = frappe.get_all(
            "Technical Support Required",
            filters={"micro_enterprise": ["in", micro_enterprises]},
            fields=[
                "name",
                "party",
                "micro_enterprise",
                "micro_enterprise_full_name",
                "status",
                "request_date",
                "support_type",
                "service_date_from",
                "service_date_to",
                "costing",
                "note"
            ],
            order_by="request_date desc"
        )
        
        # Calculate statistics
        total_requests = len(requests)
        approved_requests = len([r for r in requests if r.status.lower() == "approved"])
        pending_requests = len([r for r in requests if r.status.lower() == "draft"])
        rejected_requests = len([r for r in requests if r.status.lower() == "rejected"])
        
        # Format requests data
        formatted_requests = []
        for request in requests:
            formatted_request = {
                "name": request.name,
                "party": request.party,
                "micro_enterprise": request.micro_enterprise,
                "micro_enterprise_full_name": request.micro_enterprise_full_name,
                "status": request.status,
                "request_date": str(request.request_date) if request.request_date else None,
                "support_type": request.support_type,
                "service_date_from": str(request.service_date_from) if request.service_date_from else None,
                "service_date_to": str(request.service_date_to) if request.service_date_to else None,
                "costing": float(request.costing) if request.costing else None,
                "note": request.note
            }
            formatted_requests.append(formatted_request)
        
        return {
            "total_requests": total_requests,
            "approved_requests": approved_requests,
            "pending_requests": pending_requests,
            "rejected_requests": rejected_requests,
            "requests": formatted_requests
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting technical support requests: {str(e)}", "User Requests API")
        return {
            "total_requests": 0,
            "approved_requests": 0,
            "pending_requests": 0,
            "rejected_requests": 0,
            "requests": []
        }


@frappe.whitelist(allow_guest=True)
def get_user_requests_summary(token_id: str) -> Dict[str, Any]:
    """
    Get summary of user's requests (for dashboard/stats)
    
    Args:
        token_id: User's token ID
        
    Returns:
        Dict containing summary statistics
    """
    try:
        # Log API call
        log_api_call("get_user_requests_summary", {"token_id": token_id})
        
        # Validate token_id
        if not token_id:
            raise ValidationError(_("Token ID is required"))
        
        # Get user's micro enterprises
        micro_enterprises = get_user_micro_enterprises(token_id)
        
        if not micro_enterprises:
            return create_api_response(
                success=True,
                data={
                    "total_technical_support_requests": 0,
                    "approved_technical_support_requests": 0,
                    "pending_technical_support_requests": 0
                },
                message=_("No micro enterprises found for this user")
            )
        
        # Get technical support requests count
        total_requests = frappe.db.count(
            "Technical Support Required",
            filters={"micro_enterprise": ["in", micro_enterprises]}
        )
        
        approved_requests = frappe.db.count(
            "Technical Support Required",
            filters={
                "micro_enterprise": ["in", micro_enterprises],
                "status": ["in", ["approved", "Approved"]]
            }
        )
        
        pending_requests = frappe.db.count(
            "Technical Support Required",
            filters={
                "micro_enterprise": ["in", micro_enterprises],
                "status": ["in", ["draft", "Draft"]]
            }
        )
        
        return create_api_response(
            success=True,
            data={
                "total_technical_support_requests": total_requests,
                "approved_technical_support_requests": approved_requests,
                "pending_technical_support_requests": pending_requests
            },
            message=_("User requests summary retrieved successfully")
        )
        
    except (ValidationError, NotFoundError) as e:
        frappe.log_error(f"User requests summary validation error: {str(e)}", "User Requests API")
        return create_api_response(
            success=False,
            message=str(e)
        )
    except Exception as e:
        frappe.log_error(f"Error in get_user_requests_summary: {str(e)}", "User Requests API")
        return create_api_response(
            success=False,
            message=_("An error occurred while fetching user requests summary")
        )


@frappe.whitelist(allow_guest=True)
def test_user_requests_connection(token_id: str = None) -> Dict[str, Any]:
    """
    Test the user requests API connection and data structure
    
    Args:
        token_id: Optional token ID for testing
        
    Returns:
        Dict containing test results
    """
    try:
        # Log API call
        log_api_call("test_user_requests_connection", {"token_id": token_id})
        
        # Check if Technical Support Required doctype exists
        if not frappe.db.exists("DocType", "Technical Support Required"):
            return create_api_response(
                success=False,
                message=_("Technical Support Required doctype not found")
            )
        
        # Check if Micro Enterprise doctype exists
        if not frappe.db.exists("DocType", "Micro Enterprise"):
            return create_api_response(
                success=False,
                message=_("Micro Enterprise doctype not found")
            )
        
        # Check if Micro Enterprise Request doctype exists
        if not frappe.db.exists("DocType", "Micro Enterprise Request"):
            return create_api_response(
                success=False,
                message=_("Micro Enterprise Request doctype not found")
            )
        
        # Get sample data counts
        total_technical_support = frappe.db.count("Technical Support Required")
        total_micro_enterprises = frappe.db.count("Micro Enterprise")
        total_micro_enterprise_requests = frappe.db.count("Micro Enterprise Request")
        
        test_data = {
            "doctypes_exist": True,
            "total_technical_support_requests": total_technical_support,
            "total_micro_enterprises": total_micro_enterprises,
            "total_micro_enterprise_requests": total_micro_enterprise_requests,
            "connection_status": "success"
        }
        
        # If token_id provided, test with real data
        if token_id:
            micro_enterprises = get_user_micro_enterprises(token_id)
            requests_data = get_technical_support_requests_for_enterprises(micro_enterprises)
            test_data.update({
                "test_token_id": token_id,
                "user_micro_enterprises": micro_enterprises,
                "user_requests_count": requests_data["total_requests"]
            })
        
        return create_api_response(
            success=True,
            data=test_data,
            message=_("User requests API connection test successful")
        )
        
    except Exception as e:
        frappe.log_error(f"Error in test_user_requests_connection: {str(e)}", "User Requests API")
        return create_api_response(
            success=False,
            message=_("User requests API connection test failed"),
            data={"error": str(e)}
        )