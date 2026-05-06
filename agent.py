"""ADK agent definitions for Medallion Architecture (Bronze→Silver→Gold) pipeline.

Provides two main agents:
1. LlmAgent-based: allows the LLM to decide which tool to call next
2. SequentialAgent-based: pre-defined workflow steps executed in order

Both agents work with GCS (Bronze/Silver/Gold buckets) and optional BigQuery output.
Imports are wrapped in try/except to provide local stubs when google.adk isn't installed.
"""

try:
    from google.adk.agents import LlmAgent, SequentialAgent
except ImportError:  # pragma: no cover - provide lightweight local stubs
    class LlmAgent:
        """Stub LlmAgent for environments without google.adk installed."""
        def __init__(self, *args, **kwargs):
            self.name = kwargs.get('name') if kwargs else (args[0] if args else None)
            self.model = kwargs.get('model')
            self.instruction = kwargs.get('instruction')
            self.tools = kwargs.get('tools', [])

    class SequentialAgent:
        """Stub SequentialAgent for environments without google.adk installed."""
        def __init__(self, *args, **kwargs):
            self.name = kwargs.get('name') if kwargs else (args[0] if args else None)
            self.description = kwargs.get('description')
            self.instruction = kwargs.get('instruction')
            self.sub_agents = kwargs.get('sub_agents', [])

# Import tools (package-relative import)
from .tools import process_bronze_to_silver, process_silver_to_gold


# --- Configuration ---
# Environment variables override these defaults
import os
BRONZE_BUCKET = os.getenv("BRONZE_BUCKET", "gcs-data-pipeline-bronze")
SILVER_BUCKET = os.getenv("SILVER_BUCKET", "gcs-data-pipeline-silver")
GOLD_BUCKET = os.getenv("GOLD_BUCKET", "gcs-data-pipeline-gold")

# BigQuery configuration
BQ_DATASET = os.getenv("BQ_DATASET", "gold_analytics")
BQ_TABLE = os.getenv("BQ_TABLE", "pipeline_results")


# --- Define the LLM-driven Agent ---
bronze_to_silver_agent = LlmAgent(
    name="BronzeToSilverAgent",
    model="gemini-2.5-flash",
    instruction="""
    Your job is to call the tool `process_bronze_to_silver`.
    Extract the file name from the input and pass it to the tool.
    Example request: 'start pipeline for file_A.csv'
    Your output must be exactly the response returned by the tool.
    """,
    tools=[process_bronze_to_silver],
)


silver_to_gold_agent = LlmAgent(
    name="SilverToGoldAgent",
    model="gemini-2.5-flash",
    instruction="""
    Your job is to call the tool `process_silver_to_gold`.
    Extract the file name from the previous step's output (e.g., 'Silver file created: silver_file_A.parquet')
    Do NOT create your own file name — only use real output.
    """,
    tools=[process_silver_to_gold],
)


# --- Define the Sequential Pipeline Orchestrator ---
root_agent = SequentialAgent(
    name="BSG_Pipeline_Orchestrator",
    description="Automatic pipeline running Bronze → Silver → Gold transformations",
    instruction="""
    Execute the full Bronze-Silver-Gold pipeline in sequential order:
    1. Run BronzeToSilverAgent
    2. Take its output and pass to SilverToGoldAgent
    """,
    sub_agents=[
        bronze_to_silver_agent,
        silver_to_gold_agent,
    ],
)


if __name__ == "__main__":
    print("ADK Medallion Pipeline Agent")
    print(f"Bronze bucket: {BRONZE_BUCKET}")
    print(f"Silver bucket: {SILVER_BUCKET}")
    print(f"Gold bucket: {GOLD_BUCKET}")
    print(f"BigQuery: {BQ_DATASET}.{BQ_TABLE}")
    print("\nUse 'adk run data_pipeline_agent' to start the pipeline.")