"""
Health check and system status endpoints
"""

import frappe
from frappe import _
import datetime
import time
import psutil
import os
from override_project_integration.api.utils import api_response, get_client_ip
from override_project_integration.api.middleware import cors_handler, rate_limit


@frappe.whitelist(allow_guest=True)
@cors_handler
@rate_limit(limit=60, window=60, endpoint_name="health_check")
def health_check():
    """
    Comprehensive health check endpoint with system status
    
    Returns:
        dict: Health status response with detailed system information
    """
    try:
        start_time = time.time()
        
        # Database connectivity check
        db_status = "ok"
        db_response_time = None
        try:
            db_start = time.time()
            frappe.db.sql("SELECT 1")
            db_response_time = round((time.time() - db_start) * 1000, 2)  # ms
        except Exception as e:
            db_status = f"error: {str(e)}"
        
        # Cache connectivity check
        cache_status = "ok"
        cache_response_time = None
        try:
            cache_start = time.time()
            test_key = f"health_check_{int(time.time())}"
            frappe.cache().set(test_key, "ok", expires_in_sec=10)
            cache_result = frappe.cache().get(test_key)
            frappe.cache().delete(test_key)
            cache_response_time = round((time.time() - cache_start) * 1000, 2)  # ms
            if cache_result != "ok":
                cache_status = "error: cache test failed"
        except Exception as e:
            cache_status = f"error: {str(e)}"
        
        # System metrics
        try:
            memory_info = psutil.virtual_memory()
            disk_info = psutil.disk_usage('/')
            cpu_percent = psutil.cpu_percent(interval=0.1)
        except Exception:
            memory_info = disk_info = cpu_percent = None
        
        # Overall health status
        overall_status = "healthy"
        if "error" in db_status or "error" in cache_status:
            overall_status = "degraded"
        
        total_response_time = round((time.time() - start_time) * 1000, 2)
        
        health_data = {
            "status": overall_status,
            "timestamp": datetime.datetime.now().isoformat(),
            "response_time_ms": total_response_time,
            "version": {
                "frappe": frappe.__version__,
                "app": "override_project_integration",
                "app_version": "1.0.0"
            },
            "services": {
                "database": {
                    "status": db_status,
                    "response_time_ms": db_response_time
                },
                "cache": {
                    "status": cache_status,
                    "response_time_ms": cache_response_time
                }
            },
            "system": {
                "uptime": _get_system_uptime(),
                "memory": {
                    "total_gb": round(memory_info.total / (1024**3), 2) if memory_info else None,
                    "available_gb": round(memory_info.available / (1024**3), 2) if memory_info else None,
                    "percent_used": memory_info.percent if memory_info else None
                },
                "disk": {
                    "total_gb": round(disk_info.total / (1024**3), 2) if disk_info else None,
                    "free_gb": round(disk_info.free / (1024**3), 2) if disk_info else None,
                    "percent_used": round((disk_info.used / disk_info.total) * 100, 1) if disk_info else None
                },
                "cpu_percent": cpu_percent
            }
        }
        
        status_code = 200 if overall_status == "healthy" else 503
        
        return api_response(
            success=overall_status == "healthy",
            message=_("System health check completed"),
            data=health_data,
            status_code=status_code
        )
        
    except Exception as e:
        frappe.log_error(f"Health check failed: {str(e)}")
        return api_response(
            success=False,
            message=_("System health check failed"),
            data={
                "status": "error",
                "timestamp": datetime.datetime.now().isoformat(),
                "error": str(e)
            },
            status_code=503
        )


@frappe.whitelist(allow_guest=True)
@cors_handler
@rate_limit(limit=30, window=60, endpoint_name="api_info")
def api_info():
    """
    Get comprehensive API information and available endpoints
    
    Returns:
        dict: API information with detailed endpoint documentation
    """
    try:
        api_data = {
            "name": "Override Project Integration API",
            "version": "1.0.0",
            "description": "REST API for Vue.js/Flutter integration with Frappe",
            "timestamp": datetime.datetime.now().isoformat(),
            "endpoints": {
                "health_monitoring": {
                    "health_check": {
                        "url": "/api/method/override_project_integration.api.health.health_check",
                        "method": "GET",
                        "description": "Comprehensive system health check with metrics",
                        "rate_limit": "60 requests per minute"
                    },
                    "api_metrics": {
                        "url": "/api/method/override_project_integration.api.health.get_api_metrics",
                        "method": "GET", 
                        "description": "API performance metrics and usage statistics",
                        "rate_limit": "30 requests per minute"
                    },
                    "form_submission_logs": {
                        "url": "/api/method/override_project_integration.api.health.get_form_submission_logs",
                        "method": "GET",
                        "description": "Form submission audit logs for debugging",
                        "rate_limit": "20 requests per minute"
                    },
                    "system_diagnostics": {
                        "url": "/api/method/override_project_integration.api.health.get_system_diagnostics",
                        "method": "GET",
                        "description": "Detailed system diagnostics information",
                        "rate_limit": "10 requests per minute"
                    }
                },
                "form_processing": {
                    "submit_form": {
                        "url": "/api/method/override_project_integration.api.forms.submit_form",
                        "method": "POST",
                        "description": "Submit various business forms with file uploads",
                        "rate_limit": "10 requests per minute"
                    }
                },
                "user_management": {
                    "get_user_status": {
                        "url": "/api/method/override_project_integration.api.user_status.get_user_status",
                        "method": "GET",
                        "description": "Get current user status (requires token authentication)",
                        "rate_limit": "20 requests per minute"
                    },
                    "validate_token": {
                        "url": "/api/method/override_project_integration.api.user_status.validate_token",
                        "method": "GET/POST",
                        "description": "Validate a token without creating a session",
                        "rate_limit": "10 requests per minute"
                    },
                    "invalidate_session": {
                        "url": "/api/method/override_project_integration.api.user_status.invalidate_session",
                        "method": "POST",
                        "description": "Invalidate current user session (requires authentication)",
                        "rate_limit": "5 requests per minute"
                    }
                }
            },
            "features": [
                "CORS support with origin validation",
                "Rate limiting per endpoint",
                "Input validation and sanitization",
                "Comprehensive error handling",
                "Security headers (CSP, HSTS, etc.)",
                "Request/response logging",
                "Token-based authentication",
                "Session management",
                "File upload support",
                "Health monitoring",
                "Performance metrics",
                "Audit logging"
            ],
            "authentication": {
                "type": "Token-based",
                "header": "X-Token-ID",
                "description": "Use token_id from Vue.js frontend for authentication"
            },
            "rate_limiting": {
                "enabled": True,
                "default_limit": "60 requests per minute",
                "headers": ["X-Rate-Limit-Limit", "X-Rate-Limit-Remaining", "X-Rate-Limit-Reset"]
            },
            "cors": {
                "enabled": True,
                "allowed_origins": ["localhost", "netlify.app"],
                "allowed_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                "credentials_supported": True
            },
            "supported_form_types": [
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
        }
        
        return api_response(
            success=True,
            message=_("API information retrieved successfully"),
            data=api_data
        )
        
    except Exception as e:
        frappe.log_error(f"Error getting API info: {str(e)}")
        return api_response(
            success=False,
            message=_("Failed to retrieve API information"),
            status_code=500
        )


@frappe.whitelist(allow_guest=True)
@cors_handler
@rate_limit(limit=30, window=60, endpoint_name="api_metrics")
def get_api_metrics():
    """
    Get API performance metrics and usage statistics
    
    Returns:
        dict: API metrics and performance data
    """
    try:
        # Get basic metrics from cache or calculate
        metrics_data = _get_cached_metrics()
        
        return api_response(
            success=True,
            message=_("API metrics retrieved successfully"),
            data=metrics_data
        )
        
    except Exception as e:
        frappe.log_error(f"Error getting API metrics: {str(e)}")
        return api_response(
            success=False,
            message=_("Failed to retrieve API metrics"),
            status_code=500
        )


@frappe.whitelist(allow_guest=True)
@cors_handler
@rate_limit(limit=20, window=60, endpoint_name="form_submission_logs")
def get_form_submission_logs():
    """
    Get form submission audit logs for debugging
    
    Returns:
        dict: Form submission logs and statistics
    """
    try:
        # Get recent form submissions from error logs
        logs_data = _get_form_submission_audit_logs()
        
        return api_response(
            success=True,
            message=_("Form submission logs retrieved successfully"),
            data=logs_data
        )
        
    except Exception as e:
        frappe.log_error(f"Error getting form submission logs: {str(e)}")
        return api_response(
            success=False,
            message=_("Failed to retrieve form submission logs"),
            status_code=500
        )


@frappe.whitelist(allow_guest=True)
@cors_handler
@rate_limit(limit=10, window=60, endpoint_name="system_diagnostics")
def get_system_diagnostics():
    """
    Get detailed system diagnostics information
    
    Returns:
        dict: Comprehensive system diagnostic data
    """
    try:
        diagnostics_data = {
            "timestamp": datetime.datetime.now().isoformat(),
            "system_info": _get_detailed_system_info(),
            "frappe_info": _get_frappe_diagnostics(),
            "app_info": _get_app_diagnostics(),
            "performance": _get_performance_metrics(),
            "configuration": _get_configuration_info()
        }
        
        return api_response(
            success=True,
            message=_("System diagnostics retrieved successfully"),
            data=diagnostics_data
        )
        
    except Exception as e:
        frappe.log_error(f"Error getting system diagnostics: {str(e)}")
        return api_response(
            success=False,
            message=_("Failed to retrieve system diagnostics"),
            status_code=500
        )


def _get_system_uptime():
    """Get system uptime in human readable format"""
    try:
        uptime_seconds = time.time() - psutil.boot_time()
        days = int(uptime_seconds // 86400)
        hours = int((uptime_seconds % 86400) // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        return f"{days}d {hours}h {minutes}m"
    except Exception:
        return "unknown"


def _get_cached_metrics():
    """Get or calculate API metrics"""
    try:
        # Try to get from cache first
        cache_key = "api_metrics_data"
        cached_metrics = frappe.cache().get(cache_key)
        
        if cached_metrics:
            return cached_metrics
        
        # Calculate fresh metrics
        metrics = {
            "timestamp": datetime.datetime.now().isoformat(),
            "endpoints": {
                "total_requests": _get_total_api_requests(),
                "successful_requests": _get_successful_requests(),
                "failed_requests": _get_failed_requests(),
                "average_response_time_ms": _get_average_response_time()
            },
            "forms": {
                "total_submissions": _get_total_form_submissions(),
                "successful_submissions": _get_successful_form_submissions(),
                "failed_submissions": _get_failed_form_submissions()
            },
            "rate_limiting": {
                "active_limits": _get_active_rate_limits(),
                "blocked_requests": _get_blocked_requests()
            },
            "errors": {
                "total_errors": _get_total_errors(),
                "recent_errors": _get_recent_error_count()
            }
        }
        
        # Cache for 5 minutes
        frappe.cache().set(cache_key, metrics, expires_in_sec=300)
        return metrics
        
    except Exception as e:
        return {
            "error": f"Failed to calculate metrics: {str(e)}",
            "timestamp": datetime.datetime.now().isoformat()
        }


def _get_form_submission_audit_logs():
    """Get form submission audit logs"""
    try:
        # Get recent form submission logs from Frappe's error log
        logs = frappe.db.sql("""
            SELECT 
                creation,
                error,
                method,
                SUBSTRING(error, 1, 200) as error_preview
            FROM `tabError Log`
            WHERE error LIKE '%form submission%' 
               OR error LIKE '%submit_form%'
               OR method LIKE '%submit_form%'
            ORDER BY creation DESC
            LIMIT 50
        """, as_dict=True)
        
        # Get form submission statistics
        stats = {
            "total_logs": len(logs),
            "recent_submissions": len([log for log in logs if _is_recent(log.creation)]),
            "error_rate": _calculate_error_rate(logs),
            "most_common_errors": _get_common_errors(logs)
        }
        
        return {
            "statistics": stats,
            "recent_logs": logs[:10],  # Only return 10 most recent
            "timestamp": datetime.datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "error": f"Failed to get audit logs: {str(e)}",
            "timestamp": datetime.datetime.now().isoformat()
        }


def _get_detailed_system_info():
    """Get detailed system information"""
    try:
        return {
            "platform": os.name,
            "python_version": os.sys.version,
            "process_id": os.getpid(),
            "working_directory": os.getcwd(),
            "environment_variables": {
                "PATH": os.environ.get("PATH", "")[:100] + "...",  # Truncate for security
                "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
                "USER": os.environ.get("USER", ""),
                "HOME": os.environ.get("HOME", "")
            },
            "system_load": list(os.getloadavg()) if hasattr(os, 'getloadavg') else None,
            "cpu_count": os.cpu_count(),
            "memory": {
                "total": psutil.virtual_memory().total,
                "available": psutil.virtual_memory().available,
                "percent": psutil.virtual_memory().percent
            } if psutil else None
        }
    except Exception as e:
        return {"error": str(e)}


def _get_frappe_diagnostics():
    """Get Frappe-specific diagnostic information"""
    try:
        return {
            "version": frappe.__version__,
            "site": frappe.local.site if hasattr(frappe.local, 'site') else None,
            "user": frappe.session.user if hasattr(frappe.session, 'user') else None,
            "db_name": frappe.conf.db_name if hasattr(frappe.conf, 'db_name') else None,
            "redis_cache": bool(frappe.cache()),
            "installed_apps": frappe.get_installed_apps(),
            "hooks": list(frappe.get_hooks().keys())[:10]  # First 10 hooks
        }
    except Exception as e:
        return {"error": str(e)}


def _get_app_diagnostics():
    """Get app-specific diagnostic information"""
    try:
        return {
            "name": "override_project_integration",
            "version": "1.0.0",
            "endpoints_count": len(_get_api_endpoints()),
            "middleware_active": True,
            "cors_enabled": True,
            "rate_limiting_enabled": True,
            "security_headers_enabled": True,
            "token_management_enabled": True
        }
    except Exception as e:
        return {"error": str(e)}


def _get_performance_metrics():
    """Get performance-related metrics"""
    try:
        return {
            "database_queries": _get_db_query_count(),
            "cache_hit_rate": _get_cache_hit_rate(),
            "memory_usage_mb": _get_memory_usage(),
            "response_times": {
                "p50": _get_response_time_percentile(50),
                "p95": _get_response_time_percentile(95),
                "p99": _get_response_time_percentile(99)
            }
        }
    except Exception as e:
        return {"error": str(e)}


def _get_configuration_info():
    """Get configuration information (non-sensitive)"""
    try:
        return {
            "cors_origins_count": len(frappe.get_site_config().get("cors_allowed_origins", [])),
            "rate_limits_configured": bool(frappe.get_site_config().get("api_config", {}).get("rate_limits")),
            "file_upload_max_size": frappe.get_site_config().get("api_config", {}).get("file_upload", {}).get("max_file_size", "default"),
            "logging_enabled": frappe.get_site_config().get("api_config", {}).get("logging", {}).get("log_requests", True),
            "security_logging": frappe.get_site_config().get("enable_security_logging", False)
        }
    except Exception as e:
        return {"error": str(e)}


# Helper functions for metrics calculation
def _get_total_api_requests():
    """Get total API requests count"""
    try:
        # This would typically come from a metrics store or logs
        # For now, return a placeholder
        return frappe.cache().get("total_api_requests") or 0
    except:
        return 0


def _get_successful_requests():
    """Get successful requests count"""
    try:
        return frappe.cache().get("successful_requests") or 0
    except:
        return 0


def _get_failed_requests():
    """Get failed requests count"""
    try:
        return frappe.cache().get("failed_requests") or 0
    except:
        return 0


def _get_average_response_time():
    """Get average response time"""
    try:
        return frappe.cache().get("avg_response_time") or 0
    except:
        return 0


def _get_total_form_submissions():
    """Get total form submissions"""
    try:
        # Count from actual DocTypes if they exist
        count = 0
        doctypes = ["Micro Enterprise Request", "Training Registration", "Volunteer Application"]
        for doctype in doctypes:
            if frappe.db.exists("DocType", doctype):
                count += frappe.db.count(doctype)
        return count
    except:
        return 0


def _get_successful_form_submissions():
    """Get successful form submissions"""
    try:
        return frappe.cache().get("successful_form_submissions") or 0
    except:
        return 0


def _get_failed_form_submissions():
    """Get failed form submissions"""
    try:
        return frappe.cache().get("failed_form_submissions") or 0
    except:
        return 0


def _get_active_rate_limits():
    """Get active rate limits count"""
    try:
        # Count active rate limit cache keys
        cache_keys = frappe.cache().get("rate_limit_keys") or []
        return len(cache_keys)
    except:
        return 0


def _get_blocked_requests():
    """Get blocked requests count"""
    try:
        return frappe.cache().get("blocked_requests") or 0
    except:
        return 0


def _get_total_errors():
    """Get total errors count"""
    try:
        return frappe.db.count("Error Log")
    except:
        return 0


def _get_recent_error_count():
    """Get recent errors count (last 24 hours)"""
    try:
        yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
        return frappe.db.count("Error Log", {"creation": [">", yesterday]})
    except:
        return 0


def _is_recent(creation_date, hours=24):
    """Check if a date is within the last N hours"""
    try:
        if isinstance(creation_date, str):
            creation_date = datetime.datetime.fromisoformat(creation_date.replace('Z', '+00:00'))
        cutoff = datetime.datetime.now() - datetime.timedelta(hours=hours)
        return creation_date > cutoff
    except:
        return False


def _calculate_error_rate(logs):
    """Calculate error rate from logs"""
    try:
        if not logs:
            return 0
        error_logs = [log for log in logs if "error" in log.get("error", "").lower()]
        return round((len(error_logs) / len(logs)) * 100, 2)
    except:
        return 0


def _get_common_errors(logs):
    """Get most common error types"""
    try:
        error_counts = {}
        for log in logs:
            error_text = log.get("error", "")
            # Extract first line of error for categorization
            first_line = error_text.split('\n')[0][:100]
            error_counts[first_line] = error_counts.get(first_line, 0) + 1
        
        # Return top 5 most common errors
        return sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    except:
        return []


def _get_api_endpoints():
    """Get list of API endpoints"""
    return [
        "health_check", "get_api_metrics", "get_form_submission_logs",
        "get_system_diagnostics", "submit_form", "get_user_status",
        "validate_token", "invalidate_session"
    ]


def _get_db_query_count():
    """Get database query count (placeholder)"""
    return frappe.cache().get("db_query_count") or 0


def _get_cache_hit_rate():
    """Get cache hit rate (placeholder)"""
    return frappe.cache().get("cache_hit_rate") or 0


def _get_memory_usage():
    """Get current memory usage in MB"""
    try:
        process = psutil.Process(os.getpid())
        return round(process.memory_info().rss / 1024 / 1024, 2)
    except:
        return 0


def _get_response_time_percentile(percentile):
    """Get response time percentile (placeholder)"""
    return frappe.cache().get(f"response_time_p{percentile}") or 0