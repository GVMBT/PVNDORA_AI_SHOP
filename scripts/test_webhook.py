"""
Quick script to test webhook endpoint
Usage: python scripts/test_webhook.py
"""
import asyncio
import httpx

async def test_webhook():
    """Test if webhook endpoint is accessible"""
    webhook_url = "https://pvndora.app/webhook/telegram"
    
    # Test payload (minimal update)
    test_payload = {
        "update_id": 999999999,
        "message": {
            "message_id": 1,
            "date": 1234567890,
            "chat": {
                "id": 123456789,
                "type": "private"
            },
            "from": {
                "id": 123456789,
                "is_bot": False,
                "first_name": "Test"
            },
            "text": "/start"
        }
    }
    
    print(f"🧪 Testing webhook: {webhook_url}\n")
    
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        try:
            response = await client.post(
                webhook_url,
                json=test_payload,
                headers={"Content-Type": "application/json"}
            )
            
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.text}")
            
            if response.status_code == 200:
                print("\n✅ Webhook endpoint is accessible!")
            else:
                print(f"\n❌ Webhook returned status {response.status_code}")
                
        except httpx.TimeoutException:
            print("❌ Request timeout - webhook endpoint may be down")
        except httpx.ConnectError:
            print("❌ Connection error - check if domain is correct")
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_webhook())

