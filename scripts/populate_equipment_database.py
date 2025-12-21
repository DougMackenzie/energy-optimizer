"""
Script to extract equipment data from PDF report and upload to Google Sheets
Run with: python scripts/populate_equipment_database.py
"""

import os
from pathlib import Path
import gspread
from google.oauth2.service_account import Credentials

# Equipment data extracted from the PDF report
equipment_database = {
    "Reciprocating_Engines": [
        {
            "ID": "wartsila_34sg",
            "Manufacturer": "Wärtsilä",
            "Model": "34SG",
            "Capacity_MW": 9.8,
            "Efficiency_Pct": 44.3,
            "Heat_Rate_BTU_kWh": 7700,
            "Ramp_Rate_MW_min": 4.9,
            "Start_Time_Cold_Min": 10,
            "NOx_lb_MMBtu": 0.099,
            "CO_lb_MMBtu": 0.015,
            "Lead_Time_Months_Min": 18,
            "Lead_Time_Months_Max": 24,
            "CAPEX_per_kW": 1650,
            "VOM_per_MWh": 8.50,
            "FOM_per_kW_yr": 21.50,
            "MTBF_hrs": 2500,
            "MTTR_hrs": 24,
            "Availability_Pct": 92.0,
            "Note": "DLE (Dry Low Emissions)"
        },
        {
            "ID": "wartsila_50sg",
            "Manufacturer": "Wärtsilä",
            "Model": "50SG",
            "Capacity_MW": 18.0,
            "Efficiency_Pct": 46.5,
            "Heat_Rate_BTU_kWh": 7340,
            "Ramp_Rate_MW_min": 9.0,
            "Start_Time_Cold_Min": 10,
            "NOx_lb_MMBtu": 0.099,
            "CO_lb_MMBtu": 0.015,
            "Lead_Time_Months_Min": 18,
            "Lead_Time_Months_Max": 24,
            "CAPEX_per_kW": 1650,
            "VOM_per_MWh": 8.50,
            "FOM_per_kW_yr": 21.50,
            "MTBF_hrs": 2500,
            "MTTR_hrs": 24,
            "Availability_Pct": 92.0,
            "Note": "DLE, Most common for datacenter BTM"
        },
        {
            "ID": "jenbacher_j920",
            "Manufacturer": "INNIO Jenbacher",
            "Model": "J920 FleXtra",
            "Capacity_MW": 10.4,
            "Efficiency_Pct": 45.7,
            "Heat_Rate_BTU_kWh": 7470,
            "Ramp_Rate_MW_min": 5.2,
            "Start_Time_Cold_Min": 10,
            "NOx_lb_MMBtu": 0.099,
            "CO_lb_MMBtu": 0.015,
            "Lead_Time_Months_Min": 18,
            "Lead_Time_Months_Max": 24,
            "CAPEX_per_kW": 1650,
            "VOM_per_MWh": 8.50,
            "FOM_per_kW_yr": 21.50,
            "MTBF_hrs": 2500,
            "MTTR_hrs": 24,
            "Availability_Pct": 92.0,
            "Note": "DLE, Flexible operation"
        },
        {
            "ID": "cat_g3520c",
            "Manufacturer": "Caterpillar",
            "Model": "G3520C",
            "Capacity_MW": 2.0,
            "Efficiency_Pct": 41.0,
            "Heat_Rate_BTU_kWh": 8320,
            "Ramp_Rate_MW_min": 1.0,
            "Start_Time_Cold_Min": 5,
            "NOx_lb_MMBtu": 0.15,
            "CO_lb_MMBtu": 0.30,
            "Lead_Time_Months_Min": 12,
            "Lead_Time_Months_Max": 18,
            "CAPEX_per_kW": 1800,
            "VOM_per_MWh": 9.00,
            "FOM_per_kW_yr": 24.00,
            "MTBF_hrs": 2200,
            "MTTR_hrs": 20,
            "Availability_Pct": 91.0,
            "Note": "Smaller unit, faster start"
        }
    ],
    
    "Gas_Turbines": [
        {
            "ID": "ge_lm6000",
            "Manufacturer": "GE Vernova",
            "Model": "LM6000PF+",
            "Type": "Aeroderivative",
            "Capacity_MW": 53.2,
            "Efficiency_Pct": 42.4,
            "Heat_Rate_BTU_kWh": 8050,
            "Ramp_Rate_MW_min": 26.6,
            "Start_Time_Cold_Min": 10,
            "NOx_lb_MMBtu": 0.099,
            "CO_lb_MMBtu": 0.015,
            "Lead_Time_Months_Min": 18,
            "Lead_Time_Months_Max": 30,
            "CAPEX_per_kW": 1300,
            "VOM_per_MWh": 6.50,
            "FOM_per_kW_yr": 18.00,
            "MTBF_hrs": 2000,
            "MTTR_hrs": 48,
            "Availability_Pct": 93.0,
            "Note": "DLE, High ramping capability"
        },
        {
            "ID": "siemens_sgt800",
            "Manufacturer": "Siemens Energy",
            "Model": "SGT-800",
            "Type": "Industrial",
            "Capacity_MW": 57.1,
            "Efficiency_Pct": 39.9,
            "Heat_Rate_BTU_kWh": 8550,
            "Ramp_Rate_MW_min": 28.5,
            "Start_Time_Cold_Min": 15,
            "NOx_lb_MMBtu": 0.099,
            "CO_lb_MMBtu": 0.015,
            "Lead_Time_Months_Min": 24,
            "Lead_Time_Months_Max": 36,
            "CAPEX_per_kW": 1200,
            "VOM_per_MWh": 6.00,
            "FOM_per_kW_yr": 16.50,
            "MTBF_hrs": 2200,
            "MTTR_hrs": 48,
            "Availability_Pct": 93.5,
            "Note": "DLE, Industrial duty cycle"
        },
        {
            "ID": "mhi_mih100",
            "Manufacturer": "Mitsubishi Power",
            "Model": "MIH-100",
            "Type": "Aeroderivative",
            "Capacity_MW": 10.8,
            "Efficiency_Pct": 32.0,
            "Heat_Rate_BTU_kWh": 10660,
            "Ramp_Rate_MW_min": 5.4,
            "Start_Time_Cold_Min": 8,
            "NOx_lb_MMBtu": 0.099,
            "CO_lb_MMBtu": 0.015,
            "Lead_Time_Months_Min": 18,
            "Lead_Time_Months_Max": 24,
            "CAPEX_per_kW": 1400,
            "VOM_per_MWh": 7.00,
            "FOM_per_kW_yr": 17.00,
            "MTBF_hrs": 2000,
            "MTTR_hrs": 40,
            "Availability_Pct": 92.5,
            "Note": "Smaller aero unit"
        }
    ],
    
    "BESS": [
        {
            "ID": "tesla_megapack_2xl",
            "Manufacturer": "Tesla",
            "Model": "Megapack 2XL",
            "Chemistry": "LFP",
            "Energy_MWh": 3.9,
            "Power_MW": 1.9,
            "Duration_hrs": 2.05,
            "Efficiency_Pct": 91.0,
            "Cycle_Life": 15000,
            "Degradation_Pct_yr": 2.0,
            "Lead_Time_Months": 18,
            "CAPEX_per_kWh": 236,
            "CAPEX_per_kW": 944,
            "Availability_Pct": 97.5,
            "UL9540A": "Yes",
            "Note": "Most common for large datacenter BTM, integrated inverter"
        },
        {
            "ID": "catl_enerone",
            "Manufacturer": "CATL",
            "Model": "EnerOne",
            "Chemistry": "LFP",
            "Energy_MWh": 0.372,
            "Power_MW": 0.186,
            "Duration_hrs": 2.0,
            "Efficiency_Pct": 86.0,
            "Cycle_Life": 12000,
            "Degradation_Pct_yr": 2.0,
            "Lead_Time_Months": 4,
            "CAPEX_per_kWh": 117,
            "CAPEX_per_kW": 470,
            "Availability_Pct": 97.0,
            "UL9540A": "Yes",
            "Note": "Modular rack, global market leader"
        },
        {
            "ID": "byd_mc_cube",
            "Manufacturer": "BYD",
            "Model": "MC Cube-T",
            "Chemistry": "LFP",
            "Energy_MWh": 6.4,
            "Power_MW": 3.2,
            "Duration_hrs": 2.0,
            "Efficiency_Pct": 86.0,
            "Cycle_Life": 10000,
            "Degradation_Pct_yr": 2.0,
            "Lead_Time_Months": 4,
            "CAPEX_per_kWh": 117,
            "CAPEX_per_kW": 470,
            "Availability_Pct": 97.0,
            "UL9540A": "Yes",
            "Note": "Container solution"
        },
        {
            "ID": "fluence_gridstack_pro",
            "Manufacturer": "Fluence",
            "Model": "Gridstack Pro 5000",
            "Chemistry": "LFP",
            "Energy_MWh": 5.3,
            "Power_MW": 2.65,
            "Duration_hrs": 2.0,
            "Efficiency_Pct": 87.0,
            "Cycle_Life": 12000,
            "Degradation_Pct_yr": 2.0,
            "Lead_Time_Months": 9,
            "CAPEX_per_kWh": 170,
            "CAPEX_per_kW": 680,
            "Availability_Pct": 97.5,
            "UL9540A": "Yes",
            "Note": "Proven utility-scale platform"
        }
    ],
    
    "Solar_PV": [
        {
            "ID": "utility_tracker_sw",
            "System_Type": "Single-Axis Tracker",
            "Region": "Southwest US",
            "DC_AC_Ratio": 1.34,
            "Capacity_Factor_Pct": 33.5,
            "Degradation_Pct_yr": 0.5,
            "Performance_Ratio": 84.0,
            "CAPEX_per_W_DC": 0.93,
            "FOM_per_kW_AC_yr": 22.00,
            "Land_Use_acres_per_MW": 4.25,
            "Lead_Time_Months": 12,
            "Availability_Pct": 98.0,
            "Note": "Best CF in US, ITC eligible"
        },
        {
            "ID": "utility_tracker_se",
            "System_Type": "Single-Axis Tracker",
            "Region": "Southeast US",
            "DC_AC_Ratio": 1.34,
            "Capacity_Factor_Pct": 30.5,
            "Degradation_Pct_yr": 0.5,
            "Performance_Ratio": 84.0,
            "CAPEX_per_W_DC": 0.97,
            "FOM_per_kW_AC_yr": 23.00,
            "Land_Use_acres_per_MW": 4.25,
            "Lead_Time_Months": 12,
            "Availability_Pct": 98.0,
            "Note": "Good CF, ITC eligible"
        },
        {
            "ID": "utility_tracker_mw",
            "System_Type": "Single-Axis Tracker",
            "Region": "Midwest US",
            "DC_AC_Ratio": 1.34,
            "Capacity_Factor_Pct": 25.7,
            "Degradation_Pct_yr": 0.5,
            "Performance_Ratio": 84.0,
            "CAPEX_per_W_DC": 1.02,
            "FOM_per_kW_AC_yr": 23.00,
            "Land_Use_acres_per_MW": 4.25,
            "Lead_Time_Months": 12,
            "Availability_Pct": 98.0,
            "Note": "Lower CF, ITC eligible"
        },
        {
            "ID": "utility_fixed_tilt",
            "System_Type": "Fixed Tilt",
            "Region": "National Average",
            "DC_AC_Ratio": 1.35,
            "Capacity_Factor_Pct": 25.0,
            "Degradation_Pct_yr": 0.7,
            "Performance_Ratio": 82.5,
            "CAPEX_per_W_DC": 0.88,
            "FOM_per_kW_AC_yr": 20.00,
            "Land_Use_acres_per_MW": 3.0,
            "Lead_Time_Months": 10,
            "Availability_Pct": 98.0,
            "Note": "Lower cost, less land, lower CF"
        }
    ],
    
    "Grid_Connection": [
        {
            "ISO": "SPP",
            "Typical_Timeline_yrs": 4.0,
            "Typical_Cost_per_kW": 110,
            "Queue_Size_GW": 84,
            "Study_Process": "DISIS cluster",
            "Capacity_Market": "No",
            "Avg_LMP_per_MWh": 32.5,
            "Availability_Pct": 99.97,
            "Note": "Lowest LMP in US"
        },
        {
            "ISO": "ERCOT",
            "Typical_Timeline_yrs": 2.5,
            "Typical_Cost_per_kW": 50,
            "Queue_Size_GW": 260,
            "Study_Process": "Connect-and-Manage",
            "Capacity_Market": "No",
            "Avg_LMP_per_MWh": 37.5,
            "Availability_Pct": 99.95,
            "Note": "Fastest interconnection in US"
        },
        {
            "ISO": "PJM",
            "Typical_Timeline_yrs": 8.0,
            "Typical_Cost_per_kW": 162,
            "Queue_Size_GW": 350,
            "Study_Process": "First-ready cluster",
            "Capacity_Market": "Yes",
            "Capacity_Price_per_MW_day": 329.17,
            "Avg_LMP_per_MWh": 47.5,
            "Availability_Pct": 99.97,
            "Note": "Longest timeline, capacity market revenue"
        },
        {
            "ISO": "MISO",
            "Typical_Timeline_yrs": 4.5,
            "Typical_Cost_per_kW": 130,
            "Queue_Size_GW": 200,
            "Study_Process": "DPP cluster",
            "Capacity_Market": "Yes",
            "Capacity_Price_per_MW_day": 215.0,
            "Avg_LMP_per_MWh": 42.5,
            "Availability_Pct": 99.97,
            "Note": "Capacity market revenue available"
        }
    ]
}


def create_google_sheets_database():
    """Create and populate Google Sheets equipment database"""
    
    # Setup credentials
    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets',
        'https://www.googleapis.com/auth/drive'
    ]
    
    creds_path = Path(__file__).parent.parent / "credentials.json"
    creds = Credentials.from_service_account_file(str(creds_path), scopes=SCOPES)
    client = gspread.authorize(creds)
    
    # Use the provided spreadsheet ID
    sheet_id = "1a3AhvgtwyoNtxEVOJt82gwzLNt13c8uDttKHg1eB0so"
    
    try:
        spreadsheet = client.open_by_key(sheet_id)
        print(f"✅ Opened spreadsheet: {spreadsheet.title}")
        print(f"🔗 URL: {spreadsheet.url}\n")
    except Exception as e:
        print(f"❌ Error accessing Google Sheets: {e}")
        print("Make sure the service account has edit access to this spreadsheet")
        return
    
    # Create worksheets for each equipment type
    for sheet_name, data in equipment_database.items():
        try:
            # Try to get existing worksheet or create new
            try:
                worksheet = spreadsheet.worksheet(sheet_name)
                worksheet.clear()
                print(f"📝 Cleared existing sheet: {sheet_name}")
            except:
                worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=100, cols=26)
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
            worksheet.update('A1', rows)
            
            # Format header row
            worksheet.format('A1:Z1', {
                "backgroundColor": {"red": 0.12, "green": 0.23, "blue": 0.37},
                "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
                "horizontalAlignment": "CENTER"
            })
            
            print(f"   ✅ Added {len(data)} items to {sheet_name}")
            
        except Exception as e:
            print(f"   ❌ Error with {sheet_name}: {e}")
    
    print(f"\n✅ Database populated successfully!")
    print(f"🔗 View at: {spreadsheet.url}")
    print(f"\n📊 Equipment Summary:")
    print(f"   • {len(equipment_database['Reciprocating_Engines'])} Reciprocating Engines")
    print(f"   • {len(equipment_database['Gas_Turbines'])} Gas Turbines")
    print(f"   • {len(equipment_database['BESS'])} Battery Systems")
    print(f"   • {len(equipment_database['Solar_PV'])} Solar PV Configurations")
    print(f"   • {len(equipment_database['Grid_Connection'])} Grid Connection Profiles")


if __name__ == "__main__":
    create_google_sheets_database()
