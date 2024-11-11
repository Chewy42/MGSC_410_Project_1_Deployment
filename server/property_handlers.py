from shiny import render, ui, reactive
import plotly.graph_objects as go
import pandas as pd
import numpy as np

def register_property_handlers(input, output, session, property_service, scoring_service, market_service):
    # Add reactive values to track refresh button clicks and map state
    refresh_trigger = reactive.Value(0)
    current_zoom = reactive.Value(11)  # Default zoom level
    default_location = "94110"  # Match sidebar default
    
    @reactive.Effect
    @reactive.event(input.refresh_dashboard)
    def _handle_refresh():
        refresh_trigger.set(refresh_trigger() + 1)

    # Add a callback to store zoom level changes
    @session.download
    def store_map_zoom(zoom_level):
        current_zoom.set(float(zoom_level))

    def _get_current_filters():
        """Helper function to get current filters consistently"""
        return {
            'price_min': input.price_min() or 100000,
            'price_max': input.price_max() or 2000000,
            'property_types': input.property_types(),
            'sqft_min': input.sqft_min() or 500,
            'sqft_max': input.sqft_max() or 5000,
            'location': input.location() if input.location() and input.location().strip() else default_location,
            'show_max_results': input.show_max_results()
        }

    @output
    @render.ui
    @reactive.event(input.refresh_dashboard, input.heatmap_metric)
    def map():
        filters = _get_current_filters()
        limit = 2000 if filters['show_max_results'] else input.top_n() or 50
        
        try:
            properties = property_service.get_investment_opportunities(
                sort_by='score',
                limit=limit,
                filters=filters
            )
            scores = scoring_service.score_properties(properties)
            
            if not properties:
                fig = go.Figure().update_layout(
                    title="No properties found matching criteria",
                    height=400
                )
                return ui.HTML(fig.to_html(include_plotlyjs="cdn"))
            
            # Get heatmap values based on selected metric
            heatmap_metric = input.heatmap_metric()
            if heatmap_metric == "price":
                z_values = [p.price for p in properties]
                hover_text = [f"${p.price:,.0f}" for p in properties]
                colorbar_title = "Price ($)"
            elif heatmap_metric == "sqft":
                z_values = [p.living_area for p in properties]
                hover_text = [f"{p.living_area:,.0f} sqft" for p in properties]
                colorbar_title = "Square Footage"
            elif heatmap_metric == "score":
                z_values = [s.total_score for s in scores]
                hover_text = [f"Score: {s.total_score:.1f}" for s in scores]
                colorbar_title = "Property Score"
            else:  # roi
                z_values = [s.roi_score for s in scores]
                hover_text = [f"ROI: {s.roi_score:.1f}%" for s in scores]
                colorbar_title = "ROI (%)"
            
            data_points = []
            for p, hover, z in zip(properties, hover_text, z_values):
                property_data = {
                    'address': f"{p.address}, {p.city}",
                    'price': p.price,
                    'fair_price': p.fair_price,  # Include fair price
                    'type': p.property_type or 'Unknown',
                    'sqft': p.living_area,
                    'beds': p.bedrooms,
                    'baths': p.bathrooms,
                    'year_built': p.year_built,
                    'rent': p.rent_estimate,
                    'cap_rate': (p.rent_estimate * 12 / p.price * 100) if p.price and p.rent_estimate else 0,
                    'score': calculate_investment_score(p)
                }
                data_points.append([float(p.latitude), float(p.longitude), z, property_data])
            
            return ui.HTML(MainPanel.create_heatmap(location, data_points, metric=heatmap_metric))
            
        except Exception as e:
            print(f"Error rendering heatmap: {str(e)}")
            import traceback
            traceback.print_exc()
            return ui.HTML("Error creating map")

    # Add handler for zoom level changes
    @reactive.Effect
    @reactive.event(input.map_zoom)
    def _handle_zoom_change():
        if input.map_zoom() is not None:
            current_zoom.set(input.map_zoom())

    @output
    @render.table
    @reactive.event(input.refresh_dashboard, input.sort_criteria)
    def opportunities_table():
        try:
            filters = _get_current_filters()
            limit = 2000 if filters['show_max_results'] else input.top_n() or 50
            
            properties = property_service.get_investment_opportunities(
                sort_by=input.sort_criteria() or 'score',
                limit=limit,
                filters=filters
            )
            
            # Debug print
            print(f"Found {len(properties)} properties")
            if properties:
                print("Sample property prices:")
                for p in properties[:3]:
                    print(f"Price: ${p.price:,.0f}, Fair Price: ${p.fair_price:,.0f}")
            
            scores = scoring_service.score_properties(properties)
            
            if not properties:
                return pd.DataFrame()
            
            # Pre-filter properties based on price difference percentage
            filtered_properties_and_scores = []
            for p, s in zip(properties, scores):
                if not p.fair_price or not p.price:
                    continue
                    
                price_diff = p.fair_price - p.price
                price_diff_pct = (price_diff / p.price * 100)
                
                if abs(price_diff_pct) <= 50:
                    filtered_properties_and_scores.append((p, s))
                else:
                    print(f"Filtering out property with {price_diff_pct:.1f}% price difference: {p.address}")
            
            # Create DataFrame for display
            data = []
            for p, s in filtered_properties_and_scores:
                try:
                    # Calculate price difference and percentage
                    price_diff = p.fair_price - p.price
                    price_diff_pct = (price_diff / p.price * 100)
                    
                    row_data = {
                        'Address': p.address,
                        'Price': f"${p.price:,.0f}" if p.price else 'N/A',
                        'Fair Price': f"${p.fair_price:,.0f}" if p.fair_price else 'N/A',
                        'Price Diff': f"${price_diff:+,.0f} ({price_diff_pct:+.1f}%)" if price_diff is not None else 'N/A',
                        'City': p.city,
                        'State': p.state,
                        'ZIP': p.zipcode,
                        'Type': p.property_type,
                        'Beds/Baths': f"{p.bedrooms}/{p.bathrooms}",
                        'Sqft': f"{p.living_area:,.0f}" if p.living_area else 'N/A',
                        'Score': f"{s.total_score:.1f}",
                        'ROI Score': f"{s.roi_score:.1f}"
                    }
                    data.append(row_data)
                    
                except Exception as row_error:
                    print(f"Error processing row: {str(row_error)}")
                    continue
            
            # Create DataFrame with explicit column order
            columns = ['Address', 'Price', 'Fair Price', 'Price Diff', 'City', 'State', 'ZIP', 
                      'Type', 'Beds/Baths', 'Sqft', 'Score', 'ROI Score']
            
            df = pd.DataFrame(data, columns=columns)
            
            # Debug print
            print("DataFrame columns:", df.columns.tolist())
            print("Sample of first row:", df.iloc[0] if not df.empty else "No data")
            
            return df
            
        except Exception as e:
            print(f"Error in opportunities_table: {str(e)}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()

def _calculate_cap_rate(property):
    """Helper function to calculate cap rate"""
    if not property.rent_estimate or not property.price:
        return 0.0
    annual_rent = property.rent_estimate * 12
    operating_expenses = annual_rent * 0.4  # 40% for maintenance, vacancy, etc.
    net_operating_income = annual_rent - operating_expenses
    return (net_operating_income / property.price) * 100
