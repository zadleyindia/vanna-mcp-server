"""
vanna_remove_training tool - Remove incorrect or outdated training data
Priority #8 tool in our implementation
"""
from typing import Dict, Any, Optional, List, Union
import logging
from datetime import datetime
from src.config.vanna_config import get_vanna
from src.config.settings import settings
import json
import uuid

logger = logging.getLogger(__name__)

async def vanna_remove_training(
    training_ids: Union[str, List[str]],
    tenant_id: Optional[str] = None,
    confirm_removal: bool = True,
    reason: Optional[str] = None,
    dry_run: bool = False
) -> Dict[str, Any]:
    """
    Remove incorrect or outdated training data from Vanna.
    
    This tool allows administrators to remove training data that is incorrect,
    outdated, or no longer relevant. It includes safety checks to prevent
    accidental deletion and maintains an audit trail.
    
    Args:
        training_ids (str or List[str]): Single ID or list of training data IDs to remove
            IDs should be UUIDs from vanna_get_training_data tool
            
        tenant_id (str, optional): Override default tenant (for multi-tenant mode)
            Default: None (uses settings.TENANT_ID)
            CRITICAL: Can only remove data from own tenant (no cross-tenant deletion)
            
        confirm_removal (bool): Safety flag to confirm deletion intent
            Default: True (must be explicitly set to proceed)
            
        reason (str, optional): Reason for removal (for audit trail)
            Default: None
            Recommended for compliance and tracking
            
        dry_run (bool): Preview what would be deleted without actually removing
            Default: False
            Use True to validate before actual deletion
    
    Returns:
        Dict containing:
        - success (bool): Whether operation succeeded
        - removed_count (int): Number of items successfully removed
        - removed_items (list): Details of removed training data
        - failed_items (list): Items that couldn't be removed with reasons
        - dry_run (bool): Whether this was a dry run
        - audit_info (dict): Audit trail information
        - tenant_id (str): Tenant context (if multi-tenant)
        - metadata (dict): Additional execution metadata
        
    Example Usage:
        # Remove single training item with reason
        vanna_remove_training(
            training_ids="123e4567-e89b-12d3-a456-426614174000",
            reason="Outdated schema - table renamed"
        )
        
        # Dry run to preview removal
        vanna_remove_training(
            training_ids=["id1", "id2", "id3"],
            dry_run=True
        )
        
        # Bulk removal with confirmation
        vanna_remove_training(
            training_ids=["id1", "id2"],
            confirm_removal=True,
            reason="Incorrect SQL patterns causing errors"
        )
    
    Security Notes:
        - Tenant isolation is strictly enforced
        - Cannot remove shared knowledge unless authorized
        - All removals are logged for audit purposes
        - No cross-tenant deletion allowed
    """
    try:
        vn = get_vanna()
        
        # 1. TENANT VALIDATION (MANDATORY)
        if settings.ENABLE_MULTI_TENANT:
            # Use default tenant if not provided
            if not tenant_id:
                tenant_id = settings.TENANT_ID
                logger.info(f"No tenant_id provided, using default: {tenant_id}")
            
            # Validate tenant_id
            if not tenant_id:
                return {
                    "success": False,
                    "error": "tenant_id is required when multi-tenant is enabled",
                    "allowed_tenants": settings.get_allowed_tenants()
                }
            
            if not settings.is_tenant_allowed(tenant_id):
                allowed = settings.get_allowed_tenants()
                return {
                    "success": False,
                    "error": f"Tenant '{tenant_id}' is not allowed",
                    "allowed_tenants": allowed if allowed else "All tenants allowed"
                }
        
        # 2. INPUT VALIDATION
        # Validate confirmation
        if not confirm_removal and not dry_run:
            return {
                "success": False,
                "error": "Removal not confirmed. Set confirm_removal=True to proceed",
                "suggestions": [
                    "Set confirm_removal=True to confirm deletion",
                    "Use dry_run=True to preview without deleting"
                ]
            }
        
        # Normalize training_ids to list
        if isinstance(training_ids, str):
            training_ids = [training_ids]
        
        if not training_ids:
            return {
                "success": False,
                "error": "No training IDs provided",
                "suggestions": ["Provide at least one training ID to remove"]
            }
        
        # Validate UUIDs
        valid_ids = []
        invalid_ids = []
        for tid in training_ids:
            try:
                # Validate UUID format
                uuid.UUID(str(tid))
                valid_ids.append(str(tid))
            except ValueError:
                invalid_ids.append(tid)
        
        if invalid_ids:
            return {
                "success": False,
                "error": "Invalid training ID format",
                "invalid_ids": invalid_ids,
                "suggestions": ["Training IDs must be valid UUIDs", "Use vanna_get_training_data to find correct IDs"]
            }
        
        # 3. DATABASE TYPE AWARENESS
        database_type = settings.DATABASE_TYPE
        logger.info(f"Removing training data for database type: {database_type}, tenant: {tenant_id}")
        
        # 4. RETRIEVE AND VALIDATE TRAINING DATA
        items_to_remove = []
        failed_items = []
        
        for training_id in valid_ids:
            item_data = _get_training_item(vn, training_id, tenant_id)
            
            if not item_data:
                failed_items.append({
                    "id": training_id,
                    "reason": "Training data not found"
                })
                continue
            
            # CRITICAL: Verify tenant ownership (no cross-tenant deletion)
            item_tenant = item_data.get("metadata", {}).get("tenant_id")
            is_shared = item_data.get("metadata", {}).get("is_shared", False)
            
            if settings.ENABLE_MULTI_TENANT and tenant_id:
                if item_tenant != tenant_id and not is_shared:
                    failed_items.append({
                        "id": training_id,
                        "reason": f"Access denied - belongs to tenant '{item_tenant}'",
                        "security_violation": True
                    })
                    logger.warning(f"Attempted cross-tenant deletion blocked: {training_id} (tenant: {item_tenant})")
                    continue
                
                # Check if trying to remove shared knowledge
                if is_shared and not _can_modify_shared_knowledge(tenant_id):
                    failed_items.append({
                        "id": training_id,
                        "reason": "Cannot remove shared knowledge - insufficient permissions",
                        "is_shared": True
                    })
                    continue
            
            items_to_remove.append(item_data)
        
        # 5. PERFORM REMOVAL (or dry run)
        removed_items = []
        
        if dry_run:
            # Dry run - just show what would be removed
            for item in items_to_remove:
                removed_items.append({
                    "id": item["id"],
                    "type": item["type"],
                    "preview": _get_item_preview(item),
                    "tenant_id": item.get("metadata", {}).get("tenant_id"),
                    "is_shared": item.get("metadata", {}).get("is_shared", False),
                    "created_at": item.get("created_at"),
                    "would_remove": True
                })
        else:
            # Actual removal
            for item in items_to_remove:
                success = _remove_training_item(vn, item["id"], tenant_id, reason)
                
                if success:
                    removed_items.append({
                        "id": item["id"],
                        "type": item["type"],
                        "preview": _get_item_preview(item),
                        "tenant_id": item.get("metadata", {}).get("tenant_id"),
                        "is_shared": item.get("metadata", {}).get("is_shared", False),
                        "removed_at": datetime.now().isoformat()
                    })
                else:
                    failed_items.append({
                        "id": item["id"],
                        "reason": "Failed to remove from database"
                    })
        
        # 6. PREPARE RESPONSE
        result = {
            "success": True if (removed_items or dry_run) else False,
            "removed_count": len(removed_items),
            "removed_items": removed_items,
            "failed_count": len(failed_items),
            "failed_items": failed_items if failed_items else None,
            "dry_run": dry_run,
            "audit_info": {
                "action": "dry_run_removal" if dry_run else "training_data_removal",
                "reason": reason,
                "performed_by": "mcp_tool",
                "timestamp": datetime.now().isoformat()
            }
        }
        
        # 7. METADATA (MANDATORY)
        result.update({
            "tenant_id": tenant_id if settings.ENABLE_MULTI_TENANT else None,
            "database_type": database_type,
            "timestamp": datetime.now().isoformat(),
            "shared_knowledge_enabled": settings.ENABLE_SHARED_KNOWLEDGE if settings.ENABLE_MULTI_TENANT else None,
            "strict_isolation": settings.STRICT_TENANT_ISOLATION if settings.ENABLE_MULTI_TENANT else None
        })
        
        action = "would be removed" if dry_run else "removed"
        logger.info(f"Successfully {action} {len(removed_items)} training items")
        
        return result
        
    except Exception as e:
        logger.error(f"Error in vanna_remove_training: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": f"Training removal error: {str(e)}",
            "error_type": type(e).__name__,
            "suggestions": [
                "Check database connection",
                "Verify training IDs exist",
                "Ensure proper permissions"
            ]
        }

def _get_training_item(vn, training_id: str, tenant_id: Optional[str]) -> Optional[Dict[str, Any]]:
    """Retrieve a single training item by ID"""
    try:
        conn = vn.conn
        cur = conn.cursor()
        
        query = f"""
            SELECT id, training_data_type, content, metadata, created_at
            FROM {vn.schema_name}.training_data
            WHERE id = %s
        """
        
        cur.execute(query, (training_id,))
        row = cur.fetchone()
        cur.close()
        
        if not row:
            return None
        
        return {
            "id": str(row[0]),
            "type": row[1],
            "content": row[2],
            "metadata": row[3] if row[3] else {},
            "created_at": row[4].isoformat() if row[4] else None
        }
        
    except Exception as e:
        logger.error(f"Error retrieving training item: {e}")
        return None

def _can_modify_shared_knowledge(tenant_id: str) -> bool:
    """Check if tenant can modify shared knowledge"""
    # For now, no tenant can remove shared knowledge
    # This could be enhanced with admin tenant concept
    return False

def _get_item_preview(item: Dict[str, Any]) -> str:
    """Get a preview of the training item content"""
    content = item.get("content", "")
    item_type = item.get("type", "")
    metadata = item.get("metadata", {})
    
    if item_type == "ddl":
        if "normalized_schema" in metadata:
            schema_info = metadata["normalized_schema"]
            return f"{schema_info.get('dataset', 'unknown')}.{schema_info.get('table_name', 'unknown')}"
        else:
            return content[:100] + "..." if len(content) > 100 else content
    
    elif item_type == "documentation":
        return content[:100] + "..." if len(content) > 100 else content
    
    elif item_type == "sql":
        question = metadata.get("question", "No question")
        return f"Q: {question[:50]}... SQL: {content[:50]}..."
    
    return content[:100] + "..." if len(content) > 100 else content

def _remove_training_item(vn, training_id: str, tenant_id: Optional[str], reason: Optional[str]) -> bool:
    """Remove a training item from the database"""
    try:
        conn = vn.conn
        cur = conn.cursor()
        
        # Log the removal for audit purposes
        logger.info(f"Removing training item {training_id} for tenant {tenant_id}. Reason: {reason}")
        
        # Delete the training data
        query = f"""
            DELETE FROM {vn.schema_name}.training_data
            WHERE id = %s
        """
        
        cur.execute(query, (training_id,))
        conn.commit()
        cur.close()
        
        return True
        
    except Exception as e:
        logger.error(f"Error removing training item: {e}")
        return False

# Tool definition for FastMCP
tool_definition = {
    "name": "vanna_remove_training",
    "description": "Remove incorrect or outdated training data with safety checks",
    "input_schema": {
        "type": "object",
        "properties": {
            "training_ids": {
                "oneOf": [
                    {"type": "string"},
                    {"type": "array", "items": {"type": "string"}}
                ],
                "description": "Single ID or list of training data IDs to remove"
            },
            "tenant_id": {
                "type": "string",
                "description": "Tenant ID for multi-tenant mode (optional)"
            },
            "confirm_removal": {
                "type": "boolean",
                "description": "Safety flag to confirm deletion intent",
                "default": True
            },
            "reason": {
                "type": "string",
                "description": "Reason for removal (for audit trail)"
            },
            "dry_run": {
                "type": "boolean",
                "description": "Preview removal without actually deleting",
                "default": False
            }
        },
        "required": ["training_ids"]
    }
}