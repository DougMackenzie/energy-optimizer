"""
Gemini API Client for AI-Generated Report Content
Generates executive summaries, financial analysis, and recommendations
"""

import os
from typing import Dict, List, Optional
import google.generativeai as genai

class GeminiReportClient:
    """Client for generating AI-powered report content using Gemini 3 Flash"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Gemini client
        
        Args:
            api_key: Gemini API key (defaults to GEMINI_API_KEY env var)
        """
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("Gemini API key not found. Set GEMINI_API_KEY environment variable.")
        
        genai.configure(api_key=self.api_key)
        
        # Try latest models in order of preference
        try:
            # Gemini 3 Flash Preview (Latest!)
            self.model = genai.GenerativeModel('gemini-3-flash-preview')
            self.model_name = 'Gemini 3 Flash Preview'
        except:
            try:
                # Gemini 2.5 Flash (Stable, June 2025)
                self.model = genai.GenerativeModel('gemini-2.5-flash')
                self.model_name = 'Gemini 2.5 Flash'
            except:
                try:
                    # Gemini 2.0 Flash Experimental
                    self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
                    self.model_name = 'Gemini 2.0 Flash (Experimental)'
                except:
                    # Last fallback
                    self.model = genai.GenerativeModel('gemini-pro')
                    self.model_name = 'Gemini Pro'
    
    def generate_executive_summary(self, portfolio_data: Dict) -> str:
        """
        Generate executive summary from portfolio metrics
        
        Args:
            portfolio_data: Dict with portfolio-level metrics
        
        Returns:
            Executive summary text (2-3 paragraphs)
        """
        prompt = f"""
You are a senior energy analyst writing an executive summary for an energy optimization portfolio report.

Portfolio Data:
- Total Sites: {portfolio_data.get('num_sites', 0)}
- Total IT Capacity: {portfolio_data.get('total_capacity_mw', 0):.0f} MW
- Weighted Average LCOE: ${portfolio_data.get('weighted_lcoe', 0):.1f}/MWh
- Total NPV: ${portfolio_data.get('total_npv_m', 0):.1f}M
- Total CapEx: ${portfolio_data.get('total_capex_m', 0):.1f}M
- Portfolio IRR: {portfolio_data.get('portfolio_irr', 0):.1f}%

Write a brief, professional 2-3 paragraph executive summary highlighting:
1. Overall portfolio performance and key metrics
2. Investment attractiveness and financial viability
3. Notable strengths or opportunities

Keep it concise and actionable. Use specific numbers from the data.
"""
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            return f"Error generating summary: {str(e)}"
    
    def analyze_financial_results(self, site_data: Dict) -> str:
        """
        Generate financial analysis for a site
        
        Args:
            site_data: Dict with site financial metrics
        
        Returns:
            Financial analysis text
        """
        prompt = f"""
You are a financial analyst writing a financial analysis section for an energy project.

Site: {site_data.get('site_name', 'Unknown')}
- LCOE: ${site_data.get('lcoe', 0):.2f}/MWh
- NPV: ${site_data.get('npv_m', 0):.1f}M
- CapEx: ${site_data.get('capex_m', 0):.1f}M
- OpEx (Annual): ${site_data.get('opex_annual_m', 0):.1f}M/yr
- IRR: {site_data.get('irr_pct', 0):.1f}%
- Capacity: {site_data.get('capacity_mw', 0):.0f} MW

Write 1-2 paragraphs analyzing the financial viability of this project. Comment on:
1. LCOE competitiveness (benchmark is ~$75-90/MWh for data centers)
2. Return profile (NPV, IRR)
3. Key financial risks or opportunities

Be specific and reference the numbers.
"""
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            return f"Error generating analysis: {str(e)}"
    
    def interpret_technical_results(self, equipment_data: Dict, site_info: Dict) -> str:
        """
        Generate technical analysis of equipment configuration
        
        Args:
            equipment_data: Dict with equipment specs
            site_info: Dict with site information
        
        Returns:
            Technical analysis text
        """
        prompt = f"""
You are a power systems engineer analyzing an energy optimization solution for a data center.

Site: {site_info.get('site_name', 'Unknown')}
IT Load: {site_info.get('it_capacity_mw', 0):.0f} MW

Equipment Configuration:
- Reciprocating Engines: {equipment_data.get('recip_mw', 0):.0f} MW
- Gas Turbines: {equipment_data.get('turbine_mw', 0):.0f} MW
- BESS: {equipment_data.get('bess_mwh', 0):.0f} MWh
- Solar: {equipment_data.get('solar_mw', 0):.0f} MW DC
- Grid: {equipment_data.get('grid_mw', 0):.0f} MW

Write 1-2 paragraphs analyzing this technical solution. Comment on:
1. Equipment mix rationale (BTM generation vs grid vs renewables)
2. Reliability and redundancy considerations
3. Technical strengths or concerns

Be concise and technically accurate.
"""
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            return f"Error generating technical analysis: {str(e)}"
    
    def generate_recommendations(self, portfolio_data: Dict, site_results: List[Dict]) -> str:
        """
        Generate strategic recommendations based on portfolio results
        
        Args:
            portfolio_data: Portfolio-level metrics
            site_results: List of site result dictionaries
        
        Returns:
            Recommendations text
        """
        # Calculate some insights
        avg_lcoe = portfolio_data.get('weighted_lcoe', 0)
        best_site = min(site_results, key=lambda x: x.get('lcoe', 999)) if site_results else {}
        
        prompt = f"""
You are a strategic advisor for energy infrastructure investment.

Portfolio Summary:
- {portfolio_data.get('num_sites', 0)} sites analyzed
- Average LCOE: ${avg_lcoe:.1f}/MWh
- Best performer: {best_site.get('site_name', 'N/A')} at ${best_site.get('lcoe', 0):.1f}/MWh
- Total NPV: ${portfolio_data.get('total_npv_m', 0):.1f}M

Write 3-4 bullet point recommendations for:
1. Portfolio optimization opportunities
2. Risk mitigation strategies  
3. Next steps for development

Keep recommendations actionable and specific.
"""
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            return f"Error generating recommendations: {str(e)}"
    
    def analyze_lcoe_drivers(self, site_data: Dict) -> str:
        """
        Analyze LCOE drivers and cost breakdown
        
        Args:
            site_data: Site financial data
        
        Returns:
            LCOE analysis text
        """
        prompt = f"""
You are analyzing the levelized cost of energy (LCOE) for a data center power project.

Site: {site_data.get('site_name', 'Unknown')}
- LCOE: ${site_data.get('lcoe', 0):.2f}/MWh
- CapEx: ${site_data.get('capex_m', 0):.1f}M
- Annual OpEx: ${site_data.get('opex_annual_m', 0):.2f}M
- Annual Generation: {site_data.get('annual_generation_gwh', 0):.1f} GWh

Write a brief paragraph (3-4 sentences) explaining the key LCOE drivers and opportunities for cost reduction.
"""
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            return f"Error analyzing LCOE: {str(e)}"


def test_gemini_connection():
    """Test Gemini API connection"""
    try:
        client = GeminiReportClient()
        print(f"✓ Gemini API connection successful!")
        print(f"✓ Using model: {client.model_name}")
        
        test_data = {
            'num_sites': 3,
            'total_capacity_mw': 450,
            'weighted_lcoe': 78.5,
            'total_npv_m': 125,
            'total_capex_m': 850,
            'portfolio_irr': 12.5
        }
        
        summary = client.generate_executive_summary(test_data)
        print(f"\nTest summary:\n{summary}")
        return True
    except Exception as e:
        print(f"✗ Gemini API connection failed: {e}")
        return False


if __name__ == "__main__":
    test_gemini_connection()
