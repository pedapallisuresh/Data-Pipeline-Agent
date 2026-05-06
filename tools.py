"""ETL tools for Medallion Architecture (Bronze→Silver→Gold) pipeline.

Provides functions to:
- Read raw data from Bronze layer (GCS).
- Clean and load to Silver layer (GCS).
- Aggregate and optionally load to Gold layer (GCS and/or BigQuery).

Clients are created lazily to avoid import-time errors when credentials are missing.
"""

import pandas as pd
import os

try:
    from google.cloud import storage
except ImportError:
    storage = None

try:
    from google.cloud import bigquery
except ImportError:
    bigquery = None

# --- Configuration ---
# Load bucket names from the .env file (or use environment variables)
BRONZE_BUCKET = os.getenv("BRONZE_BUCKET", "gcs-data-pipeline-bronze")
SILVER_BUCKET = os.getenv("SILVER_BUCKET", "gcs-data-pipeline-silver")
GOLD_BUCKET = os.getenv("GOLD_BUCKET", "gcs-data-pipeline-gold")

# Helper to create a GCS client lazily. This avoids raising on import when
# application default credentials are not configured in local/dev environments.
def _get_storage_client():
    if storage is None:
        return None
    try:
        return storage.Client()
    except Exception:
        return None


def _get_bigquery_client():
    if bigquery is None:
        return None
    try:
        return bigquery.Client()
    except Exception:
        return None


def process_bronze_to_silver(file_name: str) -> str:
    """
    Reads a file from the Bronze layer (GCS), applies basic cleaning (e.g., dropping NaNs),
    and writes the structured data to the Silver layer as a Parquet file.
    Args:
        file_name (str): The name of the new raw file in the Bronze bucket (e.g., 'data/batch_1.csv').
    Returns:
        str: Status message and the name of the new file created in the Silver bucket.
    """
    print(f"--- TOOL: Starting Bronze to Silver for {file_name} ---")

    # 1. READ RAW DATA (Bronze)
    client = _get_storage_client()
    if client is None:
        return (
            "ERROR: GCS client unavailable. Application Default Credentials "
            "are not configured in this environment."
        )

    try:
        bucket = client.bucket(BRONZE_BUCKET)
        blob = bucket.blob(file_name)

        # Download as a string and read into pandas
        raw_data = blob.download_as_text()
        from io import StringIO
        df = pd.read_csv(StringIO(raw_data))

    except Exception as e:
        return f"ERROR: Failed to read from Bronze bucket {BRONZE_BUCKET}. Check file name or permissions: {e}"

    # 2. TRANSFORM (Silver Layer Logic: Cleanse and Standardize)
    df_cleaned = df.dropna()
    df_cleaned['processed_timestamp'] = pd.Timestamp.now()

    silver_file_name = file_name.replace('.csv', '_cleaned.parquet')

    # 3. WRITE ENRICHED DATA (Silver)
    silver_client = _get_storage_client()
    if silver_client is None:
        return (
            "ERROR: GCS client unavailable. Application Default Credentials "
            "are not configured in this environment."
        )

    silver_bucket = silver_client.bucket(SILVER_BUCKET)
    silver_blob = silver_bucket.blob(silver_file_name)

    # Upload Parquet for efficient storage
    silver_blob.upload_from_string(df_cleaned.to_parquet(index=False), content_type='application/octet-stream')

    return f"SUCCESS: Silver layer file created: {silver_file_name}"


def process_silver_to_gold(silver_file_name: str) -> str:
    """
    Reads a file from the Silver layer (GCS), performs aggregation/denormalization,
    and writes the final reporting data to the Gold layer as a CSV file.
    Args:
        silver_file_name (str): The cleaned Parquet file name from the Silver bucket (e.g., 'data/batch_1_cleaned.parquet').
    Returns:
        str: Final status message and the name of the report file created in the Gold bucket.
    """
    print(f"--- TOOL: Starting Silver to Gold for {silver_file_name} ---")

    # 1. READ SILVER DATA
    silver_client = _get_storage_client()
    if silver_client is None:
        return (
            "ERROR: GCS client unavailable. Application Default Credentials "
            "are not configured in this environment."
        )

    try:
        silver_bucket = silver_client.bucket(SILVER_BUCKET)
        silver_blob = silver_bucket.blob(silver_file_name)

        # Download Parquet data
        from io import BytesIO
        df_silver = pd.read_parquet(BytesIO(silver_blob.download_as_bytes()))

    except Exception as e:
        return f"ERROR: Failed to read from Silver bucket {SILVER_BUCKET}. Check file name or permissions: {e}"

    # 2. AGGREGATE/DENORMALIZE (Gold Layer Logic: Reporting)
    # This is mock aggregation - replace 'numeric_column' with a real column name from your data.
    if 'value' in df_silver.columns:  # Assuming a 'value' column exists after cleaning
        df_gold = df_silver.groupby('category_id').agg(
            total_records=('processed_timestamp', 'count'),
            sum_value=('value', 'sum')
        ).reset_index()
    else:
        # Simple count for demonstration if specific columns are unknown
        df_gold = pd.DataFrame([{'Summary': 'Data Processed', 'Count': len(df_silver)}])

    gold_file_name = silver_file_name.replace('_cleaned.parquet', '_report.csv')

    # 3a. Optionally upload final report to Gold bucket (GCS)
    gold_client = _get_storage_client()
    if gold_client is not None:
        try:
            gold_bucket = gold_client.bucket(GOLD_BUCKET)
            gold_blob = gold_bucket.blob(gold_file_name)
            gold_blob.upload_from_string(df_gold.to_csv(index=False), content_type='text/csv')
        except Exception as e:
            return f"ERROR: Failed to write report to Gold bucket {GOLD_BUCKET}: {e}"

    # 3b. Optionally load report to BigQuery when environment variables are set
    bq_dataset = os.getenv("BQ_DATASET")
    bq_table = os.getenv("BQ_TABLE")
    if bq_dataset and bq_table:
        bq_client = _get_bigquery_client()
        if bq_client is None:
            return (
                "ERROR: BigQuery client unavailable. Application Default Credentials "
                "are not configured in this environment."
            )

        # Load DataFrame to BigQuery using load_table_from_dataframe
        table_ref = f"{bq_dataset}.{bq_table}"
        try:
            job = bq_client.load_table_from_dataframe(df_gold, table_ref)
            job.result()  # wait for job to complete
        except Exception as e:
            return f"ERROR: Failed to load report to BigQuery {table_ref}: {e}"

        return f"COMPLETED: Full pipeline success. Report loaded to BigQuery: {table_ref}"
    

    return f"COMPLETED: Full pipeline success. Report in Gold layer: {gold_file_name}"

