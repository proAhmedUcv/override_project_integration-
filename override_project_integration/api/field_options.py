"""
API endpoints for fetching field options from DocTypes
"""

import frappe
from frappe import _
from override_project_integration.api.utils import api_response, log_api_request
from override_project_integration.api.middleware import cors_handler, rate_limit
from override_project_integration.api.errors import handle_api_error


@frappe.whitelist(allow_guest=True)
@cors_handler
@rate_limit(endpoint_name="get_field_options")
@handle_api_error
def get_field_options():
    """
    Get field options for Link fields in DocTypes
    
    Returns:
        dict: Field options for different DocTypes
    """
    # Handle preflight requests
    if frappe.request.method == "OPTIONS":
        from override_project_integration.api.cors_fix import handle_preflight_request
        return handle_preflight_request()
    
    # Apply CORS headers
    from override_project_integration.api.cors_fix import apply_cors_headers
    apply_cors_headers()
    
    try:
        # Log the request
        log_api_request(
            endpoint="get_field_options",
            method="GET",
            data={}
        )
        
        # Get field options for different DocTypes
        field_options = {}
        
        # Gender options
        gender_options = _get_gender_options()
        if gender_options:
            field_options["gender"] = gender_options
        
        # Enterprise Type options
        enterprise_type_options = _get_enterprise_type_options()
        if enterprise_type_options:
            field_options["enterprise_type"] = enterprise_type_options
        
        # UOM (Unit of Measure) options for productivity table
        uom_options = _get_uom_options()
        if uom_options:
            field_options["unit"] = uom_options
        
        # Salutation options
        salutation_options = _get_salutation_options()
        if salutation_options:
            field_options["salutation"] = salutation_options
        
        # Address Details Link field options
        city_options = _get_city_options()
        field_options["city_name"] = city_options  # Always include, even if empty
        
        directorate_options = _get_directorate_options()
        field_options["directorate_name"] = directorate_options  # Always include, even if empty
        
        districts_options = _get_districts_options()
        field_options["district_name"] = districts_options  # Always include, even if empty
        
        village_options = _get_village_options()
        field_options["village_name"] = village_options  # Always include, even if empty
        
        # Project Details Link field options
        sector_options = _get_sector_options()
        field_options["sector_name"] = sector_options  # Always include, even if empty
        
        sector_type_options = _get_sector_type_options()
        field_options["sector_type_name"] = sector_type_options  # Always include, even if empty
        
        sector_type_details_options = _get_sector_type_details_options()
        field_options["sector_type_details_name"] = sector_type_details_options  # Always include, even if empty
        
        return api_response(
            success=True,
            message=_("Field options retrieved successfully"),
            data=field_options,
            status_code=200
        )
        
    except Exception as e:
        frappe.log_error(f"Error fetching field options: {str(e)}", "Field Options API")
        return api_response(
            success=False,
            message=_("Failed to fetch field options"),
            status_code=500
        )


def _get_gender_options():
    """
    Get Gender options with Arabic to English mapping
    
    Returns:
        list: Gender options with mapping
    """
    try:
        # Check if Gender DocType exists
        if not frappe.db.exists("DocType", "Gender"):
            # Return default options if DocType doesn't exist
            return [
                {"label": "ذكر", "value": "Male", "arabic": "ذكر", "english": "Male"},
                {"label": "أنثى", "value": "Female", "arabic": "أنثى", "english": "Female"}
            ]
        
        # Get Gender records from database
        genders = frappe.get_all("Gender", fields=["name", "gender"])
        
        # Map to Arabic labels
        gender_mapping = {
            "Male": "ذكر",
            "Female": "أنثى"
        }
        
        options = []
        for gender in genders:
            arabic_label = gender_mapping.get(gender.name, gender.name)
            options.append({
                "label": arabic_label,
                "value": gender.name,
                "arabic": arabic_label,
                "english": gender.name
            })
        
        return options
        
    except Exception as e:
        frappe.log_error(f"Error fetching gender options: {str(e)}")
        # Return default options on error
        return [
            {"label": "ذكر", "value": "Male", "arabic": "ذكر", "english": "Male"},
            {"label": "أنثى", "value": "Female", "arabic": "أنثى", "english": "Female"}
        ]


def _get_enterprise_type_options():
    """
    Get Enterprise Type options
    
    Returns:
        list: Enterprise Type options
    """
    try:
        # Check if Enterprise Type DocType exists
        if not frappe.db.exists("DocType", "Enterprise Type"):
            return []
        
        # Get Enterprise Type records
        enterprise_types = frappe.get_all("Enterprise Type", fields=["name", "type_name"])
        
        options = []
        for etype in enterprise_types:
            options.append({
                "label": etype.get("type_name") or etype.name,
                "value": etype.name
            })
        
        return options
        
    except Exception as e:
        frappe.log_error(f"Error fetching enterprise type options: {str(e)}")
        return []


def _get_uom_options():
    """
    Get UOM (Unit of Measure) options for productivity table
    
    Returns:
        list: UOM options
    """
    try:
        # Check if UOM DocType exists
        if not frappe.db.exists("DocType", "UOM"):
            # Return default options if DocType doesn't exist
            return [
                {"label": "كيلوجرام", "value": "Kg"},
                {"label": "صندوق", "value": "Box"},
                {"label": "قطعة", "value": "Nos"},
                {"label": "متر", "value": "Meter"},
                {"label": "لتر", "value": "Litre"}
            ]
        
        # Get UOM records from database
        uoms = frappe.get_all("UOM", fields=["name", "uom_name"], limit=50)
        
        # Arabic mapping for common UOMs
        uom_mapping = {
            "Kg": "كيلوجرام",
            "Box": "صندوق", 
            "Nos": "قطعة",
            "Meter": "متر",
            "Litre": "لتر",
            "Gram": "جرام",
            "Ton": "طن"
        }
        
        options = []
        for uom in uoms:
            arabic_label = uom_mapping.get(uom.name, uom.get("uom_name") or uom.name)
            options.append({
                "label": arabic_label,
                "value": uom.name
            })
        
        return options
        
    except Exception as e:
        frappe.log_error(f"Error fetching UOM options: {str(e)}")
        # Return default options on error
        return [
            {"label": "كيلوجرام", "value": "Kg"},
            {"label": "صندوق", "value": "Box"},
            {"label": "قطعة", "value": "Nos"}
        ]


def _get_salutation_options():
    """
    Get Salutation options
    
    Returns:
        list: Salutation options
    """
    try:
        # Check if Salutation DocType exists
        if not frappe.db.exists("DocType", "Salutation"):
            return []
        
        # Get Salutation records
        salutations = frappe.get_all("Salutation", fields=["name", "salutation"])
        
        # Arabic mapping for salutations
        salutation_mapping = {
            "Mr": "السيد",
            "Ms": "الآنسة", 
            "Mrs": "السيدة",
            "Dr": "الدكتور"
        }
        
        options = []
        for salutation in salutations:
            arabic_label = salutation_mapping.get(salutation.name, salutation.name)
            options.append({
                "label": arabic_label,
                "value": salutation.name
            })
        
        return options
        
    except Exception as e:
        frappe.log_error(f"Error fetching salutation options: {str(e)}")
        return []


def _get_city_options():
    """
    Get City options for address details
    
    Returns:
        list: City options
    """
    try:
        # Check if City DocType exists
        if not frappe.db.exists("DocType", "City"):
            # Return default Yemen governorates if DocType doesn't exist
            return [
                {"label": "أمانة العاصمة", "value": "Amanat Al Asimah"},
                {"label": "صنعاء", "value": "Sana'a"},
                {"label": "عدن", "value": "Aden"},
                {"label": "تعز", "value": "Taiz"},
                {"label": "الحديدة", "value": "Al Hudaydah"},
                {"label": "إب", "value": "Ibb"},
                {"label": "ذمار", "value": "Dhamar"},
                {"label": "حضرموت", "value": "Hadramaut"}
            ]
        
        # Get City records
        cities = frappe.get_all("City", fields=["name", "city_name"], limit=100)
        
        options = []
        for city in cities:
            options.append({
                "label": city.get("city_name") or city.name,
                "value": city.name
            })
        
        return options
        
    except Exception as e:
        frappe.log_error(f"Error fetching city options: {str(e)}")
        # Return default options on error
        return [
            {"label": "أمانة العاصمة", "value": "Amanat Al Asimah"},
            {"label": "صنعاء", "value": "Sana'a"},
            {"label": "عدن", "value": "Aden"},
            {"label": "تعز", "value": "Taiz"}
        ]


def _get_directorate_options():
    """
    Get Directorate options for address details
    
    Returns:
        list: Directorate options
    """
    try:
        # Check if Directorate DocType exists
        if not frappe.db.exists("DocType", "Directorate"):
            return []
        
        # Get Directorate records
        directorates = frappe.get_all("Directorate", fields=["name", "directorate_name"], limit=100)
        
        options = []
        for directorate in directorates:
            options.append({
                "label": directorate.get("directorate_name") or directorate.name,
                "value": directorate.name
            })
        
        return options
        
    except Exception as e:
        frappe.log_error(f"Error fetching directorate options: {str(e)}")
        return []


def _get_districts_options():
    """
    Get Districts options for address details
    
    Returns:
        list: Districts options
    """
    try:
        # Check if Districts DocType exists
        if not frappe.db.exists("DocType", "Districts"):
            # Return default districts if DocType doesn't exist
            return [
                {"label": "السبعين", "value": "As Sab'een"},
                {"label": "الثورة", "value": "Ath Thawrah"},
                {"label": "شعوب", "value": "Shu'aub"},
                {"label": "الوحدة", "value": "Al Wahda"},
                {"label": "معين", "value": "Ma'een"},
                {"label": "الصافية", "value": "As Safiyah"}
            ]
        
        # Get Districts records
        districts = frappe.get_all("Districts", fields=["name", "district_name"], limit=100)
        
        options = []
        for district in districts:
            options.append({
                "label": district.get("district_name") or district.name,
                "value": district.name
            })
        
        return options
        
    except Exception as e:
        frappe.log_error(f"Error fetching districts options: {str(e)}")
        # Return default options on error
        return [
            {"label": "السبعين", "value": "As Sab'een"},
            {"label": "الثورة", "value": "Ath Thawrah"},
            {"label": "شعوب", "value": "Shu'aub"},
            {"label": "الوحدة", "value": "Al Wahda"}
        ]


def _get_village_options():
    """
    Get Village options for address details
    
    Returns:
        list: Village options
    """
    try:
        # Check if Village DocType exists
        if not frappe.db.exists("DocType", "Village"):
            # Return default villages/neighborhoods if DocType doesn't exist
            return [
                {"label": "حي السبعين", "value": "As Sab'een District"},
                {"label": "حي الثورة", "value": "Ath Thawrah District"},
                {"label": "حي شعوب", "value": "Shu'aub District"},
                {"label": "حي الوحدة", "value": "Al Wahda District"},
                {"label": "حي معين", "value": "Ma'een District"},
                {"label": "حي الصافية", "value": "As Safiyah District"}
            ]
        
        # Get Village records
        villages = frappe.get_all("Village", fields=["name", "village_name"], limit=100)
        
        options = []
        for village in villages:
            options.append({
                "label": village.get("village_name") or village.name,
                "value": village.name
            })
        
        return options
        
    except Exception as e:
        frappe.log_error(f"Error fetching village options: {str(e)}")
        # Return default options on error
        return [
            {"label": "حي السبعين", "value": "As Sab'een District"},
            {"label": "حي الثورة", "value": "Ath Thawrah District"},
            {"label": "حي شعوب", "value": "Shu'aub District"}
        ]


def _get_sector_options():
    """
    Get Sector options for project details
    
    Returns:
        list: Sector options
    """
    try:
        # Check if Sector DocType exists
        if not frappe.db.exists("DocType", "Sector"):
            return []
        
        # Get Sector records
        sectors = frappe.get_all("Sector", fields=["name", "sector_name"], limit=100)
        
        options = []
        for sector in sectors:
            options.append({
                "label": sector.get("sector_name") or sector.name,
                "value": sector.name
            })
        
        return options
        
    except Exception as e:
        frappe.log_error(f"Error fetching sector options: {str(e)}")
        return []


def _get_sector_type_options():
    """
    Get Sector Type options for project details
    
    Returns:
        list: Sector Type options
    """
    try:
        # Check if Sector Type DocType exists
        if not frappe.db.exists("DocType", "Sector Type"):
            # Return default sector types if DocType doesn't exist
            return [
                {"label": "صناعة غذائية", "value": "Food Industry"},
                {"label": "صناعة نسيجية", "value": "Textile Industry"},
                {"label": "صناعة كيميائية", "value": "Chemical Industry"},
                {"label": "تجارة تجزئة", "value": "Retail Trade"},
                {"label": "تجارة جملة", "value": "Wholesale Trade"},
                {"label": "خدمات مالية", "value": "Financial Services"},
                {"label": "تكنولوجيا المعلومات", "value": "Information Technology"}
            ]
        
        # Get Sector Type records
        sector_types = frappe.get_all("Sector Type", fields=["name", "sector_type_name"], limit=100)
        
        options = []
        for sector_type in sector_types:
            options.append({
                "label": sector_type.get("sector_type_name") or sector_type.name,
                "value": sector_type.name
            })
        
        return options
        
    except Exception as e:
        frappe.log_error(f"Error fetching sector type options: {str(e)}")
        # Return default options on error
        return [
            {"label": "صناعة غذائية", "value": "Food Industry"},
            {"label": "صناعة نسيجية", "value": "Textile Industry"},
            {"label": "تجارة تجزئة", "value": "Retail Trade"}
        ]


def _get_sector_type_details_options():
    """
    Get Sector Type Details options for project details
    
    Returns:
        list: Sector Type Details options
    """
    try:
        # Check if Sector Type Details DocType exists
        if not frappe.db.exists("DocType", "Sector Type Details"):
            # Return default sector type details if DocType doesn't exist
            return [
                {"label": "إنتاج المخبوزات", "value": "Bakery Production"},
                {"label": "تصنيع الألبان", "value": "Dairy Manufacturing"},
                {"label": "تعبئة وتغليف", "value": "Packaging"},
                {"label": "خياطة الملابس", "value": "Clothing Manufacturing"},
                {"label": "نسج السجاد", "value": "Carpet Weaving"},
                {"label": "تجارة المواد الغذائية", "value": "Food Trade"},
                {"label": "تجارة الإلكترونيات", "value": "Electronics Trade"}
            ]
        
        # Get Sector Type Details records
        sector_type_details = frappe.get_all("Sector Type Details", fields=["name", "sector_type_details_name"], limit=100)
        
        options = []
        for detail in sector_type_details:
            options.append({
                "label": detail.get("sector_type_details_name") or detail.name,
                "value": detail.name
            })
        
        return options
        
    except Exception as e:
        frappe.log_error(f"Error fetching sector type details options: {str(e)}")
        # Return default options on error
        return [
            {"label": "إنتاج المخبوزات", "value": "Bakery Production"},
            {"label": "تصنيع الألبان", "value": "Dairy Manufacturing"},
            {"label": "تعبئة وتغليف", "value": "Packaging"}
        ]


@frappe.whitelist(allow_guest=True)
@cors_handler
@rate_limit(endpoint_name="get_doctype_schema")
@handle_api_error
def get_doctype_schema():
    """
    Get DocType schema information for form generation
    
    Returns:
        dict: DocType schema with field information
    """
    # Handle preflight requests
    if frappe.request.method == "OPTIONS":
        from override_project_integration.api.cors_fix import handle_preflight_request
        return handle_preflight_request()
    
    # Apply CORS headers
    from override_project_integration.api.cors_fix import apply_cors_headers
    apply_cors_headers()
    
    try:
        doctype = frappe.local.form_dict.get("doctype", "Micro Enterprise Request")
        
        # Log the request
        log_api_request(
            endpoint="get_doctype_schema",
            method="GET",
            data={"doctype": doctype}
        )
        
        # Check if DocType exists
        if not frappe.db.exists("DocType", doctype):
            return api_response(
                success=False,
                message=_("DocType not found: {0}").format(doctype),
                status_code=404
            )
        
        # Get DocType meta
        try:
            meta = frappe.get_meta(doctype)
        except Exception as e:
            frappe.log_error(f"Error getting meta for {doctype}: {str(e)}")
            return api_response(
                success=False,
                message=_("Failed to get DocType metadata: {0}").format(str(e)),
                status_code=500
            )
        
        # Extract field information
        fields_info = {}
        link_fields = {}
        
        for field in meta.fields:
            try:
                field_info = {
                    "fieldtype": field.fieldtype,
                    "label": field.label,
                    "mandatory": field.mandatory,
                    "options": field.options
                }
                
                fields_info[field.fieldname] = field_info
                
                # Collect Link fields for option fetching
                if field.fieldtype == "Link" and field.options:
                    link_fields[field.fieldname] = field.options
            except Exception as e:
                # Skip problematic fields but continue processing
                frappe.log_error(f"Error processing field {field.fieldname}: {str(e)}")
                continue
        
        return api_response(
            success=True,
            message=_("DocType schema retrieved successfully"),
            data={
                "doctype": doctype,
                "fields": fields_info,
                "link_fields": link_fields
            },
            status_code=200
        )
        
    except Exception as e:
        frappe.log_error(f"Error fetching DocType schema: {str(e)}", "DocType Schema API")
        return api_response(
            success=False,
            message=_("Failed to fetch DocType schema: {0}").format(str(e)),
            status_code=500
        )