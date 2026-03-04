#!/usr/bin/env python3
"""
load_business_universe.py

Downloads ABN bulk extract from data.gov.au and loads qualified businesses
into the business_universe table.

LAW VII compliant: Uses streaming XML parser (lxml.etree.iterparse)
to avoid memory blowout on ~2GB XML files.

Usage:
    python scripts/load_business_universe.py
    python scripts/load_business_universe.py --dry-run
    python scripts/load_business_universe.py --skip-download
"""

import argparse
import asyncio
import logging
import os
import sys
import time
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import AsyncGenerator, Iterator

import asyncpg
import httpx
import sentry_sdk
from lxml import etree
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Initialize Sentry
sentry_sdk.init(dsn=os.getenv("SENTRY_DSN"), traces_sample_rate=0.1)

# Constants
EXTRACT_DIR = Path("/tmp/abn_extract")
ZIP_URLS = [
    "https://data.gov.au/data/dataset/5bd7fcab-e315-42cb-8daf-50b7efc2027e/resource/0ae4d427-6fa8-4d40-8e76-c6909b5a071b/download/public_split_1_10.zip",
    "https://data.gov.au/data/dataset/5bd7fcab-e315-42cb-8daf-50b7efc2027e/resource/635fcb95-7864-4509-9fa7-a62a6e32b62d/download/public_split_11_20.zip",
]

# Entity type codes to EXCLUDE
EXCLUDE_INDIVIDUAL = {"IND"}
EXCLUDE_GOVERNMENT = {"GVT", "LGV", "STG", "CGV", "GCO"}
EXCLUDE_SUPER = {"SUP", "ADF"}
EXCLUDE_CHARITY_NFP = {"DIT", "NPF", "NPB", "NPE"}

BATCH_SIZE = 1000
PROGRESS_LOG_INTERVAL = 100_000


@dataclass
class FilterStats:
    """Track how many records were filtered at each stage."""
    inactive: int = 0
    individuals: int = 0
    trusts: int = 0
    government: int = 0
    superannuation: int = 0
    charities_nfp: int = 0


@dataclass
class LoadStats:
    """Track overall load statistics."""
    total_processed: int = 0
    total_inserted: int = 0
    total_updated: int = 0
    total_filtered: int = 0
    filter_breakdown: FilterStats = field(default_factory=FilterStats)
    start_time: float = field(default_factory=time.time)

    @property
    def qualified_count(self) -> int:
        return self.total_processed - self.total_filtered

    @property
    def elapsed_seconds(self) -> float:
        return time.time() - self.start_time

    def log_final(self):
        """Log final statistics."""
        logger.info("=" * 60)
        logger.info("LOAD COMPLETE")
        logger.info("=" * 60)
        logger.info(f"total_records_processed: {self.total_processed:,}")
        logger.info(f"total_inserted: {self.total_inserted:,}")
        logger.info(f"total_updated: {self.total_updated:,}")
        logger.info(f"total_filtered_out: {self.total_filtered:,}")
        logger.info("filter_breakdown:")
        logger.info(f"  - inactive: {self.filter_breakdown.inactive:,}")
        logger.info(f"  - individuals/sole_traders: {self.filter_breakdown.individuals:,}")
        logger.info(f"  - trusts: {self.filter_breakdown.trusts:,}")
        logger.info(f"  - government: {self.filter_breakdown.government:,}")
        logger.info(f"  - superannuation: {self.filter_breakdown.superannuation:,}")
        logger.info(f"  - charities_nfp: {self.filter_breakdown.charities_nfp:,}")
        logger.info(f"final_qualified_count: {self.qualified_count:,}")
        logger.info(f"time_elapsed: {self.elapsed_seconds:.2f}s ({self.elapsed_seconds/60:.1f}m)")
        logger.info("=" * 60)


@dataclass
class BusinessRecord:
    """Represents a single business record from ABR."""
    abn: str
    acn: str | None
    legal_name: str
    trading_name: str | None
    entity_type: str
    entity_type_code: str
    state: str | None
    postcode: str | None
    gst_registered: bool
    status: str
    abn_status_code: str
    registration_date: str | None


async def download_file(url: str, dest: Path) -> None:
    """Download a file with progress bar."""
    logger.info(f"Downloading: {url}")
    
    async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=30.0)) as client:
        async with client.stream("GET", url, follow_redirects=True) as response:
            response.raise_for_status()
            total = int(response.headers.get("content-length", 0))
            
            with open(dest, "wb") as f:
                with tqdm(
                    total=total,
                    unit="B",
                    unit_scale=True,
                    desc=dest.name,
                    ncols=80,
                ) as pbar:
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        f.write(chunk)
                        pbar.update(len(chunk))
    
    logger.info(f"Downloaded: {dest} ({dest.stat().st_size / 1024 / 1024:.1f} MB)")


async def download_and_extract(skip_download: bool = False) -> list[Path]:
    """Download ZIP files and extract XML contents."""
    EXTRACT_DIR.mkdir(parents=True, exist_ok=True)
    
    xml_files = []
    
    for i, url in enumerate(ZIP_URLS, 1):
        zip_path = EXTRACT_DIR / f"abn_split_{i}.zip"
        
        if skip_download and zip_path.exists():
            logger.info(f"Skipping download (file exists): {zip_path}")
        else:
            await download_file(url, zip_path)
        
        # Extract XML files
        logger.info(f"Extracting: {zip_path}")
        with zipfile.ZipFile(zip_path, "r") as zf:
            for name in zf.namelist():
                if name.endswith(".xml"):
                    zf.extract(name, EXTRACT_DIR)
                    xml_files.append(EXTRACT_DIR / name)
                    logger.info(f"  Extracted: {name}")
    
    return sorted(xml_files)


def parse_abn_xml_streaming(xml_path: Path, stats: LoadStats) -> Iterator[BusinessRecord]:
    """
    Parse ABN XML file using streaming parser to avoid memory issues.
    LAW VII compliant: Uses iterparse, clears elements after processing.
    """
    logger.info(f"Parsing XML (streaming): {xml_path}")
    
    # ABR XML structure: <ABR> elements contain business records
    context = etree.iterparse(
        str(xml_path),
        events=("end",),
        tag="ABR",
    )
    
    for event, elem in context:
        stats.total_processed += 1
        
        # Extract fields
        abn_elem = elem.find(".//ABN")
        if abn_elem is None:
            elem.clear()
            continue
        
        abn = abn_elem.text
        if not abn:
            elem.clear()
            continue
        
        # Get entity status
        status_elem = elem.find(".//EntityStatus/EntityStatusCode")
        status_code = status_elem.text if status_elem is not None else ""
        
        # FILTER 1: Inactive
        if status_code != "ACT":
            stats.filter_breakdown.inactive += 1
            stats.total_filtered += 1
            elem.clear()
            continue
        
        # Get entity type
        entity_type_elem = elem.find(".//EntityType/EntityTypeCode")
        entity_type_code = entity_type_elem.text if entity_type_elem is not None else ""
        
        entity_type_name_elem = elem.find(".//EntityType/EntityTypeInd")
        if entity_type_name_elem is None:
            entity_type_name_elem = elem.find(".//EntityType/EntityDescription")
        entity_type_name = entity_type_name_elem.text if entity_type_name_elem is not None else ""
        
        # FILTER 2: Individuals/sole traders
        if entity_type_code in EXCLUDE_INDIVIDUAL:
            stats.filter_breakdown.individuals += 1
            stats.total_filtered += 1
            elem.clear()
            continue
        
        # FILTER 3: Trusts
        if "TRU" in entity_type_code or "Trust" in (entity_type_name or ""):
            stats.filter_breakdown.trusts += 1
            stats.total_filtered += 1
            elem.clear()
            continue
        
        # FILTER 4: Government entities
        if entity_type_code in EXCLUDE_GOVERNMENT:
            stats.filter_breakdown.government += 1
            stats.total_filtered += 1
            elem.clear()
            continue
        
        # FILTER 5: Superannuation funds
        if entity_type_code in EXCLUDE_SUPER:
            stats.filter_breakdown.superannuation += 1
            stats.total_filtered += 1
            elem.clear()
            continue
        
        # FILTER 6: Charities/NFP
        if entity_type_code in EXCLUDE_CHARITY_NFP:
            stats.filter_breakdown.charities_nfp += 1
            stats.total_filtered += 1
            elem.clear()
            continue
        
        # Extract remaining fields for qualified records
        acn_elem = elem.find(".//ASICNumber")
        acn = acn_elem.text if acn_elem is not None else None
        
        # Legal name - try multiple paths
        legal_name = None
        for path in [".//MainEntity/NonIndividualName/NonIndividualNameText",
                     ".//LegalEntity/IndividualName/GivenName",
                     ".//MainEntity/OrganisationName"]:
            name_elem = elem.find(path)
            if name_elem is not None and name_elem.text:
                legal_name = name_elem.text
                break
        
        if not legal_name:
            # Try concatenating individual name parts
            given = elem.find(".//LegalEntity/IndividualName/GivenName")
            family = elem.find(".//LegalEntity/IndividualName/FamilyName")
            if given is not None or family is not None:
                parts = []
                if given is not None and given.text:
                    parts.append(given.text)
                if family is not None and family.text:
                    parts.append(family.text)
                legal_name = " ".join(parts)
        
        if not legal_name:
            legal_name = f"ABN {abn}"  # Fallback
        
        # Trading name (business name)
        trading_name = None
        bn_elem = elem.find(".//BusinessName/OrganisationName")
        if bn_elem is not None:
            trading_name = bn_elem.text
        
        # Address info
        state = None
        postcode = None
        addr_elem = elem.find(".//MainBusinessPhysicalAddress/StateCode")
        if addr_elem is not None:
            state = addr_elem.text
        pc_elem = elem.find(".//MainBusinessPhysicalAddress/Postcode")
        if pc_elem is not None:
            postcode = pc_elem.text
        
        # GST registration
        gst_elem = elem.find(".//GoodsAndServicesTax/GSTStatus")
        gst_registered = gst_elem is not None and gst_elem.text == "Registered"
        
        # Registration date
        reg_date_elem = elem.find(".//ABN/ReplacedFrom") or elem.find(".//EntityStatus/EffectiveFrom")
        reg_date = reg_date_elem.text if reg_date_elem is not None else None
        
        # Clean up to free memory
        elem.clear()
        
        yield BusinessRecord(
            abn=abn,
            acn=acn,
            legal_name=legal_name,
            trading_name=trading_name,
            entity_type=entity_type_name or entity_type_code,
            entity_type_code=entity_type_code,
            state=state,
            postcode=postcode,
            gst_registered=gst_registered,
            status="active",
            abn_status_code=status_code,
            registration_date=reg_date,
        )
        
        # Progress logging
        if stats.total_processed % PROGRESS_LOG_INTERVAL == 0:
            qualified = stats.total_processed - stats.total_filtered
            logger.info(
                f"Processed {stats.total_processed:,} records, "
                f"{qualified:,} qualified, "
                f"{stats.total_filtered:,} filtered out"
            )


async def upsert_batch(
    pool: asyncpg.Pool,
    records: list[BusinessRecord],
    stats: LoadStats,
    dry_run: bool = False,
) -> None:
    """Upsert a batch of records into business_universe."""
    if dry_run:
        stats.total_inserted += len(records)
        return
    
    async with pool.acquire() as conn:
        # Prepare data for batch insert
        values = [
            (
                r.abn,
                r.acn,
                r.legal_name,
                r.trading_name,
                r.entity_type,
                r.entity_type_code,
                r.state,
                r.postcode,
                r.gst_registered,
                r.status,
                r.abn_status_code,
                r.registration_date,
            )
            for r in records
        ]
        
        # Use executemany with UPSERT
        result = await conn.executemany(
            """
            INSERT INTO business_universe (
                abn, acn, legal_name, trading_name, entity_type, entity_type_code,
                state, postcode, gst_registered, status, abn_status_code, registration_date
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12::date)
            ON CONFLICT (abn) DO UPDATE SET
                legal_name = EXCLUDED.legal_name,
                trading_name = EXCLUDED.trading_name,
                entity_type = EXCLUDED.entity_type,
                entity_type_code = EXCLUDED.entity_type_code,
                state = EXCLUDED.state,
                postcode = EXCLUDED.postcode,
                gst_registered = EXCLUDED.gst_registered,
                status = EXCLUDED.status,
                abn_status_code = EXCLUDED.abn_status_code,
                last_abr_check = now(),
                updated_at = now()
            """,
            values,
        )
        
        # Note: executemany doesn't return affected row counts easily
        # For accurate insert/update tracking, would need individual queries
        # For now, approximate by counting all as "processed"
        stats.total_inserted += len(records)


async def process_xml_files(
    xml_files: list[Path],
    pool: asyncpg.Pool | None,
    stats: LoadStats,
    dry_run: bool = False,
) -> None:
    """Process all XML files and load into database."""
    batch: list[BusinessRecord] = []
    
    for xml_path in xml_files:
        logger.info(f"Processing: {xml_path}")
        
        for record in parse_abn_xml_streaming(xml_path, stats):
            batch.append(record)
            
            if len(batch) >= BATCH_SIZE:
                if pool:
                    await upsert_batch(pool, batch, stats, dry_run)
                else:
                    stats.total_inserted += len(batch)
                batch = []
    
    # Final batch
    if batch:
        if pool:
            await upsert_batch(pool, batch, stats, dry_run)
        else:
            stats.total_inserted += len(batch)


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Load ABN bulk extract into business_universe table"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and filter without writing to database",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Skip download if files already exist in /tmp/abn_extract/",
    )
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("ABN BULK EXTRACT LOADER")
    logger.info(f"dry_run: {args.dry_run}")
    logger.info(f"skip_download: {args.skip_download}")
    logger.info("=" * 60)
    
    stats = LoadStats()
    
    try:
        # Download and extract
        xml_files = await download_and_extract(skip_download=args.skip_download)
        logger.info(f"Found {len(xml_files)} XML files to process")
        
        # Connect to database (unless dry run)
        pool = None
        if not args.dry_run:
            database_url = os.getenv("DATABASE_URL")
            if not database_url:
                logger.error("DATABASE_URL not set")
                sys.exit(1)
            
            logger.info("Connecting to database...")
            pool = await asyncpg.create_pool(database_url, min_size=2, max_size=10)
            logger.info("Database connected")
        
        try:
            # Process XML files
            await process_xml_files(xml_files, pool, stats, dry_run=args.dry_run)
        finally:
            if pool:
                await pool.close()
        
        # Log final stats
        stats.log_final()
        
    except Exception as e:
        logger.exception(f"Load failed: {e}")
        sentry_sdk.capture_exception(e)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
