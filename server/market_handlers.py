from shiny import render, ui
import plotly.graph_objects as go
import pandas as pd

def register_market_handlers(input, output, session, market_service):
    @output
    @render.ui
    def market_trends():
        location = input.location() or "National Average"
        trends = market_service.get_market_trends(location)
        
        # Create market trends plot
        fig = go.Figure()
        
        # Price trends
        fig.add_trace(go.Indicator(
            mode="number+delta",
            value=trends['price_trend']['last_year'],
            delta={'reference': 0},
            title={'text': "Price Change (YoY)"},
            domain={'row': 0, 'column': 0}
        ))
        
        # Inventory levels
        fig.add_trace(go.Indicator(
            mode="gauge+number",
            value=trends['inventory_level']['current'],
            title={'text': "Months of Inventory"},
            gauge={'axis': {'range': [0, 12]}},
            domain={'row': 0, 'column': 1}
        ))
        
        # Days on market
        fig.add_trace(go.Indicator(
            mode="number+delta",
            value=trends['days_on_market']['average'],
            delta={'reference': trends['days_on_market']['average'] + trends['days_on_market']['trend']},
            title={'text': "Avg Days on Market"},
            domain={'row': 0, 'column': 2}
        ))
        
        fig.update_layout(
            grid={'rows': 1, 'columns': 3},
            title=f"Market Trends - {location}",
            height=350,
            margin=dict(t=30, b=30)
        )
        
        return ui.HTML(fig.to_html(include_plotlyjs="cdn"))

    @output
    @render.ui
    def demographic_data():
        location = input.location() or "National Average"
        demographics = market_service.get_demographic_data(location)
        
        # Create demographics visualization
        fig = go.Figure()
        
        # Population metrics
        fig.add_trace(go.Indicator(
            mode="number+delta",
            value=demographics['population']['total'],
            delta={'reference': demographics['population']['total'] * (1 - demographics['population']['growth_rate']/100)},
            title={'text': "Population"},
            domain={'row': 0, 'column': 0}
        ))
        
        # Income metrics
        fig.add_trace(go.Indicator(
            mode="number+delta",
            value=demographics['income']['median'],
            delta={'reference': demographics['income']['median'] * (1 - demographics['income']['growth_rate']/100)},
            title={'text': "Median Income"},
            domain={'row': 0, 'column': 1}
        ))
        
        # Employment metrics
        fig.add_trace(go.Indicator(
            mode="gauge+number",
            value=demographics['employment']['rate'],
            title={'text': "Employment Rate"},
            gauge={'axis': {'range': [0, 100]}},
            domain={'row': 0, 'column': 2}
        ))
        
        fig.update_layout(
            grid={'rows': 1, 'columns': 3},
            title=f"Demographics - {location}",
            height=350,
            margin=dict(t=30, b=30)
        )
        
        return ui.HTML(fig.to_html(include_plotlyjs="cdn"))

    @output
    @render.ui
    def economic_indicators():
        location = input.location() or "National Average"
        indicators = market_service.get_economic_indicators(location)
        
        # Create economic indicators visualization
        fig = go.Figure()
        
        categories = ['GDP Growth', 'Job Growth', 'Business Growth']
        values = [
            indicators['gdp_growth'],
            indicators['job_growth'],
            indicators['business_growth']
        ]
        
        fig.add_trace(go.Bar(
            x=categories,
            y=values,
            text=[f"{v:.1f}%" for v in values],
            textposition='auto',
        ))
        
        fig.update_layout(
            title=f"Economic Indicators - {location}",
            yaxis_title="Growth Rate (%)",
            showlegend=False,
            height=350,
            margin=dict(t=30, b=30)
        )
        
        return ui.HTML(fig.to_html(include_plotlyjs="cdn"))
