import asyncio
import logging

from imchat.qq import QQClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


async def main():
    client = QQClient.from_saved_keys()

    try:
        gateway_url = await client.get_gateway_url()
        print(f"Gateway URL: {gateway_url}")

        resp = await client.send_c2c_message(
            openid="target_user_openid",
            content="Hello from API!",
        )
        print(f"C2C message sent: id={resp.id}")

        resp = await client.send_group_message(
            group_openid="target_group_openid",
            content="Hello Group!",
        )
        print(f"Group message sent: id={resp.id}")

        resp = await client.send_c2c_image(
            openid="target_user_openid",
            image_url="https://example.com/image.png",
        )
        print(f"Image sent: id={resp.id}")

    finally:
        await client.stop()


if __name__ == "__main__":
    asyncio.run(main())