import React, { useState, useMemo } from 'react';

// ============================================================================
// 1. DATA LIBRARIES & CONFIGURATIONS
// ============================================================================

const FOOTPRINT_LIBRARY = {
  substation_345kv_ring: { 
    acres: 6, width: 510, length: 510, 
    label: "345kV Ring Bus Substation" 
  },
  substation_345kv_bah: { 
    acres: 9, width: 625, length: 625, 
    label: "345kV Breaker-and-a-Half" 
  },
  turbine_lm6000: { 
    width: 60, length: 110, height: 55, mw: 50,
    label: "GE LM6000" 
  },
  recip_wartsila_34df: { 
    width: 30, length: 65, height: 35, mw: 9.7,
    label: "Wärtsilä 20V34DF"
  },
  bess_container_5mw: { 
    width: 40, length: 10, height: 10, mw: 5, mwh: 20,
    label: "BESS Container"
  }
};

const ELECTRICAL_SPECS = {
  poi: {
    radial: { label: "Radial Feed", type: "radial", tier: "Tier I/II" },
    ring_n1: { label: "Ring Bus (N-1)", type: "ring", tier: "Tier III" },
    breaker_half: { label: "Breaker-and-a-Half", type: "bah", tier: "Tier IV" },
  },
  generation: {
    radial: { label: "Simple Radial Bus", type: "radial", desc: "Single Bus" },
    mtm: { label: "Main-Tie-Main (MTM)", type: "mtm", desc: "Bus A+B w/ Tie" },
    double_bus: { label: "Double Bus", type: "double", desc: "Dual Redundant Buses" },
    ring: { label: "Ring Bus Loop", type: "ring", desc: "Closed Loop Breakers" },
  },
  distribution: {
    n_topology: { label: "System + System (2N)", type: "2N", desc: "Dual Active Feeds" },
    catcher: { label: "Block Redundant (N+1)", type: "catcher", desc: "Reserve Bus + STS" },
    distributed: { label: "Distributed (4/3)", type: "distributed", desc: "Rotational Redundancy" },
  }
};

// ============================================================================
// 2. HELPER COMPONENTS (SYMBOLS)
// ============================================================================

const Breaker = ({ x, y, label, open = false, vertical = false, color="#000" }) => (
  <g transform={`translate(${x}, ${y})`}>
    <rect x="-6" y="-6" width="12" height="12" fill={open ? "#fff" : color} stroke={color} strokeWidth="1"/>
    {open && <line x1="-6" y1="-6" x2="6" y2="6" stroke={color} strokeWidth="1"/>}
    {label && <text x={vertical ? 10 : 0} y={vertical ? 4 : -10} textAnchor={vertical ? "start" : "middle"} fontSize="8" fill={color}>{label}</text>}
  </g>
);

const Transformer = ({ x, y, label, color="#000" }) => (
  <g transform={`translate(${x}, ${y})`}>
    <circle cx="0" cy="-12" r="12" fill="none" stroke={color} strokeWidth="1.5"/>
    <circle cx="0" cy="12" r="12" fill="none" stroke={color} strokeWidth="1.5"/>
    {label && <text x="18" y="4" fontSize="8" fontWeight="bold" fill={color}>{label}</text>}
  </g>
);

const STS = ({ x, y }) => (
  <g transform={`translate(${x}, ${y})`}>
    <rect x="-10" y="-10" width="20" height="20" fill="#fff" stroke="#000" strokeWidth="1.5"/>
    <text x="0" y="3" textAnchor="middle" fontSize="7" fontWeight="bold">STS</text>
  </g>
);

// ============================================================================
// 3. ONE-LINE DIAGRAM COMPONENT
// ============================================================================

const OneLineDiagram = ({ results, config }) => {
  const { poiConfig, genConfig, distConfig } = config;
  const { equipment, totals } = results;

  // -- SECTION 1: POI (345kV) --
  const renderPOI = () => {
    const type = ELECTRICAL_SPECS.poi[poiConfig].type;
    return (
      <g transform="translate(450, 120)">
        <text x="0" y="-60" textAnchor="middle" fontWeight="bold" fontSize="14">UTILITY INTERCONNECTION (345 kV)</text>
        <line x1="0" y1="-50" x2="0" y2="-40" stroke="#000" strokeWidth="2"/>
        
        {type === 'ring' ? (
          <g>
            <rect x="-150" y="-40" width="300" height="60" fill="none" stroke="#000" strokeWidth="3" rx="10"/>
            <text x="0" y="-10" textAnchor="middle" fontSize="10" fontWeight="bold">345kV RING BUS</text>
            {/* Ring Breakers */}
            {[-100, 0, 100].map(x => <Breaker key={x} x={x} y={-40} />)}
            {[-100, 100].map(x => <Breaker key={x} x={x} y={20} />)}
            
            {/* Transformers */}
            <line x1="-100" y1="20" x2="-100" y2="60" stroke="#000" strokeWidth="2"/>
            <Transformer x={-100} y={80} label="T1 (300MVA)" />
            <line x1="100" y1="20" x2="100" y2="60" stroke="#000" strokeWidth="2"/>
            <Transformer x={100} y={80} label="T2 (300MVA)" />
          </g>
        ) : type === 'bah' ? (
          <g>
            <text x="0" y="-10" textAnchor="middle" fontSize="10" fontWeight="bold">BREAKER-AND-A-HALF</text>
            {/* Rails */}
            <line x1="-180" y1="-30" x2="180" y2="-30" stroke="#000" strokeWidth="2"/>
            <line x1="-180" y1="30" x2="180" y2="30" stroke="#000" strokeWidth="2"/>
            {/* Bays */}
            {[-100, 0, 100].map(x => (
              <g key={x}>
                <line x1={x} y1="-30" x2={x} y2="30" stroke="#000" strokeWidth="1"/>
                <Breaker x={x} y={-15} />
                <Breaker x={x} y={0} />
                <Breaker x={x} y={15} />
              </g>
            ))}
             {/* Transformers */}
             <line x1="-100" y1="30" x2="-100" y2="60" stroke="#000" strokeWidth="2"/>
             <Transformer x={-100} y={80} label="T1 (300MVA)" />
             <line x1="100" y1="30" x2="100" y2="60" stroke="#000" strokeWidth="2"/>
             <Transformer x={100} y={80} label="T2 (300MVA)" />
          </g>
        ) : (
          <g>
            {/* Radial */}
             <line x1="-100" y1="-40" x2="100" y2="-40" stroke="#000" strokeWidth="4"/>
             <text x="0" y="-50" textAnchor="middle" fontSize="10">RADIAL BUS</text>
             <line x1="0" y1="-40" x2="0" y2="60" stroke="#000" strokeWidth="2"/>
             <Breaker x={0} y={0} label="Main" />
             <Transformer x={0} y={80} label="T1" />
          </g>
        )}
      </g>
    );
  };

  // -- SECTION 2: MAIN BUS & GENERATION --
  const renderGeneration = () => {
    const type = ELECTRICAL_SPECS.generation[genConfig].type;
    const busY = 400;
    
    // Draw connections from POI transformers down to Main Bus
    const feeders = (
      <g>
        <line x1="350" y1="215" x2="350" y2={busY} stroke="#000" strokeWidth="2" strokeDasharray="4,2"/>
        <line x1="550" y1="215" x2="550" y2={busY} stroke="#000" strokeWidth="2" strokeDasharray="4,2"/>
      </g>
    );

    let busVisual;
    if (type === 'double') {
      busVisual = (
        <g>
          <line x1="100" y1={busY} x2="800" y2={busY} stroke="#000" strokeWidth="4"/>
          <text x="820" y={busY+4} fontSize="10" fontWeight="bold">BUS A</text>
          <line x1="100" y1={busY+60} x2="800" y2={busY+60} stroke="#000" strokeWidth="4"/>
          <text x="820" y={busY+64} fontSize="10" fontWeight="bold">BUS B</text>
          {/* Gen Connections to both */}
          {[...Array(4)].map((_, i) => {
            const x = 150 + i*80;
            return (
              <g key={i} transform={`translate(${x}, ${busY})`}>
                 {/* Generator */}
                 <circle cx="0" cy="-40" r="14" fill="#fff" stroke="#000" strokeWidth="1.5"/>
                 <text x="0" y="-36" textAnchor="middle" fontSize="10" fontWeight="bold">G</text>
                 <line x1="0" y1="-26" x2="0" y2="0" stroke="#000" strokeWidth="1.5"/>
                 
                 {/* Connection Bus A */}
                 <Breaker x={0} y={0} />
                 
                 {/* Connection Bus B */}
                 <line x1="0" y1="6" x2="0" y2={60} stroke="#000" strokeWidth="1.5"/>
                 <Breaker x={0} y={60} />
              </g>
            )
          })}
        </g>
      );
    } else if (type === 'ring') {
      busVisual = (
        <g>
          <rect x="100" y={busY} width="700" height="60" fill="none" stroke="#000" strokeWidth="4" rx="10"/>
          <text x="450" y={busY+35} textAnchor="middle" fontSize="12" fontWeight="bold">34.5kV RING</text>
          {[...Array(4)].map((_, i) => {
            const x = 200 + i*120;
            return (
              <g key={i} transform={`translate(${x}, ${busY})`}>
                 <Breaker x={0} y={0} />
                 <line x1="60" y1="0" x2="60" y2="-40" stroke="#000" strokeWidth="1.5"/>
                 <circle cx="60" cy="-55" r="14" fill="#fff" stroke="#000" strokeWidth="1.5"/>
                 <text x="60" y="-51" textAnchor="middle" fontSize="10" fontWeight="bold">G</text>
              </g>
            )
          })}
        </g>
      );
    } else { // MTM or Radial
      busVisual = (
        <g>
          <line x1="100" y1={busY} x2="440" y2={busY} stroke="#000" strokeWidth="4"/>
          <line x1="460" y1={busY} x2="800" y2={busY} stroke="#000" strokeWidth="4"/>
          {type === 'mtm' && (
            <g>
              <line x1="440" y1={busY} x2="460" y2={busY} stroke="#000" strokeWidth="2" strokeDasharray="4,2"/>
              <Breaker x={450} y={busY} open={true} label="Tie" />
            </g>
          )}
          {/* Gens */}
          {[...Array(4)].map((_, i) => {
            const x = 150 + i*150;
            return (
              <g key={i} transform={`translate(${x}, ${busY})`}>
                 <line x1="0" y1="-50" x2="0" y2="0" stroke="#000" strokeWidth="1.5"/>
                 <Breaker x={0} y={0} />
                 <circle cx="0" cy="-65" r="14" fill="#fff" stroke="#000" strokeWidth="1.5"/>
                 <text x="0" y="-61" textAnchor="middle" fontSize="10" fontWeight="bold">G</text>
              </g>
            )
          })}
        </g>
      );
    }

    return (
      <g>
        {feeders}
        {busVisual}
      </g>
    );
  };

  // -- SECTION 3: DISTRIBUTION --
  const renderDistribution = () => {
    const type = ELECTRICAL_SPECS.distribution[distConfig].type;
    const startY = 550;
    
    // Reserve Bus (only for Catcher)
    const reserveBus = type === 'catcher' ? (
      <g>
        <line x1="100" y1={startY+40} x2="800" y2={startY+40} stroke="#f97316" strokeWidth="3" strokeDasharray="5,2"/>
        <text x="810" y={startY+44} fontSize="10" fontWeight="bold" fill="#f97316">RESERVE BUS</text>
        {/* Reserve Transformer */}
        <line x1="750" y1={startY-100} x2="750" y2={startY+40} stroke="#f97316" strokeWidth="1.5"/>
        <Transformer x={750} y={startY-50} label="T-Res" color="#f97316"/>
      </g>
    ) : null;

    return (
      <g>
        {reserveBus}
        
        {/* Halls */}
        {[...Array(4)].map((_, i) => {
          const x = 150 + i*160;
          return (
            <g key={i} transform={`translate(${x}, ${startY})`}>
               {/* Primary Feed from Main Bus (approx y=400) */}
               <line x1="0" y1="-100" x2="0" y2="40" stroke="#000" strokeWidth="1.5"/>
               <Transformer x={0} y={-20} label={`T-${i+1}`} />
               <Breaker x={0} y={-60} vertical={true}/>

               {/* Configuration Specific Logic */}
               {type === 'catcher' ? (
                 <g>
                   {/* STS Logic */}
                   <line x1="0" y1="40" x2="0" y2="80" stroke="#000" strokeWidth="1.5"/>
                   <line x1="30" y1="40" x2="30" y2="80" stroke="#f97316" strokeWidth="1.5"/>
                   <circle cx="30" cy="40" r="3" fill="#f97316"/> {/* Tap Reserve */}
                   <line x1="30" y1="80" x2="0" y2="80" stroke="#f97316" strokeWidth="1.5"/>
                   <STS x={0} y={90} />
                   <line x1="0" y1="100" x2="0" y2="130" stroke="#000" strokeWidth="2"/>
                 </g>
               ) : type === '2N' ? (
                 <g>
                   {/* 2N Logic: Two full vertical feeds */}
                   <line x1="-15" y1="40" x2="-15" y2="130" stroke="#000" strokeWidth="1.5"/>
                   {/* Side B Phantom */}
                   <line x1="15" y1="-100" x2="15" y2="130" stroke="#000" strokeWidth="1.5" strokeDasharray="2,2"/>
                   <Transformer x={15} y={-20} />
                   <text x="-25" y="100" textAnchor="end" fontSize="8" fontWeight="bold">A</text>
                   <text x="25" y="100" textAnchor="start" fontSize="8" fontWeight="bold">B</text>
                 </g>
               ) : (
                 <g>
                   {/* Distributed */}
                   <line x1="-10" y1="40" x2="-10" y2="130" stroke="#000" strokeWidth="1.5"/>
                   <line x1="10" y1="40" x2="10" y2="130" stroke="#000" strokeWidth="1.5"/>
                   <text x="0" y="80" textAnchor="middle" fontSize="7">Rotational</text>
                 </g>
               )}

               {/* The Load */}
               <rect x="-25" y="130" width="50" height="40" fill="#eee" stroke="#000" strokeWidth="1"/>
               <text x="0" y="155" textAnchor="middle" fontSize="10" fontWeight="bold">HALL {i+1}</text>
            </g>
          )
        })}
      </g>
    );
  };

  return (
    <svg viewBox="0 0 900 800" className="w-full h-full bg-white">
       <rect x="0" y="0" width="900" height="800" fill="#fff"/>
       {renderPOI()}
       {renderGeneration()}
       {renderDistribution()}
       
       {/* Legends/Notes */}
       <g transform="translate(20, 750)">
         <text fontWeight="bold">NOTES:</text>
         <text y="15" fontSize="10">1. POI: {ELECTRICAL_SPECS.poi[poiConfig].label} ({ELECTRICAL_SPECS.poi[poiConfig].tier})</text>
         <text y="28" fontSize="10">2. GEN: {ELECTRICAL_SPECS.generation[genConfig].label} - {ELECTRICAL_SPECS.generation[genConfig].desc}</text>
         <text y="41" fontSize="10">3. DIST: {ELECTRICAL_SPECS.distribution[distConfig].label} - {ELECTRICAL_SPECS.distribution[distConfig].desc}</text>
       </g>
    </svg>
  );
};

// ============================================================================
// 4. SITE PLAN COMPONENT
// ============================================================================
const SitePlan = ({ results, config }) => {
  const { equipment, site } = results;
  const scale = 1.2; // Scaling factor for the view
  
  // Dynamic Footprints
  const subLib = FOOTPRINT_LIBRARY[config.poiConfig === 'breaker_half' ? 'substation_345kv_bah' : 'substation_345kv_ring'];
  const recipCount = equipment.recip.count;
  const recipW = 120; // Fixed powerhouse width
  const recipL = recipCount * 25 + 50; // Dynamic length
  
  return (
    <svg viewBox="0 0 900 600" className="w-full h-full bg-white border">
      <defs>
        <pattern id="grid" width="50" height="50" patternUnits="userSpaceOnUse">
          <path d="M 50 0 L 0 0 0 50" fill="none" stroke="#f0f0f0" strokeWidth="1"/>
        </pattern>
      </defs>
      <rect width="900" height="600" fill="url(#grid)" />
      
      {/* Property Line (Approx 50 acres at 3:2 ratio) */}
      <rect x="50" y="50" width="800" height="500" fill="none" stroke="#333" strokeWidth="3" strokeDasharray="10,5"/>
      <text x="450" y="40" textAnchor="middle" fontWeight="bold">PROPERTY BOUNDARY ({site.acreage} ACRES)</text>

      {/* 1. Substation */}
      <g transform="translate(80, 80)">
        <rect width={subLib.width/3} height={subLib.length/3} fill="#e0e7ff" stroke="#3730a3" strokeWidth="2"/>
        <text x="10" y="25" fontSize="12" fontWeight="bold">POI SUBSTATION</text>
        <text x="10" y="40" fontSize="10">{subLib.label}</text>
      </g>

      {/* 2. Generation Hall (Recips) */}
      <g transform="translate(500, 300)">
        <rect width={recipL} height={recipW} fill="#dbeafe" stroke="#1e40af" strokeWidth="2"/>
        <text x={recipL/2} y={recipW/2} textAnchor="middle" fontSize="12" fontWeight="bold">POWER HOUSE</text>
        <text x={recipL/2} y={recipW/2 + 15} textAnchor="middle" fontSize="10">{recipCount} Engines</text>
        {/* Stacks */}
        {[...Array(recipCount)].map((_, i) => (
          <circle key={i} cx={25 + i*25} cy={10} r={3} fill="#000" />
        ))}
      </g>

      {/* 3. Turbines (if any) */}
      {equipment.turbine.count > 0 && (
        <g transform="translate(300, 80)">
           {[...Array(equipment.turbine.count)].map((_, i) => (
             <g key={i} transform={`translate(${i*70}, 0)`}>
               <rect width="50" height="90" fill="#fef3c7" stroke="#b45309" strokeWidth="2"/>
               <text x="25" y="45" textAnchor="middle" fontSize="10">GT-{i+1}</text>
             </g>
           ))}
        </g>
      )}

      {/* 4. BESS */}
      {equipment.bess.rating_mw > 0 && (
        <g transform="translate(80, 400)">
           <rect width="200" height="100" fill="#dcfce7" stroke="#166534" strokeWidth="2"/>
           <text x="100" y="50" textAnchor="middle" fontSize="12" fontWeight="bold">BESS YARD</text>
           <text x="100" y="65" textAnchor="middle" fontSize="10">{equipment.bess.rating_mw} MW</text>
        </g>
      )}
      
      {/* North Arrow */}
      <g transform="translate(800, 500)">
        <path d="M0 20 L10 -10 L20 20 L10 15 Z" fill="#000"/>
        <text x="10" y="35" textAnchor="middle" fontWeight="bold">N</text>
      </g>
    </svg>
  );
};

// ============================================================================
// 5. MAIN UI WRAPPER
// ============================================================================

const EngineeringDrawingsFinal = () => {
  const [activeTab, setActiveTab] = useState('oneline');
  
  // State
  const [recipCount, setRecipCount] = useState(10);
  const [turbineCount, setTurbineCount] = useState(2);
  const [bessMW, setBessMW] = useState(50);
  const [siteAcres, setSiteAcres] = useState(50);
  
  // Configurations
  const [poiConfig, setPoiConfig] = useState('ring_n1');
  const [genConfig, setGenConfig] = useState('double_bus');
  const [distConfig, setDistConfig] = useState('catcher');
  
  // Computed Results
  const results = useMemo(() => ({
    projectName: "Project Titan",
    projectNumber: "BV-2026-X",
    equipment: {
      recip: { count: recipCount },
      turbine: { count: turbineCount },
      bess: { rating_mw: bessMW }
    },
    totals: { installed_mw: (recipCount * 9.7) + (turbineCount * 50) + bessMW },
    site: { acreage: siteAcres }
  }), [recipCount, turbineCount, bessMW, siteAcres]);

  const config = { poiConfig, genConfig, distConfig };

  return (
    <div className="min-h-screen bg-gray-50 p-6 font-sans text-gray-800">
      <div className="max-w-7xl mx-auto space-y-6">
        
        {/* HEADER */}
        <div className="bg-white p-6 rounded-lg shadow-sm border-l-4 border-blue-600 flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold">Engineering Dashboard: 15% Concept Design</h1>
            <p className="text-gray-500 text-sm">Validating: {poiConfig} | {genConfig} | {distConfig}</p>
          </div>
          <div className="text-right">
             <div className="text-3xl font-bold text-blue-600">{results.totals.installed_mw.toFixed(1)} MW</div>
             <div className="text-xs text-gray-500">Total Installed Capacity</div>
          </div>
        </div>

        {/* CONTROLS */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
           {/* Inputs */}
           <div className="bg-white p-4 rounded shadow-sm col-span-1 space-y-4">
              <h3 className="font-bold border-b pb-2">Equipment Inputs</h3>
              <div className="space-y-2">
                 <label className="flex justify-between text-sm">
                    <span>Recip Engines:</span>
                    <input type="number" value={recipCount} onChange={e=>setRecipCount(Number(e.target.value))} className="border w-16 text-right rounded"/>
                 </label>
                 <label className="flex justify-between text-sm">
                    <span>Gas Turbines:</span>
                    <input type="number" value={turbineCount} onChange={e=>setTurbineCount(Number(e.target.value))} className="border w-16 text-right rounded"/>
                 </label>
                 <label className="flex justify-between text-sm">
                    <span>BESS (MW):</span>
                    <input type="number" value={bessMW} onChange={e=>setBessMW(Number(e.target.value))} className="border w-16 text-right rounded"/>
                 </label>
              </div>
           </div>

           {/* Configs */}
           <div className="bg-white p-4 rounded shadow-sm col-span-3 grid grid-cols-3 gap-4">
              <div>
                 <h3 className="font-bold border-b pb-2 mb-2">POI Substation</h3>
                 <select value={poiConfig} onChange={e=>setPoiConfig(e.target.value)} className="w-full border p-2 rounded bg-gray-50">
                    {Object.entries(ELECTRICAL_SPECS.poi).map(([k,v]) => <option key={k} value={k}>{v.label}</option>)}
                 </select>
                 <p className="text-xs text-gray-500 mt-1">{ELECTRICAL_SPECS.poi[poiConfig].tier}</p>
              </div>
              <div>
                 <h3 className="font-bold border-b pb-2 mb-2">Generation Bus</h3>
                 <select value={genConfig} onChange={e=>setGenConfig(e.target.value)} className="w-full border p-2 rounded bg-gray-50">
                    {Object.entries(ELECTRICAL_SPECS.generation).map(([k,v]) => <option key={k} value={k}>{v.label}</option>)}
                 </select>
                 <p className="text-xs text-gray-500 mt-1">{ELECTRICAL_SPECS.generation[genConfig].desc}</p>
              </div>
              <div>
                 <h3 className="font-bold border-b pb-2 mb-2">Distribution</h3>
                 <select value={distConfig} onChange={e=>setDistConfig(e.target.value)} className="w-full border p-2 rounded bg-gray-50">
                    {Object.entries(ELECTRICAL_SPECS.distribution).map(([k,v]) => <option key={k} value={k}>{v.label}</option>)}
                 </select>
                 <p className="text-xs text-gray-500 mt-1">{ELECTRICAL_SPECS.distribution[distConfig].desc}</p>
              </div>
           </div>
        </div>

        {/* VISUALIZATION TABS */}
        <div className="bg-white rounded-lg shadow-sm overflow-hidden">
           <div className="flex border-b">
              <button onClick={()=>setActiveTab('oneline')} className={`flex-1 py-3 font-semibold ${activeTab==='oneline' ? 'bg-blue-50 text-blue-700 border-b-2 border-blue-700' : 'text-gray-500 hover:bg-gray-50'}`}>
                 ⚡ Single Line Diagram
              </button>
              <button onClick={()=>setActiveTab('site')} className={`flex-1 py-3 font-semibold ${activeTab==='site' ? 'bg-blue-50 text-blue-700 border-b-2 border-blue-700' : 'text-gray-500 hover:bg-gray-50'}`}>
                 🗺️ Site Plan
              </button>
           </div>
           
           <div className="p-6 bg-gray-100 min-h-[600px] flex items-center justify-center">
              <div className="bg-white shadow-lg w-full max-w-5xl aspect-[4/3] rounded-sm overflow-hidden border">
                 {activeTab === 'oneline' ? (
                   <OneLineDiagram results={results} config={config} />
                 ) : (
                   <SitePlan results={results} config={config} />
                 )}
              </div>
           </div>
        </div>

      </div>
    </div>
  );
};

export default EngineeringDrawingsFinal;
