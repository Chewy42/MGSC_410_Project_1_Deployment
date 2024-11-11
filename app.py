from shiny import App, ui, render
from ui.sidebar import InvestmentSidebar
from ui.main_panel import MainPanel
from server.property_handlers import register_property_handlers
from server.market_handlers import register_market_handlers
from server.analysis_handlers import register_analysis_handlers
from server.input_handlers import register_input_handlers
from services.property_service import PropertyService
from services.market_service import MarketService
from services.scoring_service import ScoringService
from models.property import Property
import pandas as pd
from pathlib import Path
from create_db import create_db
from shiny import reactive

# Initialize services
property_service = PropertyService()
market_service = MarketService()
scoring_service = ScoringService()

# Create UI components
sidebar = InvestmentSidebar()
main_panel = MainPanel()

app_ui = ui.page_fluid(
    ui.tags.head(
        ui.tags.link(rel="stylesheet", href="styles.css"),
    ),
    ui.div(
        {"class": "header"},
        ui.h2("Real Estate Investment Optimizer")
    ),
    ui.div(
        {"class": "main-container"},
        ui.row(
            ui.column(3, sidebar.create()),
            ui.column(9, main_panel.create())
        )
    )
)

def calculate_investment_score(property: Property) -> float:
    """Calculate an investment score from 0-10"""
    score = 0
    
    # Cap rate score (0-4 points)
    if property.price > 0:
        cap_rate = (property.rent_estimate * 12) / property.price
        score += min(cap_rate * 40, 4)
    
    # Appreciation potential (0-3 points)
    if property.price > 0:
        appreciation = (property.zestimate - property.price) / property.price
        score += min(appreciation * 10, 3)
    
    # Property age (0-2 points)
    if property.year_built:
        age_score = min((2023 - property.year_built) / 100, 1)
        score += 2 * (1 - age_score)
    
    # HOA consideration (0-1 point)
    if not property.monthly_hoa or property.monthly_hoa < 200:
        score += 1
    
    return score

def safe_format_address(address, city, state, zipcode):
    """Safely format address components"""
    parts = []
    if address and str(address).strip() != 'Address Not Available':
        parts.append(str(address))
    if city and str(city).strip() != 'City Not Available':
        parts.append(str(city))
    if state and str(state).strip() != 'NA':
        parts.append(str(state))
    if zipcode and str(zipcode).strip() != '00000':
        parts.append(str(zipcode))
    return ' '.join(parts) if parts else 'Address Not Available'

def server(input, output, session):
    # Register all handlers
    register_property_handlers(input, output, session, property_service, scoring_service, market_service)
    register_market_handlers(input, output, session, market_service)
    register_analysis_handlers(input, output, session, property_service, scoring_service)
    register_input_handlers(input, session)

    @output
    @render.table
    def opportunities_table():
        # Force reactivity on refresh button
        input.refresh_dashboard()
        
        # Get current filters from sidebar
        selected_types = input.property_types()
        print(f"Selected property types (raw input): {selected_types}")  # Debug print
        
        filters = {
            'price_min': input.price_min() or 100000,
            'price_max': input.price_max() or 2000000,
            'property_types': selected_types,  # Pass through directly
            'sqft_min': input.sqft_min() or 500,
            'sqft_max': input.sqft_max() or 5000,
            'location': input.location() if input.location() and input.location().strip() else None,
            'max_hoa': None
        }
        
        print(f"Filters being passed to service: {filters}")  # Debug print
        
        try:
            properties = property_service.get_investment_opportunities(sort_by='score', limit=50, filters=filters)
            print(f"Retrieved {len(properties)} properties")  # Debug print
            if properties:
                print("Sample property types:", [p.property_type for p in properties[:5]])  # Debug print
            
            # Create a list of dictionaries for the DataFrame
            data = []
            for p in properties:
                try:
                    formatted_address = safe_format_address(p.address, p.city, p.state, p.zipcode)
                    # Safe value formatting with error handling
                    def safe_format(value, format_func):
                        try:
                            return format_func(value) if value is not None else "N/A"
                        except:
                            return "N/A"
                    
                    # Calculate price difference and percentage
                    price_diff = p.fair_price - p.price if p.fair_price and p.price else None
                    price_diff_pct = (price_diff / p.price * 100) if price_diff is not None and p.price else None
                    
                    # Calculate cap rate and appreciation safely
                    cap_rate = (p.rent_estimate * 12 / p.price * 100) if p.price and p.rent_estimate else None
                    appreciation = ((p.zestimate - p.price) / p.price * 100) if p.price and p.zestimate else None
                    
                    # Clean up and standardize property type display
                    property_type = 'Unknown'
                    if p.property_type:
                        cleaned_type = p.property_type.strip().upper()
                        # Map common variations to standard names
                        type_mapping = {
                            'SINGLE FAMILY': 'Single Family',
                            'SINGLE-FAMILY': 'Single Family',
                            'SINGLEFAMILY': 'Single Family',
                            'CONDO': 'Condo',
                            'CONDOMINIUM': 'Condo',
                            'TOWNHOUSE': 'Townhouse',
                            'TOWN_HOUSE': 'Townhouse',
                            'MULTI-FAMILY': 'Multi-Family',
                            'MULTI FAMILY': 'Multi-Family',
                            'LAND': 'Land'
                        }
                        property_type = type_mapping.get(cleaned_type, cleaned_type.title())
                    
                    data.append({
                        'Address': formatted_address,
                        'City': p.city or 'N/A',
                        'State': p.state or 'N/A',
                        'ZIP': p.zipcode or 'N/A',
                        'Price': safe_format(p.price, lambda x: f"${x:,.0f}"),
                        'Fair Price': safe_format(p.fair_price, lambda x: f"${x:,.0f}"),
                        'Price Diff': f"${price_diff:+,.0f} ({price_diff_pct:+.1f}%)" if price_diff is not None else 'N/A',
                        'Type': property_type,
                        'Beds/Baths': f"{p.bedrooms or 0}/{p.bathrooms or 0}",
                        'Sqft': safe_format(p.living_area, lambda x: f"{x:,.0f}"),
                        'Year Built': safe_format(p.year_built, lambda x: f"{int(x)}"),
                        'Cap Rate': safe_format(cap_rate, lambda x: f"{x:.1f}%"),
                        'Monthly Rent': safe_format(p.rent_estimate, lambda x: f"${x:,.0f}"),
                        'HOA': safe_format(p.monthly_hoa, lambda x: f"${x:,.0f}"),
                        'Appreciation': safe_format(appreciation, lambda x: f"{x:.1f}%"),
                        'Investment Score': safe_format(calculate_investment_score(p), lambda x: f"{x:.1f}"),
                        'Location': ui.HTML(f'<a href="https://www.google.com/maps/search/?api=1&query={formatted_address.replace(" ", "+")}" target="_blank" class="map-link">🗺️ View</a>') if formatted_address != 'Address Not Available' else 'N/A'
                    })
                except Exception as row_error:
                    print(f"Error processing row: {str(row_error)}")
                    continue
            
            # Convert to DataFrame
            df = pd.DataFrame(data)
            
            # Add CSS class for styling
            return df.style.set_properties(**{
                'text-align': 'left',
                'white-space': 'nowrap',
                'padding': '8px 12px',
                'border-bottom': '1px solid #eef2f7'
            }).format({
                'Location': lambda x: str(x)
            })
            
        except Exception as e:
            print(f"Error in opportunities_table: {str(e)}")
            return pd.DataFrame(columns=[
                'Address', 'City', 'State', 'ZIP', 'Price', 'Fair Price', 'Price Diff', 'Type', 
                'Beds/Baths', 'Sqft', 'Year Built', 'Cap Rate', 
                'Monthly Rent', 'HOA', 'Appreciation', 'Investment Score', 'Location'
            ])

    @output
    @render.ui
    def heatmap():
        # Force reactivity on refresh button
        input.refresh_dashboard()
        
        try:
            # Get current filters and location from sidebar
            location = input.location() if input.location() and input.location().strip() else "93720"
            metric = input.heatmap_metric()
            
            # Get the number of results from the sidebar input
            result_limit = input.top_n() if input.top_n() else 50
            
            print(f"Current location: {location}")  # Debug print
            print(f"Current metric: {metric}")  # Debug print
            print(f"Result limit: {result_limit}")  # Debug print
            
            filters = {
                'price_min': input.price_min() or 100000,
                'price_max': input.price_max() or 2000000,
                'property_types': input.property_types() or None,
                'sqft_min': input.sqft_min() or 500,
                'sqft_max': input.sqft_max() or 5000,
                'location': location,
                'max_hoa': None
            }
            
            # Pass the limit from the sidebar input
            properties = property_service.get_investment_opportunities('score', result_limit, filters)
            print(f"Found {len(properties)} properties")  # Debug print
            
            # Always use sidebar location as center
            center_location = location
            
            # Prepare data points
            data_points = []
            for p in properties:
                if p.latitude and p.longitude:
                    # Get intensity based on selected metric
                    intensity = {
                        'price': float(p.price) if p.price else 0,
                        'fair_price': float(p.fair_price) if p.fair_price else 0,
                        'price_diff': float(p.fair_price - p.price) if p.fair_price and p.price else 0,
                        'sqft': float(p.living_area) if p.living_area else 0,
                        'score': float(calculate_investment_score(p)),
                        'roi': float((p.zestimate - p.price) / p.price) if p.price and p.zestimate else 0
                    }.get(metric, float(p.price) if p.price else 0)
                    
                    # Calculate price difference and percentage
                    price_diff = p.fair_price - p.price if p.fair_price and p.price else None
                    price_diff_pct = (price_diff / p.price * 100) if price_diff is not None and p.price else None
                    
                    property_data = {
                        'address': f"{p.address}, {p.city}",
                        'price': p.price,
                        'fair_price': p.fair_price,
                        'price_diff': f"${price_diff:+,.0f}" if price_diff is not None else "N/A",
                        'price_diff_pct': f"{price_diff_pct:+.1f}%" if price_diff_pct is not None else "N/A",
                        'type': p.property_type or 'Unknown',
                        'sqft': p.living_area,
                        'beds': p.bedrooms,
                        'baths': p.bathrooms,
                        'year_built': p.year_built,
                        'rent': p.rent_estimate,
                        'cap_rate': (p.rent_estimate * 12 / p.price * 100) if p.price and p.rent_estimate else 0,
                        'score': calculate_investment_score(p)
                    }
                    
                    data_points.append([float(p.latitude), float(p.longitude), intensity, property_data])
            
            # Update the top_n input with actual number of results
            ui.update_numeric("top_n", value=len(data_points))
            
            print(f"Created {len(data_points)} data points")  # Debug print
            
            # Create and return the heatmap
            return ui.HTML(MainPanel.create_heatmap(center_location, data_points, metric))
            
        except Exception as e:
            print(f"Error rendering heatmap: {str(e)}")
            import traceback
            traceback.print_exc()  # Print full stack trace
            return ui.div(f"Error rendering heatmap: {str(e)}")

    # Add input validation handlers
    @reactive.Effect
    def _validate_price():
        try:
            price_min = input.price_min() or 100000
            price_max = input.price_max() or 2000000
            
            if price_min < 0:
                ui.update_numeric("price_min", value=0)
            
            if price_max <= price_min:
                ui.update_numeric("price_max", value=max(price_min + 50000, 100000))
        except Exception as e:
            print(f"Error in price validation: {str(e)}")

    @reactive.Effect
    def _validate_sqft():
        try:
            sqft_min = input.sqft_min() or 500
            sqft_max = input.sqft_max() or 5000
            
            if sqft_min < 0:
                ui.update_numeric("sqft_min", value=0)
            
            if sqft_max <= sqft_min:
                ui.update_numeric("sqft_max", value=max(sqft_min + 100, 500))
        except Exception as e:
            print(f"Error in sqft validation: {str(e)}")

app = App(app_ui, server, static_assets=Path(__file__).parent / "www")

if __name__ == "__main__":
    print("Starting server on 0.0.0.0:8000...")
    create_db("lotwize_case.csv")
    app.run(host="0.0.0.0", port=8000)