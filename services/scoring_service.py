from typing import List
from models.property import Property, InvestmentScore
from statistics import mean

class ScoringService:
    def calculate_roi_score(self, property: Property) -> float:
        if not property.rent_estimate or not property.price:
            return 0.0
            
        annual_rent = property.rent_estimate * 12
        gross_roi = (annual_rent / property.price) * 100
        
        # Adjust for typical expenses
        operating_expenses = annual_rent * 0.4  # 40% for maintenance, vacancy, etc.
        net_roi = ((annual_rent - operating_expenses) / property.price) * 100
        
        # Score from 0-10 based on ROI
        return min(10, net_roi)

    def calculate_location_score(self, property: Property) -> float:
        # This would typically involve more complex analysis of:
        # - School ratings
        # - Crime rates
        # - Employment data
        # - Growth trends
        # For now, we'll use a simplified scoring
        return 7.0  # Placeholder

    def calculate_condition_score(self, property: Property) -> float:
        if not property.year_built:
            return 5.0
            
        # Base score on age of property
        age = 2024 - property.year_built
        age_score = max(0, 10 - (age / 10))
        
        # Adjust for recent zestimate vs price if available
        if property.zestimate and property.price:
            condition_factor = property.zestimate / property.price
            condition_score = 10 * min(1.2, max(0.8, condition_factor))
            return mean([age_score, condition_score])
            
        return age_score

    def calculate_market_score(self, property: Property) -> float:
        # This would analyze:
        # - Market trends
        # - Price history
        # - Days on market
        # - Comparable sales
        return 6.0  # Placeholder

    def calculate_risk_score(self, property: Property) -> float:
        risk_factors = []
        
        # Price volatility risk
        if property.zestimate and property.price:
            price_diff = abs(property.zestimate - property.price) / property.price
            price_risk = 10 - (price_diff * 100)
            risk_factors.append(price_risk)
            
        # Vacancy risk based on property type
        vacancy_risk = {
            'Single Family': 8,
            'Multi Family': 7,
            'Apartment': 6,
            'Retail': 5,
            'Office': 4,
            'Industrial': 6,
            'Land': 3
        }.get(property.property_type, 5)
        risk_factors.append(vacancy_risk)
        
        # Market risk
        market_risk = 6  # Placeholder
        risk_factors.append(market_risk)
        
        return mean(risk_factors) if risk_factors else 5.0

    def score_property(self, property: Property) -> InvestmentScore:
        roi_score = self.calculate_roi_score(property)
        location_score = self.calculate_location_score(property)
        condition_score = self.calculate_condition_score(property)
        market_score = self.calculate_market_score(property)
        risk_score = self.calculate_risk_score(property)
        
        # Calculate total score with weighted factors
        weights = {
            'roi': 0.35,
            'location': 0.25,
            'condition': 0.15,
            'market': 0.15,
            'risk': 0.10
        }
        
        total_score = (
            roi_score * weights['roi'] +
            location_score * weights['location'] +
            condition_score * weights['condition'] +
            market_score * weights['market'] +
            risk_score * weights['risk']
        ) * 10  # Scale to 0-100
        
        return InvestmentScore(
            property=property,
            total_score=total_score,
            roi_score=roi_score,
            location_score=location_score,
            condition_score=condition_score,
            market_score=market_score,
            risk_score=risk_score
        )

    def score_properties(self, properties: List[Property]) -> List[InvestmentScore]:
        return [self.score_property(prop) for prop in properties] 