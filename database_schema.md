# Real Estate Database Schema

## Properties Table
Primary table containing core property information.

| Column Name | Type | Description | Index |
|------------|------|-------------|--------|
| property_id | INTEGER | Primary Key, Auto-increment | PRIMARY |
| price | REAL | Property listing price | YES |
| homeStatus | TEXT | Current status (e.g., for sale, pending) | YES |
| propertyTypeDimension | TEXT | Type of property | YES |
| homeType | TEXT | Specific home classification | YES |
| livingArea | REAL | Square footage of living space | YES |
| bedrooms | INTEGER | Number of bedrooms | YES |
| bathrooms | REAL | Number of bathrooms | YES |
| yearBuilt | INTEGER | Year property was constructed | NO |
| lotSize | REAL | Total lot size | NO |
| latitude | REAL | Geographic latitude | NO |
| longitude | REAL | Geographic longitude | NO |
| zestimate | REAL | Zillow's estimated value | NO |
| rentZestimate | REAL | Estimated monthly rent | NO |
| taxAssessedValue | REAL | Tax assessment value | NO |
| taxAssessedYear | INTEGER | Year of tax assessment | NO |
| propertyTaxRate | REAL | Property tax rate | YES |
| monthlyHoaFee | REAL | Monthly HOA fees | YES |

## Location Table
Contains address and location details for each property.

| Column Name | Type | Description | Index |
|------------|------|-------------|--------|
| property_id | INTEGER | Primary Key, Foreign Key to properties | PRIMARY |
| streetAddress | TEXT | Street address | NO |
| city | TEXT | City name | YES |
| state | TEXT | State code | YES |
| zipcode | TEXT | ZIP code | YES |
| county | TEXT | County name | YES |
| countyFIPS | TEXT | County FIPS code | NO |

## Schools Table
Information about nearby schools for each property.

| Column Name | Type | Description | Index |
|------------|------|-------------|--------|
| school_id | INTEGER | Primary Key, Auto-increment | PRIMARY |
| property_id | INTEGER | Foreign Key to properties | YES |
| name | TEXT | School name | NO |
| distance | REAL | Distance from property | NO |
| grades | TEXT | Grade levels | NO |
| level | TEXT | School level (elementary, middle, etc.) | NO |
| rating | INTEGER | School rating (1-10) | YES |
| type | TEXT | School type (public, private, etc.) | NO |

## Price History Table
Historical price and event data for each property.

| Column Name | Type | Description | Index |
|------------|------|-------------|--------|
| history_id | INTEGER | Primary Key, Auto-increment | PRIMARY |
| property_id | INTEGER | Foreign Key to properties | YES |
| price | REAL | Historical price | NO |
| date | TEXT | Event date | YES |
| event | TEXT | Type of event (sold, listed, etc.) | NO |
| source | TEXT | Data source | NO |

## Relationships
- Location (1:1) Properties
- Schools (M:1) Properties
- Price History (M:1) Properties

Notes:
- Schema aligns with create_db.py table creation scripts
- Maintains compatibility with existing app.py queries
- Primary/foreign key relationships match the database constraints
- Indexes support common query patterns seen in app.py
- Normalized structure separates location, schools, and price history into related tables