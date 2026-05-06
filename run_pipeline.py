# bigquery_tools.py

from google.adk.tools import FunctionTool
from google.cloud import bigquery
import pandas as pd
import io

class BigQueryDataPipeline:
    """
    Manages a three-tier data pipeline (Bronze, Silver, Gold) in Google BigQuery.
    """
    def __init__(self, project_id: str):
        """Initializes the BigQuery client."""
        # Note: Authentication is typically handled automatically by the ADK environment
        # or the running environment (e.g., Application Default Credentials).
        self.client = bigquery.Client(project=project_id)
        self.project_id = project_id

    # 1. Tool for Bronze Ingestion
    def ingest_to_bronze(self, dataset_id: str, table_id: str, raw_data_string: str) -> str:
        """
        Loads raw data (e.g., CSV string) into a specified BigQuery Bronze table.
        The Bronze layer holds data in its original, raw format.
        """
        # Convert the string to a file-like object for reading
        csv_file = io.StringIO(raw_data_string)
        
        # Define job configuration
        table_ref = f"{self.project_id}.{dataset_id}.{table_id}"
        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.CSV,
            autodetect=True,
            # Use WRITE_APPEND to add new data without replacing the whole table
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        )

        # Start the load job
        job = self.client.load_table_from_file(csv_file, table_ref, job_config=job_config)
        job.result() # Wait for the job to complete

        return f"✅ Successfully ingested {job.output_rows} rows to BigQuery Bronze layer: {table_ref}"

    # 2. Tool for Data Cleansing (Silver Layer)
    def cleanse_and_load_to_silver(self, source_table: str, target_table: str) -> str:
        """
        Applies cleaning, validation, and transformations (e.g., standardizing formats,
        handling missing values) to data from the Bronze layer and loads the cleaned 
        data into the Silver layer.
        
        Args:
            source_table: The fully qualified table ID for the Bronze source (e.g., project.dataset.bronze_table).
            target_table: The fully qualified table ID for the Silver destination.
        """
        # Example Cleaning Query: standardizing ID format, uppercasing name, validating value.
        cleaning_query = f"""
            SELECT
                CAST(REPLACE(TRIM(id), 'ID-', '') AS INT64) AS clean_id,
                UPPER(SAFE_CAST(name AS STRING)) AS clean_name,
                COALESCE(SAFE_CAST(value AS NUMERIC), 0) AS validated_value,
                current_timestamp() as load_timestamp
            FROM 
                `{source_table}`
            WHERE 
                name IS NOT NULL -- Simple filter for data quality
        """
        
        # Configure a query job to run the cleaning and load to the Silver table
        job_config = bigquery.QueryJobConfig(
            destination=target_table,
            # Use WRITE_TRUNCATE to completely replace the Silver table on each run
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
            # Allow large results to be written to the destination table
            allow_large_results=True,
        )
        
        query_job = self.client.query(cleaning_query, job_config=job_config)
        query_job.result() # Wait for the job to complete

        return f"✨ Successfully cleansed and loaded to BigQuery Silver layer: {target_table}. Rows processed: {query_job.total_rows_processed}"

    # 3. Tool for Gold Aggregation (Analytics Layer)
    def aggregate_to_gold(self, silver_table: str, gold_table: str) -> str:
        """
        Aggregates, summarizes, and curates data from the Silver layer for the 
        Gold (analytics/reporting) layer. This layer is optimized for fast querying.

        Args:
            silver_table: The fully qualified table ID for the Silver source.
            gold_table: The fully qualified table ID for the Gold destination.
        """

        aggregation_query = f"""
            SELECT
                t1.clean_name,
                SUM(t1.validated_value) AS total_value_sum,
                COUNT(1) AS record_count
            FROM 
                `{silver_table}` t1
            GROUP BY 
                t1.clean_name
        """
        
        job_config = bigquery.QueryJobConfig(
            destination=gold_table,
            # Use WRITE_TRUNCATE to completely replace the Gold table on each run
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
            allow_large_results=True,
        )
        
        query_job = self.client.query(aggregation_query, job_config=job_config)
        query_job.result() # Wait for the job to complete
        
        return f"🏆 Successfully aggregated and loaded to BigQuery Gold layer: {gold_table}"

# --- ADK Tool Definition ---

# 1. Initialize the pipeline instance with your Google Cloud Project ID
# IMPORTANT: Replace 'your-gcp-project-id' with your actual Google Cloud Project ID.
PIPELINE = BigQueryDataPipeline(project_id="your-gcp-project-id")

# 2. Expose the methods as ADK FunctionTools

IngestToBronzeTool = FunctionTool(
    PIPELINE.ingest_to_bronze,
    description="Loads raw data into the Bronze layer of BigQuery. Use this first to get data into the pipeline.",
)

SilverCleansingTool = FunctionTool(
    PIPELINE.cleanse_and_load_to_silver,
    description="Cleanses, validates, and transforms data from the Bronze layer and loads it into the Silver layer.",
)

GoldAggregationTool = FunctionTool(
    PIPELINE.aggregate_to_gold,
    description="Aggregates and curates cleaned data from the Silver layer into the final Gold layer for analytics and reporting.",
)

# Optional: A list of all tools to easily export them in your agent definition file
BIGQUERY_TOOLS = [
    IngestToBronzeTool,
    SilverCleansingTool,
    GoldAggregationTool,
]