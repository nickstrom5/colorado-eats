# Colorado restaurant inspection sources: verification (2026-10-05)

This checks the earlier research from 2026-09-27. Facts carry a source URL. "Unconfirmed" means this session could not verify the point.
I made no requests to inspections.myhealthdepartment.com, citizenportal.jeffco.us, Accela or denvergov.org/restaurantinspections.
URLs on those hosts below come only from agency pages or web-search results.
The per-county list for all 64 counties is in `county_agencies.json`.

## 1. Statewide rating rule

**The tiers are not in the rule itself.** They come from a CDPHE interpretive memo issued under the statute.

- **Rating system:** CDPHE Division of Environmental Health and Sustainability, *Interpretive Memo No. 19-09 (revised)*, "Colorado Retail Food Program Requirements for Communicating Inspection Ratings".
  - Effective date: **February 15, 2020**.
  - Signed by Jeff Lawrence, Director.
  - Implements **C.R.S. 25-4-1607.7(2)**, which says ratings must follow "a system adopted by the department", and **C.R.S. 25-4-1611.5(2)**, which covers enforcement based on how widespread violations are.
  - Primary text: a copy of the CDPHE PDF hosted by El Paso County Public Health, https://epc-assets.elpasoco.com/wp-content/uploads/sites/18/2024/01/DEHS_RetailFd_IM1909_ReqsForCommInspRatings.pdf. CDPHE's own site returned HTTP 403.
  - **Pass:** "risk index is below 50 points" (defined as 0–49).
  - **Re-inspect / Re-Inspection Required:** 50–109.
  - **Closed:** 110 or more.
  - **Points are risk points and lower is better.** Each of the 56 checklist items that is OUT of compliance adds a Low, Medium or High value (for example item 8, hands washed: 0/10/25). The points are summed.
  - **Only routine inspections and re-inspections get a rating.**
  - **Displaying ratings is optional.** The memo says the department or an LPHA "may decide to display an inspection rating". An agency that does display one must use these three ratings and the Attachment B symbols ("PASS", "RE-INSPECTION REQUIRED", "CLOSED"). It must also show at least 3 years of inspections, along with the violations and their risk level.
  - **Correction to the earlier research ("Closure at any score for an imminent health hazard"):** the memo does not say this. Its "Closed" definition mentions "significant unsanitary conditions or other imminent health hazards" but ties the rating to 110+ points. Separately, rule §8-404.11 requires operations to stop when an imminent health hazard may exist. Whether that stop is shown as a "Closed" rating at any score is **unconfirmed**.
  - **Correction on the start date:** Larimer says the system took effect **1/1/2020**. The revised memo is dated **2/15/2020**, and the original memo's date is unconfirmed.
- **Rule:** *Colorado Retail Food Establishment Regulations*, **6 CCR 1010-2** (not 5 CCR 1002).
  - Adopted by the Board of Health on Jan 17, 2024, and effective **March 16, 2024**. It incorporates the 2022 FDA Food Code.
  - Authority: C.R.S. 25-1-108(1)(c)(I), 25-4-1603, 25-4-1604(1)(b)(I), 25-5-420.
  - Chapter 8 (§8-401 to 8-406) covers inspection frequency, reports and imminent health hazards. It has **no** Pass, Re-Inspection or Closure tiers.
  - §2.3(C) says the department also uses "department policy guidance", which is the vehicle for the memo above.
  - §8-403.50 makes inspection reports public documents.
  - CDPHE distribution copy: https://epc-assets.elpasoco.com/wp-content/uploads/sites/18/2024/03/6-CCR-1010-2-Retail-Food-Rules-Regulations_Distribution-Copy_031624.pdf
  - The official Secretary of State CCR URL is unconfirmed.
- **Larimer's page:** describes Pass 0–49, Re-Inspection Required 50–109, Closure 110+ and Not Rated. It cites "CRS 25-4-1607.7" and says lower is better. https://www.larimer.gov/health/environmental-health/food-safety-program/restaurant-grocery-store-inspections
- **Douglas County's page:** cites the same statute as saying a uniform system "must not summarize the results of the inspection with a letter, number, or symbol grading system." https://www.douglasco.gov/health-department/inspections-retail-food-establishments/
- **Statute text:** I did not fetch C.R.S. 25-4-1607.7, so its primary URL is unconfirmed.

## 2. Which agency inspects which county

**Source for local public health agencies (LPHAs):** CDPHE's 2026 layer of LPHA jurisdictions.
- Feature service: https://www.cohealthmaps.dphe.state.co.us/arcgis/rest/services/OPEN_DATA/cdphe_colorado_local_public_health_agencies/MapServer/1
- Catalog entry: https://data.colorado.gov/d/i97v-ek6c
- It covers all 64 counties.
- Multi-county agencies:
  - Northeast Colorado Health Dept: Logan, Morgan, Phillips, Sedgwick, Washington and Yuma.
  - Las Animas-Huerfano District: Las Animas and Huerfano.
  - Otero County Health Dept: Otero and Crowley.
  - Silver Thread Public Health District: Hinsdale and Mineral.
  - Montrose County Environmental Health: lists Montrose and Ouray.

**Counties where CDPHE inspects directly (Division of Environmental Health and Sustainability):**
- CDPHE's pages returned 403, so this list comes from web-search summaries of cdphe.colorado.gov pages. Those summaries disagree:
  - From /dehs/rf/inspections: Clear Creek, Jackson, Moffat, Ouray, Park, Pitkin.
  - From another CDPHE retail-food page: Clear Creek, Dolores, Gilpin, Moffat, Ouray, Park, Pitkin (except the City of Aspen), Rio Blanco, San Juan.
  - From the foodborne-illness contact page: Clear Creek, Dolores, Jackson, Moffat, Ouray, Park, Pitkin.
- **Named in all three:** Clear Creek, Moffat, Ouray, Park, Pitkin.
- **Named in two:** Jackson, Dolores.
- **Named in one:** Gilpin, Rio Blanco, San Juan.
- **Park is confirmed** by the county's own page, which says retail food licenses come from CDPHE's Food Safety Division: https://www.parkcountyco.gov/203/Food-Establishments

**Former Tri-County Health counties:** the successors are Adams County Health Department, Arapahoe County Public Health and Douglas County Health Department.
- All three appear in CDPHE's 2026 LPHA layer, and each links its own portal.
- The TCHD dataset 869n-zj3f covers inspections from 2019-01-02 to **2022-10-31** (7,886 rows; rows last updated 2022-12-27). This confirms the earlier research.
- The exact dissolution date was not separately confirmed this session.

**San Juan Basin Public Health** (La Plata and Archuleta) dissolved on 2023-12-31, according to search summaries of Durango Herald and La Plata County pages. La Plata County Public Health now runs the Food Safety Program.

## 3. Bulk data

**No new current bulk source was found. Boulder is still the only one.**

- **data.colorado.gov:** I searched the catalog limited to that domain for "inspection", "restaurant", "food", "retail food", "health department" and "environmental health". The only inspection datasets are:
  - Boulder `6ytb-f2cq` (2025–present, BOCO). Rows updated 2026-08-06; latest inspection 2026-06-18, so about 3.5 months behind today. 2,285 rows. The `result` column holds Pass (1,734), Reinspection Required (501) and Closure (50).
  - Boulder `tuvj-xz3m` (2013–2025-08-29).
  - Boulder map view `8f7p-zcww`.
  - TCHD `869n-zj3f` (2019–2022-10-31) and `cx7q-izrb` (2018). Both are historic.
  - All are labeled Public Domain. Boulder's ArcGIS item c9d2014e937245a494df381ec0343716 points to tuvj-xz3m with a CC BY 4.0 note.
- **ArcGIS Online and ArcGIS Hub:** I searched for "restaurant/food inspection" combined with the 20 county names.
  - No Colorado inspection layers turned up.
  - Two false positives to avoid:
    - "Summit County Food Inspections" feature services (current to 2026-10-01) are **Summit County, Utah** (Park City, Kamas, Wanship).
    - "Restaurant Ratings" / douglascountyfoodinspections.com and "Restaurant Inspections I2G" are **Douglas County, Nebraska** (Omaha).
  - Denver has "Food Retail Locations" and "Food Stores in Denver" (hysf-mrke). These list stores, not inspections.
- **Denver, Jefferson, El Paso, Larimer, Weld, Pueblo, Mesa, Adams, Arapahoe, Douglas, Broomfield and Eagle:** search-one-record portals only. Garfield and La Plata have no online lookup on their pages. Summit, Pitkin, Routt, Gunnison and San Miguel are unconfirmed or unknown.

## 4. Per-agency table

Data form: bulk / search (look up one record) / unknown. "Shows result?" means the public lookup shows Pass, Re-Inspection Required or Closure.

| County | Inspecting agency | Data | Public lookup URL | Shows result? | Notes | Sources |
|---|---|---|---|---|---|---|
| Boulder | Boulder County Public Health | **bulk** | https://bouldercounty.gov/families/food/restaurant-inspection-data/ (search tool URL unconfirmed) | Yes, in the dataset | 6ytb-f2cq current to 2026-06-18; tuvj-xz3m archive | https://data.colorado.gov/d/6ytb-f2cq · https://data.colorado.gov/d/tuvj-xz3m |
| Denver | DDPHE | search | https://denvergov.org/restaurantinspections (before 2024-09-06); new platform URL unconfirmed (earlier research: Accela) | Unconfirmed; tool shows violations and enforcement | No inspection dataset on any portal | search result for denvergov.org/restaurantinspections |
| Jefferson | Jefferson County Public Health | search | https://citizenportal.jeffco.us/citizenportal/app/landing | Unconfirmed | | https://www.jeffco.us/2408/Food-Safety |
| El Paso | El Paso County Public Health | search | https://inspections.myhealthdepartment.com/epcph | Unconfirmed | Slug from search results | search results |
| Larimer | Larimer County Health Dept | search | https://inspections.myhealthdepartment.com/larimer-county-health | **Yes** (plus Not Rated) | | Larimer page (above) |
| Weld | Weld County DPHE | search | https://inspections.myhealthdepartment.com/weldcounty | Yes, per a search snippet ("42 (Pass)") | | search results |
| Pueblo | Pueblo DPHE | search | https://inspections.myhealthdepartment.com/pueblo (confirmed) | Unconfirmed | | https://county.pueblo.org/public-health-department/food-safety-licensing |
| Mesa | Mesa County Public Health | search | https://inspections.myhealthdepartment.com/mesacountyco | Unconfirmed | | search results |
| Adams | Adams County Health Dept | search | https://inspections.myhealthdepartment.com/adcogoveh | Unconfirmed | TCHD bulk is historic only | https://adamscountyhealthdepartment.org/inspection-look-up |
| Arapahoe | Arapahoe County Public Health | search | https://inspections.myhealthdepartment.com/acph | Unconfirmed | TCHD bulk is historic only | arapahoeco.gov Inspection Look Up page |
| Douglas | Douglas County Health Dept | search | https://inspections.myhealthdepartment.com/dchd | Unconfirmed; page stresses "no letter/number/symbol" summary | Other records by open-records request | douglasco.gov page (above) |
| Broomfield | Broomfield Public Health & Environment | search | https://inspections.myhealthdepartment.com/broomfield | Unconfirmed | New slug (earlier research had no entry) | search results |
| Eagle | Eagle County Public Health & Environment | search | https://inspections.myhealthdepartment.com/colorado (shared portal) | Unconfirmed | Earlier research said unknown | https://www.eaglecounty.us/departments___services/environmental_health/food___restaurants.php |
| Summit | Summit County Public Health | search (weak evidence) | https://inspections.myhealthdepartment.com/colorado | Unconfirmed | Only evidence is a /colorado report titled with Summit's agency | search result |
| Pitkin | CDPHE (except City of Aspen, per one summary) | search | /colorado | Unconfirmed | | CDPHE page summaries |
| Routt, Gunnison, San Miguel | Their LPHAs (per CDPHE layer) | unknown | — | — | Out of search budget | CDPHE LPHA layer |
| Garfield | Garfield County Public Health (Consumer Protection) | unknown | none listed | — | Page mentions no online lookup | http://www.garfieldcountyco.gov/environmental-health/food-safety/ |
| La Plata | La Plata County Public Health (SJBPH successor) | unknown | none found | — | | https://www.lpcgov.org/departments/public_health_2/environmental_health/food_safety/index.php |
| Grand | Grand County Public Health | search | https://www.co.grand.co.us/1493/Retail-Food-Inspection-Reports | Unconfirmed | | search result |
| Logan, Morgan, Phillips, Sedgwick, Washington, Yuma | Northeast Colorado Health Dept | search | https://inspections.myhealthdepartment.com/northeast-colorado | Unconfirmed | | https://nchd.org/restaurant-inspections/ |
| Clear Creek, Moffat, Ouray, Park | CDPHE | search | https://inspections.myhealthdepartment.com/colorado | Unconfirmed | | CDPHE summaries; Park County page |

About the `/colorado` portal: it appears to be a shared statewide instance that CDPHE and some local agencies use (Eagle, and Summit per a search-result title). Each record should show the inspecting agency's name.

## 5. Parcel data terms

- **Colorado Public Parcels** (OIT GIS; ArcGIS item 55234e04218f47c9868900e439fcbd5a; data last published June 2026; https://geodata.colorado.gov/datasets/colorado-public-parcels):
  - The license field says: "**Resale of this data is strictly forbidden. Commercial use of the data is allowed so long as the State of Colorado is attributed**".
  - It also gives an attribution line to use: "State of Colorado Public addresses were accessed on [DATE] from https://gis.colorado.gov/public/rest/services/Address_and_Parcel". The wording says "addresses" because it was copied from the address dataset.
  - It disclaims all warranties.
  - Free redistribution with attribution is not prohibited. Selling the data is.
  - The file-geodatabase item (3245c94414124882b331e35c14bb23a4) has only the disclaimer.
- **Denver Parcels:**
  - The Socrata entry (https://data.colorado.gov/d/tsdg-z9uy) is labeled **Public Domain**.
  - Denver's ArcGIS item (7c53bd0894134e80ae1e478c0789bf49) carries "USE CONSTRAINTS": an as-is, no-warranty disclaimer, an agreement by the user to indemnify Denver for "use, reproduction or dissemination", and "NOT FOR ENGINEERING PURPOSES".
  - According to the search summary, Denver's open data catalog is CC BY 3.0. I did not fetch it.

## Corrections to the 2026-09-27 research

1. The tiers come from CDPHE Interpretive Memo 19-09 (revised, effective 2/15/2020) under C.R.S. 25-4-1607.7(2) and 25-4-1611.5(2). They are not in 6 CCR 1010-2.
2. The current rule is 6 CCR 1010-2, effective 3/16/2024.
3. "Closure for an imminent health hazard at any score" is not in the memo.
4. Displaying ratings is optional for agencies.
5. Eagle (/colorado) and Broomfield (/broomfield) do have search portals. Northeast Colorado Health Dept (6 counties) and Grand County also publish lookups.
6. The CDPHE-direct county list is inconsistent across CDPHE's own pages.

## Downloads used (2026-10-05)
- `ier5-5ms2` Liquor Licenses in Colorado (CDOR LED, public domain): 20,281 active rows, rows updated 2026-09-24; no coordinates (geocoded:
  Overture address points by number + street + zip/town, then the US Census batch geocoder with a town/zip agreement check; 606 unplaced).
- `pwjb-9dd5` recently expired/surrendered liquor licenses: closure hint only (renewals can be pending locally); not used to remove places.
- `6ytb-f2cq` Boulder County inspections 2025–present: 2,285 violation rows, 633 inspections at 559 businesses, inspections 2025-09-03 → 2026-07-21,
  published 2026-08-06 (metadata says "Static"/"Never": refresh is irregular). `tuvj-xz3m` archive 2013 → 2025-08-29 (2024+ used for matching only).
- Denver Active Business Licenses (ArcGIS item 5793f5349ad448b3b916a555b8f77ddf, FeatureServer layer 42, daily): Retail Food 2,583, Combined 2,035,
  Liquor 123, Commissary 211. Coordinates in Colorado Central State Plane (EPSG:2232) for about half.
- Overture Maps 2026-09-23.1: 28,758 eating/drinking listings in Colorado; 2.56M address points (none in Larimer, Summit, Chaffee and some others).

## Calibration (data/co/calibration*.json)
Share of map listings that matched an official record (app grouping, no Google):

| Listing | Denver (full food licenses) | Boulder County (inspected facilities) | App |
|---|---|---|---|
| Meta, confidence ≥ 0.95 | 76% | 71% | kept |
| Meta 0.90–0.95 with a website | 35% | 52% | kept |
| Meta 0.90–0.95, social only | 20% | 19% | dropped |
| Chain store feeds | 46% | 35% | kept |
| BrightQuery ≥ 0.95 | 30% | 21% | dropped |
| Other single sources | 14% | 13% | dropped |

Coverage the other way: the open map listings held 54% of Denver's licensed food businesses and 65% of Boulder County's inspected ones; the
rest were added from the records. Statewide, the open listings held 60–78% of each county's on-premises liquor licensees.
