"""
Training Support API
Handles creating technical support requests for training programs
"""

import frappe
from frappe import _
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from .utils import validate_token_id, create_api_response, log_api_call
from .errors import APIError, ValidationError, NotFoundError


@frappe.whitelist(allow_guest=True)
def create_training_support_request(
    token_id: str,
    full_name: str,
    phone: str,
    city: str,
    age: int,
    reason: str = None
) -> Dict[str, Any]:
    """
    Create a technical support request for training program
    
    Args:
        token_id: User's token ID from better-auth
        full_name: Full name of the applicant
        phone: Phone number
        city: City/location
        age: Age of applicant
        reason: Reason for joining (optional)
        
    Returns:
        Dict containing success status and created request details
    """
    try:
        # Log API call
        log_api_call("create_training_support_request", {
            "token_id": token_id,
            "full_name": full_name,
            "phone": phone,
            "city": city,
            "age": age
        })
        
        # Validate required fields
        if not token_id:
            raise ValidationError(_("Token ID is required"))
        if not full_name:
            raise ValidationError(_("Full name is required"))
        if not phone:
            raise ValidationError(_("Phone number is required"))
        if not city:
            raise ValidationError(_("City is required"))
        if not age:
            raise ValidationError(_("Age is required"))
        
        # Validate token_id and get user info
        user_info = validate_token_id(token_id)
        if not user_info:
            raise NotFoundError(_("Invalid token ID or user not found"))
        
        # Get user's micro enterprises
        micro_enterprises = get_user_micro_enterprises(token_id)
        if not micro_enterprises:
            raise NotFoundError(_("No micro enterprises found for this user. Please register a micro enterprise first."))
        
        # Use the first micro enterprise (or you could let user choose)
        micro_enterprise = micro_enterprises[0]
        
        # Get or create "تدريب" support type
        support_type = get_or_create_training_support_type()
        
        # Create the technical support request
        support_request = create_technical_support_request(
            micro_enterprise=micro_enterprise,
            support_type=support_type,
            full_name=full_name,
            phone=phone,
            city=city,
            age=age,
            reason=reason
        )
        
        return create_api_response(
            success=True,
            data={
                "request_id": support_request.name,
                "micro_enterprise": micro_enterprise,
                "support_type": support_type,
                "status": support_request.status,
                "request_date": str(support_request.request_date),
                "message": _("Training support request created successfully")
            },
            message=_("Training support request submitted successfully")
        )
        
    except (ValidationError, NotFoundError) as e:
        frappe.log_error(f"Training support request validation error: {str(e)}", "Training Support API")
        return create_api_response(
            success=False,
            message=str(e)
        )
    except Exception as e:
        frappe.log_error(f"Error in create_training_support_request: {str(e)}", "Training Support API")
        return create_api_response(
            success=False,
            message=_("An error occurred while creating training support request")
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
        frappe.log_error(f"Error getting user micro enterprises: {str(e)}", "Training Support API")
        return []


def get_or_create_training_support_type() -> str:
    """
    Get or create "تدريب" support type
    
    Returns:
        Support type name
    """
    try:
        support_type_name = "تدريب"
        
        # Check if support type exists
        if not frappe.db.exists("Support Type", support_type_name):
            # Create the support type
            support_type_doc = frappe.get_doc({
                "doctype": "Support Type",
                "support_type": support_type_name
            })
            support_type_doc.insert(ignore_permissions=True)
            frappe.db.commit()
        
        return support_type_name
        
    except Exception as e:
        frappe.log_error(f"Error creating support type: {str(e)}", "Training Support API")
        return "تدريب"  # Return the name anyway


def create_technical_support_request(
    micro_enterprise: str,
    support_type: str,
    full_name: str,
    phone: str,
    city: str,
    age: int,
    reason: str = None
) -> Any:
    """
    Create a Technical Support Required document
    
    Args:
        micro_enterprise: Micro enterprise name
        support_type: Support type name
        full_name: Applicant full name
        phone: Phone number
        city: City
        age: Age
        reason: Reason for joining
        
    Returns:
        Created document
    """
    try:
        # Prepare the note content
        note_content = f"""
        <div class="training-request-details">
            <h3>تفاصيل طلب التدريب</h3>
            <p><strong>الاسم الكامل:</strong> {full_name}</p>
            <p><strong>رقم الهاتف:</strong> {phone}</p>
            <p><strong>مكان الإقامة:</strong> {city}</p>
            <p><strong>العمر:</strong> {age} سنة</p>
            {f'<p><strong>سبب الرغبة في الالتحاق:</strong> {reason}</p>' if reason else ''}
            <p><strong>تاريخ الطلب:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        """
        
        # Create the document
        support_request = frappe.get_doc({
            "doctype": "Technical Support Required",
            "party": "Micro Enterprise",
            "micro_enterprise": micro_enterprise,
            "micro_enterprise_full_name": full_name,
            "support_type": support_type,
            "status": "Draft",
            "request_date": datetime.now().date(),
            "note": note_content
        })
        
        support_request.insert(ignore_permissions=True)
        frappe.db.commit()
        
        return support_request
        
    except Exception as e:
        frappe.log_error(f"Error creating technical support request: {str(e)}", "Training Support API")
        raise


@frappe.whitelist(allow_guest=True)
def get_user_training_requests(token_id: str) -> Dict[str, Any]:
    """
    Get training support requests for a user
    
    Args:
        token_id: User's token ID
        
    Returns:
        Dict containing user's training requests
    """
    try:
        # Log API call
        log_api_call("get_user_training_requests", {"token_id": token_id})
        
        # Validate token_id
        if not token_id:
            raise ValidationError(_("Token ID is required"))
        
        # Get user's micro enterprises
        micro_enterprises = get_user_micro_enterprises(token_id)
        if not micro_enterprises:
            return create_api_response(
                success=True,
                data={
                    "total_requests": 0,
                    "requests": []
                },
                message=_("No micro enterprises found for this user")
            )
        
        # Get training support requests
        requests = frappe.get_all(
            "Technical Support Required",
            filters={
                "micro_enterprise": ["in", micro_enterprises],
                "support_type": "تدريب"
            },
            fields=[
                "name",
                "micro_enterprise",
                "micro_enterprise_full_name",
                "status",
                "request_date",
                "service_date_from",
                "service_date_to",
                "note"
            ],
            order_by="request_date desc"
        )
        
        # Format requests data
        formatted_requests = []
        for request in requests:
            formatted_request = {
                "name": request.name,
                "micro_enterprise": request.micro_enterprise,
                "micro_enterprise_full_name": request.micro_enterprise_full_name,
                "status": request.status,
                "request_date": str(request.request_date) if request.request_date else None,
                "service_date_from": str(request.service_date_from) if request.service_date_from else None,
                "service_date_to": str(request.service_date_to) if request.service_date_to else None,
                "note": request.note
            }
            formatted_requests.append(formatted_request)
        
        return create_api_response(
            success=True,
            data={
                "total_requests": len(formatted_requests),
                "requests": formatted_requests
            },
            message=_("Training requests retrieved successfully")
        )
        
    except (ValidationError, NotFoundError) as e:
        frappe.log_error(f"Training requests validation error: {str(e)}", "Training Support API")
        return create_api_response(
            success=False,
            message=str(e)
        )
    except Exception as e:
        frappe.log_error(f"Error in get_user_training_requests: {str(e)}", "Training Support API")
        return create_api_response(
            success=False,
            message=_("An error occurred while fetching training requests")
        )