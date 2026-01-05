"""
Child table utilities for form processing
Handles population and processing of child table data for various DocTypes
"""

import frappe
from frappe import _
from typing import Dict, List, Any, Optional, Tuple


class ChildTableProcessor:
    """
    Utility class for processing child table data in form submissions
    """
    
    def __init__(self, parent_doctype: str):
        """
        Initialize child table processor
        
        Args:
            parent_doctype (str): Parent DocType name
        """
        self.parent_doctype = parent_doctype
        self.child_table_configs = self._get_child_table_configs()
    
    def _get_child_table_configs(self) -> Dict[str, Dict]:
        """
        Get child table configurations for the parent DocType
        
        Returns:
            Dict: Child table configurations
        """
        configs = {
            "Micro Enterprise Request": {
                "project": {
                    "child_doctype": "Project Details",
                    "required_fields": ["project_name"],
                    "field_mappings": {
                        "projectName": "project_name",
                        "projectDescription": "project_detials",
                        "workersCount": "number_of_workers",
                        "capital": "amount_capital",
                        "products": "project_detials",  # Can be combined with description
                        "startDate": None,  # Not mapped to child table
                        "projectStatus": None  # Not mapped to child table
                    },
                    "field_processors": {
                        "number_of_workers": "process_workers_count",
                        "amount_capital": "process_currency_amount",
                        "project_detials": "process_project_description"
                    }
                },
                "address_details": {
                    "child_doctype": "Address Details",
                    "required_fields": ["city_name"],
                    "field_mappings": {
                        "governorate": "city_name",
                        "district": "directorate_name", 
                        "neighborhood": "district_name",
                        "street": "district_name_info"
                    },
                    "defaults": {
                        "accommodation_type": "Owned"
                    }
                },
                "education": {
                    "child_doctype": "Employee Education",
                    "required_fields": [],  # Optional table
                    "field_mappings": {
                        "qualification": "qualification",
                        "school_univ": "school_univ",
                        "level": "level",
                        "year_of_passing": "year_of_passing",
                        "class_per": "class_per",
                        "maj_opt_subj": "maj_opt_subj"
                    },
                    "field_processors": {
                        "year_of_passing": "process_graduation_year"
                    },
                    "array_source": "educations"  # Process from educations array
                },
                "productivity": {
                    "child_doctype": "Productivity",
                    "required_fields": [],  # Optional table
                    "field_mappings": {
                        "quantity": "quantity",
                        "unit": "unit"
                    },
                    "field_processors": {
                        "quantity": "process_quantity"
                    },
                    "array_source": "productions"  # Process from productions array
                }
            }
        }
        
        return configs.get(self.parent_doctype, {})
    
    def process_child_tables(self, form_data: Dict[str, Any]) -> Dict[str, List[Dict]]:
        """
        Process all child tables for the form data
        
        Args:
            form_data (Dict): Raw form data from frontend
            
        Returns:
            Dict: Processed child table data ready for DocType creation
        """
        processed_tables = {}
        
        for table_name, table_config in self.child_table_configs.items():
            # Check condition if specified
            if "condition" in table_config:
                condition_method = table_config["condition"]
                if not self._check_condition(condition_method, form_data):
                    continue
            
            # Process the table
            table_data = self._process_single_table(table_name, table_config, form_data)
            
            if table_data:
                processed_tables[table_name] = table_data
        
        return processed_tables
    
    def _process_single_table(self, table_name: str, table_config: Dict, form_data: Dict) -> Optional[List[Dict]]:
        """
        Process a single child table
        
        Args:
            table_name (str): Name of the child table
            table_config (Dict): Configuration for the table
            form_data (Dict): Form data
            
        Returns:
            Optional[List[Dict]]: Processed table data or None if no data
        """
        # Check if this table should be processed from an array source
        array_source = table_config.get("array_source")
        if array_source and array_source in form_data:
            # Process from array data (like educations, productions)
            return self._process_array_table(table_name, table_config, form_data[array_source])
        
        # Process as single row table (like project, address_details)
        table_row = {}
        field_mappings = table_config.get("field_mappings", {})
        field_processors = table_config.get("field_processors", {})
        
        # Track fields that map to the same target for special handling
        target_field_sources = {}
        for form_field, doctype_field in field_mappings.items():
            if doctype_field is not None:
                if doctype_field not in target_field_sources:
                    target_field_sources[doctype_field] = []
                target_field_sources[doctype_field].append(form_field)
        
        # Process fields that have processors first (they might need all form data)
        processed_fields = set()
        for doctype_field, processor_method in field_processors.items():
            if doctype_field in target_field_sources:
                # Use the first source field for processing (processor will access all form data)
                first_source_field = target_field_sources[doctype_field][0]
                processed_value = self._apply_field_processor(
                    processor_method, form_data.get(first_source_field), first_source_field, form_data
                )
                if processed_value is not None:
                    table_row[doctype_field] = processed_value
                
                # Mark all source fields as processed
                for source_field in target_field_sources[doctype_field]:
                    processed_fields.add(source_field)
        
        # Process remaining fields
        for form_field, doctype_field in field_mappings.items():
            if doctype_field is None or form_field in processed_fields:
                continue
                
            if form_field in form_data and form_data[form_field] is not None:
                raw_value = form_data[form_field]
                
                # Direct mapping with basic cleaning
                cleaned_value = self._clean_field_value(raw_value)
                if cleaned_value is not None:
                    # Handle multiple fields mapping to same target
                    if len(target_field_sources[doctype_field]) > 1:
                        if doctype_field == "project_detials":
                            existing_value = table_row.get(doctype_field, "")
                            if existing_value:
                                table_row[doctype_field] = f"{existing_value}\n\n{cleaned_value}"
                            else:
                                table_row[doctype_field] = cleaned_value
                        else:
                            table_row[doctype_field] = cleaned_value
                    else:
                        table_row[doctype_field] = cleaned_value
        
        # Add default values
        defaults = table_config.get("defaults", {})
        table_row.update(defaults)
        
        # Check if we have required fields
        required_fields = table_config.get("required_fields", [])
        if required_fields:
            has_required = any(
                table_row.get(field) for field in required_fields
            )
            if not has_required:
                return None
        
        # Return as single-item list if we have data
        return [table_row] if table_row else None
    
    def _process_array_table(self, table_name: str, table_config: Dict, array_data: List[Dict]) -> Optional[List[Dict]]:
        """
        Process child table from array data (like educations, productions)
        
        Args:
            table_name (str): Name of the child table
            table_config (Dict): Configuration for the table
            array_data (List[Dict]): Array of row data
            
        Returns:
            Optional[List[Dict]]: Processed table data or None if no data
        """
        if not array_data or not isinstance(array_data, list):
            return None
        
        processed_rows = []
        field_mappings = table_config.get("field_mappings", {})
        field_processors = table_config.get("field_processors", {})
        defaults = table_config.get("defaults", {})
        
        for row_data in array_data:
            if not isinstance(row_data, dict):
                continue
                
            table_row = {}
            
            # Process fields with processors first
            for doctype_field, processor_method in field_processors.items():
                # Find the source field for this doctype field
                source_field = None
                for form_field, mapped_field in field_mappings.items():
                    if mapped_field == doctype_field:
                        source_field = form_field
                        break
                
                if source_field and source_field in row_data:
                    processed_value = self._apply_field_processor(
                        processor_method, row_data[source_field], source_field, row_data
                    )
                    if processed_value is not None:
                        table_row[doctype_field] = processed_value
            
            # Process remaining fields with direct mapping
            for form_field, doctype_field in field_mappings.items():
                if doctype_field is None or doctype_field in table_row:
                    continue
                    
                if form_field in row_data and row_data[form_field] is not None:
                    cleaned_value = self._clean_field_value(row_data[form_field])
                    if cleaned_value is not None:
                        table_row[doctype_field] = cleaned_value
            
            # Add default values
            table_row.update(defaults)
            
            # Only add row if it has some data
            if table_row:
                processed_rows.append(table_row)
        
        return processed_rows if processed_rows else None
    
    def _apply_field_processor(self, processor_method: str, value: Any, form_field: str, form_data: Dict) -> Any:
        """
        Apply field-specific processing
        
        Args:
            processor_method (str): Name of the processor method
            value (Any): Raw field value
            form_field (str): Original form field name
            form_data (Dict): Complete form data for context
            
        Returns:
            Any: Processed value
        """
        if processor_method == "process_workers_count":
            return self._process_workers_count(value)
        elif processor_method == "process_currency_amount":
            return self._process_currency_amount(value)
        elif processor_method == "process_project_description":
            return self._process_project_description(value, form_data)
        elif processor_method == "process_address_info":
            return self._process_address_info(value, form_field, form_data)
        elif processor_method == "process_graduation_year":
            return self._process_graduation_year(value)
        elif processor_method == "process_quantity":
            return self._process_quantity(value)
        
        return value
    
    def _check_condition(self, condition_method: str, form_data: Dict) -> bool:
        """
        Check condition for conditional child table creation
        
        Args:
            condition_method (str): Name of condition method
            form_data (Dict): Form data
            
        Returns:
            bool: True if condition is met
        """
        if condition_method == "has_education_data":
            return self._has_education_data(form_data)
        
        return True
    
    def _clean_field_value(self, value: Any) -> Any:
        """
        Clean field value for database storage
        
        Args:
            value (Any): Raw value
            
        Returns:
            Any: Cleaned value or None if empty
        """
        if value is None:
            return None
        
        if isinstance(value, str):
            cleaned = value.strip()
            return cleaned if cleaned else None
        
        return value
    
    # Field processors
    def _process_workers_count(self, value: Any) -> Optional[str]:
        """
        Process workers count field
        
        Args:
            value (Any): Raw workers count value
            
        Returns:
            Optional[str]: Processed workers count as string
        """
        if not value:
            return None
        
        try:
            workers_int = int(value)
            if workers_int < 0:
                return "0"
            return str(workers_int)
        except (ValueError, TypeError):
            # Return original value if can't convert
            return str(value).strip() if str(value).strip() else None
    
    def _process_currency_amount(self, value: Any) -> Optional[float]:
        """
        Process currency amount field
        
        Args:
            value (Any): Raw currency value
            
        Returns:
            Optional[float]: Processed currency amount
        """
        if not value:
            return None
        
        try:
            # Clean currency value (remove commas, spaces)
            amount_str = str(value).replace(",", "").replace(" ", "").strip()
            amount_float = float(amount_str)
            return amount_float if amount_float >= 0 else None
        except (ValueError, TypeError):
            return None
    
    def _process_project_description(self, value: Any, form_data: Dict) -> Optional[str]:
        """
        Process project description, potentially combining with products
        
        Args:
            value (Any): Raw description value
            form_data (Dict): Complete form data
            
        Returns:
            Optional[str]: Processed description
        """
        if not value:
            return None
        
        description = str(value).strip()
        
        # If we have products information, we might want to combine it
        products = form_data.get("products")
        if products and str(products).strip():
            products_str = str(products).strip()
            if products_str not in description:
                description = f"{description}\n\nProducts: {products_str}"
        
        return description if description else None
    
    def _process_address_info(self, value: Any, form_field: str, form_data: Dict) -> Optional[str]:
        """
        Process address information, combining multiple address fields into one
        
        Args:
            value (Any): Raw address value
            form_field (str): Original form field name
            form_data (Dict): Complete form data
            
        Returns:
            Optional[str]: Processed address info
        """
        # Combine all address fields into a single comprehensive address
        address_parts = []
        
        # Get all address components
        governorate = form_data.get("governorate")
        district = form_data.get("district")
        neighborhood = form_data.get("neighborhood")
        street = form_data.get("street")
        
        # Add non-empty parts
        if governorate and str(governorate).strip():
            address_parts.append(f"Province: {str(governorate).strip()}")
        
        if district and str(district).strip():
            address_parts.append(f"District: {str(district).strip()}")
        
        if neighborhood and str(neighborhood).strip():
            address_parts.append(f"Neighborhood: {str(neighborhood).strip()}")
        
        if street and str(street).strip():
            address_parts.append(f"Street: {str(street).strip()}")
        
        # Return combined address or None if no parts
        return ", ".join(address_parts) if address_parts else None
    
    def _process_graduation_year(self, value: Any) -> Optional[int]:
        """
        Process graduation year field
        
        Args:
            value (Any): Raw graduation year value
            
        Returns:
            Optional[int]: Processed graduation year
        """
        if not value:
            return None
        
        try:
            year_int = int(value)
            # Validate reasonable year range
            current_year = frappe.utils.now_datetime().year
            if 1950 <= year_int <= current_year + 10:
                return year_int
        except (ValueError, TypeError):
            pass
        
        return None
    
    def _process_quantity(self, value: Any) -> Optional[float]:
        """
        Process quantity field for productivity table
        
        Args:
            value (Any): Raw quantity value
            
        Returns:
            Optional[float]: Processed quantity as float
        """
        if not value:
            return None
        
        try:
            # Convert to float, handling string inputs
            quantity_float = float(str(value).replace(",", "").strip())
            # Ensure positive quantity
            if quantity_float >= 0:
                return quantity_float
        except (ValueError, TypeError):
            pass
        
        return None
    
    def _has_education_data(self, form_data: Dict) -> bool:
        """
        Check if form has education-related data
        
        Args:
            form_data (Dict): Form data
            
        Returns:
            bool: True if education data exists
        """
        education_fields = ["educationPlace", "educationMajor", "graduationYear"]
        return any(
            form_data.get(field) and str(form_data.get(field)).strip()
            for field in education_fields
        )
    
    def validate_child_table_data(self, table_name: str, table_data: List[Dict]) -> Tuple[bool, Dict]:
        """
        Validate child table data before creation
        
        Args:
            table_name (str): Name of the child table
            table_data (List[Dict]): Table data to validate
            
        Returns:
            Tuple[bool, Dict]: (is_valid, errors)
        """
        errors = {}
        
        if not table_data:
            return True, errors
        
        table_config = self.child_table_configs.get(table_name, {})
        required_fields = table_config.get("required_fields", [])
        
        for idx, row in enumerate(table_data):
            row_errors = []
            
            # Check required fields
            for field in required_fields:
                if not row.get(field):
                    row_errors.append(f"Field '{field}' is required")
            
            # Validate specific field types
            if table_name == "project":
                # Validate currency amount
                amount = row.get("amount_capital")
                if amount is not None:
                    try:
                        float(amount)
                    except (ValueError, TypeError):
                        row_errors.append("Capital amount must be a valid number")
                
                # Validate workers count
                workers = row.get("number_of_workers")
                if workers is not None:
                    try:
                        int(workers)
                    except (ValueError, TypeError):
                        row_errors.append("Number of workers must be a valid number")
            
            elif table_name == "education":
                # Validate graduation year
                year = row.get("year_of_passing")
                if year is not None:
                    try:
                        year_int = int(year)
                        current_year = frappe.utils.now_datetime().year
                        if not (1950 <= year_int <= current_year + 10):
                            row_errors.append("Graduation year must be between 1950 and current year")
                    except (ValueError, TypeError):
                        row_errors.append("Graduation year must be a valid number")
            
            if row_errors:
                errors[f"{table_name}_row_{idx}"] = row_errors
        
        return len(errors) == 0, errors


class ChildTableManager:
    """
    Manager class for handling child table operations in document creation
    """
    
    @staticmethod
    def populate_child_tables(doc, child_tables_data: Dict[str, List[Dict]]) -> None:
        """
        Populate child tables in a document
        
        Args:
            doc: Frappe document instance
            child_tables_data (Dict): Child table data to populate
        """
        for table_name, table_rows in child_tables_data.items():
            if not table_rows:
                continue
            
            # Clear existing rows if any
            doc.set(table_name, [])
            
            # Add new rows
            for row_data in table_rows:
                doc.append(table_name, row_data)
    
    @staticmethod
    def update_child_tables(doc, child_tables_data: Dict[str, List[Dict]]) -> None:
        """
        Update child tables in an existing document
        
        Args:
            doc: Frappe document instance
            child_tables_data (Dict): New child table data
        """
        # For now, we'll replace all child table data
        # In the future, this could be enhanced to merge/update existing rows
        ChildTableManager.populate_child_tables(doc, child_tables_data)
    
    @staticmethod
    def get_child_table_data(doc, table_names: List[str] = None) -> Dict[str, List[Dict]]:
        """
        Extract child table data from a document
        
        Args:
            doc: Frappe document instance
            table_names (List[str]): Specific table names to extract, or None for all
            
        Returns:
            Dict: Child table data
        """
        child_data = {}
        
        # Get all child table fields if no specific names provided
        if table_names is None:
            meta = frappe.get_meta(doc.doctype)
            table_names = [
                field.fieldname for field in meta.fields 
                if field.fieldtype == "Table"
            ]
        
        for table_name in table_names:
            table_data = doc.get(table_name, [])
            if table_data:
                # Convert to dict format
                child_data[table_name] = [
                    {key: value for key, value in row.as_dict().items() 
                     if not key.startswith('_')}
                    for row in table_data
                ]
        
        return child_data


def create_child_table_processor(parent_doctype: str) -> ChildTableProcessor:
    """
    Factory function to create child table processor
    
    Args:
        parent_doctype (str): Parent DocType name
        
    Returns:
        ChildTableProcessor: Configured processor instance
    """
    return ChildTableProcessor(parent_doctype)


def process_form_child_tables(parent_doctype: str, form_data: Dict[str, Any]) -> Tuple[Dict[str, List[Dict]], Dict]:
    """
    Convenience function to process child tables for form data
    
    Args:
        parent_doctype (str): Parent DocType name
        form_data (Dict): Form data
        
    Returns:
        Tuple: (processed_child_tables, validation_errors)
    """
    processor = create_child_table_processor(parent_doctype)
    child_tables = processor.process_child_tables(form_data)
    
    # Validate all child tables
    all_errors = {}
    for table_name, table_data in child_tables.items():
        is_valid, errors = processor.validate_child_table_data(table_name, table_data)
        if not is_valid:
            all_errors.update(errors)
    
    return child_tables, all_errors