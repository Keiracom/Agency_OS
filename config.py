#!/usr/bin/env python3
"""
Configuration for Siege Waterfall
CEO Directive #014 - ABN→GMB Waterfall Name Resolution
"""

import os
from typing import Optional


class Config:
    """Configuration management for Siege Waterfall"""
    
    # Supabase configuration
    SUPABASE_URL: Optional[str] = os.getenv('SUPABASE_URL')
    SUPABASE_KEY: Optional[str] = os.getenv('SUPABASE_KEY')
    
    # GMB API configuration
    GMB_API_KEY: Optional[str] = os.getenv('GMB_API_KEY')
    GMB_API_ENDPOINT: str = os.getenv('GMB_API_ENDPOINT', 'https://maps.googleapis.com/maps/api/place')
    
    # Logging configuration
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Waterfall configuration
    MAX_ASIC_NAMES_TO_TRY: int = int(os.getenv('MAX_ASIC_NAMES_TO_TRY', '10'))
    MATCH_SCORE_THRESHOLD: float = float(os.getenv('MATCH_SCORE_THRESHOLD', '0.7'))
    
    # Database table name
    MATCH_LOG_TABLE: str = 'tier2_gmb_match_log'
    
    # Generic name patterns (can be extended via env var)
    GENERIC_PATTERNS_EXTRA: list = os.getenv('GENERIC_PATTERNS_EXTRA', '').split(',') if os.getenv('GENERIC_PATTERNS_EXTRA') else []
    
    @classmethod
    def validate(cls) -> bool:
        """Validate configuration for production use"""
        required_vars = [
            'SUPABASE_URL',
            'SUPABASE_KEY'
        ]
        
        missing = [var for var in required_vars if not getattr(cls, var)]
        
        if missing:
            print(f"Missing required configuration: {', '.join(missing)}")
            return False
        
        return True
    
    @classmethod
    def get_env_template(cls) -> str:
        """Return environment variable template"""
        return """
# Siege Waterfall Configuration
# CEO Directive #014 - ABN→GMB Waterfall Name Resolution

# Required: Supabase database
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key

# Optional: Google My Business API
GMB_API_KEY=your-gmb-api-key
GMB_API_ENDPOINT=https://maps.googleapis.com/maps/api/place

# Optional: Tuning parameters
MAX_ASIC_NAMES_TO_TRY=10
MATCH_SCORE_THRESHOLD=0.7
LOG_LEVEL=INFO

# Optional: Additional generic patterns (comma-separated)
GENERIC_PATTERNS_EXTRA=corporation,ventures,capital
        """.strip()


if __name__ == '__main__':
    print("Siege Waterfall Configuration")
    print("=" * 40)
    
    if Config.validate():
        print("✅ Configuration is valid for production")
    else:
        print("❌ Configuration is incomplete")
        print("\nEnvironment template:")
        print(Config.get_env_template())