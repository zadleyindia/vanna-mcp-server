#!/usr/bin/env python3
"""
Load initial training data into Vanna
This script loads DDL and metadata from BigQuery tables
"""
import sys
import asyncio
import logging
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from scripts.extract_bigquery_ddl import BigQueryDDLExtractor
from src.config.settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    """Main function to load initial training data"""
    logger.info("=== Vanna MCP Initial Training Data Loader ===\n")
    
    # Validate configuration first
    config_status = settings.validate_config()
    if not config_status['valid']:
        logger.error("Configuration errors found:")
        for error in config_status['errors']:
            logger.error(f"  - {error}")
        sys.exit(1)
    
    logger.info(f"Configuration valid. Using schema: {settings.VANNA_SCHEMA}")
    logger.info(f"BigQuery project: {settings.BIGQUERY_PROJECT}")
    
    # Create DDL extractor
    extractor = BigQueryDDLExtractor()
    
    # Get list of datasets
    datasets = extractor.get_datasets()
    logger.info(f"\nFound {len(datasets)} accessible datasets:")
    for dataset in datasets:
        logger.info(f"  - {dataset}")
    
    # Ask user to confirm
    print("\nThis will extract DDL and metadata from all accessible tables and train Vanna.")
    response = input("Continue? (y/N): ").strip().lower()
    
    if response != 'y':
        logger.info("Cancelled by user")
        return
    
    # Start extraction and training
    logger.info("\nStarting extraction and training...")
    
    # You can limit the number of tables for initial testing
    limit = None
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        limit = int(sys.argv[1])
        logger.info(f"Limiting to {limit} tables for testing")
    
    results = extractor.extract_all_ddl(limit=limit)
    
    logger.info("\n=== Training Complete ===")
    logger.info(f"Total tables processed: {results['total']}")
    logger.info(f"Successfully trained: {results['successful']}")
    logger.info(f"Failed: {results['failed']}")
    
    if results['successful'] > 0:
        logger.info("\n✅ Initial training data loaded successfully!")
        logger.info("You can now use the vanna_ask tool to query your data.")
        
        # Suggest some initial questions
        logger.info("\nTry asking questions like:")
        logger.info("  - 'Show me all tables in the customer dataset'")
        logger.info("  - 'What columns are in the sales table?'")
        logger.info("  - 'List tables with customer data'")
    else:
        logger.error("\n❌ No training data was loaded successfully.")
        logger.error("Please check the errors above and your configuration.")

if __name__ == "__main__":
    asyncio.run(main())