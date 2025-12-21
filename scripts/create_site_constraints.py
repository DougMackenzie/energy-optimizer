"""
Script to create comprehensive site constraints and scenario structure in Google Sheets
Includes template sites with realistic data for testing
"""

import gspread
from google.oauth2.service_account import Credentials
from pathlib import Path

# Template sites with realistic constraints
template_sites = {
    "Sites": [
        {
            "Site_ID": "SITE-TX-001",
            "Site_Name": "Dallas Datacenter Campus",
            "State": "Texas",
            "ISO": "ERCOT",
            "Latitude": 32.7767,
            "Longitude": -96.7970,
            "Altitude_ft": 430,
            "Avg_Temp_F": 75,
            "IT_Capacity_MW": 160,
            "Design_PUE": 1.25,
            "Total_Facility_MW": 200,
            "Load_Factor_Pct": 72,
            "Status": "Active",
            "Created_Date": "2025-12-01",
            "Notes": "Large hyperscale facility"
        },
        {
            "Site_ID": "SITE-VA-001",
            "Site_Name": "Northern Virginia AI Cluster",
            "State": "Virginia",
            "ISO": "PJM",
            "Latitude": 38.9072,
            "Longitude": -77.0369,
            "Altitude_ft": 100,
            "Avg_Temp_F": 58,
            "IT_Capacity_MW": 120,
            "Design_PUE": 1.20,
            "Total_Facility_MW": 144,
            "Load_Factor_Pct": 85,
            "Status": "Planning",
            "Created_Date": "2025-12-15",
            "Notes": "AI training workload focus"
        },
        {
            "Site_ID": "SITE-OK-001",
            "Site_Name": "Tulsa Industrial Park",
            "State": "Oklahoma",
            "ISO": "SPP",
            "Latitude": 36.1540,
            "Longitude": -95.9928,
            "Altitude_ft": 720,
            "Avg_Temp_F": 62,
            "IT_Capacity_MW": 80,
            "Design_PUE": 1.30,
            "Total_Facility_MW": 104,
            "Load_Factor_Pct": 68,
            "Status": "Active",
            "Created_Date": "2025-11-20",
            "Notes": "Mid-size deployment"
        }
    ],
    
    "Site_Constraints": [
        # Texas Site
        {
            "Site_ID": "SITE-TX-001",
            "Site_Name": "Dallas Datacenter Campus",
            # Air Permitting
            "Air_Permit_Type": "Minor Source",
            "NOx_Limit_tpy": 100,
            "CO_Limit_tpy": 250,
            "VOC_Limit_tpy": 25,
            "Nonattainment_Area": "No",
            # Gas Supply
            "Gas_Available": "Yes",
            "Gas_Pipeline": "NGPL - 30 inch",
            "Gas_Supply_MCF_day": 120000,
            "Gas_Cost_MMBtu": 3.25,
            # Grid/Interconnection
            "Grid_Available_MW": 50,
            "Interconnection_Voltage_kV": 138,
            "Queue_Position": 23,
            "Estimated_Interconnection_Months": 30,
            "Interconnection_Cost_M": 12.5,
            # Land/Physical
            "Total_Land_Acres": 150,
            "Available_Land_Acres": 45,
            "Zoning": "Industrial M-2",
            "Solar_Feasible": "Yes",
            # Reliability/Stability
            "N_Minus_1_Required": "Yes",
            "Max_Transient_pct": 30,
            "Max_Ramp_MW_min": 50,
            "Min_Spinning_Reserve_MW": 40,
            # Strategy Constraints
            "BTM_Allowed": "Yes",
            "IFOM_Allowed": "Yes",
            "Island_Mode_Required": "No",
            "Must_Serve_Load_Pct": 100
        },
        # Virginia Site
        {
            "Site_ID": "SITE-VA-001",
            "Site_Name": "Northern Virginia AI Cluster",
            # Air Permitting
            "Air_Permit_Type": "Minor Source",
            "NOx_Limit_tpy": 100,
            "CO_Limit_tpy": 100,
            "VOC_Limit_tpy": 25,
            "Nonattainment_Area": "Moderate Ozone",
            # Gas Supply
            "Gas_Available": "Yes",
            "Gas_Pipeline": "Transco - 36 inch",
            "Gas_Supply_MCF_day": 95000,
            "Gas_Cost_MMBtu": 3.75,
            # Grid/Interconnection
            "Grid_Available_MW": 200,
            "Interconnection_Voltage_kV": 230,
            "Queue_Position": 147,
            "Estimated_Interconnection_Months": 96,
            "Interconnection_Cost_M": 28.0,
            # Land/Physical
            "Total_Land_Acres": 85,
            "Available_Land_Acres": 15,
            "Zoning": "Data Center District",
            "Solar_Feasible": "Limited",
            # Reliability/Stability
            "N_Minus_1_Required": "Yes",
            "Max_Transient_pct": 25,
            "Max_Ramp_MW_min": 40,
            "Min_Spinning_Reserve_MW": 30,
            # Strategy Constraints
            "BTM_Allowed": "Yes",
            "IFOM_Allowed": "Yes",
            "Island_Mode_Required": "No",
            "Must_Serve_Load_Pct": 100
        },
        # Oklahoma Site
        {
            "Site_ID": "SITE-OK-001",
            "Site_Name": "Tulsa Industrial Park",
            # Air Permitting
            "Air_Permit_Type": "Minor Source",
            "NOx_Limit_tpy": 100,
            "CO_Limit_tpy": 250,
            "VOC_Limit_tpy": 25,
            "Nonattainment_Area": "No",
            # Gas Supply
            "Gas_Available": "Yes",
            "Gas_Pipeline": "Enable Midstream - 24 inch",
            "Gas_Supply_MCF_day": 75000,
            "Gas_Cost_MMBtu": 2.95,
            # Grid/Interconnection
            "Grid_Available_MW": 80,
            "Interconnection_Voltage_kV": 138,
            "Queue_Position": 12,
            "Estimated_Interconnection_Months": 48,
            "Interconnection_Cost_M": 8.5,
            # Land/Physical
            "Total_Land_Acres": 1200,
            "Available_Land_Acres": 850,
            "Zoning": "Industrial",
            "Solar_Feasible": "Yes",
            # Reliability/Stability
            "N_Minus_1_Required": "Yes",
            "Max_Transient_pct": 35,
            "Max_Ramp_MW_min": 30,
            "Min_Spinning_Reserve_MW": 20,
            # Strategy Constraints
            "BTM_Allowed": "Yes",
            "IFOM_Allowed": "Yes",
            "Island_Mode_Required": "No",
            "Must_Serve_Load_Pct": 95
        }
    ],
    
    "Scenario_Templates": [
        {
            "Scenario_ID": "SCN-ALL-SOURCES",
            "Scenario_Name": "All Sources Available",
            "Description": "Full technology stack - all options enabled",
            "Recip_Engines": "True",
            "Gas_Turbines": "True",
            "BESS": "True",
            "Solar_PV": "True",
            "Grid_Connection": "True",
            "Deployment_Strategy": "Hybrid BTM + Grid",
            "Target_LCOE_MWh": 85,
            "Target_Deployment_Months": 24,
            "Notes": "Optimizes across all available technologies"
        },
        {
            "Scenario_ID": "SCN-BTM-ONLY",
            "Scenario_Name": "BTM Only (Microgrid)",
            "Description": "Behind-the-meter generation only, no grid",
            "Recip_Engines": "True",
            "Gas_Turbines": "True",
            "BESS": "True",
            "Solar_PV": "True",
            "Grid_Connection": "False",
            "Deployment_Strategy": "Island Mode Microgrid",
            "Target_LCOE_MWh": 95,
            "Target_Deployment_Months": 18,
            "Notes": "Fastest deployment, no grid dependency"
        },
        {
            "Scenario_ID": "SCN-BESS-GT",
            "Scenario_Name": "BESS + Gas Turbine",
            "Description": "Fast-ramping turbine with battery smoothing",
            "Recip_Engines": "False",
            "Gas_Turbines": "True",
            "BESS": "True",
            "Solar_PV": "False",
            "Grid_Connection": "True",
            "Deployment_Strategy": "BTM Primary + Grid Backup",
            "Target_LCOE_MWh": 88,
            "Target_Deployment_Months": 20,
            "Notes": "Optimized for fast ramp response"
        },
        {
            "Scenario_ID": "SCN-GRID-SOLAR",
            "Scenario_Name": "Grid + Solar (Renewable)",
            "Description": "Grid primary with solar offset",
            "Recip_Engines": "False",
            "Gas_Turbines": "False",
            "BESS": "True",
            "Solar_PV": "True",
            "Grid_Connection": "True",
            "Deployment_Strategy": "Grid Primary + Renewable",
            "Target_LCOE_MWh": 72,
            "Target_Deployment_Months": 36,
            "Notes": "Lowest LCOE, grid dependent"
        },
        {
            "Scenario_ID": "SCN-IFOM-BRIDGE",
            "Scenario_Name": "IFOM Bridging Strategy",
            "Description": "Co-located IFOM while awaiting grid",
            "Recip_Engines": "True",
            "Gas_Turbines": "True",
            "BESS": "True",
            "Solar_PV": "True",
            "Grid_Connection": "True",
            "Deployment_Strategy": "IFOM Bridge to Grid",
            "Target_LCOE_MWh": 92,
            "Target_Deployment_Months": 18,
            "Notes": "Early energization, transitions to grid later"
        }
    ],
    
    "Load_Requirements": [
        {
            "Site_ID": "SITE-TX-001",
            "Scenario_ID": "SCN-ALL-SOURCES",
            "Year": 2026,
            "Required_MW": 200,
            "BTM_Target_Pct": 70,
            "IFOM_Target_Pct": 20,
            "Grid_Target_Pct": 10,
            "Availability_Target_Pct": 99.99,
            "N_Minus_X": 1,
            "Notes": "Year 1 target"
        },
        {
            "Site_ID": "SITE-TX-001",
            "Scenario_ID": "SCN-BTM-ONLY",
            "Year": 2026,
            "Required_MW": 200,
            "BTM_Target_Pct": 100,
            "IFOM_Target_Pct": 0,
            "Grid_Target_Pct": 0,
            "Availability_Target_Pct": 99.95,
            "N_Minus_X": 2,
            "Notes": "Full microgrid operation"
        }
    ],
    
    "Optimization_Objectives": [
        {
            "Site_ID": "SITE-TX-001",
            "Primary_Objective": "Fastest Deployment",
            "LCOE_Max_MWh": 95,
            "PPA_Target_MWh": 88,
            "CAPEX_Max_M": 450,
            "Deployment_Max_Months": 24,
            "Reliability_Min_Pct": 99.95,
            "Emissions_Constraint": "Minor Source",
            "Grid_Dependency_Max_Pct": 30,
            "Weight_LCOE": 0.3,
            "Weight_Deployment_Speed": 0.5,
            "Weight_Reliability": 0.2
        },
        {
            "Site_ID": "SITE-VA-001",
            "Primary_Objective": "Lowest LCOE",
            "LCOE_Max_MWh": 85,
            "PPA_Target_MWh": 78,
            "CAPEX_Max_M": 500,
            "Deployment_Max_Months": 36,
            "Reliability_Min_Pct": 99.99,
            "Emissions_Constraint": "Minor Source",
            "Grid_Dependency_Max_Pct": 50,
            "Weight_LCOE": 0.6,
            "Weight_Deployment_Speed": 0.2,
            "Weight_Reliability": 0.2
        }
    ]
}


def create_comprehensive_structure():
    """Create comprehensive site constraints and scenario structure"""
    
    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    
    creds_path = Path(__file__).parent.parent / "credentials.json"
    creds = Credentials.from_service_account_file(str(creds_path), scopes=SCOPES)
    client = gspread.authorize(creds)
    
    # Open existing spreadsheet
    sheet_id = "1a3AhvgtwyoNtxEVOJt82gwzLNt13c8uDttKHg1eB0so"
    spreadsheet = client.open_by_key(sheet_id)
    
    print(f"✅ Opened spreadsheet: {spreadsheet.title}")
    print(f"🔗 URL: {spreadsheet.url}\n")
    
    # Create each worksheet
    for sheet_name, data in template_sites.items():
        try:
            # Try to get existing worksheet or create new
            try:
                worksheet = spreadsheet.worksheet(sheet_name)
                worksheet.clear()
                print(f"📝 Cleared existing sheet: {sheet_name}")
            except:
                worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=100, cols=40)
                print(f"✨ Created new sheet: {sheet_name}")
            
            if not data:
                continue
            
            # Get headers from first item
            headers = list(data[0].keys())
            
            # Prepare data rows
            rows = [headers]
            for item in data:
                row = [str(item.get(h, "")) for h in headers]
                rows.append(row)
            
            # Update the worksheet
            worksheet.update(values=rows, range_name='A1')
            
            # Format header row
            worksheet.format('A1:AZ1', {
                "backgroundColor": {"red": 0.12, "green": 0.23, "blue": 0.37},
                "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
                "horizontalAlignment": "CENTER"
            })
            
            print(f"   ✅ Added {len(data)} items to {sheet_name}")
            
        except Exception as e:
            print(f"   ❌ Error with {sheet_name}: {e}")
    
    print(f"\n✅ Site constraints structure created successfully!")
    print(f"📊 Created worksheets:")
    print(f"   • Sites (3 template sites)")
    print(f"   • Site_Constraints (comprehensive constraints)")
    print(f"   • Scenario_Templates (5 pre-loaded scenarios)")
    print(f"   • Load_Requirements (MW targets by source)")
    print(f"   • Optimization_Objectives (goals and weights)")


if __name__ == "__main__":
    create_comprehensive_structure()
