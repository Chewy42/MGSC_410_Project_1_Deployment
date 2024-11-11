import pandas as pd
import sqlite3
from pathlib import Path
import os

def calculate_fair_price(row):
    """Calculate fair price based on property attributes"""
    try:
        # Base price from actual price
        base_price = row['price']
        
        # Adjust based on market factors
        if pd.notna(row['zestimate']):
            return (base_price + row['zestimate']) / 2
        
        return base_price
        
    except Exception as e:
        print(f"Error calculating fair price: {str(e)}")
        return row['price']  # Fallback to actual price

def create_db(csv_file):
    """Create and initialize the database with property data"""
    try:
        print(f"Reading CSV file: {csv_file}")
        properties_df = pd.read_csv(csv_file)
        
        # Add property_id if it doesn't exist
        if 'property_id' not in properties_df.columns:
            properties_df['property_id'] = range(1, len(properties_df) + 1)
        
        # Standardize property types
        property_type_mapping = {
            'SINGLE FAMILY': 'SINGLE FAMILY',
            'SINGLE-FAMILY': 'SINGLE FAMILY',
            'SINGLEFAMILY': 'SINGLE FAMILY',
            'CONDO': 'CONDO',
            'CONDOMINIUM': 'CONDO',
            'TOWNHOUSE': 'TOWNHOUSE',
            'TOWN_HOUSE': 'TOWNHOUSE',
            'TOWNHOME': 'TOWNHOUSE'
        }
        
        # Convert property types to standard format
        properties_df['propertyTypeDimension'] = properties_df['propertyTypeDimension'].str.upper()
        properties_df['propertyTypeDimension'] = properties_df['propertyTypeDimension'].map(
            property_type_mapping).fillna('SINGLE FAMILY')  # Default to SINGLE FAMILY if unknown
        
        # Calculate fair prices
        properties_df['fair_price'] = properties_df.apply(calculate_fair_price, axis=1)
        
        # Ensure address fields are not null
        properties_df['streetAddress'] = properties_df['streetAddress'].fillna('Address Not Available')
        properties_df['city'] = properties_df['city'].fillna('City Not Available')
        properties_df['state'] = properties_df['state'].fillna('NA')
        properties_df['zipcode'] = properties_df['zipcode'].fillna('00000')
        
        # Save predictions to CSV
        predictions_dir = Path('data')
        predictions_dir.mkdir(exist_ok=True)
        
        predictions_df = pd.DataFrame({
            'property_id': properties_df['property_id'],
            'fair_price': properties_df['fair_price']
        })
        
        predictions_path = predictions_dir / 'predictions.csv'
        predictions_df.to_csv(predictions_path, index=False)
        print(f"Saved predictions to {predictions_path}")
        
        # Create database
        print("Creating database...")
        conn = sqlite3.connect('real_estate.db')
        properties_df.to_sql('properties', conn, if_exists='replace', index=False)
        conn.close()
        print("Database created successfully")
        
        # Print sample of data
        print("\nSample of processed data:")
        print(properties_df[['property_id', 'price', 'fair_price', 'propertyTypeDimension']].head())
        
    except Exception as e:
        print(f"Error creating database: {str(e)}")
        raise

if __name__ == "__main__":
    base_dir = Path(__file__).parent
    csv_path = base_dir / "lotwize_case.csv"
    create_db(str(csv_path))