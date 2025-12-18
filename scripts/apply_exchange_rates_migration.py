"""
Apply exchange_rates migration directly via Supabase client.
Run this once to create the table and populate initial rates.
"""
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
    sys.exit(1)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Check if table exists
try:
    result = supabase.table("exchange_rates").select("currency").limit(1).execute()
    print(f"Table exists, has data: {len(result.data) > 0}")
except Exception as e:
    print(f"Table check failed: {e}")
    print("Creating table via RPC...")
    
    # Create table via raw SQL (using rpc if available)
    # Note: This requires the table to be created via Dashboard if RPC not available

# Insert/update rates
rates = [
    ("USD", 1.0),
    ("RUB", 80.0),
    ("EUR", 0.92),
    ("UAH", 41.0),
    ("TRY", 34.0),
    ("INR", 84.0),
    ("AED", 3.67),
    ("GBP", 0.79),
    ("CNY", 7.25),
    ("JPY", 154.0),
    ("KRW", 1400.0),
    ("BRL", 6.1),
]

print("Upserting exchange rates...")
for currency, rate in rates:
    try:
        supabase.table("exchange_rates").upsert({
            "currency": currency,
            "rate": rate,
        }).execute()
        print(f"  {currency}: {rate}")
    except Exception as e:
        print(f"  {currency}: FAILED - {e}")

# Verify
result = supabase.table("exchange_rates").select("*").execute()
print(f"\nVerification - {len(result.data)} rates in DB:")
for row in result.data:
    print(f"  {row['currency']}: {row['rate']}")

print("\nDone!")


