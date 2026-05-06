from pydantic import BaseModel, Field


class FileTransferResult(BaseModel):
    """
    Defines the required output structure for the BronzeToSilverAgent.
    This ensures that the SilverToGoldAgent reliably receives the newly created
    Silver layer file name, preventing LLM parsing errors.
    """
    status: str = Field(description="The status of the file transfer (SUCCESS or ERROR).")
    filename: str = Field(description="The name of the file created in the next layer, e.g., 'data_cleaned.parquet'.")
from pydantic import BaseModel, Field

class FileTransferResult(BaseModel):
    """
    Defines the required output structure for the BronzeToSilverAgent.
    This ensures that the SilverToGoldAgent reliably receives the newly created 
    Silver layer file name, preventing LLM parsing errors.
    """
    status: str = Field(description="The status of the file transfer (SUCCESS or ERROR).")
    filename: str = Field(description="The name of the file created in the next layer, e.g., 'data_cleaned.parquet'.")