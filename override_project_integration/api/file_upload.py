"""
File upload API endpoints for Vue.js integration
"""

import frappe
from frappe import _
from override_project_integration.api.utils import api_response
from override_project_integration.api.middleware import cors_handler, rate_limit
from override_project_integration.api.file_handler import FileUploadHandler, get_file_upload_config, validate_uploaded_file


@frappe.whitelist(allow_guest=True)
@cors_handler
@rate_limit(endpoint_name="upload_file")
def upload_file():
    """
    Upload a single file
    
    Returns:
        dict: Upload result with file information
    """
    try:
        field_name = frappe.local.form_dict.get("field_name")
        if not field_name:
            return api_response(
                success=False,
                message=_("Field name is required"),
                status_code=400,
                errors={"field_name": [_("Field name parameter is missing")]}
            )
        
        # Check if file was uploaded
        if not hasattr(frappe.request, 'files') or not frappe.request.files:
            return api_response(
                success=False,
                message=_("No file uploaded"),
                status_code=400,
                errors={"file": [_("No file was provided")]}
            )
        
        # Get the first uploaded file
        file_storage = None
        for field, storage in frappe.request.files.items():
            if storage and storage.filename:
                file_storage = storage
                break
        
        if not file_storage:
            return api_response(
                success=False,
                message=_("No valid file uploaded"),
                status_code=400,
                errors={"file": [_("No valid file was provided")]}
            )
        
        # Read file content
        file_content = file_storage.read()
        
        # Prepare file data
        file_data = {
            "filename": file_storage.filename,
            "content": file_content,
            "content_type": file_storage.content_type
        }
        
        # Process upload
        upload_handler = FileUploadHandler()
        result = upload_handler.process_file_upload(file_data, field_name)
        
        if result["success"]:
            return api_response(
                success=True,
                message=result["message"],
                data={
                    "file_url": result["file_url"],
                    "file_name": result["file_name"],
                    "file_size": result.get("file_size"),
                    "mime_type": result.get("mime_type"),
                    "reused": result.get("reused", False)
                }
            )
        else:
            return api_response(
                success=False,
                message=_("File upload failed"),
                status_code=400,
                errors={"file": [result["error"]]}
            )
    
    except Exception as e:
        frappe.log_error(f"File upload API error: {str(e)}", "File Upload API")
        return api_response(
            success=False,
            message=_("An error occurred while uploading the file"),
            status_code=500
        )


@frappe.whitelist(allow_guest=True)
@cors_handler
def validate_file():
    """
    Validate a file without uploading it
    
    Returns:
        dict: Validation result
    """
    try:
        field_name = frappe.local.form_dict.get("field_name")
        if not field_name:
            return api_response(
                success=False,
                message=_("Field name is required"),
                status_code=400,
                errors={"field_name": [_("Field name parameter is missing")]}
            )
        
        # Check if file was uploaded
        if not hasattr(frappe.request, 'files') or not frappe.request.files:
            return api_response(
                success=False,
                message=_("No file uploaded"),
                status_code=400,
                errors={"file": [_("No file was provided")]}
            )
        
        # Get the first uploaded file
        file_storage = None
        for field, storage in frappe.request.files.items():
            if storage and storage.filename:
                file_storage = storage
                break
        
        if not file_storage:
            return api_response(
                success=False,
                message=_("No valid file uploaded"),
                status_code=400,
                errors={"file": [_("No valid file was provided")]}
            )
        
        # Read file content
        file_content = file_storage.read()
        
        # Validate file
        validation_result = validate_uploaded_file(file_content, file_storage.filename, field_name)
        
        if validation_result["valid"]:
            return api_response(
                success=True,
                message=_("File is valid"),
                data={
                    "filename": file_storage.filename,
                    "mime_type": validation_result["mime_type"],
                    "file_size": validation_result["file_size"]
                }
            )
        else:
            return api_response(
                success=False,
                message=_("File validation failed"),
                status_code=400,
                errors={"file": [validation_result["error"]]}
            )
    
    except Exception as e:
        frappe.log_error(f"File validation API error: {str(e)}", "File Validation API")
        return api_response(
            success=False,
            message=_("An error occurred while validating the file"),
            status_code=500
        )


@frappe.whitelist(allow_guest=True)
@cors_handler
def get_file_config():
    """
    Get file upload configuration for a specific field
    
    Returns:
        dict: File upload configuration
    """
    try:
        field_name = frappe.local.form_dict.get("field_name")
        if not field_name:
            return api_response(
                success=False,
                message=_("Field name is required"),
                status_code=400,
                errors={"field_name": [_("Field name parameter is missing")]}
            )
        
        config = get_file_upload_config(field_name)
        if not config:
            return api_response(
                success=False,
                message=_("File configuration not found"),
                status_code=404,
                errors={"field_name": [_("Configuration for field '{0}' not found").format(field_name)]}
            )
        
        # Convert bytes to MB for frontend display
        config_display = config.copy()
        config_display["max_size_mb"] = config["max_size"] / (1024 * 1024)
        
        return api_response(
            success=True,
            message=_("File configuration retrieved successfully"),
            data={"config": config_display}
        )
    
    except Exception as e:
        frappe.log_error(f"File config API error: {str(e)}", "File Config API")
        return api_response(
            success=False,
            message=_("An error occurred while retrieving file configuration"),
            status_code=500
        )


@frappe.whitelist(allow_guest=True)
@cors_handler
def get_document_files():
    """
    Get all files attached to a document
    
    Returns:
        dict: List of attached files
    """
    try:
        doctype = frappe.local.form_dict.get("doctype")
        docname = frappe.local.form_dict.get("docname")
        
        if not doctype or not docname:
            return api_response(
                success=False,
                message=_("DocType and document name are required"),
                status_code=400,
                errors={
                    "doctype": [_("DocType parameter is missing")] if not doctype else [],
                    "docname": [_("Document name parameter is missing")] if not docname else []
                }
            )
        
        from override_project_integration.api.file_handler import AttachmentManager
        
        attachment_manager = AttachmentManager()
        attachments = attachment_manager.get_document_attachments(doctype, docname)
        
        return api_response(
            success=True,
            message=_("Document attachments retrieved successfully"),
            data={"attachments": attachments}
        )
    
    except Exception as e:
        frappe.log_error(f"Document files API error: {str(e)}", "Document Files API")
        return api_response(
            success=False,
            message=_("An error occurred while retrieving document files"),
            status_code=500
        )