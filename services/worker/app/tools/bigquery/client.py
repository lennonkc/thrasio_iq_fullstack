"""BigQuery client wrapper for data analysis."""

from typing import Any, Dict, List, Optional, Union
import os
import json
import pandas as pd
import structlog
from google.cloud import bigquery
from google.cloud.bigquery import QueryJobConfig, ScalarQueryParameter, ArrayQueryParameter
from google.api_core.exceptions import GoogleAPIError


class BigQueryClient:
    """Wrapper for Google BigQuery client with enhanced functionality."""
    
    def __init__(self, project_id: Optional[str] = None, credentials_path: Optional[str] = None):
        """Initialize BigQuery client.
        
        Args:
            project_id: Google Cloud project ID (defaults to env var GOOGLE_CLOUD_PROJECT)
            credentials_path: Path to service account credentials JSON file
        """
        self.logger = structlog.get_logger()
        self.project_id = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT")
        
        if not self.project_id:
            raise ValueError("Project ID must be provided or set as GOOGLE_CLOUD_PROJECT env var")
        
        # Initialize client
        if credentials_path:
            self.client = bigquery.Client.from_service_account_json(
                credentials_path, project=self.project_id
            )
        else:
            # Use default credentials
            self.client = bigquery.Client(project=self.project_id)
            
        self.logger.info("BigQuery client initialized", project_id=self.project_id)
    
    def execute_query(
        self, 
        query: str, 
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
        dry_run: bool = False,
        max_results: Optional[int] = None
    ) -> pd.DataFrame:
        """Execute a BigQuery SQL query and return results as DataFrame.
        
        Args:
            query: SQL query string
            params: Query parameters dict
            timeout: Query timeout in seconds
            dry_run: If True, don't actually run the query
            max_results: Maximum number of results to return
            
        Returns:
            Pandas DataFrame with query results
            
        Raises:
            GoogleAPIError: If query execution fails
        """
        job_config = QueryJobConfig()
        
        # Set dry run if requested
        if dry_run:
            job_config.dry_run = True
        
        # Set query parameters if provided
        if params:
            query_params = []
            for name, value in params.items():
                if isinstance(value, list):
                    param = ArrayQueryParameter(name, self._get_array_type(value), value)
                else:
                    param = ScalarQueryParameter(name, self._get_scalar_type(value), value)
                query_params.append(param)
            
            job_config.query_parameters = query_params
        
        try:
            self.logger.info("Executing BigQuery query", query_length=len(query))
            query_job = self.client.query(query, job_config=job_config, timeout=timeout)
            
            # For dry run, just return empty DataFrame with estimated bytes
            if dry_run:
                self.logger.info(
                    "Dry run completed", 
                    bytes_processed=query_job.total_bytes_processed
                )
                return pd.DataFrame()
            
            # Wait for query to complete and fetch results
            results = query_job.result(timeout=timeout)
            
            # Convert to DataFrame
            if max_results:
                df = results.to_dataframe(max_results=max_results)
            else:
                df = results.to_dataframe()
                
            self.logger.info(
                "Query executed successfully",
                rows=len(df),
                bytes_processed=query_job.total_bytes_processed,
                billing_tier=query_job.billing_tier
            )
            
            return df
            
        except GoogleAPIError as e:
            self.logger.error(
                "BigQuery query failed",
                error=str(e),
                query_length=len(query)
            )
            raise

    def get_dataset_info(self, dataset_id: str) -> Dict[str, Any]:
        """Get detailed information about a dataset.
        
        Args:
            dataset_id: BigQuery dataset ID
            
        Returns:
            Dictionary with dataset metadata
        """
        try:
            dataset_ref = self.client.dataset(dataset_id)
            dataset = self.client.get_dataset(dataset_ref)
            
            dataset_info = {
                "dataset_id": dataset.dataset_id,
                "project_id": dataset.project,
                "location": dataset.location,
                "description": dataset.description,
                "created": dataset.created.isoformat() if dataset.created else None,
                "modified": dataset.modified.isoformat() if dataset.modified else None,
            }
            
            self.logger.info(
                "Retrieved dataset info",
                dataset=dataset_id
            )
            
            return dataset_info
            
        except GoogleAPIError as e:
            self.logger.error(
                "Failed to get dataset info",
                error=str(e),
                dataset=dataset_id
            )
            raise
    
    def get_table_schema(self, dataset_id: str, table_id: str) -> List[Dict[str, Any]]:
        """Get schema for a BigQuery table.
        
        Args:
            dataset_id: BigQuery dataset ID
            table_id: BigQuery table ID
            
        Returns:
            List of schema field definitions
            
        Raises:
            GoogleAPIError: If schema retrieval fails
        """
        try:
            table_ref = self.client.dataset(dataset_id).table(table_id)
            table = self.client.get_table(table_ref)
            
            schema = []
            for field in table.schema:
                field_info = {
                    "name": field.name,
                    "field_type": field.field_type,
                    "mode": field.mode,
                    "description": field.description
                }
                schema.append(field_info)
            
            self.logger.info(
                "Retrieved table schema",
                dataset=dataset_id,
                table=table_id,
                field_count=len(schema)
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
    
    def list_datasets(self) -> List[str]:
        """List all datasets in the project.
        
        Returns:
            List of dataset IDs
        """
        try:
            datasets = list(self.client.list_datasets())
            dataset_ids = [dataset.dataset_id for dataset in datasets]
            
            self.logger.info("Listed datasets", count=len(dataset_ids))
            return dataset_ids
            
        except GoogleAPIError as e:
            self.logger.error("Failed to list datasets", error=str(e))
            raise
    
    def list_tables(self, dataset_id: str) -> List[str]:
        """List all tables in a dataset.
        
        Args:
            dataset_id: BigQuery dataset ID
            
        Returns:
            List of table IDs
        """
        try:
            dataset_ref = self.client.dataset(dataset_id)
            tables = list(self.client.list_tables(dataset_ref))
            table_ids = [table.table_id for table in tables]
            
            self.logger.info(
                "Listed tables", 
                dataset=dataset_id, 
                count=len(table_ids)
            )
            return table_ids
            
        except GoogleAPIError as e:
            self.logger.error(
                "Failed to list tables", 
                error=str(e), 
                dataset=dataset_id
            )
            raise
    
    def get_table_info(self, dataset_id: str, table_id: str) -> Dict[str, Any]:
        """Get detailed information about a table.
        
        Args:
            dataset_id: BigQuery dataset ID
            table_id: BigQuery table ID
            
        Returns:
            Dictionary with table metadata
        """
        try:
            table_ref = self.client.dataset(dataset_id).table(table_id)
            table = self.client.get_table(table_ref)
            
            table_info = {
                "id": table.table_id,
                "dataset_id": table.dataset_id,
                "project_id": table.project,
                "description": table.description,
                "friendly_name": table.friendly_name,
                "created": table.created.isoformat() if table.created else None,
                "modified": table.modified.isoformat() if table.modified else None,
                "num_rows": table.num_rows,
                "num_bytes": table.num_bytes,
                "schema": [{
                    "name": field.name,
                    "field_type": field.field_type,
                    "mode": field.mode,
                    "description": field.description
                } for field in table.schema]
            }
            
            self.logger.info(
                "Retrieved table info",
                dataset=dataset_id,
                table=table_id
            )
            
            return table_info
            
        except GoogleAPIError as e:
            self.logger.error(
                "Failed to get table info",
                error=str(e),
                dataset=dataset_id,
                table=table_id
            )
            raise
    
    def _get_scalar_type(self, value: Any) -> str:
        """Get BigQuery parameter type for a scalar value.
        
        Args:
            value: Python value
            
        Returns:
            BigQuery type string
        """
        if isinstance(value, bool):
            return "BOOL"
        elif isinstance(value, int):
            return "INT64"
        elif isinstance(value, float):
            return "FLOAT64"
        elif isinstance(value, str):
            return "STRING"
        elif value is None:
            return "STRING"
        else:
            return "STRING"
    
    def _get_array_type(self, values: List[Any]) -> str:
        """Get BigQuery parameter type for an array.
        
        Args:
            values: List of values
            
        Returns:
            BigQuery array type string
        """
        if not values:
            return "STRING"
        
        sample = values[0]
        return self._get_scalar_type(sample)