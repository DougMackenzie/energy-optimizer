const fs = require('fs');
const { 
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, 
  Header, Footer, AlignmentType, PageOrientation, LevelFormat,
  HeadingLevel, BorderStyle, WidthType, ShadingType, PageBreak, PageNumber
} = require('docx');

// Define table borders
const tableBorder = { style: BorderStyle.SINGLE, size: 1, color: "999999" };
const cellBorders = { top: tableBorder, bottom: tableBorder, left: tableBorder, right: tableBorder };
const headerShading = { fill: "1E3A5F", type: ShadingType.CLEAR };
const altRowShading = { fill: "F5F5F5", type: ShadingType.CLEAR };

// Helper functions
function createHeaderCell(text, width) {
  return new TableCell({
    borders: cellBorders,
    width: { size: width, type: WidthType.DXA },
    shading: headerShading,
    children: [new Paragraph({ 
      alignment: AlignmentType.CENTER,
      children: [new TextRun({ text: text, bold: true, color: "FFFFFF", size: 22, font: "Arial" })]
    })]
  });
}

function createDataCell(text, width, shade = false) {
  return new TableCell({
    borders: cellBorders,
    width: { size: width, type: WidthType.DXA },
    shading: shade ? altRowShading : undefined,
    children: [new Paragraph({ 
      children: [new TextRun({ text: text, size: 20, font: "Arial" })]
    })]
  });
}

// Create document
const doc = new Document({
  styles: {
    default: { document: { run: { font: "Arial", size: 22 } } },
    paragraphStyles: [
      { id: "Title", name: "Title", basedOn: "Normal",
        run: { size: 48, bold: true, color: "1E3A5F", font: "Arial" },
        paragraph: { spacing: { before: 0, after: 200 }, alignment: AlignmentType.CENTER } },
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, color: "1E3A5F", font: "Arial" },
        paragraph: { spacing: { before: 300, after: 150 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 26, bold: true, color: "2E5984", font: "Arial" },
        paragraph: { spacing: { before: 200, after: 100 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 22, bold: true, color: "333333", font: "Arial" },
        paragraph: { spacing: { before: 150, after: 80 }, outlineLevel: 2 } },
    ]
  },
  numbering: {
    config: [
      { reference: "bullet-list",
        levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "check-list",
        levels: [{ level: 0, format: LevelFormat.BULLET, text: "✓", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
    ]
  },
  sections: [{
    properties: {
      page: { margin: { top: 1080, right: 1080, bottom: 1080, left: 1080 } }
    },
    headers: {
      default: new Header({ children: [new Paragraph({ 
        alignment: AlignmentType.RIGHT,
        children: [new TextRun({ text: "bvNexus Integration Guide", italics: true, size: 18, color: "666666" })]
      })] })
    },
    footers: {
      default: new Footer({ children: [new Paragraph({ 
        alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: "Page ", size: 18 }), 
                   new TextRun({ children: [PageNumber.CURRENT], size: 18 }), 
                   new TextRun({ text: " of ", size: 18 }), 
                   new TextRun({ children: [PageNumber.TOTAL_PAGES], size: 18 })]
      })] })
    },
    children: [
      // Title Page
      new Paragraph({ heading: HeadingLevel.TITLE, children: [new TextRun("bvNexus Integration")] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 100 },
        children: [new TextRun({ text: "Sample File Structures & Data Exchange Guide", size: 28, color: "666666" })] }),
      new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 400 },
        children: [new TextRun({ text: "ETAP • PSS/e • Windchill RAM", size: 24, color: "999999" })] }),
      
      // Overview
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("Overview")] }),
      new Paragraph({ spacing: { after: 150 },
        children: [new TextRun("This document describes the file formats and data structures used to exchange information between bvNexus and external validation tools. The integration enables a closed-loop workflow where optimization results are validated against detailed engineering analyses.")] }),
      
      // Data Flow Diagram (as text description)
      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("Integration Workflow")] }),
      new Paragraph({ numbering: { reference: "bullet-list", level: 0 },
        children: [new TextRun({ text: "Step 1:", bold: true }), new TextRun(" bvNexus optimization produces equipment configuration")] }),
      new Paragraph({ numbering: { reference: "bullet-list", level: 0 },
        children: [new TextRun({ text: "Step 2:", bold: true }), new TextRun(" Export Hub generates tool-specific input files")] }),
      new Paragraph({ numbering: { reference: "bullet-list", level: 0 },
        children: [new TextRun({ text: "Step 3:", bold: true }), new TextRun(" Engineers run studies in ETAP, PSS/e, and Windchill RAM")] }),
      new Paragraph({ numbering: { reference: "bullet-list", level: 0 },
        children: [new TextRun({ text: "Step 4:", bold: true }), new TextRun(" Export results from external tools (CSV/Excel)")] }),
      new Paragraph({ numbering: { reference: "bullet-list", level: 0 },
        children: [new TextRun({ text: "Step 5:", bold: true }), new TextRun(" Import Hub parses results and validates against criteria")] }),
      new Paragraph({ numbering: { reference: "bullet-list", level: 0 },
        children: [new TextRun({ text: "Step 6:", bold: true }), new TextRun(" Constraint updates feed back to re-optimization if needed")] }),
      
      // Page break before ETAP section
      new Paragraph({ children: [new PageBreak()] }),
      
      // ETAP Section
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("⚡ ETAP Integration")] }),
      new Paragraph({ spacing: { after: 150 },
        children: [new TextRun("ETAP integration uses Excel/CSV files for bulk data exchange via the DataX import feature.")] }),
      
      // ETAP Equipment Table
      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("Equipment Import Format")] }),
      new Paragraph({ spacing: { after: 100 },
        children: [new TextRun({ text: "File: ETAP_Equipment_Import.csv", italics: true, color: "666666" })] }),
      
      new Table({
        columnWidths: [1800, 2500, 5000],
        rows: [
          new TableRow({ tableHeader: true, children: [
            createHeaderCell("Column", 1800),
            createHeaderCell("Example", 2500),
            createHeaderCell("Description", 5000)
          ]}),
          new TableRow({ children: [
            createDataCell("ID", 1800),
            createDataCell("GEN_RECIP_01", 2500),
            createDataCell("Unique equipment identifier", 5000)
          ]}),
          new TableRow({ children: [
            createDataCell("Name", 1800, true),
            createDataCell("Recip Engine 1", 2500, true),
            createDataCell("Descriptive name for display", 5000, true)
          ]}),
          new TableRow({ children: [
            createDataCell("Type", 1800),
            createDataCell("Synchronous Generator", 2500),
            createDataCell("Equipment type for ETAP modeling", 5000)
          ]}),
          new TableRow({ children: [
            createDataCell("Bus_ID", 1800, true),
            createDataCell("BUS_100", 2500, true),
            createDataCell("Connected bus for topology", 5000, true)
          ]}),
          new TableRow({ children: [
            createDataCell("Rated_MW", 1800),
            createDataCell("18.3", 2500),
            createDataCell("Power rating in megawatts", 5000)
          ]}),
          new TableRow({ children: [
            createDataCell("Xd_pu", 1800, true),
            createDataCell("1.80", 2500, true),
            createDataCell("Synchronous reactance (per-unit)", 5000, true)
          ]}),
          new TableRow({ children: [
            createDataCell("H_inertia_sec", 1800),
            createDataCell("1.5", 2500),
            createDataCell("Inertia constant (seconds)", 5000)
          ]}),
        ]
      }),
      
      // ETAP Scenarios Table
      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("Scenario Definitions")] }),
      new Paragraph({ spacing: { after: 100 },
        children: [new TextRun({ text: "File: ETAP_Scenarios.csv", italics: true, color: "666666" })] }),
      
      new Table({
        columnWidths: [1800, 2200, 2800, 2500],
        rows: [
          new TableRow({ tableHeader: true, children: [
            createHeaderCell("Scenario_ID", 1800),
            createHeaderCell("Type", 2200),
            createHeaderCell("Tripped_Equipment", 2800),
            createHeaderCell("Load_MW", 2500)
          ]}),
          new TableRow({ children: [
            createDataCell("BASE_100", 1800),
            createDataCell("Normal", 2200),
            createDataCell("(none)", 2800),
            createDataCell("200.0", 2500)
          ]}),
          new TableRow({ children: [
            createDataCell("N1_RECIP_01", 1800, true),
            createDataCell("N-1 Contingency", 2200, true),
            createDataCell("GEN_RECIP_01", 2800, true),
            createDataCell("200.0", 2500, true)
          ]}),
          new TableRow({ children: [
            createDataCell("N1_GT_01", 1800),
            createDataCell("N-1 Contingency", 2200),
            createDataCell("GEN_GT_01", 2800),
            createDataCell("200.0", 2500)
          ]}),
          new TableRow({ children: [
            createDataCell("N2_GT_BOTH", 1800, true),
            createDataCell("N-2 Contingency", 2200, true),
            createDataCell("GEN_GT_01,GEN_GT_02", 2800, true),
            createDataCell("200.0", 2500, true)
          ]}),
        ]
      }),
      
      // ETAP Results Format
      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("Load Flow Results (Import)")] }),
      new Paragraph({ spacing: { after: 100 },
        children: [new TextRun({ text: "File: ETAP_LoadFlow_Results.csv (exported from ETAP Results Analyzer)", italics: true, color: "666666" })] }),
      
      new Table({
        columnWidths: [1600, 2100, 1600, 1600, 1600, 1800],
        rows: [
          new TableRow({ tableHeader: true, children: [
            createHeaderCell("Bus_ID", 1600),
            createHeaderCell("Bus_Name", 2100),
            createHeaderCell("Voltage_pu", 1600),
            createHeaderCell("Angle_deg", 1600),
            createHeaderCell("P_MW", 1600),
            createHeaderCell("Loading_pct", 1800)
          ]}),
          new TableRow({ children: [
            createDataCell("BUS_100", 1600),
            createDataCell("RECIP_1_BUS", 2100),
            createDataCell("1.012", 1600),
            createDataCell("2.3", 1600),
            createDataCell("18.3", 1600),
            createDataCell("72.5", 1800)
          ]}),
          new TableRow({ children: [
            createDataCell("BUS_120", 1600, true),
            createDataCell("GT_1_BUS", 2100, true),
            createDataCell("1.025", 1600, true),
            createDataCell("0.0", 1600, true),
            createDataCell("50.0", 1600, true),
            createDataCell("78.0", 1800, true)
          ]}),
        ]
      }),
      
      // Validation Criteria
      new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun("Validation Criteria")] }),
      new Paragraph({ numbering: { reference: "check-list", level: 0 },
        children: [new TextRun({ text: "Voltage:", bold: true }), new TextRun(" 0.95 ≤ V ≤ 1.05 pu")] }),
      new Paragraph({ numbering: { reference: "check-list", level: 0 },
        children: [new TextRun({ text: "Loading:", bold: true }), new TextRun(" < 80% (warning), < 100% (fail)")] }),
      new Paragraph({ numbering: { reference: "check-list", level: 0 },
        children: [new TextRun({ text: "Breaker Duty:", bold: true }), new TextRun(" < 100% of rating")] }),
      
      // Page break before PSS/e section
      new Paragraph({ children: [new PageBreak()] }),
      
      // PSS/e Section
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("🔌 PSS/e Integration")] }),
      new Paragraph({ spacing: { after: 150 },
        children: [new TextRun("PSS/e integration uses the industry-standard RAW format for network models and CSV for results.")] }),
      
      // PSS/e RAW Format
      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("Network Model (RAW Format)")] }),
      new Paragraph({ spacing: { after: 100 },
        children: [new TextRun({ text: "File: bvNexus_Network.raw", italics: true, color: "666666" })] }),
      
      new Paragraph({ spacing: { after: 100 },
        children: [new TextRun({ text: "RAW file structure consists of data sections, each terminated by a zero record:", size: 20 })] }),
      
      new Table({
        columnWidths: [2500, 6800],
        rows: [
          new TableRow({ tableHeader: true, children: [
            createHeaderCell("Section", 2500),
            createHeaderCell("Contents", 6800)
          ]}),
          new TableRow({ children: [
            createDataCell("Header (3 lines)", 2500),
            createDataCell("System MVA base, case title, comments", 6800)
          ]}),
          new TableRow({ children: [
            createDataCell("BUS DATA", 2500, true),
            createDataCell("Bus numbers, names, voltage levels, types (1=Load, 2=Gen, 3=Swing)", 6800, true)
          ]}),
          new TableRow({ children: [
            createDataCell("LOAD DATA", 2500),
            createDataCell("Load MW/MVAR at each bus (negative = generation)", 6800)
          ]}),
          new TableRow({ children: [
            createDataCell("GENERATOR DATA", 2500, true),
            createDataCell("Generator ratings, setpoints, impedances, MBASE", 6800, true)
          ]}),
          new TableRow({ children: [
            createDataCell("BRANCH DATA", 2500),
            createDataCell("Lines/cables connecting buses (R, X, B, ratings)", 6800)
          ]}),
          new TableRow({ children: [
            createDataCell("AREA DATA", 2500, true),
            createDataCell("Control area definitions for interchange", 6800, true)
          ]}),
        ]
      }),
      
      // Sample RAW content
      new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun("Sample RAW File Content")] }),
      new Paragraph({ spacing: { after: 50 },
        shading: { fill: "F0F0F0", type: ShadingType.CLEAR },
        children: [new TextRun({ text: "0,   100.00     / PSS/E-35    Fri, Dec 27 2024", font: "Courier New", size: 18 })] }),
      new Paragraph({ spacing: { after: 50 },
        shading: { fill: "F0F0F0", type: ShadingType.CLEAR },
        children: [new TextRun({ text: "Dallas Hyperscale DC - Power Flow Base Case", font: "Courier New", size: 18 })] }),
      new Paragraph({ spacing: { after: 50 },
        shading: { fill: "F0F0F0", type: ShadingType.CLEAR },
        children: [new TextRun({ text: "/ BUS DATA", font: "Courier New", size: 18 })] }),
      new Paragraph({ spacing: { after: 50 },
        shading: { fill: "F0F0F0", type: ShadingType.CLEAR },
        children: [new TextRun({ text: "100,'RECIP_01',  13.800,1,   1,   1,   1,1.01000,   0.0000", font: "Courier New", size: 18 })] }),
      new Paragraph({ spacing: { after: 100 },
        shading: { fill: "F0F0F0", type: ShadingType.CLEAR },
        children: [new TextRun({ text: "0 / END OF BUS DATA", font: "Courier New", size: 18 })] }),
      
      // PSS/e Results Format
      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("Power Flow Results (Import)")] }),
      new Paragraph({ spacing: { after: 100 },
        children: [new TextRun({ text: "File: PSSe_PowerFlow_Results.csv (exported via dyntools or API)", italics: true, color: "666666" })] }),
      
      new Table({
        columnWidths: [1200, 1800, 1500, 1500, 1500, 2000],
        rows: [
          new TableRow({ tableHeader: true, children: [
            createHeaderCell("BUS", 1200),
            createHeaderCell("NAME", 1800),
            createHeaderCell("VM_PU", 1500),
            createHeaderCell("VA_DEG", 1500),
            createHeaderCell("P_GEN_MW", 1500),
            createHeaderCell("Q_GEN_MVAR", 2000)
          ]}),
          new TableRow({ children: [
            createDataCell("100", 1200),
            createDataCell("RECIP_01", 1800),
            createDataCell("1.010", 1500),
            createDataCell("2.3", 1500),
            createDataCell("18.3", 1500),
            createDataCell("9.8", 2000)
          ]}),
          new TableRow({ children: [
            createDataCell("120", 1200, true),
            createDataCell("GT_01", 1800, true),
            createDataCell("1.025", 1500, true),
            createDataCell("0.0", 1500, true),
            createDataCell("50.0", 1500, true),
            createDataCell("25.0", 2000, true)
          ]}),
        ]
      }),
      
      // Page break before RAM section
      new Paragraph({ children: [new PageBreak()] }),
      
      // Windchill RAM Section
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("📈 Windchill RAM Integration")] }),
      new Paragraph({ spacing: { after: 150 },
        children: [new TextRun("Windchill RAM integration uses Excel files for component data, RBD structure, and FMEA templates.")] }),
      
      // Component Data
      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("Component Reliability Data")] }),
      new Paragraph({ spacing: { after: 100 },
        children: [new TextRun({ text: "File: RAM_Component_Data.csv", italics: true, color: "666666" })] }),
      
      new Table({
        columnWidths: [2000, 1500, 1500, 1500, 1500, 1400],
        rows: [
          new TableRow({ tableHeader: true, children: [
            createHeaderCell("Component_ID", 2000),
            createHeaderCell("Type", 1500),
            createHeaderCell("MTBF_Hrs", 1500),
            createHeaderCell("MTTR_Hrs", 1500),
            createHeaderCell("Availability", 1500),
            createHeaderCell("Distribution", 1400)
          ]}),
          new TableRow({ children: [
            createDataCell("GEN_RECIP_01", 2000),
            createDataCell("RECIP_ENGINE", 1500),
            createDataCell("8,760", 1500),
            createDataCell("24", 1500),
            createDataCell("0.9973", 1500),
            createDataCell("Exponential", 1400)
          ]}),
          new TableRow({ children: [
            createDataCell("GEN_GT_01", 2000, true),
            createDataCell("GAS_TURBINE", 1500, true),
            createDataCell("17,520", 1500, true),
            createDataCell("48", 1500, true),
            createDataCell("0.9973", 1500, true),
            createDataCell("Weibull", 1400, true)
          ]}),
          new TableRow({ children: [
            createDataCell("BESS_01", 2000),
            createDataCell("BATTERY", 1500),
            createDataCell("43,800", 1500),
            createDataCell("8", 1500),
            createDataCell("0.9998", 1500),
            createDataCell("Exponential", 1400)
          ]}),
          new TableRow({ children: [
            createDataCell("XFMR_MAIN", 2000, true),
            createDataCell("TRANSFORMER", 1500, true),
            createDataCell("175,200", 1500, true),
            createDataCell("168", 1500, true),
            createDataCell("0.9990", 1500, true),
            createDataCell("Exponential", 1400, true)
          ]}),
        ]
      }),
      
      // RBD Structure
      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("Reliability Block Diagram Structure")] }),
      new Paragraph({ spacing: { after: 100 },
        children: [new TextRun({ text: "File: RAM_RBD_Structure.csv", italics: true, color: "666666" })] }),
      
      new Table({
        columnWidths: [2000, 2500, 2400, 1200, 1200],
        rows: [
          new TableRow({ tableHeader: true, children: [
            createHeaderCell("Block_ID", 2000),
            createHeaderCell("Block_Type", 2500),
            createHeaderCell("Description", 2400),
            createHeaderCell("K_Req", 1200),
            createHeaderCell("N_Total", 1200)
          ]}),
          new TableRow({ children: [
            createDataCell("THERMAL_GEN", 2000),
            createDataCell("PARALLEL_K_OF_N", 2500),
            createDataCell("N-1 redundancy", 2400),
            createDataCell("9", 1200),
            createDataCell("10", 1200)
          ]}),
          new TableRow({ children: [
            createDataCell("ELECTRICAL", 2000, true),
            createDataCell("SERIES", 2500, true),
            createDataCell("All required", 2400, true),
            createDataCell("2", 1200, true),
            createDataCell("2", 1200, true)
          ]}),
          new TableRow({ children: [
            createDataCell("SYSTEM", 2000),
            createDataCell("SERIES", 2500),
            createDataCell("Top-level system", 2400),
            createDataCell("4", 1200),
            createDataCell("4", 1200)
          ]}),
        ]
      }),
      
      // RAM Results
      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("Analysis Results (Import)")] }),
      new Paragraph({ spacing: { after: 100 },
        children: [new TextRun({ text: "File: RAM_Results.csv (exported from Windchill simulation)", italics: true, color: "666666" })] }),
      
      new Table({
        columnWidths: [2200, 1700, 1700, 1700, 2000],
        rows: [
          new TableRow({ tableHeader: true, children: [
            createHeaderCell("Block_Name", 2200),
            createHeaderCell("Availability", 1700),
            createHeaderCell("MTBF_Hrs", 1700),
            createHeaderCell("MTTR_Hrs", 1700),
            createHeaderCell("Downtime_Hrs/Yr", 2000)
          ]}),
          new TableRow({ children: [
            createDataCell("Thermal Generation", 2200),
            createDataCell("99.987%", 1700),
            createDataCell("76,923", 1700),
            createDataCell("10", 1700),
            createDataCell("1.14", 2000)
          ]}),
          new TableRow({ children: [
            createDataCell("Electrical Distribution", 2200, true),
            createDataCell("99.965%", 1700, true),
            createDataCell("25,000", 1700, true),
            createDataCell("88", 1700, true),
            createDataCell("3.07", 2000, true)
          ]}),
          new TableRow({ children: [
            createDataCell("Complete System", 2200),
            createDataCell("99.952%", 1700),
            createDataCell("18,292", 1700),
            createDataCell("88", 1700),
            createDataCell("4.20", 2000)
          ]}),
        ]
      }),
      
      // RAM Validation Criteria
      new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun("Validation Criteria")] }),
      new Paragraph({ numbering: { reference: "check-list", level: 0 },
        children: [new TextRun({ text: "System Availability:", bold: true }), new TextRun(" ≥ 99.95% (4.38 hours/year max downtime)")] }),
      new Paragraph({ numbering: { reference: "check-list", level: 0 },
        children: [new TextRun({ text: "N-1 Redundancy:", bold: true }), new TextRun(" System meets load with any single component offline")] }),
      new Paragraph({ numbering: { reference: "check-list", level: 0 },
        children: [new TextRun({ text: "System MTBF:", bold: true }), new TextRun(" ≥ 8,760 hours (1 year)")] }),
      
      // Page break before summary
      new Paragraph({ children: [new PageBreak()] }),
      
      // Summary Section
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("Summary & Quick Reference")] }),
      
      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("File Summary")] }),
      
      new Table({
        columnWidths: [2000, 3500, 3800],
        rows: [
          new TableRow({ tableHeader: true, children: [
            createHeaderCell("Tool", 2000),
            createHeaderCell("Export Files (from bvNexus)", 3500),
            createHeaderCell("Import Files (to bvNexus)", 3800)
          ]}),
          new TableRow({ children: [
            createDataCell("ETAP", 2000),
            createDataCell("Equipment.csv, Scenarios.csv", 3500),
            createDataCell("LoadFlow_Results.csv, ShortCircuit_Results.csv", 3800)
          ]}),
          new TableRow({ children: [
            createDataCell("PSS/e", 2000, true),
            createDataCell("Network.raw, Scenarios.csv", 3500, true),
            createDataCell("PowerFlow_Results.csv", 3800, true)
          ]}),
          new TableRow({ children: [
            createDataCell("Windchill RAM", 2000),
            createDataCell("Component_Data.csv, RBD_Structure.csv, FMEA.csv", 3500),
            createDataCell("RAM_Results.csv", 3800)
          ]}),
        ]
      }),
      
      new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun("Validation Thresholds")] }),
      
      new Table({
        columnWidths: [3000, 2500, 2000, 1800],
        rows: [
          new TableRow({ tableHeader: true, children: [
            createHeaderCell("Study", 3000),
            createHeaderCell("Metric", 2500),
            createHeaderCell("Pass", 2000),
            createHeaderCell("Fail", 1800)
          ]}),
          new TableRow({ children: [
            createDataCell("ETAP Load Flow", 3000),
            createDataCell("Voltage (pu)", 2500),
            createDataCell("0.95 - 1.05", 2000),
            createDataCell("< 0.95 or > 1.05", 1800)
          ]}),
          new TableRow({ children: [
            createDataCell("ETAP Load Flow", 3000, true),
            createDataCell("Loading (%)", 2500, true),
            createDataCell("< 80%", 2000, true),
            createDataCell("> 100%", 1800, true)
          ]}),
          new TableRow({ children: [
            createDataCell("ETAP Short Circuit", 3000),
            createDataCell("Breaker Duty (%)", 2500),
            createDataCell("< 80%", 2000),
            createDataCell("> 100%", 1800)
          ]}),
          new TableRow({ children: [
            createDataCell("PSS/e Power Flow", 3000, true),
            createDataCell("Voltage (pu)", 2500, true),
            createDataCell("0.95 - 1.05", 2000, true),
            createDataCell("< 0.95 or > 1.05", 1800, true)
          ]}),
          new TableRow({ children: [
            createDataCell("RAM Analysis", 3000),
            createDataCell("Availability (%)", 2500),
            createDataCell("≥ 99.95%", 2000),
            createDataCell("< 99.90%", 1800)
          ]}),
          new TableRow({ children: [
            createDataCell("RAM Analysis", 3000, true),
            createDataCell("Downtime (hrs/yr)", 2500, true),
            createDataCell("≤ 4.38", 2000, true),
            createDataCell("> 8.76", 1800, true)
          ]}),
        ]
      }),
      
      // Footer note
      new Paragraph({ spacing: { before: 400 }, alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: "Generated by bvNexus Integration Module", italics: true, color: "999999", size: 18 })] }),
    ]
  }]
});

// Save document
Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync("/mnt/user-data/outputs/bvNexus_Integration_File_Guide.docx", buffer);
  console.log("Document created successfully!");
}).catch(err => {
  console.error("Error creating document:", err);
});
