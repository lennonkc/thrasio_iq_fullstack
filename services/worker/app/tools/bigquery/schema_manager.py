"""Schema management for BigQuery tables and datasets."""

import os
import json
from typing import List, Dict, Any, Optional, Set
import structlog
from dataclasses import dataclass
from google.cloud.exceptions import NotFound
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
    
    def get_table_schema(self, dataset_id: str, table_id: str, use_cache: bool = True) -> TableSchema:
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
            table_info = self.client.get_table_info(dataset_id, table_id)
            
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
    
    def get_dataset_schemas(self, dataset_id: str) -> List[TableSchema]:
        """Get schemas for all tables in a dataset.
        
        Args:
            dataset_id: BigQuery dataset ID
            
        Returns:
            List of TableSchema objects
        """
        try:
            # Get list of tables in dataset
            table_ids = self.client.list_tables(dataset_id)
            
            # Get schema for each table
            schemas = []
            for table_id in table_ids:
                try:
                    schema = self.get_table_schema(dataset_id, table_id)
                    schemas.append(schema)
                except GoogleAPIError as e:
                    self.logger.warning(
                        "Failed to get schema for table",
                        error=str(e),
                        dataset=dataset_id,
                        table=table_id
                    )
            
            return schemas
            
        except GoogleAPIError as e:
            self.logger.error(
                "Failed to get dataset schemas",
                error=str(e),
                dataset=dataset_id
            )
            return []
    
    def export_schemas_to_json(self, schemas: List[TableSchema], file_path: str):
        """Export a list of schemas to a JSON file.
        
        Args:
            schemas: List of TableSchema objects
            file_path: Path to the output JSON file
        """
        try:
            # Convert schemas to dictionaries
            schema_dicts = [schema.to_dict() for schema in schemas]
            
            # Write to JSON file
            with open(file_path, "w") as f:
                json.dump(schema_dicts, f, indent=2)
                
            self.logger.info(
                "Exported schemas to JSON",
                file_path=file_path,
                schema_count=len(schemas)
            )
            
        except IOError as e:
            self.logger.error(
                "Failed to write schemas to JSON file",
                error=str(e),
                file_path=file_path
            )
            raise