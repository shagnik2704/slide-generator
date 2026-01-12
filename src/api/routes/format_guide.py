"""
Formatting Guide for Route Files

This file serves as a template/reference for formatting route files.
DO NOT import or use this file - it's for reference only.
"""
# ============================================================================
# IMPORTS
# ============================================================================
# Standard library imports (alphabetically sorted)
import json
import os
import time
import traceback
from pathlib import Path
from typing import Optional

# Third-party imports (alphabetically sorted)
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Local application imports (grouped by module type)
# - Auth and security
from src.api.auth import get_current_user, TokenData
from src.api.exceptions import ValidationError, InternalServerError

# - Common utilities
from src.api.common.constants import ALLOWED_SCRIPT_EXTENSIONS, MAX_FILE_SIZE_MB
from src.api.common.helpers import (
    ensure_directory_exists,
    generate_project_id,
    get_output_path,
    get_project_root,
    get_upload_path,
)

# - Services
from src.services.my_service import process_data

# ============================================================================
# CONSTANTS AND CONFIGURATION
# ============================================================================
router = APIRouter(tags=["example"])

# Module-level constants
MAX_UPLOAD_SIZE = MAX_FILE_SIZE_MB * 1024 * 1024  # Convert to bytes

# ============================================================================
# MODELS
# ============================================================================
class RequestModel(BaseModel):
    """Request model description."""
    field1: str
    field2: Optional[int] = None


class ResponseModel(BaseModel):
    """Response model description."""
    result: dict
    message: str

# ============================================================================
# ROUTE HANDLERS
# ============================================================================
@router.post("/endpoint")
async def endpoint_handler(
    request: RequestModel,
    current_user: TokenData = Depends(get_current_user)
) -> ResponseModel:
    """
    Endpoint description.
    
    Detailed description of what this endpoint does, its purpose,
    and any important notes about usage.
    
    Args:
        request: Request payload with field descriptions
        current_user: Authenticated user information
    
    Returns:
        ResponseModel: Response containing result and message
    
    Raises:
        ValidationError: If request validation fails
        InternalServerError: If processing fails
    
    Example:
        POST /endpoint
        {
            "field1": "value",
            "field2": 123
        }
    """
    try:
        # Step 1: Validate input (if needed beyond Pydantic)
        if not request.field1:
            raise ValidationError("field1 is required")
        
        # Step 2: Process the request
        result = process_data(request.field1, request.field2)
        
        # Step 3: Return response
        return ResponseModel(
            result=result,
            message="Operation completed successfully"
        )
        
    except ValidationError:
        # Re-raise validation errors
        raise
    except Exception as e:
        # Log and convert to internal server error
        logger.error(f"Error in endpoint_handler: {e}", exc_info=True)
        raise InternalServerError("Failed to process request")


@router.get("/list")
async def list_items(
    current_user: TokenData = Depends(get_current_user)
) -> list[dict]:
    """
    List items endpoint.
    
    Returns a list of items for the authenticated user.
    
    Args:
        current_user: Authenticated user information
    
    Returns:
        List of item dictionaries
    """
    # Implementation
    return []

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================
def _private_helper_function(data: dict) -> bool:
    """
    Private helper function (prefixed with underscore).
    
    Args:
        data: Input data dictionary
    
    Returns:
        True if valid, False otherwise
    """
    return bool(data.get("required_field"))


def validate_input(data: dict) -> None:
    """
    Validate input data.
    
    Args:
        data: Data dictionary to validate
    
    Raises:
        ValidationError: If validation fails
    """
    if not data:
        raise ValidationError("Data is required")
    
    if "required_field" not in data:
        raise ValidationError("required_field is missing")
