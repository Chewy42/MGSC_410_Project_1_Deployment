from typing import List, Optional, Dict
import sqlite3
import pandas as pd
from contextlib import contextmanager
from models.property import Property

class PropertyService:
    # Class-level constants for queries
    BASE_PROPERTY_QUERY = """
        SELECT DISTINCT
            property_id, price, propertyTypeDimension as property_type,
            livingArea as living_area, bedrooms, bathrooms, yearBuilt as year_built,
            lotSize as lot_size, latitude, longitude, zestimate,
            rentZestimate as rent_estimate, taxAssessedValue as tax_assessed_value,
            propertyTaxRate as tax_rate, monthlyHoaFee as monthly_hoa,
            streetAddress as address, city, state, zipcode, county,
            fair_price
        FROM properties
        WHERE 1=1
    """

    PROPERTY_BY_ID_QUERY = """
        SELECT 
            property_id, price, propertyTypeDimension as property_type,
            livingArea as living_area, bedrooms, bathrooms, yearBuilt as year_built,
            lotSize as lot_size, latitude, longitude, zestimate,
            rentZestimate as rent_estimate, taxAssessedValue as tax_assessed_value,
            propertyTaxRate as tax_rate, monthlyHoaFee as monthly_hoa,
            streetAddress as address, city, state, zipcode, county,
            fair_price
        FROM properties
        WHERE property_id = ?
    """

    def __init__(self, db_path: str = 'real_estate.db'):
        self.db_path = db_path

    @contextmanager
    def get_connection(self):
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            yield conn
        except sqlite3.Error as e:
            raise Exception(f"Database error: {str(e)}")
        finally:
            if conn:
                conn.close()

    @staticmethod
    def _create_property_from_row(row) -> Property:
        """Helper method to create Property object from database row"""
        return Property(
            property_id=row['property_id'],
            price=row['price'],
            fair_price=row['fair_price'],
            property_type=row['property_type'],
            living_area=row['living_area'],
            bedrooms=row['bedrooms'],
            bathrooms=row['bathrooms'],
            year_built=row['year_built'],
            lot_size=row['lot_size'],
            latitude=row['latitude'],
            longitude=row['longitude'],
            zestimate=row['zestimate'],
            rent_estimate=row['rent_estimate'],
            tax_assessed_value=row['tax_assessed_value'],
            tax_rate=row['tax_rate'],
            monthly_hoa=row['monthly_hoa'],
            address=row['address'],
            city=row['city'],
            state=row['state'],
            zipcode=row['zipcode'],
            county=row['county']
        )

    def search_properties(self, filters: Dict, limit: int = 100) -> List[Property]:
        """Search properties with filters and limit results"""
        query = self.BASE_PROPERTY_QUERY
        params = []
        
        if filters.get('price_min') and filters.get('price_max'):
            query += " AND price BETWEEN ? AND ?"
            params.extend([filters['price_min'], filters['price_max']])
        
        if filters.get('sqft_min') and filters.get('sqft_max'):
            query += " AND livingArea BETWEEN ? AND ?"
            params.extend([filters['sqft_min'], filters['sqft_max']])
        
        if property_types := filters.get('property_types'):
            if property_types:
                query += f" AND propertyTypeDimension IN ({','.join('?' * len(property_types))})"
                params.extend(property_types)
        
        if location := filters.get('location'):
            query += """ 
            AND (
                LOWER(city) LIKE LOWER(?) OR 
                zipcode LIKE ? OR 
                LOWER(state) LIKE LOWER(?)
            )"""
            location_param = f"%{location}%"
            params.extend([location_param] * 3)

        if max_hoa := filters.get('max_hoa'):
            query += " AND (monthlyHoaFee <= ? OR monthlyHoaFee IS NULL)"
            params.append(max_hoa)

        query += f" LIMIT {limit}"

        try:
            with self.get_connection() as conn:
                df = pd.read_sql(query, conn, params=params)
                return [self._create_property_from_row(row) for _, row in df.iterrows()]
        except Exception as e:
            raise Exception(f"Error searching properties: {str(e)}")

    def get_property_by_id(self, property_id: int) -> Optional[Property]:
        """Get a single property by ID"""
        try:
            with self.get_connection() as conn:
                df = pd.read_sql(self.PROPERTY_BY_ID_QUERY, conn, params=[property_id])
                
                if df.empty:
                    return None
                    
                return self._create_property_from_row(df.iloc[0])
        except Exception as e:
            raise Exception(f"Error getting property {property_id}: {str(e)}")

    def get_investment_opportunities(self, sort_by: str = 'score', limit: int = 50, filters: Dict = None) -> List[Property]:
        """Get investment opportunities with filters and sorting"""
        try:
            # Handle show_max_results filter
            show_max_results = filters.pop('show_max_results', False) if filters else False
            actual_limit = 2000 if show_max_results else (limit or 50)
            
            # Build query with limit
            query = self.BASE_PROPERTY_QUERY
            params = []
            
            # Add filter conditions
            if filters:
                query, params = self._add_filters_to_query(query, params, filters)
            
            # Add sorting
            query = self._add_sorting_to_query(query, sort_by)
            
            # Add LIMIT clause
            query += f" LIMIT {actual_limit}"
            
            print(f"Executing query with limit {actual_limit}")  # Debug print
            
            with self.get_connection() as conn:
                df = pd.read_sql(query, conn, params=params)
                return [self._create_property_from_row(row) for _, row in df.iterrows()]
                
        except Exception as e:
            print(f"Error in get_investment_opportunities: {str(e)}")
            import traceback
            traceback.print_exc()
            return []

    def _add_filters_to_query(self, query: str, params: list, filters: Dict) -> tuple:
        """Helper method to add filter conditions to query"""
        if filters.get('price_min') is not None and filters.get('price_max') is not None:
            query += " AND price BETWEEN ? AND ?"
            params.extend([filters['price_min'], filters['price_max']])
        
        if filters.get('sqft_min') is not None and filters.get('sqft_max') is not None:
            query += " AND livingArea BETWEEN ? AND ?"
            params.extend([filters['sqft_min'], filters['sqft_max']])
        
        # Strictly enforce allowed property types
        allowed_types = ['SINGLE FAMILY', 'CONDO', 'TOWNHOUSE']
        if property_types := filters.get('property_types'):
            if isinstance(property_types, (list, tuple)) and property_types:
                # Filter out any property types not in allowed_types
                valid_types = [pt for pt in property_types if pt.upper() in allowed_types]
                if valid_types:
                    query += f" AND UPPER(propertyTypeDimension) IN ({','.join(['?' for _ in valid_types])})"
                    params.extend([pt.upper() for pt in valid_types])

        return query, params

    def _add_sorting_to_query(self, query: str, sort_by: str, center_coords: tuple = None) -> str:
        """Helper method to add sorting to query"""
        if center_coords:
            if sort_by == 'score':
                query += """ 
                ORDER BY (
                    CASE 
                        WHEN price > 0 THEN (
                            COALESCE(rentZestimate * 12.0 / NULLIF(price, 0), 0) * 0.4 + 
                            COALESCE((zestimate - price) / NULLIF(price, 0), 0) * 0.3
                        )
                    END
                ) DESC, distance ASC
                """
            else:
                sort_clause = {
                    'roi_potential': 'COALESCE((zestimate - price) / NULLIF(price, 0), 0) DESC',
                    'cap_rate': 'COALESCE(rentZestimate * 12.0 / NULLIF(price, 0), 0) DESC',
                    'price_asc': 'price ASC',
                    'price_desc': 'price DESC'
                }.get(sort_by, 'distance ASC')
                query += f" ORDER BY {sort_clause}"
        else:
            # Default sorting when no location is specified
            sort_clause = {
                'score': '''ORDER BY (
                    CASE 
                        WHEN price > 0 THEN (
                            COALESCE(rentZestimate * 12.0 / NULLIF(price, 0), 0) * 0.4 + 
                            COALESCE((zestimate - price) / NULLIF(price, 0), 0) * 0.3
                        )
                    END
                ) DESC''',
                'roi_potential': 'ORDER BY COALESCE((zestimate - price) / NULLIF(price, 0), 0) DESC',
                'cap_rate': 'ORDER BY COALESCE(rentZestimate * 12.0 / NULLIF(price, 0), 0) DESC',
                'price_asc': 'ORDER BY price ASC',
                'price_desc': 'ORDER BY price DESC'
            }.get(sort_by, 'ORDER BY price DESC')
            query += f" {sort_clause}"

        return query
