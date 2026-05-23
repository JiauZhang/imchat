import argparse
import asyncio
import logging

from imchat.qq import QQClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


def main():
    parser = argparse.ArgumentParser(description="QQ Bot API example")
    parser.add_argument("--app-id", help="QQ bot app_id (from https://bot.q.qq.com/)")
    parser.add_argument("--client-secret", help="QQ bot client_secret (from https://bot.q.qq.com/)")
    args = parser.parse_args()

    if args.app_id and args.client_secret:
        client = QQClient(app_id=args.app_id, client_secret=args.client_secret)
        client.save_credentials()
        print("Credentials saved to ~/.imchat/qq.json")
    else:
        client = QQClient.from_saved_keys()

    if client is None:
        print("QQ credentials not configured.")
        print("Get app_id and client_secret from: https://bot.q.qq.com/")
        print("\nThen run with:")
        print(f"  python {__file__} --app-id <app_id> --client-secret <client_secret>")
        return

    asyncio.run(async_main(client))


async def async_main(client: QQClient):
    try:
        gateway_url = await client.get_gateway_url()
        print(f"Gateway URL: {gateway_url}")
        print("Credentials verified successfully!")
        print("\nAvailable API methods:")
        print("  await client.send_c2c_message(openid='USER_OPENID', content='hello')")
        print("  await client.send_group_message(group_openid='GROUP_OPENID', content='hello')")
        print("  await client.send_c2c_image(openid='USER_OPENID', image_url='https://...')")
        print("  await client.send_c2c_voice(openid='USER_OPENID', voice_url='https://...')")
        print("  await client.send_c2c_file(openid='USER_OPENID', file_url='https://...', file_name='doc.pdf')")
        print("  await client.send_c2c_video(openid='USER_OPENID', video_url='https://...')")
        print()
        print("Replace placeholders (USER_OPENID, GROUP_OPENID) with real values from QQ Bot platform.")

    finally:
        await client.stop()


if __name__ == "__main__":
    main()