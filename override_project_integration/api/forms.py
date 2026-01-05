"""
Form submission API endpoints for Vue.js integration
"""

import frappe
from frappe import _
import json
import base64
from override_project_integration.api.utils import api_response, validate_request, log_api_request, validate_file_upload
from override_project_integration.api.middleware import cors_handler, rate_limit, validate_content_type
from override_project_integration.api.errors import (
    handle_api_error, ValidationError, FileUploadError, ErrorLogger, ErrorResponseFormatter
)


def _extract_uploaded_files():
    """
    Enhanced file extraction from multipart form data with validation
    
    Returns:
        dict: Dictionary of file data keyed by field name
    """
    files_data = {}
    
    try:
        # Get files from request
        if hasattr(frappe.request, 'files'):
            for field_name, file_storage in frappe.request.files.items():
                if file_storage and file_storage.filename:
                    # Read file content
                    try:
                        file_content = file_storage.read()
                    except Exception as e:
                        ErrorLogger.log_error(
                            e,
                            context={"field_name": field_name, "filename": file_storage.filename}
                        )
                        continue
                    
                    file_data = {
                        "filename": file_storage.filename,
                        "content": file_content,
                        "content_type": file_storage.content_type or "application/octet-stream"
                    }
                    
                    # Handle multiple files for the same field (like promote-project)
                    if field_name == "files":
                        if field_name not in files_data:
                            files_data[field_name] = []
                        files_data[field_name].append(file_data)
                    else:
                        files_data[field_name] = file_data
        
        # Handle base64 encoded files from form data
        form_dict = frappe.local.form_dict
        for key, value in form_dict.items():
            if key.endswith("_base64") and value:
                # Extract field name (remove _base64 suffix)
                field_name = key[:-7]
                
                try:
                    # Decode base64 content
                    file_content = base64.b64decode(value)
                    filename = form_dict.get(f"{field_name}_filename", "uploaded_file")
                    content_type = form_dict.get(f"{field_name}_type", "application/octet-stream")
                    
                    files_data[field_name] = {
                        "filename": filename,
                        "content": file_content,
                        "content_type": content_type
                    }
                except Exception as e:
                    ErrorLogger.log_error(
                        e,
                        context={
                            "field_name": field_name,
                            "base64_key": key,
                            "function": "_extract_uploaded_files"
                        }
                    )
                    continue
        
        return files_data
        
    except Exception as e:
        ErrorLogger.log_error(e, context={"function": "_extract_uploaded_files"})
        return {}


@frappe.whitelist(allow_guest=True)
@cors_handler
@rate_limit(endpoint_name="submit_form")
@validate_content_type()
@handle_api_error
def submit_form():
    """
    Enhanced main form submission endpoint for Vue.js frontend
    
    Accepts form data and routes to appropriate processors based on form_type
    Handles both JSON data and multipart form data with file uploads
    Includes comprehensive error handling and validation
    
    Returns:
        dict: API response with success/error status
    """
    # Handle preflight requests
    if frappe.request.method == "OPTIONS":
        from override_project_integration.api.cors_fix import handle_preflight_request
        return handle_preflight_request()
    
    # Apply CORS headers for all requests
    from override_project_integration.api.cors_fix import apply_cors_headers
    apply_cors_headers()
    
    try:
        # Get request data based on content type
        request_data = {}
        files_data = {}
        
        if frappe.request.method == "POST":
            content_type = frappe.get_request_header("Content-Type", "")
            
            if "multipart/form-data" in content_type:
                # Handle multipart form data with files
                request_data = frappe.local.form_dict.copy()
                
                # Extract file uploads with validation
                files_data = _extract_uploaded_files()
                
            elif "application/json" in content_type:
                # Handle JSON data
                try:
                    request_data = frappe.request.get_json() or {}
                except json.JSONDecodeError as e:
                    raise ValidationError(
                        message=_("Invalid JSON format"),
                        field_errors={"request_body": [_("Request body contains invalid JSON")]}
                    )
            else:
                # Handle regular form data
                request_data = frappe.local.form_dict
        else:
            request_data = frappe.local.form_dict
        
        # Validate required parameters
        form_type = request_data.get("form_type")
        form_data = request_data.get("form_data")
        token_id = request_data.get("token_id")
        
        # Enhanced parameter validation
        validation_errors = {}
        
        if not form_type:
            validation_errors["form_type"] = [_("Form type is required")]
        
        if not form_data:
            validation_errors["form_data"] = [_("Form data is required")]
        
        if validation_errors:
            raise ValidationError(field_errors=validation_errors)
        
        # Parse form_data if it's a JSON string
        if isinstance(form_data, str):
            try:
                form_data = json.loads(form_data)
            except json.JSONDecodeError:
                raise ValidationError(
                    field_errors={"form_data": [_("Form data must be valid JSON")]}
                )
        
        # Ensure form_data is a dictionary
        if not isinstance(form_data, dict):
            raise ValidationError(
                field_errors={"form_data": [_("Form data must be a JSON object")]}
            )
        
        # Validate and merge file data into form_data
        if files_data:
            file_errors = []
            for field_name, file_info in files_data.items():
                if isinstance(file_info, list):
                    # Multiple files
                    for i, file_data in enumerate(file_info):
                        is_valid, error_msg = validate_file_upload(
                            file_data,
                            allowed_types=['jpg', 'jpeg', 'png', 'pdf', 'doc', 'docx'],
                            max_size_mb=10
                        )
                        if not is_valid:
                            file_errors.append({
                                "field": field_name,
                                "file_index": i,
                                "filename": file_data.get("filename", "unknown"),
                                "error": error_msg
                            })
                else:
                    # Single file
                    is_valid, error_msg = validate_file_upload(
                        file_info,
                        allowed_types=['jpg', 'jpeg', 'png', 'pdf', 'doc', 'docx'],
                        max_size_mb=10
                    )
                    if not is_valid:
                        file_errors.append({
                            "field": field_name,
                            "filename": file_info.get("filename", "unknown"),
                            "error": error_msg
                        })
            
            if file_errors:
                raise FileUploadError(
                    message=_("File validation failed"),
                    file_errors=file_errors
                )
            
            form_data.update(files_data)
        
        # Log the form submission attempt
        log_api_request(
            endpoint="submit_form",
            method="POST",
            data={
                "form_type": form_type,
                "has_token": bool(token_id),
                "has_files": bool(files_data)
            }
        )
        
        # Route to appropriate form processor
        from override_project_integration.api.processors import get_form_processor
        
        processor = get_form_processor(form_type)
        if not processor:
            return api_response(
                success=False,
                message=_("Unsupported form type"),
                status_code=400,
                errors={"form_type": [_("Form type '{}' is not supported").format(form_type)]}
            )
        
        # Process the form submission
        result = processor.process_form(form_data, token_id)
        
        if result.get("success"):
            return api_response(
                success=True,
                message=_("Form submitted successfully"),
                data=result.get("data"),
                status_code=201
            )
        else:
            return api_response(
                success=False,
                message=result.get("message", _("Form submission failed")),
                status_code=400,
                errors=result.get("errors")
            )
    
    except Exception as e:
        frappe.log_error(f"Form submission error: {str(e)}", "Form Submission")
        return api_response(
            success=False,
            message=_("An error occurred while processing your form"),
            status_code=500
        )