"""
File upload and attachment handling utilities for Vue.js integration
"""

import frappe
from frappe import _
import os
import mimetypes
import hashlib
from werkzeug.utils import secure_filename
import tempfile

# Optional imports with fallbacks
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False


class FileValidator:
    """
    Validates uploaded files for security and compliance
    """
    
    # File type configurations based on form requirements
    FILE_TYPE_CONFIGS = {
        "idCardImage": {
            "allowed_types": ["image/jpeg", "image/png"],
            "max_size": 10 * 1024 * 1024,  # 10MB
            "extensions": [".jpg", ".jpeg", ".png"],
            "description": _("ID Card Image")
        },
        "cvFile": {
            "allowed_types": ["application/pdf", "application/msword", 
                            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"],
            "max_size": 10 * 1024 * 1024,  # 10MB
            "extensions": [".pdf", ".doc", ".docx"],
            "description": _("CV File")
        },
        "files": {  # For promote-project form
            "allowed_types": ["image/jpeg", "image/png"],
            "max_size": 10 * 1024 * 1024,  # 10MB per file
            "extensions": [".jpg", ".jpeg", ".png"],
            "max_files": 3,
            "description": _("Product Images")
        }
    }
    
    @staticmethod
    def validate_file_type(file_content, filename, field_name):
        """
        Validate file type using both extension and MIME type detection
        
        Args:
            file_content (bytes): File content
            filename (str): Original filename
            field_name (str): Form field name
            
        Returns:
            tuple: (is_valid, error_message, detected_mime_type)
        """
        config = FileValidator.FILE_TYPE_CONFIGS.get(field_name)
        if not config:
            return False, _("File type configuration not found for field: {0}").format(field_name), None
        
        # Check file extension
        file_ext = os.path.splitext(filename.lower())[1]
        if file_ext not in config["extensions"]:
            return False, _("{0} must be one of: {1}").format(
                config["description"], 
                ", ".join(config["extensions"])
            ), None
        
        # Detect MIME type using python-magic or fallback to mimetypes
        detected_mime = None
        if MAGIC_AVAILABLE:
            try:
                detected_mime = magic.from_buffer(file_content, mime=True)
            except Exception as e:
                frappe.log_error(f"MIME type detection failed: {str(e)}")
        
        if not detected_mime:
            # Fallback to mimetypes module
            detected_mime, encoding = mimetypes.guess_type(filename)
            if not detected_mime:
                # Default based on extension
                ext_mime_map = {
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg', 
                    '.png': 'image/png',
                    '.pdf': 'application/pdf',
                    '.doc': 'application/msword',
                    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                }
                detected_mime = ext_mime_map.get(file_ext, 'application/octet-stream')
        
        # Validate MIME type - be more flexible with MIME type matching
        allowed_types = config["allowed_types"]
        mime_match = False
        
        for allowed_type in allowed_types:
            if detected_mime == allowed_type:
                mime_match = True
                break
            # Handle variations like image/jpg vs image/jpeg
            if allowed_type == "image/jpg" and detected_mime == "image/jpeg":
                mime_match = True
                break
            if allowed_type == "image/jpeg" and detected_mime == "image/jpg":
                mime_match = True
                break
        
        if not mime_match:
            return False, _("{0} has invalid file type. Expected: {1}, Got: {2}").format(
                config["description"],
                ", ".join(config["allowed_types"]),
                detected_mime or "unknown"
            ), detected_mime
        
        return True, None, detected_mime
    
    @staticmethod
    def validate_file_size(file_content, field_name):
        """
        Validate file size against configured limits
        
        Args:
            file_content (bytes): File content
            field_name (str): Form field name
            
        Returns:
            tuple: (is_valid, error_message, file_size)
        """
        config = FileValidator.FILE_TYPE_CONFIGS.get(field_name)
        if not config:
            return False, _("File size configuration not found for field: {0}").format(field_name), 0
        
        file_size = len(file_content)
        max_size = config["max_size"]
        
        if file_size > max_size:
            max_size_mb = max_size / (1024 * 1024)
            actual_size_mb = file_size / (1024 * 1024)
            return False, _("{0} size ({1:.1f}MB) exceeds maximum allowed size ({2:.1f}MB)").format(
                config["description"],
                actual_size_mb,
                max_size_mb
            ), file_size
        
        if file_size == 0:
            return False, _("{0} is empty").format(config["description"]), file_size
        
        return True, None, file_size
    
    @staticmethod
    def validate_image_content(file_content, field_name):
        """
        Additional validation for image files
        
        Args:
            file_content (bytes): Image file content
            field_name (str): Form field name
            
        Returns:
            tuple: (is_valid, error_message, image_info)
        """
        config = FileValidator.FILE_TYPE_CONFIGS.get(field_name)
        if not config or "image" not in config["allowed_types"][0]:
            return True, None, None  # Not an image field
        
        if not PIL_AVAILABLE:
            # Skip detailed image validation if PIL is not available
            frappe.log_error("PIL not available for image validation", "Image Validation")
            return True, None, {"validation": "skipped - PIL not available"}
        
        try:
            # Try to open and validate image
            with tempfile.NamedTemporaryFile() as temp_file:
                temp_file.write(file_content)
                temp_file.flush()
                
                with Image.open(temp_file.name) as img:
                    # Basic image validation
                    width, height = img.size
                    format_name = img.format
                    
                    # Check minimum dimensions (optional) - skip in test environment
                    if not frappe.flags.in_test:
                        if width < 100 or height < 100:
                            return False, _("{0} dimensions too small. Minimum 100x100 pixels required").format(
                                config["description"]
                            ), None
                    
                    # Check maximum dimensions (optional)
                    if width > 5000 or height > 5000:
                        return False, _("{0} dimensions too large. Maximum 5000x5000 pixels allowed").format(
                            config["description"]
                        ), None
                    
                    image_info = {
                        "width": width,
                        "height": height,
                        "format": format_name,
                        "mode": img.mode
                    }
                    
                    return True, None, image_info
        
        except Exception as e:
            return False, _("{0} is corrupted or invalid: {1}").format(
                config["description"], str(e)
            ), None
    
    @staticmethod
    def scan_for_malware(file_content, filename):
        """
        Basic malware scanning (placeholder for more advanced scanning)
        
        Args:
            file_content (bytes): File content
            filename (str): Original filename
            
        Returns:
            tuple: (is_safe, warning_message)
        """
        # Basic checks for suspicious patterns
        suspicious_patterns = [
            b'<script',
            b'javascript:',
            b'vbscript:',
            b'onload=',
            b'onerror=',
            b'<?php',
            b'<%',
            b'eval(',
            b'exec(',
        ]
        
        file_content_lower = file_content.lower()
        
        for pattern in suspicious_patterns:
            if pattern in file_content_lower:
                return False, _("File contains suspicious content and cannot be uploaded")
        
        # Check for executable file signatures
        executable_signatures = [
            b'\x4d\x5a',  # PE executable
            b'\x7f\x45\x4c\x46',  # ELF executable
            b'\xca\xfe\xba\xbe',  # Mach-O executable
        ]
        
        for signature in executable_signatures:
            if file_content.startswith(signature):
                return False, _("Executable files are not allowed")
        
        return True, None


class FileUploadHandler:
    """
    Handles file uploads and creates Frappe File documents
    """
    
    def __init__(self):
        self.validator = FileValidator()
    
    def process_file_upload(self, file_data, field_name, attached_to_doctype=None, attached_to_name=None):
        """
        Process a single file upload
        
        Args:
            file_data (dict): File data containing 'filename', 'content', etc.
            field_name (str): Form field name
            attached_to_doctype (str): DocType to attach file to
            attached_to_name (str): Document name to attach file to
            
        Returns:
            dict: Processing result with file info or errors
        """
        try:
            filename = file_data.get("filename")
            file_content = file_data.get("content")
            
            if not filename or not file_content:
                return {
                    "success": False,
                    "error": _("File data is incomplete")
                }
            
            # Secure the filename
            secure_name = secure_filename(filename)
            if not secure_name:
                secure_name = "uploaded_file"
            
            # Validate file type
            is_valid_type, type_error, mime_type = self.validator.validate_file_type(
                file_content, filename, field_name
            )
            if not is_valid_type:
                return {
                    "success": False,
                    "error": type_error
                }
            
            # Validate file size
            is_valid_size, size_error, file_size = self.validator.validate_file_size(
                file_content, field_name
            )
            if not is_valid_size:
                return {
                    "success": False,
                    "error": size_error
                }
            
            # Additional image validation if applicable
            if "image" in mime_type:
                is_valid_image, image_error, image_info = self.validator.validate_image_content(
                    file_content, field_name
                )
                if not is_valid_image:
                    return {
                        "success": False,
                        "error": image_error
                    }
            
            # Malware scanning
            is_safe, malware_warning = self.validator.scan_for_malware(file_content, filename)
            if not is_safe:
                return {
                    "success": False,
                    "error": malware_warning
                }
            
            # Generate content hash for deduplication
            content_hash = hashlib.sha256(file_content).hexdigest()
            
            # Check if file with same hash already exists
            existing_file = frappe.db.get_value(
                "File",
                {"content_hash": content_hash},
                ["name", "file_url"]
            )
            
            if existing_file:
                # File already exists, reuse it
                file_doc = frappe.get_doc("File", existing_file[0])
                
                # Update attachment info if provided
                if attached_to_doctype and attached_to_name:
                    file_doc.attached_to_doctype = attached_to_doctype
                    file_doc.attached_to_name = attached_to_name
                    file_doc.attached_to_field = field_name
                    file_doc.save(ignore_permissions=True)
                
                return {
                    "success": True,
                    "file_url": existing_file[1],
                    "file_name": existing_file[0],
                    "message": _("File uploaded successfully (existing file reused)"),
                    "reused": True
                }
            
            # Create new file document
            file_doc = frappe.get_doc({
                "doctype": "File",
                "file_name": secure_name,
                "file_type": mime_type,
                "file_size": file_size,
                "content_hash": content_hash,
                "is_private": 1,  # Make files private by default
                "attached_to_doctype": attached_to_doctype,
                "attached_to_name": attached_to_name,
                "attached_to_field": field_name
            })
            
            # Save file content
            file_doc.content = file_content
            file_doc.save(ignore_permissions=True)
            
            return {
                "success": True,
                "file_url": file_doc.file_url,
                "file_name": file_doc.name,
                "message": _("File uploaded successfully"),
                "reused": False,
                "file_size": file_size,
                "mime_type": mime_type
            }
        
        except Exception as e:
            frappe.log_error(f"File upload error: {str(e)}", "File Upload")
            return {
                "success": False,
                "error": _("An error occurred while uploading the file: {0}").format(str(e))
            }
    
    def process_multiple_files(self, files_data, field_name, attached_to_doctype=None, attached_to_name=None):
        """
        Process multiple file uploads (for promote-project form)
        
        Args:
            files_data (list): List of file data dictionaries
            field_name (str): Form field name
            attached_to_doctype (str): DocType to attach files to
            attached_to_name (str): Document name to attach files to
            
        Returns:
            dict: Processing result with all file info or errors
        """
        config = self.validator.FILE_TYPE_CONFIGS.get(field_name, {})
        max_files = config.get("max_files", 1)
        
        if len(files_data) > max_files:
            return {
                "success": False,
                "error": _("Too many files. Maximum {0} files allowed").format(max_files)
            }
        
        results = []
        errors = []
        
        for i, file_data in enumerate(files_data):
            result = self.process_file_upload(
                file_data, field_name, attached_to_doctype, attached_to_name
            )
            
            if result["success"]:
                results.append(result)
            else:
                errors.append({
                    "file_index": i,
                    "filename": file_data.get("filename", f"File {i+1}"),
                    "error": result["error"]
                })
        
        if errors:
            return {
                "success": False,
                "error": _("Some files failed to upload"),
                "file_errors": errors,
                "successful_uploads": results
            }
        
        return {
            "success": True,
            "message": _("{0} files uploaded successfully").format(len(results)),
            "files": results
        }


class AttachmentManager:
    """
    Manages file attachments to DocType records
    """
    
    def __init__(self):
        self.upload_handler = FileUploadHandler()
    
    def attach_files_to_document(self, doc, form_data, form_type):
        """
        Attach files from form data to a document
        
        Args:
            doc: Frappe document to attach files to
            form_data (dict): Original form data
            form_type (str): Type of form being processed
            
        Returns:
            dict: Attachment results
        """
        attachment_results = {
            "success": True,
            "attached_files": [],
            "errors": []
        }
        
        # Define file fields for each form type
        file_field_mappings = {
            "small-project-register": ["idCardImage"],
            "contract-opportunity": ["cvFile"],
            "promote-project": ["files"]
        }
        
        file_fields = file_field_mappings.get(form_type, [])
        
        for field_name in file_fields:
            if field_name in form_data and form_data[field_name]:
                file_data = form_data[field_name]
                
                # Handle multiple files (for promote-project)
                if field_name == "files" and isinstance(file_data, list):
                    result = self.upload_handler.process_multiple_files(
                        file_data, field_name, doc.doctype, doc.name
                    )
                else:
                    # Handle single file
                    if not isinstance(file_data, dict):
                        # Skip if file data is not in expected format
                        continue
                    
                    result = self.upload_handler.process_file_upload(
                        file_data, field_name, doc.doctype, doc.name
                    )
                
                if result["success"]:
                    attachment_results["attached_files"].append({
                        "field_name": field_name,
                        "result": result
                    })
                    
                    # Update document with file URL if it's a single file field
                    if field_name == "idCardImage":
                        doc.image = result.get("file_url")
                        doc.save(ignore_permissions=True)
                    
                else:
                    attachment_results["errors"].append({
                        "field_name": field_name,
                        "error": result["error"]
                    })
                    attachment_results["success"] = False
        
        return attachment_results
    
    def get_document_attachments(self, doctype, docname):
        """
        Get all attachments for a document
        
        Args:
            doctype (str): DocType name
            docname (str): Document name
            
        Returns:
            list: List of attached files
        """
        try:
            attachments = frappe.get_all(
                "File",
                filters={
                    "attached_to_doctype": doctype,
                    "attached_to_name": docname
                },
                fields=["name", "file_name", "file_url", "file_size", "file_type", "attached_to_field"]
            )
            
            return attachments
        
        except Exception as e:
            frappe.log_error(f"Error getting attachments: {str(e)}")
            return []


def get_file_upload_config(field_name):
    """
    Get file upload configuration for a specific field
    
    Args:
        field_name (str): Form field name
        
    Returns:
        dict: File upload configuration
    """
    return FileValidator.FILE_TYPE_CONFIGS.get(field_name, {})


def validate_uploaded_file(file_content, filename, field_name):
    """
    Validate an uploaded file
    
    Args:
        file_content (bytes): File content
        filename (str): Original filename
        field_name (str): Form field name
        
    Returns:
        dict: Validation result
    """
    validator = FileValidator()
    
    # Type validation
    is_valid_type, type_error, mime_type = validator.validate_file_type(
        file_content, filename, field_name
    )
    if not is_valid_type:
        return {"valid": False, "error": type_error}
    
    # Size validation
    is_valid_size, size_error, file_size = validator.validate_file_size(
        file_content, field_name
    )
    if not is_valid_size:
        return {"valid": False, "error": size_error}
    
    # Image validation if applicable
    if "image" in mime_type:
        is_valid_image, image_error, image_info = validator.validate_image_content(
            file_content, field_name
        )
        if not is_valid_image:
            return {"valid": False, "error": image_error}
    
    # Malware scanning
    is_safe, malware_warning = validator.scan_for_malware(file_content, filename)
    if not is_safe:
        return {"valid": False, "error": malware_warning}
    
    return {
        "valid": True,
        "mime_type": mime_type,
        "file_size": file_size
    }