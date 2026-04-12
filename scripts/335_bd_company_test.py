"""
Directive #335 — Bright Data LinkedIn Company dataset test.
RUN 1: single batch of 20 URLs.
RUN 2: 5 parallel batches of 4 URLs each.
Dataset: gd_l1vikfnt1wgvvqz95w
"""
import asyncio
import json
import os
import time
import httpx

DATASET_ID = "gd_l1vikfnt1wgvvqz95w"
BASE_URL = "https://api.brightdata.com/datasets/v3"

COMPANY_URLS = [
    "https://www.linkedin.com/company/dentalboutique",
    "https://www.linkedin.com/company/lsj",
    "https://www.linkedin.com/company/myimplantdentist",
    "https://www.linkedin.com/company/chelseadentalgroup",
    "https://www.linkedin.com/company/puredentistry",
    "https://www.linkedin.com/company/jamesonlaw",
    "https://www.linkedin.com/company/mydentistwestryde",
    "https://www.linkedin.com/company/australianmigrationlawyers",
    "https://www.linkedin.com/company/criminal-lawyers",
    "https://www.linkedin.com/company/dalyellupdental",
    "https://www.linkedin.com/company/mountlawleydental",
    "https://www.linkedin.com/company/brydens",
    "https://www.linkedin.com/company/dentistportmelbourne",
    "https://www.linkedin.com/company/criminaldefencelawyers",
    "https://www.linkedin.com/company/oasisdentalstudio",
    "https://www.linkedin.com/company/turnerfreeman",
    "https://www.linkedin.com/company/sydneycriminallawyers",
    "https://www.linkedin.com/company/australianfamilylawyers",
    "https://www.linkedin.com/company/astorlegal",
    "https://www.linkedin.com/company/hwlebsworth",
]


def get_api_key():
    key = os.environ.get("BRIGHTDATA_API_KEY")
    if not key:
        # Try loading from env file
        env_path = os.path.expanduser("~/.config/agency-os/.env")
        with open(env_path) as f:
            for line in f:
                if line.startswith("BRIGHTDATA_API_KEY="):
                    key = line.strip().split("=", 1)[1]
                    break
    if not key:
        raise ValueError("BRIGHTDATA_API_KEY not found")
    return key


def headers(api_key):
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


async def trigger_batch(client, api_key, urls, label=""):
    payload = [{"url": u} for u in urls]
    trigger_url = f"{BASE_URL}/trigger?dataset_id={DATASET_ID}&include_errors=true"
    print(f"  [{label}] POST {trigger_url} with {len(urls)} URLs")
    resp = await client.post(trigger_url, headers=headers(api_key), json=payload, timeout=30.0)
    print(f"  [{label}] trigger status={resp.status_code} body={resp.text[:200]}")
    if resp.status_code >= 400:
        raise ValueError(f"Trigger failed {resp.status_code}: {resp.text[:300]}")
    data = resp.json()
    snapshot_id = data.get("snapshot_id") or data.get("id")
    if not snapshot_id:
        raise ValueError(f"No snapshot_id in response: {data}")
    print(f"  [{label}] snapshot_id={snapshot_id}")
    return snapshot_id


async def poll_until_ready(client, api_key, snapshot_id, label="", poll_interval=30):
    """Poll every poll_interval seconds until status=ready. Returns elapsed seconds."""
    start = time.time()
    attempt = 0
    while True:
        attempt += 1
        await asyncio.sleep(poll_interval)
        elapsed = time.time() - start
        prog_url = f"{BASE_URL}/progress/{snapshot_id}"
        try:
            resp = await client.get(prog_url, headers=headers(api_key), timeout=15.0)
            status_data = resp.json()
            status = status_data.get("status", "unknown")
            print(f"  [{label}] poll#{attempt} elapsed={elapsed:.0f}s status={status} data={json.dumps(status_data)[:150]}")
            if status == "ready":
                return elapsed
            if status in ("failed", "error"):
                raise ValueError(f"Snapshot {snapshot_id} failed: {status_data}")
        except httpx.RequestError as e:
            print(f"  [{label}] poll#{attempt} network error: {e} — retrying")


async def download_snapshot(client, api_key, snapshot_id, label=""):
    dl_url = f"{BASE_URL}/snapshot/{snapshot_id}?format=json"
    print(f"  [{label}] downloading snapshot {snapshot_id}")
    resp = await client.get(dl_url, headers=headers(api_key), timeout=120.0)
    resp.raise_for_status()
    data = resp.json()
    count = len(data) if isinstance(data, list) else 1
    print(f"  [{label}] downloaded {count} records")
    return data


async def run1_single_batch(api_key):
    print("\n=== RUN 1: Single batch of 20 URLs ===")
    t0 = time.time()
    async with httpx.AsyncClient() as client:
        snapshot_id = await trigger_batch(client, api_key, COMPANY_URLS, label="run1")
        elapsed = await poll_until_ready(client, api_key, snapshot_id, label="run1")
        results = await download_snapshot(client, api_key, snapshot_id, label="run1")
    wall_time = time.time() - t0
    print(f"\n  RUN 1 wall_time={wall_time:.1f}s records={len(results) if isinstance(results, list) else 1}")
    out_path = "scripts/output/335_bd_run1_single_batch.json"
    with open(out_path, "w") as f:
        json.dump({"snapshot_id": snapshot_id, "wall_time_seconds": wall_time,
                   "records_returned": len(results) if isinstance(results, list) else 1,
                   "results": results}, f, indent=2)
    print(f"  Saved to {out_path}")
    return wall_time, results


async def run2_parallel_batches(api_key):
    print("\n=== RUN 2: 5 parallel batches of 4 URLs ===")
    batches = [COMPANY_URLS[i:i+4] for i in range(0, 20, 4)]
    t0 = time.time()
    async with httpx.AsyncClient() as client:
        # Trigger all 5 simultaneously
        trigger_tasks = [
            trigger_batch(client, api_key, batch, label=f"run2-b{i+1}")
            for i, batch in enumerate(batches)
        ]
        snapshot_ids = await asyncio.gather(*trigger_tasks)
        print(f"\n  All 5 triggered. snapshot_ids={snapshot_ids}")

        # Poll all 5 concurrently
        poll_tasks = [
            poll_until_ready(client, api_key, sid, label=f"run2-b{i+1}")
            for i, sid in enumerate(snapshot_ids)
        ]
        elapsed_times = await asyncio.gather(*poll_tasks)
        print(f"\n  All 5 ready. per-batch elapsed={[f'{e:.0f}s' for e in elapsed_times]}")

        # Download all
        dl_tasks = [
            download_snapshot(client, api_key, sid, label=f"run2-b{i+1}")
            for i, sid in enumerate(snapshot_ids)
        ]
        batch_results = await asyncio.gather(*dl_tasks)

    wall_time = time.time() - t0
    all_results = []
    for r in batch_results:
        if isinstance(r, list):
            all_results.extend(r)
        else:
            all_results.append(r)
    print(f"\n  RUN 2 wall_time={wall_time:.1f}s total_records={len(all_results)}")

    out_path = "scripts/output/335_bd_run2_parallel_batches.json"
    with open(out_path, "w") as f:
        json.dump({
            "snapshot_ids": snapshot_ids,
            "wall_time_seconds": wall_time,
            "per_batch_elapsed_seconds": elapsed_times,
            "records_returned": len(all_results),
            "results": all_results,
        }, f, indent=2)
    print(f"  Saved to {out_path}")
    return wall_time, all_results


def print_sample_records(results, n=2):
    print(f"\n=== SAMPLE RECORDS (first {n}) ===")
    sample = results[:n] if isinstance(results, list) else [results]
    for i, rec in enumerate(sample):
        print(f"\n--- Record {i+1} ---")
        print(json.dumps(rec, indent=2))


async def main():
    api_key = get_api_key()
    print(f"API key loaded (last 8 chars): ...{api_key[-8:]}")
    print(f"Dataset ID: {DATASET_ID}")
    print(f"Total URLs: {len(COMPANY_URLS)}")

    wall1, results1 = await run1_single_batch(api_key)
    wall2, results2 = await run2_parallel_batches(api_key)

    print("\n=== FINAL REPORT ===")
    print(f"RUN 1 (single batch 20):    wall_time={wall1:.1f}s  records={len(results1) if isinstance(results1, list) else 1}")
    print(f"RUN 2 (5x parallel, 4 ea):  wall_time={wall2:.1f}s  records={len(results2)}")

    # Fields available
    if results1 and isinstance(results1, list) and results1[0]:
        print(f"\nFields available in RUN 1 response:")
        print(sorted(results1[0].keys()))

    # Sample records from run1
    print_sample_records(results1, n=2)


if __name__ == "__main__":
    asyncio.run(main())
