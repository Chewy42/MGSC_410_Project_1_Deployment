from shiny import render
import plotly.graph_objects as go
import pandas as pd

def register_analysis_handlers(input, output, session, property_service, scoring_service):
    @output
    @render.ui
    def roi_analysis():
        filters = {
            'price_range': input.price_range(),
            'property_types': input.property_types(),
            'sqft_range': input.sqft_range(),
            'location': input.location()
        }
        
        properties = property_service.search_properties(filters)
        scores = scoring_service.score_properties(properties)
        
        # Create ROI analysis plot
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=[p.property.price for p in scores],
            y=[p.roi_score for p in scores],
            mode='markers',
            marker=dict(
                size=[p.property.living_area/100 for p in scores],
                color=[p.total_score for p in scores],
                colorscale='Viridis',
                showscale=True
            ),
            text=[
                f"Address: {p.property.address}<br>"
                f"Price: ${p.property.price:,.0f}<br>"
                f"ROI Score: {p.roi_score:.1f}"
                for p in scores
            ],
            hovertemplate="%{text}<extra></extra>"
        ))
        
        fig.update_layout(
            title="ROI Analysis by Property Price",
            xaxis_title="Property Price ($)",
            yaxis_title="ROI Score",
            showlegend=False
        )
        
        return fig.to_html(include_plotlyjs="cdn")

    @output
    @render.ui
    def risk_assessment():
        filters = {
            'price_range': input.price_range(),
            'property_types': input.property_types(),
            'sqft_range': input.sqft_range(),
            'location': input.location()
        }
        
        properties = property_service.search_properties(filters)
        scores = scoring_service.score_properties(properties)
        
        # Create risk assessment radar chart
        categories = ['Price Volatility', 'Vacancy', 'Market', 'Location', 'Property Condition']
        
        fig = go.Figure()
        
        for score in scores[:5]:  # Show top 5 properties
            fig.add_trace(go.Scatterpolar(
                r=[
                    10 - score.risk_score,  # Invert risk score
                    score.property.vacancy_risk if hasattr(score.property, 'vacancy_risk') else 5,
                    score.market_score,
                    score.location_score,
                    score.condition_score
                ],
                theta=categories,
                fill='toself',
                name=f"{score.property.address[:30]}..."
            ))
            
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 10]
                )
            ),
            showlegend=True,
            title="Risk Assessment - Top Properties"
        )
        
        return fig.to_html(include_plotlyjs="cdn") 