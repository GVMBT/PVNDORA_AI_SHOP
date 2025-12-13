#!/usr/bin/env python3
"""Check DB user count vs leaderboard"""
import requests
import json

# Get leaderboard from production API (no auth needed for this check)
try:
    r = requests.get('https://pvndora-ai-shop.vercel.app/api/webapp/leaderboard?limit=100', timeout=10)
    print(f"Status code: {r.status_code}")
    print(f"Response text: {r.text[:500]}")
    
    if r.status_code == 200:
        data = r.json()
        
        print("\n=== LEADERBOARD API RESPONSE ===")
        print(f"total_users: {data.get('total_users', 'NOT SET')}")
        print(f"leaderboard entries: {len(data.get('leaderboard', []))}")
        print(f"has_more: {data.get('has_more', 'NOT SET')}")
        
        print("\n=== FIRST 10 ENTRIES ===")
        for e in data.get('leaderboard', [])[:10]:
            print(f"  Rank {e.get('rank'):3d}: {e.get('name'):15s} | saved: {e.get('total_saved'):8.2f}")
        
except Exception as e:
    print(f"Error: {e}")

