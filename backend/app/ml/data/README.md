# Township One Complaints Dataset (v1.0)

## Overview

The `complaints_v1.csv` dataset contains 360 labelled complaints designed for training and evaluating residential complaint triage models in large-scale housing societies. The dataset addresses multilingual and code-mixed citizen communications common across Indian metropolitan townships (notably Maharashtra and Delhi-NCR regions), incorporating English, Hindi, and Marathi.

## Dataset Structure

The dataset contains the following columns:

- `text` (string): The raw resident complaint text.
- `category` (string): One of 8 functional maintenance domains:
  - `PLUMBING`: Pipes, fixtures, taps, flush cisterns, drains, and internal sewage lines.
  - `ELECTRICAL`: Power supply, switches, wiring, corridor lighting, geysers, and circuit breakers.
  - `LIFT`: Passenger and service elevator cabs, doors, motors, call buttons, and indicator panels.
  - `CLEANLINESS`: Housekeeping, garbage disposal, waste chutes, pest control, and common corridors.
  - `WATER_SUPPLY`: Municipal and tanker water feeds, rooftop tanks, pumps, filtration, and water quality.
  - `SECURITY`: Main gates, security personnel, visitor validation, perimeter CCTV, boom barriers, and intercoms.
  - `COMMON_AREA`: Clubhouses, gymnasiums, sports facilities, children play parks, swimming pools, and internal roads.
  - `GENERAL`: Administrative inquiries, billing and receipts, parking allocations, pet conduct, and late-night noise.
- `urgency` (string): Priority level reflecting safety hazard, health risk, and operational SLA:
  - `CRITICAL`: Life safety risk, immediate structural or fire hazard, trapped individuals, complete utility failure, or severe active flooding. Target resolution / first response SLA: < 1 hour.
  - `HIGH`: Severe inconvenience, health risk, major water leak, single-floor power outage, or security breach without direct physical violence. Target SLA: < 4 hours.
  - `MEDIUM`: Moderate functional impediment, noisy equipment, partial component defect, slow drainage, or low water pressure. Target SLA: < 24 hours.
  - `LOW`: Cosmetic defects, routine queries, minor informational delays, light bulb replacements, or administrative approvals. Target SLA: < 48 hours.
- `language` (string): Dominant language code:
  - `en`: English.
  - `hi`: Hindi (both Devanagari script and Latin romanized Hinglish, including code-mixed phrases).
  - `mr`: Marathi (both Devanagari script and Latin romanized Marathi, including code-mixed phrases).
- `incident_family` (string): Fine-grained cluster tag (40 families total, 5 per category) defining the underlying root issue. This allows grouped evaluation so testing measures generalizability to new incident formulations rather than memorizing surface keywords.

## Balanced Distributions

- Total entries: 360
- Category distribution: Exactly 45 entries per category (8 categories).
- Language distribution: Exactly 120 entries per language (English: 120, Hindi: 120, Marathi: 120).
- Urgency distribution:
  - CRITICAL: 90
  - HIGH: 89
  - MEDIUM: 91
  - LOW: 90

## Incident Family Taxonomy

1. **PLUMBING**: `pipe_burst_leakage`, `tap_damage`, `drainage_blockage`, `flush_cistern_fault`, `sewage_backflow`.
2. **ELECTRICAL**: `sparking_switchboard`, `geyser_short_circuit`, `power_outage_partial`, `corridor_light_fused`, `circuit_breaker_tripping`.
3. **LIFT**: `lift_stuck_with_passengers`, `lift_door_jammed`, `lift_jerking_noise`, `lift_button_unresponsive`, `lift_display_error`.
4. **CLEANLINESS**: `garbage_pile_corridor`, `cockroach_pest_infestation`, `stray_dog_poop`, `staircase_spill_stain`, `duct_waste_dumping`.
5. **WATER_SUPPLY**: `no_water_tower`, `low_water_pressure`, `dirty_muddy_water`, `overhead_tank_overflow`, `hot_water_line_empty`.
6. **SECURITY**: `unauthorized_visitor_entry`, `guard_sleeping_gate`, `cctv_camera_offline`, `intercom_system_down`, `boom_barrier_damaged`.
7. **COMMON_AREA**: `children_park_swing_broken`, `swimming_pool_dirty`, `gym_equipment_broken`, `clubhouse_ac_leaking`, `badminton_court_net_torn`.
8. **GENERAL**: `late_night_loud_music`, `visitor_parking_encroachment`, `maintenance_receipt_delay`, `pet_policy_violation`, `renovation_noc_request`.

## Labeling Rationale and Methodology

1. **Multilingual and Script Variety**: Real estate and township communities exhibit high linguistic variety. Residents mix English technical terms (e.g., 'MCB', 'flush', 'lift', 'swimming pool') into vernacular Hindi and Marathi sentences. The dataset pairs authentic native Devanagari expressions with everyday transliterated text.
2. **SLA and Severity Grounding**: Urgency labels are calibrated against township operational reality. For example, a resident trapped in an elevator (`LIFT` / `CRITICAL`) or an active sparking panel (`ELECTRICAL` / `CRITICAL`) requires immediate automated dispatch, whereas an unlit decorative foyer bulb (`ELECTRICAL` / `LOW`) does not disrupt essential operations.
3. **Incident Family Grouping**: Grouping evaluations by `incident_family` guarantees that the train and evaluation splits evaluate true semantic generalization across distinct incident variants rather than memorizing family-specific terminology.
