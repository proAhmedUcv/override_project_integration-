"""
API Documentation Generation Endpoints
"""

import frappe
from frappe import _
import json
from override_project_integration.api.utils import api_response
from override_project_integration.api.middleware import cors_handler, rate_limit


@frappe.whitelist(allow_guest=True)
@cors_handler
@rate_limit(limit=30, window=60, endpoint_name="api_documentation")
def get_api_documentation():
    """
    Generate comprehensive API documentation
    
    Returns:
        dict: Complete API documentation with endpoints, schemas, and examples
    """
    try:
        documentation = {
            "api_info": {
                "name": "Override Project Integration API",
                "version": "1.0.0",
                "description": "REST API for Vue.js/Flutter integration with Frappe Framework",
                "base_url": f"{frappe.utils.get_url()}/api/method/override_project_integration.api",
                "authentication": {
                    "type": "Token-based",
                    "header": "X-Token-ID",
                    "description": "Include token_id from Vue.js frontend in X-Token-ID header"
                },
                "content_type": "application/json",
                "cors_enabled": True,
                "rate_limiting": True
            },
            "endpoints": _get_endpoint_documentation(),
            "form_schemas": _get_form_schemas_documentation(),
            "response_formats": _get_response_format_examples(),
            "file_upload": _get_file_upload_documentation(),
            "error_codes": _get_error_codes_documentation(),
            "security": _get_security_documentation()
        }
        
        return api_response(
            success=True,
            message=_("API documentation generated successfully"),
            data=documentation
        )
        
    except Exception as e:
        frappe.log_error(f"Error generating API documentation: {str(e)}")
        return api_response(
            success=False,
            message=_("Failed to generate API documentation"),
            status_code=500
        )


@frappe.whitelist(allow_guest=True)
@cors_handler
@rate_limit(limit=20, window=60, endpoint_name="form_schemas")
def get_form_schemas():
    """
    Get detailed form schemas with validation rules
    
    Returns:
        dict: Form schemas with field definitions and validation rules
    """
    try:
        schemas = _get_detailed_form_schemas()
        
        return api_response(
            success=True,
            message=_("Form schemas retrieved successfully"),
            data=schemas
        )
        
    except Exception as e:
        frappe.log_error(f"Error getting form schemas: {str(e)}")
        return api_response(
            success=False,
            message=_("Failed to retrieve form schemas"),
            status_code=500
        )


@frappe.whitelist(allow_guest=True)
@cors_handler
@rate_limit(limit=20, window=60, endpoint_name="response_examples")
def get_response_examples():
    """
    Get response format examples for all endpoints
    
    Returns:
        dict: Response examples for success and error cases
    """
    try:
        examples = _get_comprehensive_response_examples()
        
        return api_response(
            success=True,
            message=_("Response examples retrieved successfully"),
            data=examples
        )
        
    except Exception as e:
        frappe.log_error(f"Error getting response examples: {str(e)}")
        return api_response(
            success=False,
            message=_("Failed to retrieve response examples"),
            status_code=500
        )


def _get_endpoint_documentation():
    """Generate comprehensive endpoint documentation"""
    return {
        "form_processing": {
            "submit_form": {
                "url": "/forms.submit_form",
                "method": "POST",
                "description": "Submit various business forms with file uploads",
                "authentication": "Required (X-Token-ID header)",
                "rate_limit": "10 requests per minute",
                "parameters": {
                    "form_type": {
                        "type": "string",
                        "required": True,
                        "description": "Type of form being submitted",
                        "allowed_values": [
                            "small-project-register",
                            "training-program",
                            "volunteer-program", 
                            "training-service",
                            "training-ad",
                            "promote-project",
                            "specs-memo-request",
                            "contract-opportunity",
                            "contact-form"
                        ]
                    },
                    "form_data": {
                        "type": "object",
                        "required": True,
                        "description": "Form field data as JSON object"
                    },
                    "files": {
                        "type": "array",
                        "required": False,
                        "description": "Array of file objects for upload"
                    }
                },
                "response": {
                    "success": "Returns created document details",
                    "error": "Returns validation errors or server errors"
                }
            }
        },
        "user_management": {
            "get_user_status": {
                "url": "/user_status.get_user_status",
                "method": "GET",
                "description": "Get current user status and session information",
                "authentication": "Required (X-Token-ID header)",
                "rate_limit": "20 requests per minute",
                "parameters": {},
                "response": {
                    "success": "Returns user details and session status",
                    "error": "Returns authentication errors"
                }
            },
            "validate_token": {
                "url": "/user_status.validate_token",
                "method": "GET/POST",
                "description": "Validate a token without creating a session",
                "authentication": "Required (X-Token-ID header)",
                "rate_limit": "10 requests per minute",
                "parameters": {
                    "token_id": {
                        "type": "string",
                        "required": True,
                        "description": "Token ID to validate"
                    }
                },
                "response": {
                    "success": "Returns token validation status",
                    "error": "Returns validation errors"
                }
            },
            "invalidate_session": {
                "url": "/user_status.invalidate_session",
                "method": "POST",
                "description": "Invalidate current user session",
                "authentication": "Required (X-Token-ID header)",
                "rate_limit": "5 requests per minute",
                "parameters": {},
                "response": {
                    "success": "Returns session invalidation confirmation",
                    "error": "Returns authentication errors"
                }
            }
        },
        "health_monitoring": {
            "health_check": {
                "url": "/health.health_check",
                "method": "GET",
                "description": "Comprehensive system health check with metrics",
                "authentication": "Not required",
                "rate_limit": "60 requests per minute",
                "parameters": {},
                "response": {
                    "success": "Returns system health status and metrics",
                    "error": "Returns system error information"
                }
            },
            "get_api_metrics": {
                "url": "/health.get_api_metrics",
                "method": "GET",
                "description": "API performance metrics and usage statistics",
                "authentication": "Not required",
                "rate_limit": "30 requests per minute",
                "parameters": {},
                "response": {
                    "success": "Returns API metrics and statistics",
                    "error": "Returns metrics collection errors"
                }
            },
            "get_form_submission_logs": {
                "url": "/health.get_form_submission_logs",
                "method": "GET",
                "description": "Form submission audit logs for debugging",
                "authentication": "Not required",
                "rate_limit": "20 requests per minute",
                "parameters": {},
                "response": {
                    "success": "Returns form submission logs and statistics",
                    "error": "Returns log retrieval errors"
                }
            },
            "get_system_diagnostics": {
                "url": "/health.get_system_diagnostics",
                "method": "GET",
                "description": "Detailed system diagnostics information",
                "authentication": "Not required",
                "rate_limit": "10 requests per minute",
                "parameters": {},
                "response": {
                    "success": "Returns comprehensive system diagnostics",
                    "error": "Returns diagnostic collection errors"
                }
            }
        },
        "documentation": {
            "get_api_documentation": {
                "url": "/documentation.get_api_documentation",
                "method": "GET",
                "description": "Get complete API documentation",
                "authentication": "Not required",
                "rate_limit": "30 requests per minute",
                "parameters": {},
                "response": {
                    "success": "Returns complete API documentation",
                    "error": "Returns documentation generation errors"
                }
            },
            "get_form_schemas": {
                "url": "/documentation.get_form_schemas",
                "method": "GET",
                "description": "Get detailed form schemas with validation rules",
                "authentication": "Not required",
                "rate_limit": "20 requests per minute",
                "parameters": {},
                "response": {
                    "success": "Returns form schemas and validation rules",
                    "error": "Returns schema retrieval errors"
                }
            },
            "get_response_examples": {
                "url": "/documentation.get_response_examples",
                "method": "GET",
                "description": "Get response format examples for all endpoints",
                "authentication": "Not required",
                "rate_limit": "20 requests per minute",
                "parameters": {},
                "response": {
                    "success": "Returns response format examples",
                    "error": "Returns example generation errors"
                }
            }
        }
    }


def _get_form_schemas_documentation():
    """Generate form schemas documentation based on actual Vue.js formsConfig"""
    return {
        "small-project-register": {
            "description": "استمارة تسجيل مشروعك لدى الهيئة العامة لتنمية المشاريع الصغيرة والأصغر",
            "doctype": "Micro Enterprise Request",
            "required_fields": [
                "ownerFullName", "governorate", "district", "neighborhood", "street",
                "age", "primaryPhone", "projectName", "projectStatus", "capital",
                "workersCount", "startDate", "products", "projectDescription"
            ],
            "optional_fields": [
                "secondaryPhone", "email", "educationPlace", "educationMajor", "graduationYear"
            ],
            "child_tables": {
                "project_details": {
                    "description": "Project implementation details",
                    "fields": ["project_name", "project_detials", "number_of_workers", "amount_capital"]
                },
                "address_details": {
                    "description": "Address information",
                    "fields": ["city_name", "directorate_name", "district_name", "district_name_info"]
                }
            },
            "file_uploads": {
                "idCardImage": {
                    "description": "صورة البطاقة الشخصية",
                    "allowed_types": ["jpg", "jpeg", "png"],
                    "max_size": "10MB",
                    "required": true
                }
            },
            "validation_rules": {
                "email": "Valid email format required",
                "primaryPhone": "Valid phone number format required",
                "age": "Age must be between 18 and 100",
                "projectStatus": "Must be one of: قيد الفكرة, قيد التنفيذ, قائم"
            }
        },
        "promote-project": {
            "description": "استمارة تسجيل خدمة روج لمشروعك لدى الهيئة العامة لتنمية المشاريع الصغيرة والأصغر",
            "doctype": "Project Promotion Request",
            "required_fields": [
                "projectName", "projectDescription"
            ],
            "optional_fields": [
                "price"
            ],
            "file_uploads": {
                "files": {
                    "description": "صور لمنتجاتك (حتى 3 صور)",
                    "allowed_types": ["jpg", "jpeg", "png"],
                    "max_size": "10MB",
                    "max_files": 3,
                    "required": false
                }
            },
            "validation_rules": {
                "projectName": "Project name is required",
                "projectDescription": "Project description is required"
            }
        },
        "training-program": {
            "description": "استمارة طلب الالتحاق ببرنامج تدريبي",
            "doctype": "Training Registration",
            "required_fields": [
                "fullName", "phone", "city", "age"
            ],
            "optional_fields": [
                "reason"
            ],
            "validation_rules": {
                "phone": "Valid phone number format required",
                "age": "Age must be between 16 and 100"
            }
        },
        "volunteer-program": {
            "description": "استمارة طلب الانضمام لبرنامج التطوع",
            "doctype": "Volunteer Application",
            "required_fields": [
                "fullName", "phone", "city", "age", "favField"
            ],
            "optional_fields": [
                "summary"
            ],
            "validation_rules": {
                "phone": "Valid phone number format required",
                "age": "Age must be between 16 and 100",
                "favField": "Volunteer field preference is required"
            }
        },
        "training-service": {
            "description": "استمارة طلب خدمة التدريب لدى الهيئة العامة لتنمية المشاريع الصغيرة والأصغر",
            "doctype": "Training Service Request",
            "required_fields": [
                "fullName", "phone", "city", "age", "trainingFields"
            ],
            "optional_fields": [
                "reason"
            ],
            "checkbox_fields": {
                "trainingFields": [
                    "تصنيع غذائي", "خياطة", "حرف", "ريادة أعمال",
                    "تدريب مهني ومعرفي لأصحاب المشاريع الصغيرة"
                ]
            },
            "validation_rules": {
                "phone": "Valid phone number format required",
                "age": "Age must be between 16 and 100",
                "trainingFields": "At least one training field must be selected"
            }
        },
        "specs-memo-request": {
            "description": "استمارة تسجيل خدمة طلب مذكرة المواصفات والمقاييس",
            "doctype": "Specification Memo Request",
            "required_fields": [
                "projectType", "projectName", "projectStatus", "startDate", "capital",
                "location", "ownerName", "gender", "birthDate", "educationLevel",
                "currentAddress", "phone"
            ],
            "optional_fields": [
                "qualification", "graduationYear", "relativePhone"
            ],
            "validation_rules": {
                "phone": "Valid phone number format required",
                "projectType": "Must be one of: صغير, متناهي الصغر, مشروع صغير قيد التأسيس",
                "projectStatus": "Must be one of: نشط, غير نشط",
                "gender": "Must be one of: ذكر, أنثى",
                "educationLevel": "Must be one of: مدرسة, جامعة, معهد"
            }
        },
        "training-ad": {
            "description": "استمارة إعلان برنامج التدريب",
            "doctype": "Training Advertisement",
            "required_fields": [
                "fullName", "phone", "city", "age"
            ],
            "optional_fields": [
                "reason"
            ],
            "validation_rules": {
                "phone": "Valid phone number format required",
                "age": "Age must be between 16 and 100"
            }
        },
        "contract-opportunity": {
            "description": "استمارة التقديم على فرصة التعاقد",
            "doctype": "Contract Opportunity",
            "required_fields": [
                "fullName", "phone", "email", "specialization", "experienceYears", "field"
            ],
            "optional_fields": [
                "coverLetter", "notes"
            ],
            "file_uploads": {
                "cvFile": {
                    "description": "السيرة الذاتية (PDF أو Word)",
                    "allowed_types": ["pdf", "doc", "docx"],
                    "max_size": "10MB",
                    "required": true
                }
            },
            "validation_rules": {
                "email": "Valid email format required",
                "phone": "Valid phone number format required",
                "experienceYears": "Experience years must be a positive number"
            }
        },
        "contact-form": {
            "description": "نموذج تواصل مع الهيئة",
            "doctype": "Contact Inquiry",
            "required_fields": [
                "fullName", "phone", "subject", "message"
            ],
            "optional_fields": [
                "email"
            ],
            "validation_rules": {
                "phone": "Valid phone number format required",
                "email": "Valid email format required (if provided)"
            }
        }
    }


def _get_response_format_examples():
    """Generate response format examples"""
    return {
        "success_response": {
            "structure": {
                "success": True,
                "message": "Operation completed successfully",
                "data": "Response data object",
                "timestamp": "ISO 8601 timestamp",
                "request_id": "Unique request identifier"
            },
            "example": {
                "success": True,
                "message": "Form submitted successfully",
                "data": {
                    "document_name": "MER-2024-001",
                    "doctype": "Micro Enterprise Request",
                    "status": "Draft",
                    "created_by": "user@example.com",
                    "creation_time": "2024-01-01T12:00:00Z"
                },
                "timestamp": "2024-01-01T12:00:00Z",
                "request_id": "req_123456789"
            }
        },
        "error_response": {
            "structure": {
                "success": False,
                "message": "Error description",
                "error_code": "Error code identifier",
                "errors": "Detailed error information",
                "timestamp": "ISO 8601 timestamp",
                "request_id": "Unique request identifier"
            },
            "validation_error_example": {
                "success": False,
                "message": "Validation failed",
                "error_code": "VALIDATION_ERROR",
                "errors": {
                    "field_errors": {
                        "email": ["Invalid email format"],
                        "phone": ["Phone number is required"]
                    },
                    "general_errors": ["Form type is not supported"]
                },
                "timestamp": "2024-01-01T12:00:00Z",
                "request_id": "req_123456789"
            },
            "server_error_example": {
                "success": False,
                "message": "Internal server error occurred",
                "error_code": "SERVER_ERROR",
                "errors": {
                    "type": "DatabaseError",
                    "description": "Unable to save document"
                },
                "timestamp": "2024-01-01T12:00:00Z",
                "request_id": "req_123456789"
            }
        },
        "health_check_response": {
            "example": {
                "success": True,
                "message": "System health check completed",
                "data": {
                    "status": "healthy",
                    "timestamp": "2024-01-01T12:00:00Z",
                    "response_time_ms": 45.2,
                    "version": {
                        "frappe": "15.0.0",
                        "app": "override_project_integration",
                        "app_version": "1.0.0"
                    },
                    "services": {
                        "database": {
                            "status": "ok",
                            "response_time_ms": 12.5
                        },
                        "cache": {
                            "status": "ok", 
                            "response_time_ms": 8.3
                        }
                    },
                    "system": {
                        "uptime": "5d 12h 30m",
                        "memory": {
                            "total_gb": 8.0,
                            "available_gb": 4.2,
                            "percent_used": 47.5
                        },
                        "cpu_percent": 25.8
                    }
                }
            }
        }
    }


def _get_file_upload_documentation():
    """Generate file upload documentation"""
    return {
        "general_requirements": {
            "max_file_size": "5MB per file",
            "max_files_per_request": 10,
            "supported_formats": {
                "documents": ["pdf", "doc", "docx", "txt"],
                "images": ["jpg", "jpeg", "png", "gif"],
                "archives": ["zip", "rar"]
            },
            "security_checks": [
                "File type validation",
                "File size validation", 
                "Virus scanning",
                "Content type verification"
            ]
        },
        "upload_process": {
            "step_1": "Include files in form submission request",
            "step_2": "Files are validated for type and size",
            "step_3": "Files are scanned for security threats",
            "step_4": "Files are stored in Frappe file system",
            "step_5": "File attachments are linked to created documents"
        },
        "form_specific_requirements": {
            "small-project-register": {
                "cv_file": {
                    "description": "CV/Resume document",
                    "required": False,
                    "formats": ["pdf", "doc", "docx"],
                    "max_size": "5MB"
                },
                "id_card_image": {
                    "description": "ID card or passport image",
                    "required": False,
                    "formats": ["jpg", "jpeg", "png"],
                    "max_size": "2MB"
                }
            }
        },
        "error_handling": {
            "file_too_large": "File size exceeds maximum allowed size",
            "invalid_format": "File format is not supported",
            "virus_detected": "File contains malicious content",
            "upload_failed": "File upload process failed"
        }
    }


def _get_error_codes_documentation():
    """Generate error codes documentation"""
    return {
        "validation_errors": {
            "VALIDATION_ERROR": {
                "description": "Form validation failed",
                "http_status": 400,
                "common_causes": [
                    "Required fields missing",
                    "Invalid field formats",
                    "Field length constraints violated"
                ]
            },
            "INVALID_FORM_TYPE": {
                "description": "Unsupported form type specified",
                "http_status": 400,
                "common_causes": ["Form type not in allowed list"]
            },
            "FILE_VALIDATION_ERROR": {
                "description": "File upload validation failed",
                "http_status": 400,
                "common_causes": [
                    "File size too large",
                    "Invalid file format",
                    "File security check failed"
                ]
            }
        },
        "authentication_errors": {
            "AUTHENTICATION_REQUIRED": {
                "description": "Authentication token required",
                "http_status": 401,
                "common_causes": ["Missing X-Token-ID header"]
            },
            "INVALID_TOKEN": {
                "description": "Invalid or expired token",
                "http_status": 401,
                "common_causes": [
                    "Token not found in system",
                    "Token has expired",
                    "Token format invalid"
                ]
            }
        },
        "server_errors": {
            "SERVER_ERROR": {
                "description": "Internal server error",
                "http_status": 500,
                "common_causes": [
                    "Database connection issues",
                    "File system errors",
                    "Unexpected application errors"
                ]
            },
            "RATE_LIMIT_EXCEEDED": {
                "description": "Rate limit exceeded",
                "http_status": 429,
                "common_causes": ["Too many requests in time window"]
            }
        }
    }


def _get_security_documentation():
    """Generate security documentation"""
    return {
        "authentication": {
            "method": "Token-based authentication",
            "header": "X-Token-ID",
            "description": "Include token_id received from Vue.js frontend",
            "token_validation": "Tokens are validated against user sessions"
        },
        "cors": {
            "enabled": True,
            "allowed_origins": ["localhost", "netlify.app"],
            "allowed_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "credentials_supported": True,
            "preflight_handling": "Automatic OPTIONS request handling"
        },
        "rate_limiting": {
            "enabled": True,
            "default_limit": "60 requests per minute",
            "endpoint_specific_limits": {
                "submit_form": "10 requests per minute",
                "health_check": "60 requests per minute",
                "get_user_status": "20 requests per minute"
            },
            "headers": [
                "X-Rate-Limit-Limit",
                "X-Rate-Limit-Remaining", 
                "X-Rate-Limit-Reset"
            ]
        },
        "input_validation": {
            "enabled": True,
            "features": [
                "Field type validation",
                "Field length validation",
                "Email format validation",
                "Phone number validation",
                "File type validation",
                "File size validation"
            ]
        },
        "security_headers": {
            "content_security_policy": "Strict CSP headers",
            "hsts": "HTTP Strict Transport Security",
            "x_frame_options": "Clickjacking protection",
            "x_content_type_options": "MIME type sniffing protection"
        },
        "logging": {
            "request_logging": "All API requests are logged",
            "error_logging": "All errors are logged with details",
            "security_logging": "Security events are logged",
            "audit_trail": "Form submissions are audited"
        }
    }


def _get_detailed_form_schemas():
    """Get detailed form schemas with complete field definitions"""
    return _get_form_schemas_documentation()


def _get_comprehensive_response_examples():
    """Get comprehensive response examples"""
    return _get_response_format_examples()