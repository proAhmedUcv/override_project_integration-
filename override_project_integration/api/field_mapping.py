"""
Field mapping utilities for form processing
"""

import frappe
from frappe import _
from datetime import datetime
import re


class FieldMappingConfig:
    """
    Configuration class for field mappings between forms and DocTypes
    """
    
    # Comprehensive field mappings for all form types
    MAPPINGS = {
        "small-project-register": {
            "doctype": "Micro Enterprise Request",
            "main_fields": {
                # Basic information - mapping to actual DocType fields
                "ownerFullName": "family_name",  # Maps to Full Name field
                "firstName": "first_name",       # Required field
                "middleName": "middle_name",     # Optional field
                "lastName": "last_name",         # Optional field
                "gender": "gender",              # Required field (Link to Gender)
                "age": "age",                    # Will be computed to date_of_birth
                "birthDate": "date_of_birth",    # Required Date field
                "workJoinDate": "date_of_joining", # Optional Date field
                
                # Contact information
                "primaryPhone": "cell_number",   # Mobile field
                "secondaryPhone": "emergency_phone_number", # Emergency phone
                "email": "personal_email",       # Personal Email field
                
                # Emergency contact - fix field mapping
                "emergencyContactName": "person_to_be_contacted",
                "emergencyContactPhone": "emergency_phone_number", 
                "emergencyRelation": "relation",
                
                # Project information - these will be mapped to Project Details child table
                "projectName": "project_name",   # Will go to child table
                "projectDescription": "project_detials", # Will go to child table
                "projectStatus": "status",       # Main document status
                
                # Additional fields
                "familyInfo": "family_background", # Small Text field
                "idNumber": "token_id",          # Token ID field
                
                # Fields that don't have direct mapping but will be handled in child tables
                "governorate": "governorate",    # Will be mapped to Address Details
                "district": "district",          # Will be mapped to Address Details
                "neighborhood": "neighborhood",  # Will be mapped to Address Details
                "street": "street",              # Will be mapped to Address Details
                "capital": "capital",            # Will be mapped to Project Details
                "workersCount": "workersCount",  # Will be mapped to Project Details
                "startDate": "startDate",        # Will be mapped to Project Details
                "products": "products"           # Will be mapped to Project Details
            },
            "computed_fields": {
                "age": {
                    "target": "date_of_birth",
                    "computation": "age_to_birth_date"
                },
                "ownerFullName": {
                    "target": "family_name",
                    "computation": "copy_full_name"
                },
                "firstName": {
                    "target": "first_name",
                    "computation": "extract_first_name_from_full"
                }
            },
            "child_tables": {
                "educations": {
                    "table_field": "education",  # Actual field name in DocType
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
                    "table_field": "project",  # Actual field name in DocType
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
                    "table_field": "productivity",  # Actual field name in DocType
                    "doctype": "Productivity",
                    "fields": {
                        "quantity": "quantity",
                        "unit": "unit"
                    }
                },
                "addresses": {
                    "table_field": "address_details",  # Actual field name in DocType
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
    }
    
    @classmethod
    def get_mapping(cls, form_type):
        """
        Get mapping configuration for a specific form type
        
        Args:
            form_type (str): Form type identifier
            
        Returns:
            dict: Mapping configuration or None if not found
        """
        return cls.MAPPINGS.get(form_type)


class FieldMapper:
    """
    Advanced field mapping utility with support for computed fields and child tables
    """
    
    def __init__(self, form_type):
        self.form_type = form_type
        self.config = FieldMappingConfig.get_mapping(form_type)
        
        if not self.config:
            raise ValueError(f"No mapping configuration found for form type: {form_type}")
    
    def map_form_data(self, form_data):
        """
        Map complete form data to DocType structure
        
        Args:
            form_data (dict): Raw form data from frontend
            
        Returns:
            tuple: (main_data, child_tables_data)
        """
        main_data = {}
        child_tables_data = {}
        
        # Map main fields
        main_data.update(self._map_main_fields(form_data))
        
        # Map computed fields
        main_data.update(self._map_computed_fields(form_data))
        
        # Map child tables
        child_tables_data = self._map_child_tables(form_data)
        
        return main_data, child_tables_data
    
    def _map_main_fields(self, form_data):
        """
        Map direct field mappings
        
        Args:
            form_data (dict): Form data
            
        Returns:
            dict: Mapped main fields
        """
        mapped_data = {}
        main_fields = self.config.get("main_fields", {})
        
        for form_field, doctype_field in main_fields.items():
            if form_field in form_data and form_data[form_field] is not None:
                value = form_data[form_field]
                # Clean string values
                if isinstance(value, str):
                    value = value.strip()
                    if value:  # Only add non-empty strings
                        mapped_data[doctype_field] = value
                else:
                    mapped_data[doctype_field] = value
        
        return mapped_data
    
    def _map_computed_fields(self, form_data):
        """
        Map fields that require computation or have default values
        
        Args:
            form_data (dict): Form data
            
        Returns:
            dict: Mapped computed fields
        """
        mapped_data = {}
        computed_fields = self.config.get("computed_fields", {})
        
        for form_field, field_config in computed_fields.items():
            target_field = field_config["target"]
            
            if "computation" in field_config:
                # Apply computation
                computation_method = field_config["computation"]
                
                # Get the source value
                source_value = form_data.get(form_field)
                
                computed_value = self._apply_computation(
                    computation_method, 
                    source_value
                )
                if computed_value is not None:
                    mapped_data[target_field] = computed_value
            
            elif "default" in field_config:
                # Use default value
                mapped_data[target_field] = field_config["default"]
        
        return mapped_data
    
    def _map_child_tables(self, form_data):
        """
        Map child table data with enhanced support for form data structure
        
        Args:
            form_data (dict): Form data
            
        Returns:
            dict: Child tables data
        """
        child_tables_data = {}
        child_tables_config = self.config.get("child_tables", {})
        
        for table_name, table_config in child_tables_config.items():
            # Handle different types of child table data
            if table_name == "project_data":
                # Create project data from main form fields
                project_data = {}
                table_fields = table_config.get("fields", {})
                
                for form_field, doctype_field in table_fields.items():
                    if form_field in form_data and form_data[form_field] is not None:
                        value = form_data[form_field]
                        if isinstance(value, str):
                            value = value.strip()
                            if value:
                                project_data[doctype_field] = value
                        else:
                            project_data[doctype_field] = value
                
                if project_data:
                    child_tables_data["project"] = [project_data]
                    
            elif table_name == "address_data":
                # Create address data from main form fields
                address_data = {}
                table_fields = table_config.get("fields", {})
                
                for form_field, doctype_field in table_fields.items():
                    if form_field in form_data and form_data[form_field] is not None:
                        value = form_data[form_field]
                        if isinstance(value, str):
                            value = value.strip()
                            if value:
                                address_data[doctype_field] = value
                        else:
                            address_data[doctype_field] = value
                
                if address_data:
                    child_tables_data["address_details"] = [address_data]
                    
            else:
                # Handle array-based child tables (educations, productions, etc.)
                if table_name in form_data and isinstance(form_data[table_name], list):
                    table_data_list = []
                    table_fields = table_config.get("fields", {})
                    
                    for row_data in form_data[table_name]:
                        if isinstance(row_data, dict):
                            mapped_row = {}
                            for form_field, doctype_field in table_fields.items():
                                if form_field in row_data and row_data[form_field] is not None:
                                    value = row_data[form_field]
                                    if isinstance(value, str):
                                        value = value.strip()
                                        if value:
                                            mapped_row[doctype_field] = value
                                    else:
                                        mapped_row[doctype_field] = value
                            
                            if mapped_row:
                                table_data_list.append(mapped_row)
                    
                    if table_data_list:
                        # Use the table_field name from config or fallback to table_name
                        table_field_name = table_config.get("table_field", table_name)
                        child_tables_data[table_field_name] = table_data_list
        
        return child_tables_data
    
    def _apply_computation(self, computation_method, value):
        """
        Apply computation to field value
        
        Args:
            computation_method (str): Name of computation method
            value: Input value
            
        Returns:
            Computed value or None
        """
        if computation_method == "age_to_birth_date":
            return self._age_to_birth_date(value)
        elif computation_method == "extract_first_name":
            return self._extract_first_name(value)
        elif computation_method == "copy_full_name":
            return self._copy_full_name(value)
        elif computation_method == "build_full_name":
            return self._build_full_name(value)
        elif computation_method == "extract_first_name_from_full":
            return self._extract_first_name(value)
        
        return None
    
    def _check_condition(self, condition_method, form_data):
        """
        Check condition for conditional field mapping
        
        Args:
            condition_method (str): Name of condition method
            form_data (dict): Form data
            
        Returns:
            bool: True if condition is met
        """
        if condition_method == "has_education_data":
            return self._has_education_data(form_data)
        
        return True
    
    def _age_to_birth_date(self, age):
        """
        Convert age to approximate birth date
        
        Args:
            age: Age value (string or number)
            
        Returns:
            str: Birth date in YYYY-MM-DD format or None
        """
        if not age:
            return None
        
        try:
            age_int = int(age)
            if 0 < age_int <= 150:  # Reasonable age range
                birth_year = datetime.now().year - age_int
                return f"{birth_year}-01-01"
        except (ValueError, TypeError):
            pass
        
        return None
    
    def _extract_first_name(self, full_name):
        """
        Extract first name from full name
        
        Args:
            full_name (str): Full name string
            
        Returns:
            str: First name or full name if can't split
        """
        if not full_name:
            return None
        
        full_name = str(full_name).strip()
        if not full_name:
            return None
        
        # Split by spaces and take first part
        parts = full_name.split()
        return parts[0] if parts else full_name
    
    def _copy_full_name(self, full_name):
        """
        Copy full name as is
        
        Args:
            full_name (str): Full name string
            
        Returns:
            str: Full name
        """
        if not full_name:
            return None
        
        return str(full_name).strip() or None
    
    def _build_full_name(self, form_data):
        """
        Build full name from firstName, middleName, lastName
        
        Args:
            form_data (dict): Form data containing name fields
            
        Returns:
            str: Full name
        """
        if not isinstance(form_data, dict):
            return None
        
        name_parts = []
        
        # Get name components
        first_name = form_data.get("firstName", "").strip()
        middle_name = form_data.get("middleName", "").strip()
        last_name = form_data.get("lastName", "").strip()
        
        # Build full name
        if first_name:
            name_parts.append(first_name)
        if middle_name:
            name_parts.append(middle_name)
        if last_name:
            name_parts.append(last_name)
        
        return " ".join(name_parts) if name_parts else None
    
    def _has_education_data(self, form_data):
        """
        Check if form has education-related data
        
        Args:
            form_data (dict): Form data
            
        Returns:
            bool: True if education data exists
        """
        education_fields = ["educationPlace", "educationMajor", "graduationYear"]
        return any(
            form_data.get(field) and str(form_data.get(field)).strip()
            for field in education_fields
        )


class ValidationHelper:
    """
    Helper class for field validation
    """
    
    @staticmethod
    def validate_email(email):
        """
        Validate email format
        
        Args:
            email (str): Email to validate
            
        Returns:
            tuple: (is_valid, error_message)
        """
        if not email:
            return True, None  # Email might be optional
        
        email = email.strip()
        if not email:
            return True, None
        
        # Basic email validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if re.match(email_pattern, email):
            return True, None
        
        return False, _("Invalid email format")
    
    @staticmethod
    def validate_phone(phone, min_length=7):
        """
        Validate phone number
        
        Args:
            phone (str): Phone number to validate
            min_length (int): Minimum length required
            
        Returns:
            tuple: (is_valid, error_message)
        """
        if not phone:
            return False, _("Phone number is required")
        
        phone = str(phone).strip()
        if len(phone) < min_length:
            return False, _("Phone number must be at least {0} digits").format(min_length)
        
        # Check if contains only valid phone characters
        phone_pattern = r'^[0-9+\-\s()]+$'
        if not re.match(phone_pattern, phone):
            return False, _("Phone number contains invalid characters")
        
        return True, None
    
    @staticmethod
    def validate_age(age, min_age=18, max_age=100):
        """
        Validate age value
        
        Args:
            age: Age value to validate
            min_age (int): Minimum allowed age
            max_age (int): Maximum allowed age
            
        Returns:
            tuple: (is_valid, error_message)
        """
        if not age:
            return False, _("Age is required")
        
        try:
            age_int = int(age)
            if age_int < min_age or age_int > max_age:
                return False, _("Age must be between {0} and {1}").format(min_age, max_age)
            return True, None
        except (ValueError, TypeError):
            return False, _("Age must be a valid number")
    
    @staticmethod
    def validate_currency(amount, allow_negative=False):
        """
        Validate currency/numeric amount
        
        Args:
            amount: Amount to validate
            allow_negative (bool): Whether negative values are allowed
            
        Returns:
            tuple: (is_valid, error_message, cleaned_value)
        """
        if not amount:
            return False, _("Amount is required"), None
        
        try:
            # Clean the amount (remove commas, spaces)
            amount_str = str(amount).replace(",", "").replace(" ", "").strip()
            amount_float = float(amount_str)
            
            if not allow_negative and amount_float < 0:
                return False, _("Amount must be a positive number"), None
            
            return True, None, amount_float
        except (ValueError, TypeError):
            return False, _("Amount must be a valid number"), None
    
    @staticmethod
    def validate_required_field(value, field_name):
        """
        Validate that a required field has a value
        
        Args:
            value: Field value
            field_name (str): Name of the field for error message
            
        Returns:
            tuple: (is_valid, error_message)
        """
        if value is None or str(value).strip() == "":
            return False, _("{0} is required").format(field_name)
        
        return True, None