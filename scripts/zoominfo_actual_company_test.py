#!/usr/bin/env python3
"""
DIRECTIVE #146 PART A - ZoomInfo AU Coverage Test (Part 2)
Test with actual ZoomInfo company URLs.
"""

import asyncio
import json
import httpx

ZOOMINFO_DATASET_ID = "gd_m0ci4a4ivx3j5l6nx"
API_KEY = "2bab0747-ede2-4437-9b6f-6a77e8f0ca3e"

# Known AU agency ZoomInfo URLs (from web search)
TEST_COMPANY_URLS = [
    "https://www.zoominfo.com/c/clemenger-bbdo/11338759",
    "https://www.zoominfo.com/c/clemenger-group-ltd/1155585405",
    # Let's also try some variations to see how discovery works
    "https://www.zoominfo.com/c/ogilvy/47882",  # Global Ogilvy
    "https://www.zoominfo.com/c/ddb-worldwide/55648",  # DDB Global
    "https://www.zoominfo.com/c/tbwa-worldwide/166093",  # TBWA
]

async def test_specific_companies():
    """Test scraping specific ZoomInfo company pages."""
    print("=" * 80)
    print("ZOOMINFO COMPANY SCRAPE TEST - AUSTRALIAN AGENCIES")
    print("=" * 80)
    
    inputs = [{"url": url} for url in TEST_COMPANY_URLS]
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    trigger_url = f"https://api.brightdata.com/datasets/v3/trigger?dataset_id={ZOOMINFO_DATASET_ID}&include_errors=true"
    
    async with httpx.AsyncClient(timeout=120.0, verify=False) as client:
        print(f"\n[1] Triggering ZoomInfo scrape for {len(inputs)} companies...")
        
        response = await client.post(trigger_url, headers=headers, json=inputs)
        
        print(f"    Status: {response.status_code}")
        print(f"    Response: {response.text[:500]}")
        
        if response.status_code == 200:
            data = response.json()
            snapshot_id = data.get("snapshot_id")
            print(f"\n[2] Snapshot: {snapshot_id}")
            
            # Poll for completion
            for i in range(60):
                await asyncio.sleep(5)
                progress = await client.get(
                    f"https://api.brightdata.com/datasets/v3/progress/{snapshot_id}",
                    headers=headers
                )
                status_data = progress.json()
                status = status_data.get("status")
                records = status_data.get("records", 0)
                print(f"    Poll {i+1}: Status={status}, Records={records}")
                
                if status == "ready":
                    print("\n[3] Downloading results...")
                    results = await client.get(
                        f"https://api.brightdata.com/datasets/v3/snapshot/{snapshot_id}?format=json",
                        headers=headers
                    )
                    
                    if results.status_code == 200:
                        records = results.json()
                        print(f"    Retrieved {len(records)} records\n")
                        
                        # Save raw results
                        with open("/home/elliotbot/clawd-build-2/scripts/zoominfo_company_results.json", "w") as f:
                            json.dump(records, f, indent=2)
                        
                        # Analyze each record
                        print("=" * 80)
                        print("FIELD ANALYSIS")
                        print("=" * 80)
                        
                        for i, record in enumerate(records):
                            if "error" in record:
                                print(f"\n[Record {i+1}] ERROR: {record.get('error')}")
                                continue
                                
                            print(f"\n[Record {i+1}] Company: {record.get('name', 'N/A')}")
                            print("-" * 60)
                            
                            # Check key fields
                            fields_to_check = [
                                ('name', 'Company Name'),
                                ('description', 'Description'),
                                ('revenue', 'Revenue'),
                                ('revenue_range', 'Revenue Range'),
                                ('employees', 'Employee Count'),
                                ('employee_count', 'Employee Count Alt'),
                                ('num_employees', 'Num Employees'),
                                ('founded', 'Founded Year'),
                                ('industry', 'Industry'),
                                ('headquarters', 'Headquarters'),
                                ('website', 'Website'),
                                ('phone', 'Phone'),
                                ('address', 'Address'),
                                ('city', 'City'),
                                ('state', 'State'),
                                ('country', 'Country'),
                                ('linkedin_url', 'LinkedIn URL'),
                                ('facebook_url', 'Facebook URL'),
                                ('twitter_url', 'Twitter URL'),
                                ('stock_symbol', 'Stock Symbol'),
                                ('funding', 'Funding'),
                                ('technologies', 'Technologies'),
                                ('competitors', 'Competitors'),
                                ('similar_companies', 'Similar Companies'),
                                ('last_updated', 'Last Updated'),
                                ('timestamp', 'Timestamp'),
                            ]
                            
                            for key, label in fields_to_check:
                                value = record.get(key)
                                if value is not None:
                                    # Truncate long values
                                    str_val = str(value)
                                    if len(str_val) > 100:
                                        str_val = str_val[:100] + "..."
                                    print(f"  {label}: {str_val}")
                            
                            # Print all keys present
                            print(f"\n  ALL KEYS: {list(record.keys())}")
                        
                        return records
                        
                elif status == "failed":
                    print(f"\n    JOB FAILED: {status_data}")
                    return None
    
    return None

if __name__ == "__main__":
    asyncio.run(test_specific_companies())
