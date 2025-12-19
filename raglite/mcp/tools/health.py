"""Health MCP tools."""
import json

from raglite.main import mcp
from raglite.shared.logging import get_logger

logger = get_logger(__name__)

@mcp.tool()
async def check_database_health() -> str:
    """Check data synchronization between Qdrant and PostgreSQL.
    Validates that all documents ingested into Qdrant also have their table data
    stored in PostgreSQL. Detects data drift caused by:
    - Snapshot restorations without PostgreSQL sync
    - Table extraction failures during ingestion
    - Partial ingestion runs
    Returns a detailed integrity report with:
    - Document counts per database
    - List of any missing documents
    - Actionable recommendations to fix drift
    Example:
        check_database_health()
        -> {"is_synchronized": false, "missing_in_postgresql": ["2024-05 Report.pdf", ...]}
    Returns:
        JSON string with DataIntegrityResult containing sync status and recommendations
    """
    from raglite.shared.validation import check_data_integrity
    logger.info("Running database health check")
    try:
        result = await check_data_integrity()
        if result.is_synchronized:
            logger.info( "Database health check passed", extra={ "qdrant_docs": result.qdrant.documents, "postgresql_docs": result.postgresql.documents, }, )
        else:
            logger.warning( "Database health check found data drift", extra={ "qdrant_docs": result.qdrant.documents, "postgresql_docs": result.postgresql.documents, "missing_in_postgresql": len(result.missing_in_postgresql), "missing_in_qdrant": len(result.missing_in_qdrant), }, )
        return result.model_dump_json(indent=2)
    except Exception as e:
        logger.error(f"Database health check failed: {e}", exc_info=True)
        return json.dumps(
            {
                "error": f"Health check failed: {e}",
                "is_synchronized": False,
                "recommendations": ["Check database connectivity"],
            },
            indent=2,
        )
