import asyncio
from agent import cai_agent

async def main():
    try:
        response = await cai_agent.get_cai_response('What is MSc?', 'msc')
        print("Success:", response)
    except Exception as e:
        print("Crash:", e)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
