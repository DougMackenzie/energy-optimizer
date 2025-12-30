"""
EMERGENCY CACHING FIX for Google Sheets API Quota
Add this at the TOP of greenfield_heuristic_v2.py after the imports

This prevents hitting API quota by caching Equipment and Global_Parameters
for 5 minutes in module-level variables.
"""

# Add after line 46 (after logger = logging.getLogger(__name__))

# Module-level cache to prevent API quota exhaustion  
_CACHE_TTL_SECONDS = 300  # 5 minutes
_EQUIPMENT_CACHE = {}
_PARAMS_CACHE = {}

def get_cached_or_load(cache_dict, cache_key, load_func, ttl_seconds=300):
    """Generic caching wrapper with TTL."""
    import time
    current_time = time.time()
    
    if cache_key in cache_dict:
        data, timestamp = cache_dict[cache_key]
        if current_time - timestamp < ttl_seconds:
            print(f"✅ Using cached {cache_key} ({int(current_time - timestamp)}s old)")
            return data
    
    # Cache miss or expired - load fresh
    print(f"📥 Loading fresh {cache_key} from Google Sheets...")
    data = load_func()
    cache_dict[cache_key] = (data, current_time)
    return data
