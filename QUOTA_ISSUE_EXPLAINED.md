# SIMPLER SOLUTION: Wait for quota to reset, then optimization will work

The 429 errors are because you're hitting the Google Sheets API quota limit.

## Why it's happening:
1. Dashboard loads → many API calls to Sites, Load_Profiles, Results tabs
2. You click Run Optimization → tries to load Equipment tab → 429!
3. Falls back to default equipment → runs fast (0.1s) with incomplete data

## Solution 1: WAIT 60 SECONDS
The quota resets on a rolling 60-second window. Just wait 1 minute and try again.

## Solution 2: Request Quota Increase (You already started this)
- Google Cloud Console → APIs & Services → Quotas
- Find "Google Sheets API - Read requests per minute"
- Request increase to 300 or 600 requests/minute

## Solution 3: I'll implement proper caching RIGHT NOW
Adding @st.cache_data to equipment/params loading so it only loads ONCE per 5 minutes.
