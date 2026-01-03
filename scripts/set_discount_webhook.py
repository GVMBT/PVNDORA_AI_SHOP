"""Set discount bot webhook."""
import asyncio
import httpx


async def main():
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post("https://pvndora.app/api/webhook/discount/set")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")


if __name__ == "__main__":
    asyncio.run(main())
