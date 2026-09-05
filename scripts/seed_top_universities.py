"""Seeder script for Top-Tier Universities & Engineering Institutions in Tamil Nadu.
Populates realistic faculty expertise, specialized research labs, CoEs, and past projects
aligned with societal challenge domains (Water, Agriculture, Healthcare, Waste, Energy, GIS, IoT, Infrastructure).
"""
import sqlite3
from database.db import get_db

TOP_UNIVERSITIES_DATA = [
    {
        "name": "Indian Institute of Technology Madras (IIT Madras)",
        "city": "Chennai",
        "description": "Premier institute of national importance specializing in DeepTech, RBCDSAI artificial intelligence, Pravartak cyber-physical sensor systems, solid-state battery tech, water desalination, and clean energy.",
        "capacity": 15,
        "contact_email": "dean.icmr@iitm.ac.in",
        "faculty": [
            ("Dr. B. Ravindran", "Data Science and AI", "artificial intelligence, machine learning, reinforcement learning, network data science"),
            ("Dr. Thalappil Pradeep", "Chemistry and Water Technology", "water purification, nanotechnology, heavy metal remediation, clean drinking water"),
            ("Dr. V. Kamakoti", "Computer Science", "cyber-physical systems, secure microprocessors, edge computing, rural telemetry"),
            ("Dr. Ligy Philip", "Civil and Environmental Engineering", "wastewater treatment, biological waste management, wetland ecology, sanitation")
        ],
        "labs": [
            ("Robert Bosch Centre for Data Science and AI (RBCDSAI)", "machine learning compute clusters, NLP models, predictive healthcare, edge AI"),
            ("National Centre for Combustion & Clean Energy (NCCRD)", "micro-turbines, clean combustion, biofuel synthesis, alternative energy"),
            ("IITM Pravartak Cyber-Physical Systems Lab", "sensor networks, IoT gateways, drone telemetry, smart infrastructure"),
            ("International Centre for Clean Water (ICCW)", "spectrophotometers, water quality testbeds, nano-filter fabrication, arsenic removal")
        ],
        "projects": [
            ("Nano-Scale Water Filtration Pilot", "Affordable point-of-use nano-filtration units deployed across rural drinking water supply tanks."),
            ("AI-Driven Crop Health Surveillance", "Computer vision aerial analytics for pest and early blight detection across agricultural clusters."),
            ("Urban Flood Early Warning Network", "IoT sensor telemetry deployed across Adyar & Cooum river basins for real-time flood forecasting.")
        ]
    },
    {
        "name": "National Institute of Technology Tiruchirappalli (NIT Trichy)",
        "city": "Tiruchirappalli",
        "description": "National institute renowned for Siemens CoE smart manufacturing, clean water research, transportation infrastructure, smart microgrids, and renewable energy.",
        "capacity": 12,
        "contact_email": "dean_academic@nitt.edu",
        "faculty": [
            ("Dr. G. Swaminathan", "Civil and Environmental Engineering", "water quality testing, sewage treatment plants, environmental impact assessment, hydrology"),
            ("Dr. N. Sivakumaran", "Instrumentation & Control", "IoT sensors, process automation, medical instrumentation, remote monitoring"),
            ("Dr. S. Arul Daniel", "Electrical and Electronics", "solar microgrids, renewable energy storage, rural electrification, power electronics"),
            ("Dr. P. Sathiya", "Production Engineering", "additive manufacturing, advanced welding, precision machinery, materials characterization")
        ],
        "labs": [
            ("Siemens Centre of Excellence in Manufacturing", "industrial robotics, CNC testbeds, digital twins, reverse engineering, rapid prototyping"),
            ("Centre of Excellence in Transportation Engineering (CETrans)", "smart traffic simulators, pavement testing, GIS road analysis, emission monitoring"),
            ("Environmental Engineering Analytical Lab", "BOD/COD analysers, atomic absorption spectrometers, water contaminant testing"),
            ("Microgrid & Renewable Energy Laboratory", "solar PV simulator, battery testing racks, hybrid grid controllers")
        ],
        "projects": [
            ("Cauvery Delta Groundwater Monitoring", "Continuous telemetry monitoring nitrate and salinity intrusion in farm irrigation wells."),
            ("Solar Smart Microgrid for Rural Health Centers", "Hybrid solar-storage microgrids providing uninterruptible power for rural primary health clinics."),
            ("Plastic Waste Modified Bitumen Roads", "Field pilot using shredded plastic waste additives to construct high-durability rural roads.")
        ]
    },
    {
        "name": "Anna University (CEG & MIT Campuses)",
        "city": "Chennai",
        "description": "State premier engineering university. Houses CASR drone research centre, AU-FRG CAD/CAM, Centre for Climate Change, water resources and geo-informatics.",
        "capacity": 14,
        "contact_email": "director_research@annauniv.edu",
        "faculty": [
            ("Dr. K. Senthil Kumar", "Aerospace Engineering (CASR - MIT)", "unmanned aerial vehicles, drone surveillance, disaster mapping payloads, remote sensing"),
            ("Dr. B. V. Mudgal", "Centre for Water Resources (CEG)", "hydrological modeling, flood mitigation, urban drainage, rainwater harvesting"),
            ("Dr. R. Vidhyapriya", "Information Technology", "IoT systems, cloud platforms, healthcare informatics, citizen feedback systems"),
            ("Dr. K. Balamurugan", "Automobile Engineering (MIT)", "electric vehicle battery systems, smart mobility, low-emission propulsion")
        ],
        "labs": [
            ("Centre for Aerospace Research (CASR)", "UAV fabrication, autonomous flight controllers, thermal imaging cameras, LiDAR payloads"),
            ("Centre for Water Resources & GIS Lab", "GIS mapping software, satellite telemetry, hydro-meteorological stations, ground radar"),
            ("Centre for Artificial Intelligence & Data Science (CAIDS)", "GPU cluster, municipal big-data analytics, applied AI smart city models"),
            ("National Centre for Sustainable Coastal Management (NCSCM)", "marine quality testing, coastal erosion monitoring, satellite oceanography")
        ],
        "projects": [
            ("Disaster Relief & Damage Assessment Drone Fleet", "Autonomous multi-rotor drones mapping structural damage and delivering medical kits during cyclonic floods."),
            ("Smart Tank Cascade Rejuvenation System", "Geo-informatics mapping and automated sluice-gate control across rural cascade irrigation tanks."),
            ("Municipal Solid Waste Route Optimization", "AI and GPS tracking system optimizing waste collection routes and landfill diversion in Chennai.")
        ]
    },
    {
        "name": "PSG College of Technology",
        "city": "Coimbatore",
        "description": "Autonomous premier technical institution with strong industry integration, Siemens automation, robotics, biomedical devices, and textile technology.",
        "capacity": 10,
        "contact_email": "principal@psgtech.edu",
        "faculty": [
            ("Dr. P. Radhakrishnan", "Mechatronics and Robotics", "industrial automation, robotics, PLC/SCADA, sensor calibration"),
            ("Dr. S. Subha", "Biomedical Engineering", "biomedical devices, patient vital sensors, low-cost diagnostic kits"),
            ("Dr. R. Rudramoorthy", "Mechanical Engineering", "solar thermal systems, waste heat recovery, energy audits"),
            ("Dr. G. Thilagavathi", "Textile Technology", "eco-friendly technical textiles, wastewater filtration geotextiles, antimicrobial fabrics")
        ],
        "labs": [
            ("PSG-Siemens CoE in Automation & Robotics", "robotic arms, pneumatic/hydraulic test rigs, PLC simulation, automated sorting"),
            ("Nanotechnology Research Centre (NRC)", "SEM, XRD, electrospinning rigs, nanomaterials for water purification"),
            ("Biomedical Instrumentation Testing Facility", "ECG/EEG simulators, patient monitoring calibration, biosensors"),
            ("Centre for Industrial Energy Conservation", "thermal imaging cameras, flue gas analyzers, power quality meters")
        ],
        "projects": [
            ("Low-Cost Neonatal Vital Signs Monitor", "Portable IoT-connected pulse-oximeter and temperature monitor for rural maternity wards."),
            ("Industrial Effluent Textile Filter Modules", "Nanofiber membrane cartridges treating chemical dye effluents for textile micro-units in Tiruppur."),
            ("Solar Cold Storage for Perishable Produce", "Decentralized 5-tonne solar-powered cold room deployed for smallholder vegetable farmers.")
        ]
    },
    {
        "name": "SSN College of Engineering",
        "city": "Chennai",
        "description": "Top-tier research institution renowned for single-crystal growth, optoelectronics, speech processing, and environmental monitoring.",
        "capacity": 9,
        "contact_email": "research@ssn.edu.in",
        "faculty": [
            ("Dr. P. Ramasamy", "SSN Research Centre", "crystal growth, optoelectronic sensors, radiation detectors, advanced materials"),
            ("Dr. T. Nagarajan", "Computer Science & Speech Lab", "speech processing, Tamil NLP, low-resource language translation, voice assistants"),
            ("Dr. S. Chitra", "Chemical Engineering", "catalysis, water effluent treatment, heavy metal removal, bio-fuels"),
            ("Dr. V. Kamalkannan", "Civil Engineering", "structural health monitoring, geopolymer concrete, GIS flood mapping")
        ],
        "labs": [
            ("SSN Research Centre (SSNRC)", "crystal growth furnaces, HRTEM, spectrophotometers, cleanroom facilities"),
            ("Speech and Language Processing Lab", "high-end audio workstations, speech recognition engines, NLP models"),
            ("Chemical Environmental Analysis Facility", "HPLC, Gas Chromatograph, UV-Vis Spectrometer, TOC analyzer"),
            ("IoT & Smart Cities Innovation Lab", "LoRaWAN gateways, environmental sensor nodes, edge computing boards")
        ],
        "projects": [
            ("Tamil Voice-Enabled Agricultural Advisory", "Dial-in automated voice system answering crop pest queries in conversational Tamil for rural farmers."),
            ("LoRaWAN Air Quality Mesh Network", "Continuous particulate matter (PM2.5/PM10) and gas emission sensor mesh across industrial belts."),
            ("Recycled Fly-Ash Geopolymer Pavement Blocks", "High-strength eco-friendly paving blocks utilizing thermal power plant fly ash for rural roads.")
        ]
    },
    {
        "name": "SASTRA Deemed University",
        "city": "Thanjavur",
        "description": "Premier multidisciplinary university near the Cauvery delta with state-of-the-art Anusandhan Kendra, biotechnology, VLSI, and agricultural innovation labs.",
        "capacity": 10,
        "contact_email": "dean.research@sastra.edu",
        "faculty": [
            ("Dr. S. Swaminathan", "Nanotechnology and Biotechnology", "tissue engineering, 3D bioprinting, biomaterials, nano-biosensors"),
            ("Dr. K. Uma", "School of Electrical Engineering", "smart grids, embedded systems, agricultural telemetry, sensor networks"),
            ("Dr. P. R. Vaidyanathan", "Civil and Rural Engineering", "delta water management, canal irrigation optimization, soil testing"),
            ("Dr. B. Santhi", "Computer Science", "cybersecurity, machine learning, medical image processing")
        ],
        "labs": [
            ("Anusandhan Kendra (Central Research Facility)", "HRTEM, Field-Emission SEM, NMR, X-Ray Diffraction, confocal microscope"),
            ("Centre for Advanced Research in Indian System of Medicine (CARISM)", "phytochemical extraction, drug screening, bio-assays"),
            ("TBI 3D Bioprinting & Medical Additive Lab", "bioprinters, biomaterial extruders, cell culture suites"),
            ("Precision Agriculture & Soil Health Lab", "soil nutrient spectrometers, automated NPK testers, moisture sensors")
        ],
        "projects": [
            ("Rapid Soil NPK Optical Scanner", "Handheld optical probe giving farmers instant on-field NPK nutrient and pH readouts via mobile app."),
            ("Cauvery Sluice Automation & Canal Silt Monitor", "Ultrasonic silt depth measurement nodes communicating water availability to downstream farmers."),
            ("Low-Cost Water-Borne Pathogen Detection Kit", "Paper-based microfluidic strip detecting E. coli contamination in rural drinking wells within 30 minutes.")
        ]
    },
    {
        "name": "Vellore Institute of Technology (VIT)",
        "city": "Vellore",
        "description": "Deemed institution of eminence with TIFAC-CORE automotive infotronics, renewable energy, clean water research, and electric mobility systems.",
        "capacity": 12,
        "contact_email": "dean.rnd@vit.ac.in",
        "faculty": [
            ("Dr. K. Chidambaram", "Automotive & Mechanical", "battery management systems, EV powertrains, thermal management, vehicle dynamics"),
            ("Dr. A. Mary Saral", "Chemistry & Clean Water", "membrane distillation, solar water desalination, water fluoride defluoridation"),
            ("Dr. R. Sivabalan", "Chemical Engineering", "waste-to-energy, biomass gasification, carbon capture, bio-adsorbents"),
            ("Dr. P. Geetha", "School of Computer Science", "AI in healthcare, IoT edge computing, deep learning, smart municipal systems")
        ],
        "labs": [
            ("TIFAC-CORE in Automotive Infotronics", "battery cycler testbenches, hardware-in-the-loop (HIL) simulators, CAN bus analyzers"),
            ("Centre for Nanotechnology Research (CNR)", "solar membrane distillation rigs, supercapacitor testers, electrochemistry workstations"),
            ("Energy Research Centre", "biomass gasifiers, solar concentrating collectors, wind energy simulators"),
            ("IoT & Smart Health Research Lab", "wearable sensors, edge gateways, telemedicine communication kits")
        ],
        "projects": [
            ("Solar-Assisted Defluoridation Unit", "Community-scale solar-driven activated alumina filtration unit for high-fluoride groundwater belts."),
            ("Battery Pack Health Monitoring for Rural E-Rickshaws", "IoT telemetry board diagnosing battery cell degradation and range estimation for electric transit."),
            ("Agricultural Biomass Pelletizer & Biochar Unit", "Mobile farm-waste pelletizer converting crop stubble into smokeless heating pellets and biochar.")
        ]
    },
    {
        "name": "Thiagarajar College of Engineering (TCE)",
        "city": "Madurai",
        "description": "Historic top autonomous institution in southern Tamil Nadu with pioneering plastic road technology, environmental nanotechnology, and smart grid labs.",
        "capacity": 8,
        "contact_email": "principal@tce.edu",
        "faculty": [
            ("Dr. R. Vasudevan", "Chemistry & Environmental Technology", "waste plastic utilization in road construction, solid waste management, eco-materials"),
            ("Dr. S. Charles Raja", "Electrical and Electronics", "smart microgrids, demand-side power management, rural solar irrigation pumps"),
            ("Dr. C. Jeyamala", "Information Technology", "AI for healthcare, mobile apps for citizen grievance redressal, GIS mapping"),
            ("Dr. G. Chitra", "Civil Engineering", "sustainable concrete, groundwater recharge, stormwater harvesting structures")
        ],
        "labs": [
            ("TCE Centre for Waste Plastic Management", "polymer blending test rigs, bitumen viscosity analyzers, asphalt testing machines"),
            ("TCE-Honeywell Wireless Innovation Lab", "wireless sensor network testbeds, Zigbee/LoRa transceivers, IoT mesh modules"),
            ("Environmental Nanotechnology Lab", "turbidity meters, spectrophotometers, water remediation reaction vessels"),
            ("Smart Grid & Solar Pump Testing Facility", "solar pump dynamometer, inverter testbench, power grid simulator")
        ],
        "projects": [
            ("Plastic-Waste Pavement Road Technology", "Patented bitumen-plastic blend paving over 500 km of rural roads with 2x lifespan."),
            ("Solar Smart Irrigation Pump Controller", "IoT-controlled solar pump providing remote scheduling and automated dry-run protection for small farms."),
            ("Temple City Solid Waste & Compost Monitor", "Sensorized aerobic composting pits with temperature and moisture telemetry for municipal waste.")
        ]
    },
    {
        "name": "SRM Institute of Science and Technology",
        "city": "Chennai",
        "description": "Multi-campus deemed university with strong automotive research, nanotechnology, bioinformatics, and large-scale IoT infrastructure programs.",
        "capacity": 11,
        "contact_email": "research.director@srmist.edu.in",
        "faculty": [
            ("Dr. Sandeep Sancheti", "Mechanical Engineering (Automotive)", "vehicle dynamics, EV powertrains, automotive composites, hybrid energy systems"),
            ("Dr. M. Vimalanathan", "Biotechnology", "molecular biology, bioinformatics, plant tissue culture, vaccine diagnostics"),
            ("Dr. T. Sridhar", "Electronics & IoT", "embedded systems, LoRaWAN, sensor networks, industrial IoT"),
            ("Dr. K. Raja", "Civil Engineering", "structural health monitoring, green concrete, bridge diagnostics")
        ],
        "labs": [
            ("SRM Automotive Research Centre", "engine dynamometer, vehicle crash testbed, EV battery test rigs, NVH lab"),
            ("Centre for Nanotechnology", "AFM, electron beam lithography, nano-composite fabrication"),
            ("Bioinformatics & Molecular Diagnostics Lab", "next-gen sequencer, PCR workstations, protein crystallography"),
            ("IoT Innovation Cell", "ARM Cortex dev kits, Zigbee/LoRa gateways, edge-AI inference boards")
        ],
        "projects": [
            ("Low-Cost EV Retrofit for Auto-Rickshaws", "Conversion kits with swappable battery packs deployed across Chennai pilot fleet."),
            ("Portable DNA-Based Pathogen Detector", "Rapid field test detecting water-borne pathogens in rural wells within 45 minutes."),
            ("Smart Building Vibration Monitor", "LoRaWAN-based structural integrity sensors for Chennai Metro elevated corridors.")
        ]
    },
    {
        "name": "Amrita Vishwa Vidyapeetham (Coimbatore Campus)",
        "city": "Coimbatore",
        "description": "Multi-campus deemed university renowned for AmritaWNA wireless sensor network for disaster early warning, CEN deep learning lab, and live-in-lab humanitarian engineering programs.",
        "capacity": 12,
        "contact_email": "research@amrita.edu",
        "faculty": [
            ("Dr. M. Sethumadhavan", "Cyber Security & CEN", "deep learning, NLP, vulnerability analysis, post-quantum cryptography"),
            ("Dr. Maneesha V. Ramesh", "Wireless Networks & AmritaWNA", "wireless sensor networks, disaster early warning, IoT telemetry, landslide detection"),
            ("Dr. K. P. Soman", "Computational Engineering", "machine learning, signal processing, healthcare analytics"),
            ("Dr. B. V. K. Reddy", "Civil Engineering", "disaster-resilient housing, landslide mitigation, low-cost rural infrastructure")
        ],
        "labs": [
            ("Amrita Centre for Cybersecurity (CEN)", "deep learning GPU cluster, NLP pipelines, threat modelling, cryptographic test rigs"),
            ("AmritaWNA Wireless Sensor Network Lab", "deployable landslide monitoring nodes, MEMS geophones, LoRa gateways"),
            ("AmritaLIVE Humanitarian Tech Lab", "field-deployable IoT kits, off-grid solar computing, low-power mesh networks"),
            ("Molecular Biology & Biomedical Lab", "PCR, ELISA readers, immunohistochemistry, regenerative tissue scaffolds")
        ],
        "projects": [
            ("Landslide Early Warning - Western Ghats", "Real-time sensor network in Munnar hills providing SMS alerts to villagers 30 minutes before landslides."),
            ("AI Chatbot for Tamil Citizen Services", "NLP-based conversational agent answering government scheme queries in Tamil."),
            ("Portable Drinking Water Quality Analyzer", "Solar-powered multi-parameter IoT kit measuring pH, TDS, turbidity in rural schools.")
        ]
    },
    {
        "name": "Sathyabama Institute of Science and Technology",
        "city": "Chennai",
        "description": "Deemed university with Col. Dr. Jeppiaar Research Park housing DST/DBT-funded centres in ocean research, nanomedicine, drug discovery, and IoT-enabled aquaculture monitoring.",
        "capacity": 10,
        "contact_email": "research@sathyabama.ac.in",
        "faculty": [
            ("Dr. T. Sasipraba", "Biotechnology & Ocean Research", "marine biotechnology, biopolymers, aquaculture monitoring, water biofouling"),
            ("Dr. S. Suresh Kumar", "Nanomedical Sciences", "nanomedicine, targeted drug delivery, cancer diagnostics, molecular imaging"),
            ("Dr. A. Chitra", "IoT & Embedded Systems", "edge-AI inference, smart healthcare wearables, precision agriculture sensor nodes"),
            ("Dr. R. A. K. Reddy", "Space Technology & Nanoscience", "nanosatellites, satellite telemetry, MEMS design, NEMS biosensors")
        ],
        "labs": [
            ("Centre for Ocean Research (COR)", "seawater flow-through lab, marine microalgae culture, chromatography & spectroscopy rigs"),
            ("Centre for Molecular and Nanomedical Sciences (CMNS)", "confocal microscopy, flow cytometry, real-time PCR, cell culture suites"),
            ("Centre for Waste Management (CWM)", "biodegradation reactors, biogas/microbial fuel cells, microplastics remediation rigs"),
            ("Centre for IoT & AI (CAIML)", "ESP32/ARM Cortex dev boards, LoRaWAN/NB-IoT gateways, edge-AI inference kits")
        ],
        "projects": [
            ("IoT-Enabled Coastal Aquaculture Buoy", "Solar-powered offshore sensor buoy measuring dissolved oxygen, pH, and salinity for shrimp farms."),
            ("Smart Biosensor Point-of-Care Diagnostics", "Paper microfluidic strips transmitting patient vitals via IoT to primary health centre."),
            ("SATHYABAMASAT Nano-Satellite Programme", "Student-built nanosatellite launched via ISRO PSLV carrying agricultural imaging payload.")
        ]
    },
    {
        "name": "Kumaraguru College of Technology (KCT)",
        "city": "Coimbatore",
        "description": "Autonomous institution linked to Coimbatore's automotive and textile industrial ecosystem, with strong product innovation, smart manufacturing, and applied materials research.",
        "capacity": 8,
        "contact_email": "principal@kct.ac.in",
        "faculty": [
            ("Dr. P. Karvannan", "Automobile Engineering", "vehicle dynamics, electric two-wheeler design, automotive composites"),
            ("Dr. S. Saravanan", "Mechanical Engineering", "smart manufacturing, Industry 4.0, CNC retrofitting, additive manufacturing"),
            ("Dr. M. Ramachandran", "Fashion Technology", "technical textiles, sustainable dyeing, anti-microbial fabrics"),
            ("Dr. R. Nagaraj", "Computer Science", "machine learning, edge AI, IoT for industrial monitoring")
        ],
        "labs": [
            ("Centre for Innovation and Product Development (CIPD)", "rapid prototyping, 3D printers, laser cutters, design thinking workshop"),
            ("Automotive Component Testing Lab", "engine dynamometer, suspension test rig, NVH analyser, EV powertrain bench"),
            ("Technical Textile Testing Facility", "GSM cutter, tensile tester, water permeability, fabric breathability rigs"),
            ("Fabrication & Additive Lab", "CNC milling, lathe, FDM/SLA 3D printers, PCB prototyping")
        ],
        "projects": [
            ("Low-Cost EV Conversion for Two-Wheelers", "Conversion kit for petrol two-wheelers to electric drive, deployed in Coimbatore's delivery fleet."),
            ("Anti-Microbial Medical Textiles", "Herbal-coated fabric for hospital bed-sheets reducing HAIs by 60% in pilot wards."),
            ("Smart Factory Energy Monitor", "IoT platform tracking real-time power consumption across Coimbatore SME units.")
        ]
    },
    {
        "name": "Coimbatore Institute of Technology (CIT)",
        "city": "Coimbatore",
        "description": "Historic autonomous engineering institution pioneering cryogenic engineering, motorsport research, and VLSI design in Tamil Nadu.",
        "capacity": 7,
        "contact_email": "principal@cit.edu.in",
        "faculty": [
            ("Dr. R. Prabhakar", "Mechanical (Cryogenics)", "cryogenic storage, LNG transport, low-temperature material testing"),
            ("Dr. C. Pugazhendhi", "Electrical & VLSI", "FPGA design, VLSI layout, embedded signal processing"),
            ("Dr. M. Senthil Kumar", "Civil Engineering", "structural retrofitting, GIS mapping, pavement engineering"),
            ("Dr. K. Anuradha", "Computer Science", "data mining, healthcare analytics, software engineering")
        ],
        "labs": [
            ("Cryogenic Engineering Lab", "cryostat test chambers, LNG storage simulators, vacuum-insulated transfer lines"),
            ("CIT Motorsports Research Centre", "formula student chassis fab, CFD workstation, telemetry rigs"),
            ("VLSI Design Lab", "FPGA dev boards, ASIC synthesis workstations, EDA toolchain licenses"),
            ("Structural Health Diagnostics Lab", "accelerometers, strain gauges, modal analysis, NDT equipment")
        ],
        "projects": [
            ("Rural Cryogenic Milk Chilling Unit", "Decentralized LNG-powered milk chilling point for dairy cooperatives in Pollachi."),
            ("Formula Student Electric Race Vehicle", "Student-built EV race car with bespoke battery management system."),
            ("Pavement Health GIS Mapping", "Drone-based crack detection for Coimbatore rural road network with auto-classification.")
        ]
    },
    {
        "name": "Bannari Amman Institute of Technology",
        "city": "Sathyamangalam",
        "description": "Autonomous institution near Western Ghats with strong agricultural engineering, food technology, renewable energy, and tribal-area rural development research.",
        "capacity": 6,
        "contact_email": "principal@bitsathy.ac.in",
        "faculty": [
            ("Dr. S. Shanmugam", "Food Technology", "food processing, dairy engineering, post-harvest technology, packaging"),
            ("Dr. P. Selvam", "Electrical Engineering", "solar PV systems, wind energy hybrid controllers, microgrid power electronics"),
            ("Dr. M. Suresh", "Agricultural Engineering", "precision agriculture, soil moisture telemetry, drip irrigation optimization"),
            ("Dr. K. Prakash", "Civil Engineering", "low-cost housing, bamboo-reinforced concrete, watershed management")
        ],
        "labs": [
            ("Food Processing & Dairy Technology Lab", "pasteurization unit, spray dryer, cold storage chambers, quality testing rigs"),
            ("Renewable Energy & Microgrid Lab", "solar PV simulator, wind turbine testbench, hybrid inverter benches"),
            ("Precision Agriculture Lab", "soil moisture sensors, automated drip controllers, drone NDVI cameras"),
            ("Bamboo & Low-Cost Materials Lab", "bamboo treatment chambers, geopolymer concrete mixers, tile press")
        ],
        "projects": [
            ("Solar-Powered Cold Storage for Tribal Farmers", "5-tonne cold room with battery backup in Sathyamangalam tribal hamlets reducing post-harvest loss by 40%."),
            ("Community Watershed Restoration", "GIS-based watershed mapping and check-dam construction across Moyar river basin."),
            ("Low-Cost Bamboo Poultry Shelters", "Modular bamboo-framed poultry housing units for 200+ small-scale tribal farmers.")
        ]
    },
    {
        "name": "Vel Tech Rangarajan Dr. Sagunthala R&D Institute of Science and Technology",
        "city": "Chennai",
        "description": "Deemed university with strong AI, autonomous vehicles, medical robotics, and solar energy research programs backed by DST-funded research centres.",
        "capacity": 7,
        "contact_email": "research@veltech.edu.in",
        "faculty": [
            ("Dr. E. Kanniga", "AI & Machine Learning", "deep learning, computer vision, autonomous navigation, medical image analysis"),
            ("Dr. R. Rajesh", "Robotics & Automation", "medical robotics, exoskeleton design, rehabilitation devices, SLAM algorithms"),
            ("Dr. P. Malarvizhi", "Solar Energy", "perovskite solar cells, photovoltaic thermal systems, solar desalination"),
            ("Dr. S. Balaji", "Biomedical Engineering", "biosignal processing, ECG/EEG analysis, low-cost prosthetics")
        ],
        "labs": [
            ("AI & Autonomous Systems Lab", "GPU cluster for deep learning, NVIDIA Jetson kits, ROS-based mobile robots"),
            ("Medical Robotics & Rehabilitation Centre", "6-DOF robotic arms, force-feedback exoskeletons, gait analysis platforms"),
            ("Solar Energy Research Centre", "solar simulator, IV tracer, perovskite fabrication glovebox, thermal storage rigs"),
            ("Biomedical Signal Processing Lab", "multi-channel EEG, ECG, EMG acquisition systems, prosthetic prototyping")
        ],
        "projects": [
            ("Low-Cost Robotic Prosthetic Arm", "3D-printed below-elbow prosthetic with EMG-based grip control under ₹15,000."),
            ("Solar-Powered Brackish Water Purifier", "Off-grid unit producing 200 L/day from high-TDS borewell water for Chennai outskirts."),
            ("AI-Based Diabetic Retinopathy Screener", "Deep learning model running on tablet to grade retinal images in primary health centres.")
        ]
    },
    {
        "name": "Karunya Institute of Technology and Sciences",
        "city": "Coimbatore",
        "description": "Deemed Christian university with biomedical engineering, IoT-based healthcare, smart agriculture, and DRDO-funded defence research programmes.",
        "capacity": 8,
        "contact_email": "research@karunya.edu",
        "faculty": [
            ("Dr. D. Jude Hemanth", "Biomedical Engineering & AI", "medical image analysis, deep learning, IoT healthcare, diabetic screening"),
            ("Dr. J. Immanuel John Raja", "Robotics & IoT", "industrial IoT, swarm robotics, edge AI, agricultural drones"),
            ("Dr. R. Arumugam", "Aerospace Engineering", "UAV design, computational fluid dynamics, satellite subsystems"),
            ("Dr. V. Ebenezer", "Biotechnology", "plant molecular biology, biofertilizers, phytoremediation")
        ],
        "labs": [
            ("Karunya AI & Medical Imaging Lab", "deep learning workstations, GPU servers, medical image annotation tools"),
            ("DRDO-Karunya Defence Research Centre", "UAV integration testbed, sensor payload racks, RF/wireless test chambers"),
            ("IoT & Smart Agriculture Lab", "LoRaWAN/NB-IoT gateways, drone flight controllers, multispectral sensors"),
            ("Plant Molecular Biology Lab", "PCR, gel electrophoresis, plant tissue culture, biofertilizer bioreactors")
        ],
        "projects": [
            ("AI-Powered Cervical Cancer Screener", "Deep learning classifier for cervical smear images validated across 12 district hospitals."),
            ("Drone-Based Crop Spraying Service", "Autonomous multirotor drones for pesticide application across Coimbatore sugarcane farms."),
            ("IoT-Enabled Biofertilizer Production Monitor", "Real-time pH/temperature tracking for village-level biofertilizer units.")
        ]
    }
]


def populate_top_universities():
    """Populate database with rich institutional data."""
    with get_db() as db:
        for u in TOP_UNIVERSITIES_DATA:
            existing = db.execute("SELECT id FROM universities WHERE name=?", (u["name"],)).fetchone()
            if existing:
                uid = existing["id"]
                # Update capacity and description
                db.execute(
                    "UPDATE universities SET city=?, description=?, capacity=?, contact_email=? WHERE id=?",
                    (u["city"], u["description"], u["capacity"], u["contact_email"], uid)
                )
            else:
                cur = db.execute(
                    "INSERT INTO universities(name, city, description, capacity, verified, contact_email) VALUES(?,?,?,?,1,?)",
                    (u["name"], u["city"], u["description"], u["capacity"], u["contact_email"])
                )
                uid = cur.lastrowid

            # Insert faculty
            for f in u["faculty"]:
                db.execute(
                    "INSERT INTO faculty(university_id, name, department, expertise) VALUES(?,?,?,?)",
                    (uid, f[0], f[1], f[2])
                )

            # Insert labs
            for lab in u["labs"]:
                db.execute(
                    "INSERT INTO labs(university_id, name, facilities) VALUES(?,?,?)",
                    (uid, lab[0], lab[1])
                )

            # Insert past projects
            for proj in u["projects"]:
                db.execute(
                    "INSERT INTO previous_projects(university_id, title, description) VALUES(?,?,?)",
                    (uid, proj[0], proj[1])
                )

            # Create an authenticated university login account if missing
            slug = u["name"].split()[0].lower().replace("(", "").replace(")", "")
            email = f"lead@{slug}.edu"
            existing_user = db.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
            if not existing_user:
                from auth.models import hash_password
                db.execute(
                    "INSERT INTO users(email, password_hash, name, role, org_id) VALUES(?,?,?,?,?)",
                    (email, hash_password("uni123"), u["name"] + " Lead", "university", uid)
                )

    print(f"Populated {len(TOP_UNIVERSITIES_DATA)} top-tier institutions in Tamil Nadu.")


if __name__ == "__main__":
    populate_top_universities()
