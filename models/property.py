from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime

@dataclass
class Property:
    property_id: int
    price: float
    fair_price: float
    property_type: str
    living_area: float
    bedrooms: Optional[int]
    bathrooms: Optional[float]
    year_built: Optional[int]
    lot_size: Optional[float]
    latitude: float
    longitude: float
    zestimate: Optional[float]
    rent_estimate: Optional[float]
    tax_assessed_value: Optional[float]
    tax_rate: Optional[float]
    monthly_hoa: Optional[float]
    address: str
    city: str
    state: str
    zipcode: str
    county: Optional[str]
    
    @property
    def cap_rate(self) -> Optional[float]:
        if self.rent_estimate and self.price:
            annual_rent = self.rent_estimate * 12
            return (annual_rent - (annual_rent * 0.1)) / self.price * 100
        return None
    
    @property
    def price_per_sqft(self) -> Optional[float]:
        if self.living_area and self.price:
            return self.price / self.living_area
        return None

@dataclass
class InvestmentScore:
    property: Property
    total_score: float
    roi_score: float
    location_score: float
    condition_score: float
    market_score: float
    risk_score: float
    
    def to_dict(self):
        return {
            'property_id': self.property.property_id,
            'address': self.property.address,
            'price': self.property.price,
            'total_score': self.total_score,
            'roi_score': self.roi_score,
            'location_score': self.location_score,
            'condition_score': self.condition_score,
            'market_score': self.market_score,
            'risk_score': self.risk_score
        } 