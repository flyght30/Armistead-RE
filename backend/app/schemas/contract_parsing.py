from pydantic import BaseModel, Field
from typing import Dict, List, Optional


class PropertyDetails(BaseModel):
    address: str = Field("", description="Street address of the property")
    city: str = Field("", description="City of property location")
    state: str = Field("", description="State abbreviation (e.g. AL, GA)")
    zip_code: str = Field("", description="ZIP code of property location")
    county: Optional[str] = Field(None, description="County where property is located")


class FinancialTerms(BaseModel):
    purchase_price: float = Field(0, description="Final purchase price")
    original_list_price: Optional[float] = Field(None, description="Original listing / counter price if different")
    down_payment: Optional[float] = Field(None, description="Down payment amount")
    financing_type: Optional[str] = Field(None, description="Financing type: conventional, fha, va, cash, usda")
    earnest_money: Optional[float] = Field(None, description="Earnest money deposit amount")
    earnest_money_holder: Optional[str] = Field(None, description="Who holds the earnest money (company/attorney name)")
    seller_concessions: Optional[float] = Field(None, description="Seller concessions / closing cost credits")
    home_warranty_amount: Optional[float] = Field(None, description="Home warranty cost if included")
    home_warranty_paid_by: Optional[str] = Field(None, description="Who pays for home warranty: buyer or seller")


class AgentInfo(BaseModel):
    name: str = Field("", description="Agent's full name")
    license_number: Optional[str] = Field(None, description="Agent license number")
    company: Optional[str] = Field(None, description="Brokerage company name")
    company_license: Optional[str] = Field(None, description="Brokerage license number")
    email: Optional[str] = Field(None, description="Agent email")
    phone: Optional[str] = Field(None, description="Agent phone")


class PartyInfo(BaseModel):
    name: str = Field("", description="Party name")
    role: str = Field("", description="Role: buyer, seller, buyer_agent, seller_agent, lender, closing_attorney, title_company, inspector")
    email: Optional[str] = Field(None, description="Email address if available")
    phone: Optional[str] = Field(None, description="Phone number if available")
    company: Optional[str] = Field(None, description="Company/firm name if applicable")
    license_number: Optional[str] = Field(None, description="License number if applicable")


class ContractDates(BaseModel):
    contract_date: Optional[str] = Field(None, description="Date contract was executed (ISO format YYYY-MM-DD)")
    closing_date: Optional[str] = Field(None, description="Scheduled closing date (ISO format YYYY-MM-DD)")
    inspection_deadline: Optional[str] = Field(None, description="Inspection contingency deadline (ISO format YYYY-MM-DD)")
    financing_deadline: Optional[str] = Field(None, description="Financing contingency deadline (ISO format YYYY-MM-DD)")
    earnest_money_deadline: Optional[str] = Field(None, description="Earnest money delivery deadline (ISO format YYYY-MM-DD)")
    appraisal_contingency_date: Optional[str] = Field(None, description="Appraisal contingency date if applicable")
    offer_deadline: Optional[str] = Field(None, description="Offer expiration / acceptance deadline")


class AdditionalProvisions(BaseModel):
    provisions: List[str] = Field(default_factory=list, description="List of additional provisions / special stipulations")
    contingencies: List[str] = Field(default_factory=list, description="Active contingencies (inspection, financing, appraisal, sale)")
    home_warranty: bool = Field(False, description="Whether a home warranty is included")
    wood_infestation_report: bool = Field(False, description="Whether wood/termite inspection is required")
    lead_based_paint: bool = Field(False, description="Whether lead-based paint disclosure applies")
    fha_va_agreement: bool = Field(False, description="Whether FHA/VA agreement addendum applies")
    property_sale_contingency: bool = Field(False, description="Whether sale is contingent on buyer selling their property")


class ContractExtractionSchema(BaseModel):
    property_details: PropertyDetails = Field(default_factory=PropertyDetails)
    financial_terms: FinancialTerms = Field(default_factory=FinancialTerms)
    parties: List[PartyInfo] = Field(default_factory=list)
    dates: ContractDates = Field(default_factory=ContractDates)
    additional_provisions: AdditionalProvisions = Field(default_factory=AdditionalProvisions)
    representation_side: Optional[str] = Field(None, description="Which side the uploading agent represents: buyer or seller")
    contract_type: Optional[str] = Field(None, description="Contract form type, e.g. 'LCAR Residential Real Estate Sales Contract'")
    confidence_scores: Dict[str, float] = Field(default_factory=dict)
    detected_features: List[str] = Field(default_factory=list)


class ParseResponse(BaseModel):
    status: str = Field(..., description="Status of the parsing operation")
    data: ContractExtractionSchema
    confidence_scores: Dict[str, float]
    detected_features: List[str]
