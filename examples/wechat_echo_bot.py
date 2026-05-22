import asyncio
import logging

from imchat.wechat import WeChatClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


async def main():
    client = WeChatClient.from_saved_keys()
    if client is None:
        client = WeChatClient()
        result = await client.login_with_qr(verbose=True)
        if not result.connected:
            print("Login failed")
            return
        print(f"Logged in as {result.user_id}")

    async for ctx in client.poll_messages():
        print(f"[WeChat] from={ctx.from_user_id}: {ctx.body}")
        await client.send_text(ctx.from_user_id, f"Echo: {ctx.body}")


if __name__ == "__main__":
    asyncio.run(main())