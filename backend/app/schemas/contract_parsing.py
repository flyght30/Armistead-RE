from pydantic import BaseModel, Field
from typing import Dict, List, Optional

class PropertyDetails(BaseModel):
    address: str = Field(..., description="Property address")
    city: str = Field(..., description="City of property location")
    state: str = Field(..., description="State of property location")
    zip_code: str = Field(..., description="ZIP code of property location")

class FinancialTerms(BaseModel):
    purchase_price: float = Field(..., description="Purchase price of the property")
    down_payment: Optional[float] = Field(None, description="Down payment amount")
    financing_type: Optional[str] = Field(None, description="Type of financing used")

class Party(BaseModel):
    name: str = Field(..., description="Party name")
    role: str = Field(..., description="Role of the party in the transaction")
    contact_info: Dict[str, str] = Field(..., description="Contact information for the party")

class ContractExtractionSchema(BaseModel):
    property_details: PropertyDetails
    financial_terms: FinancialTerms
    parties: List[Party]
    dates: Dict[str, str]
    confidence_scores: Dict[str, float]
    detected_features: List[str]

class ParseResponse(BaseModel):
    status: str = Field(..., description="Status of the parsing operation")
    data: ContractExtractionSchema
    confidence_scores: Dict[str, float]
    detected_features: List[str]
