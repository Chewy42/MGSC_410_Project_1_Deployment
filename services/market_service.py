from typing import Dict, List, Optional
import pandas as pd
import sqlite3
from contextlib import contextmanager
from models.property import Property

class MarketService:
    def __init__(self, db_path: str = 'real_estate.db'):
        self.db_path = db_path

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()

    def get_market_metrics(self, location: str = None) -> Dict:
        """Get combined market metrics for a location"""
        trends = self.get_market_trends(location)
        demographics = self.get_demographic_data(location)
        economics = self.get_economic_indicators(location)
        
        return {
            'market_trends': trends,
            'demographics': demographics,
            'economics': economics
        }

    def get_market_trends(self, location: str = None) -> Dict:
        """Get market trends using actual data from database"""
        with self.get_connection() as conn:
            # Base query for filtering by location
            location_filter = ""
            params = []
            if location:
                location_filter = """
                    AND (l.city LIKE ? OR l.state LIKE ? OR l.zipcode LIKE ?)
                """
                params.extend([f"%{location}%"] * 3)

            # Get price trends
            price_query = f"""
                WITH price_stats AS (
                    SELECT 
                        AVG(ph.price) as avg_price,
                        strftime('%Y-%m', ph.date) as month
                    FROM price_history ph
                    JOIN location l ON ph.property_id = l.property_id
                    WHERE ph.event = 'Sold'
                    {location_filter}
                    GROUP BY strftime('%Y-%m', ph.date)
                    ORDER BY month DESC
                    LIMIT 13
                )
                SELECT 
                    (LAST_VALUE(avg_price) OVER w - FIRST_VALUE(avg_price) OVER w) / 
                    NULLIF(FIRST_VALUE(avg_price) OVER w, 0) * 100 as yearly_change,
                    (LAST_VALUE(avg_price) OVER w - NTH_VALUE(avg_price, 2) OVER w) / 
                    NULLIF(NTH_VALUE(avg_price, 2) OVER w, 0) * 100 as monthly_change
                FROM price_stats
                WINDOW w AS (ORDER BY month ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING)
                LIMIT 1
            """
            
            # Get inventory levels
            inventory_query = f"""
                SELECT 
                    COUNT(*) as current_inventory,
                    AVG(CAST(julianday('now') - julianday(ph.date) AS INTEGER)) as avg_days
                FROM properties p
                JOIN location l ON p.property_id = l.property_id
                LEFT JOIN price_history ph ON p.property_id = ph.property_id
                WHERE p.homeStatus = 'FOR_SALE'
                {location_filter}
                AND ph.event = 'Listed'
            """
            
            df_price = pd.read_sql(price_query, conn, params=params)
            df_inventory = pd.read_sql(inventory_query, conn, params=params)
            
            return {
                'price_trend': {
                    'last_year': float(df_price['yearly_change'].iloc[0]),
                    'last_month': float(df_price['monthly_change'].iloc[0]),
                    'forecast': float(df_price['yearly_change'].iloc[0]) * 0.8  # Simple forecast
                },
                'inventory_level': {
                    'current': float(df_inventory['current_inventory'].iloc[0] / 100),  # Convert to months of inventory
                    'trend': -0.3  # Placeholder for trend calculation
                },
                'days_on_market': {
                    'average': float(df_inventory['avg_days'].iloc[0]),
                    'trend': -5  # Placeholder for trend calculation
                }
            }

    def get_demographic_data(self, location: str = None) -> Dict:
        """Get demographic data based on property aggregations"""
        with self.get_connection() as conn:
            location_filter = ""
            params = []
            if location:
                location_filter = """
                    WHERE (l.city LIKE ? OR l.state LIKE ? OR l.zipcode LIKE ?)
                """
                params.extend([f"%{location}%"] * 3)

            query = f"""
                SELECT 
                    COUNT(DISTINCT l.zipcode) as total_areas,
                    AVG(p.price) as median_price,
                    COUNT(*) as total_properties,
                    AVG(p.yearBuilt) as avg_year_built
                FROM properties p
                JOIN location l ON p.property_id = l.property_id
                {location_filter}
            """
            
            df = pd.read_sql(query, conn, params=params)
            
            return {
                'population': {
                    'total': int(df['total_areas'].iloc[0] * 10000),  # Rough estimate
                    'growth_rate': 2.1  # Placeholder
                },
                'income': {
                    'median': float(df['median_price'].iloc[0] / 3),  # Rough income estimate
                    'growth_rate': 3.2  # Placeholder
                },
                'employment': {
                    'rate': 96.5,  # Placeholder
                    'trend': 0.8  # Placeholder
                }
            }

    def get_economic_indicators(self, location: str = None) -> Dict:
        """Get economic indicators from property data"""
        with self.get_connection() as conn:
            location_filter = ""
            params = []
            if location:
                location_filter = """
                    WHERE (l.city LIKE ? OR l.state LIKE ? OR l.zipcode LIKE ?)
                """
                params.extend([f"%{location}%"] * 3)

            query = f"""
                WITH yearly_stats AS (
                    SELECT 
                        strftime('%Y', ph.date) as year,
                        COUNT(*) as sales,
                        AVG(ph.price) as avg_price
                    FROM price_history ph
                    JOIN location l ON ph.property_id = l.property_id
                    WHERE ph.event = 'Sold'
                    {location_filter}
                    GROUP BY year
                    ORDER BY year DESC
                    LIMIT 2
                )
                SELECT 
                    (LAST_VALUE(sales) OVER w - FIRST_VALUE(sales) OVER w) / 
                    NULLIF(FIRST_VALUE(sales) OVER w, 0) * 100 as sales_growth,
                    (LAST_VALUE(avg_price) OVER w - FIRST_VALUE(avg_price) OVER w) / 
                    NULLIF(FIRST_VALUE(avg_price) OVER w, 0) * 100 as price_growth
                FROM yearly_stats
                WINDOW w AS (ORDER BY year ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING)
                LIMIT 1
            """
            
            df = pd.read_sql(query, conn, params=params)
            
            return {
                'gdp_growth': float(df['price_growth'].iloc[0]),
                'job_growth': float(df['sales_growth'].iloc[0]),
                'business_growth': float((df['price_growth'].iloc[0] + df['sales_growth'].iloc[0]) / 2),
                'new_construction': {
                    'residential': int(df['sales_growth'].iloc[0] * 10),  # Rough estimate
                    'commercial': int(df['sales_growth'].iloc[0] * 2)  # Rough estimate
                }
            }

    def analyze_competition(self, property: Property) -> Dict:
        """Analyze competing properties"""
        with self.get_connection() as conn:
            query = """
                SELECT 
                    COUNT(*) as similar_count,
                    AVG(p.price) as avg_price,
                    AVG(CAST(julianday('now') - julianday(ph.date) AS INTEGER)) as avg_days
                FROM properties p
                JOIN location l ON p.property_id = l.property_id
                LEFT JOIN price_history ph ON p.property_id = ph.property_id
                WHERE p.propertyTypeDimension = ?
                AND p.livingArea BETWEEN ? * 0.8 AND ? * 1.2
                AND p.price BETWEEN ? * 0.8 AND ? * 1.2
                AND l.zipcode = ?
                AND ph.event = 'Listed'
            """
            
            df = pd.read_sql(query, conn, params=[
                property.property_type,
                property.living_area,
                property.living_area,
                property.price,
                property.price,
                property.zipcode
            ])
            
            row = df.iloc[0]
            price_position = 'competitive'
            if property.price > row['avg_price'] * 1.1:
                price_position = 'high'
            elif property.price < row['avg_price'] * 0.9:
                price_position = 'low'
            
            return {
                'similar_properties': int(row['similar_count']),
                'avg_price': float(row['avg_price']),
                'avg_days_on_market': int(row['avg_days']),
                'price_position': price_position
            }
