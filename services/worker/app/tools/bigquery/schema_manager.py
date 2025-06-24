"""Schema management for BigQuery tables and datasets."""

from typing import Any, Dict, List, Optional, Set
import json
import structlog
from dataclasses import dataclass
from google.cloud import bigquery
from google.api_core.exceptions import GoogleAPIError

from .client import BigQueryClient


@dataclass
class TableSchema:
    """Represents a BigQuery table schema."""
    dataset_id: str
    table_id: str
    project_id: str
    description: Optional[str]
    fields: List[Dict[str, Any]]
    created: Optional[str]
    modified: Optional[str]
    num_rows: Optional[int]
    num_bytes: Optional[int]
    
    def get_field_names(self) -> List[str]:
        """Get list of field names.
        
        Returns:
            List of field names
        """
        return [field["name"] for field in self.fields]
    
    def get_field_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get field definition by name.
        
        Args:
            name: Field name
            
        Returns:
            Field definition or None if not found
        """
        for field in self.fields:
            if field["name"] == name:
                return field
        return None
    
    def get_numeric_fields(self) -> List[str]:
        """Get list of numeric field names.
        
        Returns:
            List of numeric field names
        """
        numeric_types = {"INTEGER", "INT64", "FLOAT", "FLOAT64", "NUMERIC", "DECIMAL"}
        return [
            field["name"] for field in self.fields 
            if field["type"] in numeric_types
        ]
    
    def get_string_fields(self) -> List[str]:
        """Get list of string field names.
        
        Returns:
            List of string field names
        """
        string_types = {"STRING", "TEXT"}
        return [
            field["name"] for field in self.fields 
            if field["type"] in string_types
        ]
    
    def get_date_fields(self) -> List[str]:
        """Get list of date/datetime field names.
        
        Returns:
            List of date/datetime field names
        """
        date_types = {"DATE", "DATETIME", "TIMESTAMP", "TIME"}
        return [
            field["name"] for field in self.fields 
            if field["type"] in date_types
        ]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary.
        
        Returns:
            Dictionary representation
        """
        return {
            "dataset_id": self.dataset_id,
            "table_id": self.table_id,
            "project_id": self.project_id,
            "description": self.description,
            "fields": self.fields,
            "created": self.created,
            "modified": self.modified,
            "num_rows": self.num_rows,
            "num_bytes": self.num_bytes
        }


class SchemaManager:
    """Manages BigQuery schemas and metadata."""
    
    def __init__(self, bigquery_client: BigQueryClient):
        """Initialize schema manager.
        
        Args:
            bigquery_client: BigQuery client instance
        """
        self.client = bigquery_client
        self.logger = structlog.get_logger()
        self._schema_cache: Dict[str, TableSchema] = {}
    
    async def get_table_schema(self, dataset_id: str, table_id: str, use_cache: bool = True) -> TableSchema:
        """Get schema for a specific table.
        
        Args:
            dataset_id: BigQuery dataset ID
            table_id: BigQuery table ID
            use_cache: Whether to use cached schema if available
            
        Returns:
            TableSchema object
            
        Raises:
            GoogleAPIError: If schema retrieval fails
        """
        cache_key = f"{dataset_id}.{table_id}"
        
        # Check cache first
        if use_cache and cache_key in self._schema_cache:
            self.logger.debug("Using cached schema", table=cache_key)
            return self._schema_cache[cache_key]
        
        try:
            # Get table info from BigQuery
            table_info = await self.client.get_table_info(dataset_id, table_id)
            
            # Create TableSchema object
            schema = TableSchema(
                dataset_id=dataset_id,
                table_id=table_id,
                project_id=table_info["project_id"],
                description=table_info["description"],
                fields=table_info["schema"],
                created=table_info["created"],
                modified=table_info["modified"],
                num_rows=table_info["num_rows"],
                num_bytes=table_info["num_bytes"]
            )
            
            # Cache the schema
            self._schema_cache[cache_key] = schema
            
            self.logger.info(
                "Retrieved table schema",
                dataset=dataset_id,
                table=table_id,
                field_count=len(schema.fields)
            )
            
            return schema
            
        except GoogleAPIError as e:
            self.logger.error(
                "Failed to get table schema",
                error=str(e),
                dataset=dataset_id,
                table=table_id
            )
            raise
    
    async def get_dataset_schemas(self, dataset_id: str) -> List[TableSchema]:
        """Get schemas for all tables in a dataset.
        
        Args:
            dataset_id: BigQuery dataset ID
            
        Returns:
            List of TableSchema objects
        """
        try:
            # Get list of tables in dataset
            table_ids = await self.client.list_tables(dataset_id)
            
            # Get schema for each table
            schemas = []
            for table_id in table_ids:
                try:
                    schema = await self.get_table_schema(dataset_id, table_id)
                    schemas.append(schema)
                except GoogleAPIError as e:
                    self.logger.warning(
                        "Failed to get schema for table",
                        error=str(e),
                        dataset=dataset_id,
                        table=table_id
                    )
                    continue
            
            self.logger.info(
                "Retrieved dataset schemas",
                dataset=dataset_id,
                table_count=len(schemas)
            )
            
            return schemas
            
        except GoogleAPIError as e:
            self.logger.error(
                "Failed to get dataset schemas",
                error=str(e),
                dataset=dataset_id
            )
            raise
    
    async def search_tables_by_field(self, field_name: str, datasets: Optional[List[str]] = None) -> List[TableSchema]:
        """Search for tables containing a specific field.
        
        Args:
            field_name: Name of the field to search for
            datasets: Optional list of datasets to search in (searches all if None)
            
        Returns:
            List of TableSchema objects containing the field
        """
        matching_tables = []
        
        try:
            # Get datasets to search
            if datasets is None:
                datasets = await self.client.list_datasets()
            
            # Search each dataset
            for dataset_id in datasets:
                try:
                    schemas = await self.get_dataset_schemas(dataset_id)
                    
                    # Check each table for the field
                    for schema in schemas:
                        if field_name.lower() in [f["name"].lower() for f in schema.fields]:
                            matching_tables.append(schema)
                            
                except GoogleAPIError as e:
                    self.logger.warning(
                        "Failed to search dataset",
                        error=str(e),
                        dataset=dataset_id
                    )
                    continue
            
            self.logger.info(
                "Field search completed",
                field_name=field_name,
                matching_tables=len(matching_tables)
            )
            
            return matching_tables
            
        except Exception as e:
            self.logger.error(
                "Field search failed",
                error=str(e),
                field_name=field_name
            )
            raise
    
    async def search_tables_by_description(self, keyword: str, datasets: Optional[List[str]] = None) -> List[TableSchema]:
        """Search for tables by description keyword.
        
        Args:
            keyword: Keyword to search for in table descriptions
            datasets: Optional list of datasets to search in
            
        Returns:
            List of TableSchema objects with matching descriptions
        """
        matching_tables = []
        keyword_lower = keyword.lower()
        
        try:
            # Get datasets to search
            if datasets is None:
                datasets = await self.client.list_datasets()
            
            # Search each dataset
            for dataset_id in datasets:
                try:
                    schemas = await self.get_dataset_schemas(dataset_id)
                    
                    # Check each table description
                    for schema in schemas:
                        if (schema.description and 
                            keyword_lower in schema.description.lower()):
                            matching_tables.append(schema)
                            
                        # Also check field descriptions
                        for field in schema.fields:
                            if (field.get("description") and 
                                keyword_lower in field["description"].lower()):
                                if schema not in matching_tables:
                                    matching_tables.append(schema)
                                break
                                
                except GoogleAPIError as e:
                    self.logger.warning(
                        "Failed to search dataset",
                        error=str(e),
                        dataset=dataset_id
                    )
                    continue
            
            self.logger.info(
                "Description search completed",
                keyword=keyword,
                matching_tables=len(matching_tables)
            )
            
            return matching_tables
            
        except Exception as e:
            self.logger.error(
                "Description search failed",
                error=str(e),
                keyword=keyword
            )
            raise
    
    def get_schema_summary(self, schema: TableSchema) -> Dict[str, Any]:
        """Get a summary of a table schema.
        
        Args:
            schema: TableSchema object
            
        Returns:
            Dictionary with schema summary
        """
        return {
            "table": f"{schema.dataset_id}.{schema.table_id}",
            "description": schema.description,
            "total_fields": len(schema.fields),
            "numeric_fields": len(schema.get_numeric_fields()),
            "string_fields": len(schema.get_string_fields()),
            "date_fields": len(schema.get_date_fields()),
            "num_rows": schema.num_rows,
            "size_mb": round(schema.num_bytes / (1024 * 1024), 2) if schema.num_bytes else None,
            "created": schema.created,
            "modified": schema.modified
        }
    
    def clear_cache(self) -> None:
        """Clear the schema cache."""
        self._schema_cache.clear()
        self.logger.info("Schema cache cleared")
    
    def export_schemas_to_json(self, schemas: List[TableSchema], file_path: str) -> None:
        """Export schemas to JSON file.
        
        Args:
            schemas: List of TableSchema objects
            file_path: Path to output JSON file
        """
        try:
            schema_data = [schema.to_dict() for schema in schemas]
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(schema_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(
                "Schemas exported to JSON",
                file_path=file_path,
                schema_count=len(schemas)
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to export schemas",
                error=str(e),
                file_path=file_path
            )
            raise