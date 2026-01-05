"""
Form processors for different form types
"""

import frappe
from frappe import _
from abc import ABC, abstractmethod
import re
from datetime import datetime
from .child_table_utils import create_child_table_processor, ChildTableManager


# Form type to DocType mapping
FORM_DOCTYPE_MAPPING = {
    "small-project-register": "Micro Enterprise Request",
    "training-program": "Training Registration",
    "volunteer-program": "Volunteer Application", 
    "training-service": "Training Service Request",
    "training-ad": "Training Advertisement",
    "promote-project": "Project Promotion Request",
    "specs-memo-request": "Specification Memo Request",
    "contract-opportunity": "Contract Opportunity",
    "contact-form": "Contact Inquiry"
}

# Field mapping configurations for each form type
FIELD_MAPPINGS = {
    "small-project-register": {
        # Main fields - direct mapping
        "firstName": "first_name",
        "middleName": "middle_name", 
        "lastName": "last_name",
        "gender": "gender",
        "birthDate": "date_of_birth",
        "workJoinDate": "date_of_joining",
        "idNumber": "token_id",
        
        # Emergency contact
        "emergencyContactName": "person_to_be_contacted",
        "emergencyContactPhone": "emergency_phone_number",
        "emergencyRelation": "relation",
        
        # Contact details
        "mobile": "cell_number",
        "email": "personal_email",
        "familyInfo": "family_background",
        
        # Project type and status
        "projectType": "enterprise_type",
        "projectStatus": "status",
        
        # Child table mappings
        "educations": {
            "table_name": "education",
            "doctype": "Employee Education",
            "fields": {
                "qualification": "qualification",
                "school_univ": "school_univ",
                "level": "level",
                "year_of_passing": "year_of_passing",
                "class_per": "class_per",
                "maj_opt_subj": "maj_opt_subj"
            }
        },
        "projects": {
            "table_name": "project",
            "doctype": "Project Details",
            "fields": {
                "project_name": "project_name",
                "project_detials": "project_detials",
                "sector_name": "sector_name",
                "sector_type_name": "sector_type_name",
                "sector_type_nam_info": "sector_type_nam_info",
                "sector_type_details_name": "sector_type_details_name",
                "sector_type_details_name_info": "sector_type_details_name_info",
                "number_of_workers": "number_of_workers",
                "amount_capital": "amount_capital"
            }
        },
        "productions": {
            "table_name": "productivity",
            "doctype": "Productivity",
            "fields": {
                "quantity": "quantity",
                "unit": "unit"
            }
        },
        "addresses": {
            "table_name": "address_details",
            "doctype": "Address Details",
            "fields": {
                "city_name": "city_name",
                "directorate_name": "directorate_name",
                "district_name": "district_name",
                "district_name_info": "district_name_info",
                "village_name": "village_name",
                "village_name_info": "village_name_info",
                "accommodation_type": "accommodation_type"
            }
        }
    }
}

# Form descriptions for API documentation
FORM_DESCRIPTIONS = {
    "small-project-register": "Micro enterprise registration form for small business applications",
    "training-program": "Training program registration form",
    "volunteer-program": "Volunteer program application form",
    "training-service": "Training service request form",
    "training-ad": "Training advertisement registration form",
    "promote-project": "Project promotion service request form",
    "specs-memo-request": "Specification memo request form",
    "contract-opportunity": "Contract opportunity application form",
    "contact-form": "General contact inquiry form"
}


class TokenValidator:
    """
    Validates and manages token_id from Vue.js frontend
    """
    
    @staticmethod
    def validate_token_format(token_id):
        """
        Validate token_id format
        
        Args:
            token_id (str): Token ID to validate
            
        Returns:
            tuple: (is_valid, error_message)
        """
        if not token_id:
            return False, _("Token ID is required")
        
        if not isinstance(token_id, str):
            return False, _("Token ID must be a string")
        
        # Basic format validation - adjust pattern as needed
        if len(token_id.strip()) < 5:
            return False, _("Token ID must be at least 5 characters long")
        
        # Check for valid characters (alphanumeric, hyphens, underscores)
        if not re.match(r'^[a-zA-Z0-9_-]+$', token_id.strip()):
            return False, _("Token ID contains invalid characters")
        
        return True, None
    
    @staticmethod
    def check_duplicate_token(token_id, doctype="Micro Enterprise Request"):
        """
        Check if token_id already exists in the system
        
        Args:
            token_id (str): Token ID to check
            doctype (str): DocType to check against
            
        Returns:
            tuple: (is_duplicate, existing_record_name)
        """
        if not token_id:
            return False, None
        
        try:
            existing_record = frappe.db.get_value(
                doctype,
                {"token_id": token_id.strip()},
                "name"
            )
            
            return bool(existing_record), existing_record
        except Exception as e:
            frappe.log_error(f"Error checking duplicate token: {str(e)}")
            return False, None
    
    @staticmethod
    def handle_duplicate_token(token_id, doctype="Micro Enterprise Request"):
        """
        Handle duplicate token scenario
        
        Args:
            token_id (str): Token ID that is duplicate
            doctype (str): DocType where duplicate was found
            
        Returns:
            dict: Response indicating how duplicate was handled
        """
        is_duplicate, existing_record = TokenValidator.check_duplicate_token(token_id, doctype)
        
        if is_duplicate:
            # Log the duplicate attempt
            frappe.log_error(
                f"Duplicate token_id submission: {token_id} for {doctype}. Existing record: {existing_record}",
                "Duplicate Token Submission"
            )
            
            return {
                "is_duplicate": True,
                "existing_record": existing_record,
                "message": _("This token has already been used for registration"),
                "action": "rejected"  # Could be "merged", "updated", etc. based on business logic
            }
        
        return {
            "is_duplicate": False,
            "existing_record": None,
            "message": _("Token is valid and unique"),
            "action": "proceed"
        }


class FieldMapper:
    """
    Utility class for mapping form fields to DocType fields
    """
    
    @staticmethod
    def map_fields(form_data, form_type):
        """
        Map form fields to DocType fields based on configuration
        
        Args:
            form_data (dict): Form data to map
            form_type (str): Type of form being processed
            
        Returns:
            dict: Mapped data ready for DocType creation
        """
        mapping_config = FIELD_MAPPINGS.get(form_type, {})
        mapped_data = {}
        child_tables = {}
        
        if form_type == "small-project-register":
            # Map main fields
            for form_field, doctype_field in mapping_config.items():
                if form_field in ["project_fields", "address_fields", "education_fields"]:
                    continue
                    
                if form_field == "age":
                    # Special handling for age -> date_of_birth conversion
                    age = form_data.get("age")
                    if age:
                        try:
                            age_int = int(age)
                            birth_year = datetime.now().year - age_int
                            mapped_data["date_of_birth"] = f"{birth_year}-01-01"
                        except (ValueError, TypeError):
                            pass
                elif form_field == "gender":
                    # Default gender if not provided
                    mapped_data["gender"] = "Male"
                elif form_field == "status":
                    # Default status
                    mapped_data["status"] = "Open"
                elif form_field in form_data:
                    mapped_data[doctype_field] = form_data[form_field]
            
            # Map project fields to child table
            project_fields = mapping_config.get("project_fields", {})
            project_data = {}
            for form_field, doctype_field in project_fields.items():
                if form_field in form_data:
                    project_data[doctype_field] = form_data[form_field]
            
            if project_data:
                child_tables["project"] = [project_data]
            
            # Map address fields to child table
            address_fields = mapping_config.get("address_fields", {})
            address_data = {}
            for form_field, doctype_field in address_fields.items():
                if form_field in form_data:
                    address_data[doctype_field] = form_data[form_field]
            
            # Add default accommodation type
            if address_data:
                address_data["accommodation_type"] = "Owned"
                child_tables["address_details"] = [address_data]
            
            # Map education fields to child table if provided
            education_fields = mapping_config.get("education_fields", {})
            education_data = {}
            for form_field, doctype_field in education_fields.items():
                if form_field in form_data and form_data[form_field]:
                    education_data[doctype_field] = form_data[form_field]
            
            if education_data:
                child_tables["education"] = [education_data]
        
        return mapped_data, child_tables


class BaseFormProcessor(ABC):
    """
    Abstract base class for form processors
    """
    
    def __init__(self, form_type):
        self.form_type = form_type
        self.doctype = FORM_DOCTYPE_MAPPING.get(form_type)
        self.token_validator = TokenValidator()
        self.field_mapper = FieldMapper()
    
    @abstractmethod
    def validate_form_data(self, form_data):
        """
        Validate form data specific to this form type
        
        Args:
            form_data (dict): Form data to validate
            
        Returns:
            tuple: (is_valid, errors)
        """
        pass
    
    def validate_token_id(self, token_id):
        """
        Validate token_id if provided
        
        Args:
            token_id (str): Token ID to validate
            
        Returns:
            tuple: (is_valid, error_message, duplicate_info)
        """
        if not token_id:
            return True, None, None  # Token is optional
        
        # Validate format
        is_valid_format, format_error = self.token_validator.validate_token_format(token_id)
        if not is_valid_format:
            return False, format_error, None
        
        # Check for duplicates only if DocType exists
        if frappe.db.exists("DocType", self.doctype):
            duplicate_info = self.token_validator.handle_duplicate_token(token_id, self.doctype)
            if duplicate_info["is_duplicate"]:
                return False, duplicate_info["message"], duplicate_info
        else:
            # If DocType doesn't exist, we can't check for duplicates
            duplicate_info = {
                "is_duplicate": False,
                "existing_record": None,
                "message": _("Token is valid (DocType not found for duplicate check)"),
                "action": "proceed"
            }
        
        return True, None, duplicate_info
    
    def map_form_fields(self, form_data):
        """
        Map form fields to DocType fields using FieldMapper and ChildTableProcessor
        Default implementation - can be overridden by specific processors
        
        Args:
            form_data (dict): Form data to map
            
        Returns:
            tuple: (mapped_data, child_tables)
        """
        # Use child table processor for comprehensive mapping
        child_processor = create_child_table_processor(self.doctype)
        child_tables = child_processor.process_child_tables(form_data)
        
        # Use existing field mapper for main fields
        mapped_data, _ = self.field_mapper.map_fields(form_data, self.form_type)
        
        return mapped_data, child_tables
    
    def process_form(self, form_data, token_id=None):
        """
        Process form submission
        
        Args:
            form_data (dict): Form data
            token_id (str): Optional token ID from Vue.js frontend
            
        Returns:
            dict: Processing result with success status and data/errors
        """
        try:
            # Validate token_id if provided
            if token_id:
                is_valid_token, token_error, duplicate_info = self.validate_token_id(token_id)
                if not is_valid_token:
                    return {
                        "success": False,
                        "message": token_error,
                        "errors": {"token_id": [token_error]}
                    }
            
            # Validate form data
            is_valid, validation_errors = self.validate_form_data(form_data)
            if not is_valid:
                return {
                    "success": False,
                    "message": _("Form validation failed"),
                    "errors": validation_errors
                }
            
            # Map form fields to DocType fields
            mapped_data, child_tables = self.map_form_fields(form_data)
            
            # Add token_id if provided
            if token_id:
                mapped_data["token_id"] = token_id.strip()
            
            # Check if DocType exists before creating document
            if not frappe.db.exists("DocType", self.doctype):
                # For now, return success with a placeholder response
                # This allows the processor to work even without the actual DocTypes
                return {
                    "success": True,
                    "message": _("Form submitted successfully (DocType {0} not found - using placeholder)").format(self.doctype),
                    "data": {
                        "record_id": f"placeholder_{self.form_type}_{frappe.utils.now()}",
                        "doctype": self.doctype,
                        "status": "Open",
                        "token_id": token_id,
                        "note": f"DocType '{self.doctype}' does not exist yet"
                    }
                }
            
            # Create DocType record
            doc = frappe.get_doc({
                "doctype": self.doctype,
                **mapped_data
            })
            
            # Add child table records using ChildTableManager
            ChildTableManager.populate_child_tables(doc, child_tables)
            
            doc.insert(ignore_permissions=True)
            
            # Handle file attachments if any
            self.handle_file_attachments(doc, form_data)
            
            return {
                "success": True,
                "message": _("Form submitted successfully"),
                "data": {
                    "record_id": doc.name,
                    "doctype": self.doctype,
                    "status": doc.get("status", "Open"),
                    "token_id": token_id
                }
            }
        
        except Exception as e:
            # Log error only if not in test environment
            if not frappe.flags.in_test:
                frappe.log_error(f"Form processing error for {self.form_type}: {str(e)}")
            return {
                "success": False,
                "message": _("An error occurred while processing the form"),
                "errors": {"general": [str(e)]}
            }
    
    def handle_file_attachments(self, doc, form_data):
        """
        Handle file attachments for the document
        
        Args:
            doc: Created document
            form_data (dict): Original form data
        """
        from override_project_integration.api.file_handler import AttachmentManager
        
        attachment_manager = AttachmentManager()
        result = attachment_manager.attach_files_to_document(doc, form_data, self.form_type)
        
        if not result["success"] and result["errors"]:
            # Log attachment errors but don't fail the entire form submission
            error_messages = [error["error"] for error in result["errors"]]
            frappe.log_error(
                f"File attachment errors for {doc.doctype} {doc.name}: {'; '.join(error_messages)}",
                "File Attachment Error"
            )
        
        return result


class SmallProjectProcessor(BaseFormProcessor):
    """
    Processor for small-project-register forms
    """
    
    def __init__(self, form_type):
        super().__init__(form_type)
        from override_project_integration.api.field_mapping import FieldMapper, ValidationHelper
        self.field_mapper = FieldMapper(form_type)
        self.validator = ValidationHelper()
    
    def validate_form_data(self, form_data):
        """
        Validate small project registration form data including child tables
        """
        errors = {}
        
        # Required fields validation based on formsConfig.js
        required_fields = [
            ("ownerFullName", "Owner Full Name"),
            ("governorate", "Governorate"),
            ("district", "District"),
            ("neighborhood", "Neighborhood"),
            ("street", "Street"),
            ("age", "Age"),
            ("primaryPhone", "Primary Phone"),
            ("email", "Email"),
            ("projectName", "Project Name"),
            ("projectStatus", "Project Status"),
            ("capital", "Capital"),
            ("workersCount", "Workers Count"),
            ("startDate", "Start Date"),
            ("products", "Products"),
            ("projectDescription", "Project Description")
        ]
        
        # Validate required fields
        for field_name, field_label in required_fields:
            is_valid, error_msg = self.validator.validate_required_field(
                form_data.get(field_name), field_label
            )
            if not is_valid:
                if "field_errors" not in errors:
                    errors["field_errors"] = {}
                errors["field_errors"][field_name] = [error_msg]
        
        # Email validation
        email = form_data.get("email")
        if email:  # Only validate if provided (it's required but might be empty)
            is_valid, error_msg = self.validator.validate_email(email)
            if not is_valid:
                if "field_errors" not in errors:
                    errors["field_errors"] = {}
                errors["field_errors"]["email"] = [error_msg]
        
        # Age validation
        age = form_data.get("age")
        if age:
            is_valid, error_msg = self.validator.validate_age(age, min_age=18, max_age=100)
            if not is_valid:
                if "field_errors" not in errors:
                    errors["field_errors"] = {}
                errors["field_errors"]["age"] = [error_msg]
        
        # Capital validation
        capital = form_data.get("capital")
        if capital:
            is_valid, error_msg, cleaned_value = self.validator.validate_currency(capital)
            if not is_valid:
                if "field_errors" not in errors:
                    errors["field_errors"] = {}
                errors["field_errors"]["capital"] = [error_msg]
        
        # Workers count validation
        workers_count = form_data.get("workersCount")
        if workers_count:
            try:
                workers_int = int(workers_count)
                if workers_int < 0:
                    if "field_errors" not in errors:
                        errors["field_errors"] = {}
                    errors["field_errors"]["workersCount"] = [_("Workers count must be a positive number")]
            except (ValueError, TypeError):
                if "field_errors" not in errors:
                    errors["field_errors"] = {}
                errors["field_errors"]["workersCount"] = [_("Workers count must be a valid number")]
        
        # Phone number validation
        phone = form_data.get("primaryPhone")
        if phone:
            is_valid, error_msg = self.validator.validate_phone(phone)
            if not is_valid:
                if "field_errors" not in errors:
                    errors["field_errors"] = {}
                errors["field_errors"]["primaryPhone"] = [error_msg]
        
        # Project status validation - map to DocType values
        project_status = form_data.get("projectStatus")
        if project_status:
            # Map Arabic values to English DocType values
            status_mapping = {
                "قيد الفكرة": "Open",
                "قيد التنفيذ": "Open", 
                "قائم": "Approved"
            }
            
            if project_status in status_mapping:
                # Update form_data with mapped value for DocType
                form_data["projectStatus"] = status_mapping[project_status]
            elif project_status not in ["Open", "Approved", "Rejected", "Cancelled"]:
                if "field_errors" not in errors:
                    errors["field_errors"] = {}
                errors["field_errors"]["projectStatus"] = [_("Invalid project status. Must be one of: {0}").format(", ".join(["قيد الفكرة", "قيد التنفيذ", "قائم"]))]
        
        # Validate child table data
        child_processor = create_child_table_processor(self.doctype)
        child_tables = child_processor.process_child_tables(form_data)
        
        for table_name, table_data in child_tables.items():
            is_valid, table_errors = child_processor.validate_child_table_data(table_name, table_data)
            if not is_valid:
                if "child_table_errors" not in errors:
                    errors["child_table_errors"] = {}
                errors["child_table_errors"].update(table_errors)
        
        return len(errors) == 0, errors
    
    def map_form_fields(self, form_data):
        """
        Map form fields using the advanced field mapper and child table processor
        
        Args:
            form_data (dict): Form data to map
            
        Returns:
            tuple: (mapped_data, child_tables)
        """
        # Use the advanced field mapper for main fields
        main_data, _ = self.field_mapper.map_form_data(form_data)
        
        # Use child table processor for comprehensive child table handling
        child_processor = create_child_table_processor(self.doctype)
        child_tables = child_processor.process_child_tables(form_data)
        
        return main_data, child_tables
    
    def handle_file_attachments(self, doc, form_data):
        """
        Handle ID card image attachment for small project registration
        
        Args:
            doc: Created Micro Enterprise Request document
            form_data (dict): Original form data
        """
        from override_project_integration.api.file_handler import AttachmentManager
        
        attachment_manager = AttachmentManager()
        result = attachment_manager.attach_files_to_document(doc, form_data, self.form_type)
        
        if result["success"] and result["attached_files"]:
            # Log successful file attachments
            file_count = len(result["attached_files"])
            frappe.msgprint(
                _("Successfully attached {0} file(s) to {1}").format(file_count, doc.name),
                alert=True
            )
        
        return result


class TrainingProgramProcessor(BaseFormProcessor):
    """
    Processor for training-program forms
    """
    
    def validate_form_data(self, form_data):
        """
        Validate training program registration form data
        """
        errors = {}
        
        # Required fields validation
        required_fields = [
            ("fullName", "Full Name"),
            ("phone", "Phone"),
            ("city", "City"),
            ("age", "Age")
        ]
        
        # Validate required fields
        for field_name, field_label in required_fields:
            value = form_data.get(field_name)
            if not value or (isinstance(value, str) and not value.strip()):
                if "field_errors" not in errors:
                    errors["field_errors"] = {}
                errors["field_errors"][field_name] = [_("{0} is required").format(field_label)]
        
        # Age validation
        age = form_data.get("age")
        if age:
            try:
                age_int = int(age)
                if age_int < 16 or age_int > 100:
                    if "field_errors" not in errors:
                        errors["field_errors"] = {}
                    errors["field_errors"]["age"] = [_("Age must be between 16 and 100")]
            except (ValueError, TypeError):
                if "field_errors" not in errors:
                    errors["field_errors"] = {}
                errors["field_errors"]["age"] = [_("Age must be a valid number")]
        
        # Phone validation
        phone = form_data.get("phone")
        if phone:
            # Basic phone validation
            phone_clean = re.sub(r'[^\d+]', '', phone)
            if len(phone_clean) < 9:
                if "field_errors" not in errors:
                    errors["field_errors"] = {}
                errors["field_errors"]["phone"] = [_("Phone number must be at least 9 digits")]
        
        return len(errors) == 0, errors
    
    def map_form_fields(self, form_data):
        """
        Map training program form fields to DocType fields
        """
        mapped_data = {
            "full_name": form_data.get("fullName", ""),
            "phone": form_data.get("phone", ""),
            "city": form_data.get("city", ""),
            "age": form_data.get("age"),
            "reason": form_data.get("reason", ""),
            "status": "Open"
        }
        
        # Clean up empty values
        mapped_data = {k: v for k, v in mapped_data.items() if v is not None and v != ""}
        
        return mapped_data, {}


class VolunteerProgramProcessor(BaseFormProcessor):
    """
    Processor for volunteer-program forms
    """
    
    def validate_form_data(self, form_data):
        """
        Validate volunteer program application form data
        """
        errors = {}
        
        # Required fields validation
        required_fields = [
            ("fullName", "Full Name"),
            ("phone", "Phone"),
            ("city", "City"),
            ("age", "Age"),
            ("favField", "Favorite Field")
        ]
        
        # Validate required fields
        for field_name, field_label in required_fields:
            value = form_data.get(field_name)
            if not value or (isinstance(value, str) and not value.strip()):
                if "field_errors" not in errors:
                    errors["field_errors"] = {}
                errors["field_errors"][field_name] = [_("{0} is required").format(field_label)]
        
        # Age validation
        age = form_data.get("age")
        if age:
            try:
                age_int = int(age)
                if age_int < 16 or age_int > 100:
                    if "field_errors" not in errors:
                        errors["field_errors"] = {}
                    errors["field_errors"]["age"] = [_("Age must be between 16 and 100")]
            except (ValueError, TypeError):
                if "field_errors" not in errors:
                    errors["field_errors"] = {}
                errors["field_errors"]["age"] = [_("Age must be a valid number")]
        
        # Phone validation
        phone = form_data.get("phone")
        if phone:
            # Basic phone validation
            phone_clean = re.sub(r'[^\d+]', '', phone)
            if len(phone_clean) < 9:
                if "field_errors" not in errors:
                    errors["field_errors"] = {}
                errors["field_errors"]["phone"] = [_("Phone number must be at least 9 digits")]
        
        return len(errors) == 0, errors
    
    def map_form_fields(self, form_data):
        """
        Map volunteer program form fields to DocType fields
        """
        mapped_data = {
            "full_name": form_data.get("fullName", ""),
            "phone": form_data.get("phone", ""),
            "city": form_data.get("city", ""),
            "age": form_data.get("age"),
            "favorite_field": form_data.get("favField", ""),
            "summary": form_data.get("summary", ""),
            "status": "Open"
        }
        
        # Clean up empty values
        mapped_data = {k: v for k, v in mapped_data.items() if v is not None and v != ""}
        
        return mapped_data, {}


class TrainingServiceProcessor(BaseFormProcessor):
    """
    Processor for training-service forms with checkbox field processing
    """
    
    def validate_form_data(self, form_data):
        """
        Validate training service request form data
        """
        errors = {}
        
        # Required fields validation
        required_fields = [
            ("fullName", "Full Name"),
            ("phone", "Phone"),
            ("city", "City"),
            ("age", "Age"),
            ("trainingFields", "Training Fields")
        ]
        
        # Validate required fields
        for field_name, field_label in required_fields:
            value = form_data.get(field_name)
            if field_name == "trainingFields":
                # Special validation for checkbox array
                if not value or not isinstance(value, list) or len(value) == 0:
                    if "field_errors" not in errors:
                        errors["field_errors"] = {}
                    errors["field_errors"][field_name] = [_("At least one training field must be selected")]
            else:
                if not value or (isinstance(value, str) and not value.strip()):
                    if "field_errors" not in errors:
                        errors["field_errors"] = {}
                    errors["field_errors"][field_name] = [_("{0} is required").format(field_label)]
        
        # Age validation
        age = form_data.get("age")
        if age:
            try:
                age_int = int(age)
                if age_int < 16 or age_int > 100:
                    if "field_errors" not in errors:
                        errors["field_errors"] = {}
                    errors["field_errors"]["age"] = [_("Age must be between 16 and 100")]
            except (ValueError, TypeError):
                if "field_errors" not in errors:
                    errors["field_errors"] = {}
                errors["field_errors"]["age"] = [_("Age must be a valid number")]
        
        # Phone validation
        phone = form_data.get("phone")
        if phone:
            # Basic phone validation
            phone_clean = re.sub(r'[^\d+]', '', phone)
            if len(phone_clean) < 9:
                if "field_errors" not in errors:
                    errors["field_errors"] = {}
                errors["field_errors"]["phone"] = [_("Phone number must be at least 9 digits")]
        
        # Training fields validation
        training_fields = form_data.get("trainingFields", [])
        if training_fields:
            valid_fields = [
                "تصنيع غذائي",
                "خياطة", 
                "حرف",
                "ريادة أعمال",
                "تدريب مهني ومعرفي لأصحاب المشاريع الصغيرة"
            ]
            
            invalid_fields = [field for field in training_fields if field not in valid_fields]
            if invalid_fields:
                if "field_errors" not in errors:
                    errors["field_errors"] = {}
                errors["field_errors"]["trainingFields"] = [
                    _("Invalid training fields: {0}").format(", ".join(invalid_fields))
                ]
        
        return len(errors) == 0, errors
    
    def map_form_fields(self, form_data):
        """
        Map training service form fields to DocType fields with checkbox processing
        """
        # Process checkbox array into comma-separated string
        training_fields = form_data.get("trainingFields", [])
        training_fields_str = ", ".join(training_fields) if isinstance(training_fields, list) else str(training_fields)
        
        mapped_data = {
            "full_name": form_data.get("fullName", ""),
            "phone": form_data.get("phone", ""),
            "city": form_data.get("city", ""),
            "age": form_data.get("age"),
            "training_fields": training_fields_str,
            "reason": form_data.get("reason", ""),
            "status": "Open"
        }
        
        # Clean up empty values
        mapped_data = {k: v for k, v in mapped_data.items() if v is not None and v != ""}
        
        return mapped_data, {}


class TrainingAdProcessor(BaseFormProcessor):
    """
    Processor for training-ad forms
    """
    
    def validate_form_data(self, form_data):
        """
        Validate training advertisement registration form data
        """
        errors = {}
        
        # Required fields validation
        required_fields = [
            ("fullName", "Full Name"),
            ("phone", "Phone"),
            ("city", "City"),
            ("age", "Age")
        ]
        
        # Validate required fields
        for field_name, field_label in required_fields:
            value = form_data.get(field_name)
            if not value or (isinstance(value, str) and not value.strip()):
                if "field_errors" not in errors:
                    errors["field_errors"] = {}
                errors["field_errors"][field_name] = [_("{0} is required").format(field_label)]
        
        # Age validation
        age = form_data.get("age")
        if age:
            try:
                age_int = int(age)
                if age_int < 16 or age_int > 100:
                    if "field_errors" not in errors:
                        errors["field_errors"] = {}
                    errors["field_errors"]["age"] = [_("Age must be between 16 and 100")]
            except (ValueError, TypeError):
                if "field_errors" not in errors:
                    errors["field_errors"] = {}
                errors["field_errors"]["age"] = [_("Age must be a valid number")]
        
        # Phone validation
        phone = form_data.get("phone")
        if phone:
            # Basic phone validation
            phone_clean = re.sub(r'[^\d+]', '', phone)
            if len(phone_clean) < 9:
                if "field_errors" not in errors:
                    errors["field_errors"] = {}
                errors["field_errors"]["phone"] = [_("Phone number must be at least 9 digits")]
        
        return len(errors) == 0, errors
    
    def map_form_fields(self, form_data):
        """
        Map training advertisement form fields to DocType fields
        """
        mapped_data = {
            "full_name": form_data.get("fullName", ""),
            "phone": form_data.get("phone", ""),
            "city": form_data.get("city", ""),
            "age": form_data.get("age"),
            "reason": form_data.get("reason", ""),
            "status": "Open"
        }
        
        # Clean up empty values
        mapped_data = {k: v for k, v in mapped_data.items() if v is not None and v != ""}
        
        return mapped_data, {}


class BusinessServiceProcessor(BaseFormProcessor):
    """
    Processor for business service forms (promote-project, specs-memo-request, contract-opportunity, contact-form)
    """
    
    def validate_form_data(self, form_data):
        """
        Validate business service form data based on form type
        """
        errors = {}
        
        if self.form_type == "promote-project":
            return self._validate_promote_project(form_data)
        elif self.form_type == "specs-memo-request":
            return self._validate_specs_memo_request(form_data)
        elif self.form_type == "contract-opportunity":
            return self._validate_contract_opportunity(form_data)
        elif self.form_type == "contact-form":
            return self._validate_contact_form(form_data)
        else:
            errors["general"] = [_("Unsupported business service form type: {0}").format(self.form_type)]
            return False, errors
    
    def _validate_promote_project(self, form_data):
        """
        Validate promote-project form data
        """
        errors = {}
        
        # Required fields validation
        required_fields = [
            ("projectName", "Project Name"),
            ("projectDescription", "Project Description")
        ]
        
        # Validate required fields
        for field_name, field_label in required_fields:
            value = form_data.get(field_name)
            if not value or (isinstance(value, str) and not value.strip()):
                if "field_errors" not in errors:
                    errors["field_errors"] = {}
                errors["field_errors"][field_name] = [_("{0} is required").format(field_label)]
        
        # Price validation (optional field)
        price = form_data.get("price")
        if price and price.strip():
            try:
                price_float = float(re.sub(r'[^\d.]', '', price))
                if price_float < 0:
                    if "field_errors" not in errors:
                        errors["field_errors"] = {}
                    errors["field_errors"]["price"] = [_("Price must be a positive number")]
            except (ValueError, TypeError):
                if "field_errors" not in errors:
                    errors["field_errors"] = {}
                errors["field_errors"]["price"] = [_("Price must be a valid number")]
        
        return len(errors) == 0, errors
    
    def _validate_specs_memo_request(self, form_data):
        """
        Validate specs-memo-request form data
        """
        errors = {}
        
        # Required fields validation
        required_fields = [
            ("projectType", "Project Type"),
            ("projectName", "Project Name"),
            ("projectStatus", "Project Status"),
            ("startDate", "Start Date"),
            ("capital", "Capital"),
            ("location", "Location"),
            ("ownerName", "Owner Name"),
            ("gender", "Gender"),
            ("birthDate", "Birth Date"),
            ("educationLevel", "Education Level"),
            ("currentAddress", "Current Address"),
            ("phone", "Phone")
        ]
        
        # Validate required fields
        for field_name, field_label in required_fields:
            value = form_data.get(field_name)
            if not value or (isinstance(value, str) and not value.strip()):
                if "field_errors" not in errors:
                    errors["field_errors"] = {}
                errors["field_errors"][field_name] = [_("{0} is required").format(field_label)]
        
        # Validate project type
        project_type = form_data.get("projectType")
        valid_project_types = ["صغير", "متناهي الصغر", "مشروع صغير قيد التأسيس"]
        if project_type and project_type not in valid_project_types:
            if "field_errors" not in errors:
                errors["field_errors"] = {}
            errors["field_errors"]["projectType"] = [_("Invalid project type. Must be one of: {0}").format(", ".join(valid_project_types))]
        
        # Validate project status
        project_status = form_data.get("projectStatus")
        valid_statuses = ["نشط", "غير نشط"]
        if project_status and project_status not in valid_statuses:
            if "field_errors" not in errors:
                errors["field_errors"] = {}
            errors["field_errors"]["projectStatus"] = [_("Invalid project status. Must be one of: {0}").format(", ".join(valid_statuses))]
        
        # Validate gender
        gender = form_data.get("gender")
        valid_genders = ["ذكر", "أنثى"]
        if gender and gender not in valid_genders:
            if "field_errors" not in errors:
                errors["field_errors"] = {}
            errors["field_errors"]["gender"] = [_("Invalid gender. Must be one of: {0}").format(", ".join(valid_genders))]
        
        # Validate education level
        education_level = form_data.get("educationLevel")
        valid_education_levels = ["مدرسة", "جامعة", "معهد"]
        if education_level and education_level not in valid_education_levels:
            if "field_errors" not in errors:
                errors["field_errors"] = {}
            errors["field_errors"]["educationLevel"] = [_("Invalid education level. Must be one of: {0}").format(", ".join(valid_education_levels))]
        
        # Phone validation
        phone = form_data.get("phone")
        if phone:
            phone_clean = re.sub(r'[^\d+]', '', phone)
            if len(phone_clean) < 9:
                if "field_errors" not in errors:
                    errors["field_errors"] = {}
                errors["field_errors"]["phone"] = [_("Phone number must be at least 9 digits")]
        
        # Capital validation
        capital = form_data.get("capital")
        if capital:
            try:
                capital_float = float(re.sub(r'[^\d.]', '', capital))
                if capital_float < 0:
                    if "field_errors" not in errors:
                        errors["field_errors"] = {}
                    errors["field_errors"]["capital"] = [_("Capital must be a positive number")]
            except (ValueError, TypeError):
                if "field_errors" not in errors:
                    errors["field_errors"] = {}
                errors["field_errors"]["capital"] = [_("Capital must be a valid number")]
        
        return len(errors) == 0, errors
    
    def _validate_contract_opportunity(self, form_data):
        """
        Validate contract-opportunity form data
        """
        errors = {}
        
        # Required fields validation
        required_fields = [
            ("fullName", "Full Name"),
            ("phone", "Phone"),
            ("email", "Email"),
            ("specialization", "Specialization"),
            ("experienceYears", "Experience Years"),
            ("field", "Field"),
            ("cvFile", "CV File")
        ]
        
        # Validate required fields
        for field_name, field_label in required_fields:
            value = form_data.get(field_name)
            if not value or (isinstance(value, str) and not value.strip()):
                if "field_errors" not in errors:
                    errors["field_errors"] = {}
                errors["field_errors"][field_name] = [_("{0} is required").format(field_label)]
        
        # Email validation
        email = form_data.get("email")
        if email:
            email_pattern = r'^[^@]+@[^@]+\.[^@]+$'
            if not re.match(email_pattern, email):
                if "field_errors" not in errors:
                    errors["field_errors"] = {}
                errors["field_errors"]["email"] = [_("Invalid email format")]
        
        # Phone validation
        phone = form_data.get("phone")
        if phone:
            phone_clean = re.sub(r'[^\d+]', '', phone)
            if len(phone_clean) < 9:
                if "field_errors" not in errors:
                    errors["field_errors"] = {}
                errors["field_errors"]["phone"] = [_("Phone number must be at least 9 digits")]
        
        # Experience years validation
        experience_years = form_data.get("experienceYears")
        if experience_years:
            try:
                exp_int = int(experience_years)
                if exp_int < 0 or exp_int > 50:
                    if "field_errors" not in errors:
                        errors["field_errors"] = {}
                    errors["field_errors"]["experienceYears"] = [_("Experience years must be between 0 and 50")]
            except (ValueError, TypeError):
                if "field_errors" not in errors:
                    errors["field_errors"] = {}
                errors["field_errors"]["experienceYears"] = [_("Experience years must be a valid number")]
        
        return len(errors) == 0, errors
    
    def _validate_contact_form(self, form_data):
        """
        Validate contact-form form data
        """
        errors = {}
        
        # Required fields validation
        required_fields = [
            ("fullName", "Full Name"),
            ("phone", "Phone"),
            ("subject", "Subject"),
            ("message", "Message")
        ]
        
        # Validate required fields
        for field_name, field_label in required_fields:
            value = form_data.get(field_name)
            if not value or (isinstance(value, str) and not value.strip()):
                if "field_errors" not in errors:
                    errors["field_errors"] = {}
                errors["field_errors"][field_name] = [_("{0} is required").format(field_label)]
        
        # Email validation (optional field)
        email = form_data.get("email")
        if email and email.strip():
            email_pattern = r'^[^@]+@[^@]+\.[^@]+$'
            if not re.match(email_pattern, email):
                if "field_errors" not in errors:
                    errors["field_errors"] = {}
                errors["field_errors"]["email"] = [_("Invalid email format")]
        
        # Phone validation
        phone = form_data.get("phone")
        if phone:
            phone_clean = re.sub(r'[^\d+]', '', phone)
            if len(phone_clean) < 9:
                if "field_errors" not in errors:
                    errors["field_errors"] = {}
                errors["field_errors"]["phone"] = [_("Phone number must be at least 9 digits")]
        
        return len(errors) == 0, errors
    
    def map_form_fields(self, form_data):
        """
        Map business service form fields to DocType fields based on form type
        """
        if self.form_type == "promote-project":
            return self._map_promote_project_fields(form_data)
        elif self.form_type == "specs-memo-request":
            return self._map_specs_memo_request_fields(form_data)
        elif self.form_type == "contract-opportunity":
            return self._map_contract_opportunity_fields(form_data)
        elif self.form_type == "contact-form":
            return self._map_contact_form_fields(form_data)
        else:
            return {}, {}
    
    def _map_promote_project_fields(self, form_data):
        """
        Map promote-project form fields to DocType fields
        """
        mapped_data = {
            "project_name": form_data.get("projectName", ""),
            "project_description": form_data.get("projectDescription", ""),
            "price": form_data.get("price", ""),
            "status": "Open"
        }
        
        # Clean up empty values
        mapped_data = {k: v for k, v in mapped_data.items() if v is not None and v != ""}
        
        return mapped_data, {}
    
    def _map_specs_memo_request_fields(self, form_data):
        """
        Map specs-memo-request form fields to DocType fields
        """
        mapped_data = {
            "project_type": form_data.get("projectType", ""),
            "project_name": form_data.get("projectName", ""),
            "project_status": form_data.get("projectStatus", ""),
            "start_date": form_data.get("startDate", ""),
            "capital": form_data.get("capital", ""),
            "location": form_data.get("location", ""),
            "owner_name": form_data.get("ownerName", ""),
            "gender": form_data.get("gender", ""),
            "birth_date": form_data.get("birthDate", ""),
            "education_level": form_data.get("educationLevel", ""),
            "qualification": form_data.get("qualification", ""),
            "graduation_year": form_data.get("graduationYear", ""),
            "current_address": form_data.get("currentAddress", ""),
            "phone": form_data.get("phone", ""),
            "relative_phone": form_data.get("relativePhone", ""),
            "status": "Open"
        }
        
        # Clean up empty values
        mapped_data = {k: v for k, v in mapped_data.items() if v is not None and v != ""}
        
        return mapped_data, {}
    
    def _map_contract_opportunity_fields(self, form_data):
        """
        Map contract-opportunity form fields to DocType fields
        """
        mapped_data = {
            "full_name": form_data.get("fullName", ""),
            "phone": form_data.get("phone", ""),
            "email": form_data.get("email", ""),
            "specialization": form_data.get("specialization", ""),
            "experience_years": form_data.get("experienceYears"),
            "field": form_data.get("field", ""),
            "cover_letter": form_data.get("coverLetter", ""),
            "notes": form_data.get("notes", ""),
            "status": "Open"
        }
        
        # Clean up empty values
        mapped_data = {k: v for k, v in mapped_data.items() if v is not None and v != ""}
        
        return mapped_data, {}
    
    def _map_contact_form_fields(self, form_data):
        """
        Map contact-form form fields to DocType fields
        """
        mapped_data = {
            "full_name": form_data.get("fullName", ""),
            "phone": form_data.get("phone", ""),
            "email": form_data.get("email", ""),
            "subject": form_data.get("subject", ""),
            "message": form_data.get("message", ""),
            "status": "Open"
        }
        
        # Clean up empty values
        mapped_data = {k: v for k, v in mapped_data.items() if v is not None and v != ""}
        
        return mapped_data, {}
    
    def handle_file_attachments(self, doc, form_data):
        """
        Handle file attachments for business service forms
        """
        from override_project_integration.api.file_handler import AttachmentManager
        
        attachment_manager = AttachmentManager()
        result = attachment_manager.attach_files_to_document(doc, form_data, self.form_type)
        
        if result["success"] and result["attached_files"]:
            # Log successful file attachments
            file_count = len(result["attached_files"])
            frappe.msgprint(
                _("Successfully attached {0} file(s) to {1}").format(file_count, doc.name),
                alert=True
            )
        
        return result


def get_form_processor(form_type):
    """
    Get appropriate form processor for the given form type
    
    Args:
        form_type (str): Type of form to process
        
    Returns:
        BaseFormProcessor: Form processor instance or None if not supported
    """
    processors = {
        "small-project-register": SmallProjectProcessor,
        "training-program": TrainingProgramProcessor,
        "volunteer-program": VolunteerProgramProcessor,
        "training-service": TrainingServiceProcessor,
        "training-ad": TrainingAdProcessor,
        "promote-project": BusinessServiceProcessor,
        "specs-memo-request": BusinessServiceProcessor,
        "contract-opportunity": BusinessServiceProcessor,
        "contact-form": BusinessServiceProcessor,
    }
    
    processor_class = processors.get(form_type)
    if processor_class:
        return processor_class(form_type)
    
    return None


def get_form_schema(form_type):
    """
    Get form schema for the given form type
    
    Args:
        form_type (str): Type of form
        
    Returns:
        dict: Form schema or None if not found
    """
    # Basic schema structure - will be enhanced in later tasks
    schemas = {
        "small-project-register": {
            "fields": [
                {"name": "ownerFullName", "type": "string", "required": True, "label": "Owner Full Name"},
                {"name": "governorate", "type": "string", "required": True, "label": "Governorate"},
                {"name": "district", "type": "string", "required": True, "label": "District"},
                {"name": "neighborhood", "type": "string", "required": True, "label": "Neighborhood"},
                {"name": "street", "type": "string", "required": True, "label": "Street"},
                {"name": "age", "type": "number", "required": True, "label": "Age", "min": 18, "max": 100},
                {"name": "primaryPhone", "type": "string", "required": True, "label": "Primary Phone"},
                {"name": "secondaryPhone", "type": "string", "required": False, "label": "Secondary Phone"},
                {"name": "email", "type": "email", "required": True, "label": "Email"},
                {"name": "projectName", "type": "string", "required": True, "label": "Project Name"},
                {"name": "projectStatus", "type": "string", "required": True, "label": "Project Status"},
                {"name": "capital", "type": "number", "required": True, "label": "Capital"},
                {"name": "workersCount", "type": "number", "required": True, "label": "Workers Count"},
                {"name": "startDate", "type": "date", "required": True, "label": "Start Date"},
                {"name": "products", "type": "string", "required": True, "label": "Products"},
                {"name": "projectDescription", "type": "text", "required": True, "label": "Project Description"},
                {"name": "idCardImage", "type": "file", "required": False, "label": "ID Card Image", "accept": "image/*"}
            ],
            "validation_rules": {
                "email": {"pattern": "^[^@]+@[^@]+\\.[^@]+$"},
                "age": {"min": 18, "max": 100},
                "primaryPhone": {"pattern": "^[0-9+\\-\\s()]+$"}
            }
        },
        "training-program": {
            "fields": [
                {"name": "fullName", "type": "string", "required": True, "label": "Full Name"},
                {"name": "phone", "type": "string", "required": True, "label": "Phone"},
                {"name": "city", "type": "string", "required": True, "label": "City"},
                {"name": "age", "type": "number", "required": True, "label": "Age", "min": 16, "max": 100},
                {"name": "reason", "type": "text", "required": False, "label": "Reason for Joining"}
            ],
            "validation_rules": {
                "age": {"min": 16, "max": 100},
                "phone": {"pattern": "^[0-9+\\-\\s()]+$"}
            }
        },
        "volunteer-program": {
            "fields": [
                {"name": "fullName", "type": "string", "required": True, "label": "Full Name"},
                {"name": "phone", "type": "string", "required": True, "label": "Phone"},
                {"name": "city", "type": "string", "required": True, "label": "City"},
                {"name": "age", "type": "number", "required": True, "label": "Age", "min": 16, "max": 100},
                {"name": "favField", "type": "string", "required": True, "label": "Favorite Field"},
                {"name": "summary", "type": "text", "required": False, "label": "Experience Summary"}
            ],
            "validation_rules": {
                "age": {"min": 16, "max": 100},
                "phone": {"pattern": "^[0-9+\\-\\s()]+$"}
            }
        },
        "training-service": {
            "fields": [
                {"name": "fullName", "type": "string", "required": True, "label": "Full Name"},
                {"name": "phone", "type": "string", "required": True, "label": "Phone"},
                {"name": "city", "type": "string", "required": True, "label": "City"},
                {"name": "age", "type": "number", "required": True, "label": "Age", "min": 16, "max": 100},
                {
                    "name": "trainingFields", 
                    "type": "array", 
                    "required": True, 
                    "label": "Training Fields",
                    "options": [
                        "تصنيع غذائي",
                        "خياطة",
                        "حرف",
                        "ريادة أعمال",
                        "تدريب مهني ومعرفي لأصحاب المشاريع الصغيرة"
                    ]
                },
                {"name": "reason", "type": "text", "required": False, "label": "Reason for Training"}
            ],
            "validation_rules": {
                "age": {"min": 16, "max": 100},
                "phone": {"pattern": "^[0-9+\\-\\s()]+$"},
                "trainingFields": {"min_items": 1}
            }
        },
        "training-ad": {
            "fields": [
                {"name": "fullName", "type": "string", "required": True, "label": "Full Name"},
                {"name": "phone", "type": "string", "required": True, "label": "Phone"},
                {"name": "city", "type": "string", "required": True, "label": "City"},
                {"name": "age", "type": "number", "required": True, "label": "Age", "min": 16, "max": 100},
                {"name": "reason", "type": "text", "required": False, "label": "Reason for Joining"}
            ],
            "validation_rules": {
                "age": {"min": 16, "max": 100},
                "phone": {"pattern": "^[0-9+\\-\\s()]+$"}
            }
        },
        "promote-project": {
            "fields": [
                {"name": "projectName", "type": "string", "required": True, "label": "Project Name"},
                {"name": "projectDescription", "type": "text", "required": True, "label": "Project Description"},
                {"name": "price", "type": "string", "required": False, "label": "Price"},
                {"name": "files", "type": "file", "required": False, "label": "Product Images", "accept": "image/*", "maxFiles": 3}
            ],
            "validation_rules": {
                "price": {"pattern": "^[0-9.]+$"}
            }
        },
        "specs-memo-request": {
            "fields": [
                {"name": "projectType", "type": "radio", "required": True, "label": "Project Type", "options": ["صغير", "متناهي الصغر", "مشروع صغير قيد التأسيس"]},
                {"name": "projectName", "type": "string", "required": True, "label": "Project Name"},
                {"name": "projectStatus", "type": "radio", "required": True, "label": "Project Status", "options": ["نشط", "غير نشط"]},
                {"name": "startDate", "type": "string", "required": True, "label": "Start Date"},
                {"name": "capital", "type": "string", "required": True, "label": "Capital"},
                {"name": "location", "type": "string", "required": True, "label": "Location"},
                {"name": "ownerName", "type": "string", "required": True, "label": "Owner Name"},
                {"name": "gender", "type": "radio", "required": True, "label": "Gender", "options": ["ذكر", "أنثى"]},
                {"name": "birthDate", "type": "string", "required": True, "label": "Birth Date"},
                {"name": "educationLevel", "type": "radio", "required": True, "label": "Education Level", "options": ["مدرسة", "جامعة", "معهد"]},
                {"name": "qualification", "type": "string", "required": False, "label": "Qualification"},
                {"name": "graduationYear", "type": "string", "required": False, "label": "Graduation Year"},
                {"name": "currentAddress", "type": "string", "required": True, "label": "Current Address"},
                {"name": "phone", "type": "string", "required": True, "label": "Phone"},
                {"name": "relativePhone", "type": "string", "required": False, "label": "Relative Phone"}
            ],
            "validation_rules": {
                "phone": {"pattern": "^[0-9+\\-\\s()]+$"},
                "capital": {"pattern": "^[0-9.]+$"}
            }
        },
        "contract-opportunity": {
            "fields": [
                {"name": "fullName", "type": "string", "required": True, "label": "Full Name"},
                {"name": "phone", "type": "string", "required": True, "label": "Phone"},
                {"name": "email", "type": "email", "required": True, "label": "Email"},
                {"name": "specialization", "type": "string", "required": True, "label": "Specialization"},
                {"name": "experienceYears", "type": "number", "required": True, "label": "Experience Years", "min": 0, "max": 50},
                {"name": "field", "type": "string", "required": True, "label": "Field"},
                {"name": "cvFile", "type": "file", "required": True, "label": "CV File", "accept": ".pdf,.doc,.docx"},
                {"name": "coverLetter", "type": "text", "required": False, "label": "Cover Letter"},
                {"name": "notes", "type": "text", "required": False, "label": "Notes"}
            ],
            "validation_rules": {
                "email": {"pattern": "^[^@]+@[^@]+\\.[^@]+$"},
                "phone": {"pattern": "^[0-9+\\-\\s()]+$"},
                "experienceYears": {"min": 0, "max": 50}
            }
        },
        "contact-form": {
            "fields": [
                {"name": "fullName", "type": "string", "required": True, "label": "Full Name"},
                {"name": "phone", "type": "string", "required": True, "label": "Phone"},
                {"name": "email", "type": "email", "required": False, "label": "Email"},
                {"name": "subject", "type": "string", "required": True, "label": "Subject"},
                {"name": "message", "type": "text", "required": True, "label": "Message"}
            ],
            "validation_rules": {
                "email": {"pattern": "^[^@]+@[^@]+\\.[^@]+$"},
                "phone": {"pattern": "^[0-9+\\-\\s()]+$"}
            }
        }
    }
    
    return schemas.get(form_type)


def get_supported_forms():
    """
    Get list of all supported form types with descriptions
    
    Returns:
        list: List of supported forms with metadata
    """
    supported_forms = []
    
    for form_type, description in FORM_DESCRIPTIONS.items():
        supported_forms.append({
            "form_type": form_type,
            "description": description,
            "doctype": FORM_DOCTYPE_MAPPING.get(form_type),
            "processor_available": get_form_processor(form_type) is not None
        })
    
    return supported_forms