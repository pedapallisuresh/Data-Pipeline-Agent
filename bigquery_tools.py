"""BigQuery wrapper for Medallion Architecture data pipeline.

This module provides a simple wrapper class around the core tools for users
who prefer a BigQuery-centric interface. The underlying implementation uses
the functions from `tools.py`.

Example:
    from bigquery_tools import BigQueryDataPipeline
    
    pipeline = BigQueryDataPipeline(project_id="my-gcp-project")
    result = pipeline.ingest_to_bronze(dataset_id="bronze", table_id="raw", raw_data_string="...")
"""

try:
    from google.cloud import bigquery
except ImportError:
    bigquery = None

from .tools import process_bronze_to_silver, process_silver_to_gold


class BigQueryDataPipeline:
    """Wrapper for Medallion pipeline operations on BigQuery datasets."""

    def __init__(self, project_id: str):
        """Initialize the pipeline with a GCP project ID.
        
        Args:
            project_id: GCP project ID (e.g., 'my-gcp-project').
        """
        self.project_id = project_id
        self.bq_client = None
        if bigquery is not None:
            try:
                self.bq_client = bigquery.Client(project=project_id)
            except Exception:
                pass  # Will error later if actually used without credentials.

    def ingest_to_bronze(self, dataset_id: str, table_id: str, raw_data_string: str) -> str:
        """Ingest raw data into the Bronze layer (BigQuery).
        
        Args:
            dataset_id: BigQuery dataset ID.
            table_id: BigQuery table ID.
            raw_data_string: Raw CSV data as a string.
            
        Returns:
            Status message.
        """
        if self.bq_client is None:
            return "ERROR: BigQuery client is not available. Check credentials and dependencies."

        try:
            import pandas as pd
            from io import StringIO
            
            # Parse raw data
            df = pd.read_csv(StringIO(raw_data_string))
            
            # Load to BigQuery
            full_table_id = f"{self.project_id}.{dataset_id}.{table_id}"
            job = self.bq_client.load_table_from_dataframe(df, full_table_id)
            job.result()
            
            return f"SUCCESS: Ingested {len(df)} rows to Bronze table {full_table_id}"
        except Exception as e:
            return f"ERROR: Failed to ingest to Bronze: {e}"

    def cleanse_and_load_to_silver(self, source_table: str, target_table: str) -> str:
        """Cleanse Bronze data and load to Silver layer.
        
        Args:
            source_table: Full BigQuery table ID of Bronze layer (e.g., 'project.bronze.raw').
            target_table: Full BigQuery table ID for Silver layer (e.g., 'project.silver.clean').
            
        Returns:
            Status message.
        """
        if self.bq_client is None:
            return "ERROR: BigQuery client is not available. Check credentials and dependencies."

        try:
            # Read from source
            df_bronze = self.bq_client.query(f"SELECT * FROM `{source_table}`").to_dataframe()
            
            # Cleanse: remove nulls, deduplicate, etc.
            df_silver = df_bronze.dropna().drop_duplicates()
            df_silver['ingestion_timestamp'] = pd.Timestamp.now()
            
            # Write to target
            job = self.bq_client.load_table_from_dataframe(df_silver, target_table)
            job.result()
            
            return f"SUCCESS: Cleansed and loaded {len(df_silver)} rows to Silver table {target_table}"
        except Exception as e:
            return f"ERROR: Failed to cleanse and load to Silver: {e}"

    def aggregate_to_gold(self, silver_table: str, gold_table: str) -> str:
        """Aggregate Silver data and load to Gold layer (reporting).
        
        Args:
            silver_table: Full BigQuery table ID of Silver layer.
            gold_table: Full BigQuery table ID for Gold layer (e.g., 'project.gold.summary').
            
        Returns:
            Status message.
        """
        if self.bq_client is None:
            return "ERROR: BigQuery client is not available. Check credentials and dependencies."

        try:
            import pandas as pd
            
            # Read from Silver
            df_silver = self.bq_client.query(f"SELECT * FROM `{silver_table}`").to_dataframe()
            
            # Aggregate (example: group by and count)
            if 'category_id' in df_silver.columns and 'value' in df_silver.columns:
                df_gold = df_silver.groupby('category_id').agg(
                    total_records=('id', 'count') if 'id' in df_silver.columns else ('value', 'count'),
                    sum_value=('value', 'sum')
                ).reset_index()
            else:
                # Simple count if columns don't exist
                df_gold = pd.DataFrame([{'Summary': 'Data Processed', 'Count': len(df_silver)}])
            
            # Write to Gold
            job = self.bq_client.load_table_from_dataframe(df_gold, gold_table)
            job.result()
            
            return f"SUCCESS: Aggregated and loaded {len(df_gold)} rows to Gold table {gold_table}"
        except Exception as e:
            return f"ERROR: Failed to aggregate to Gold: {e}"
