import asyncio

from imchat.wechat import WeChatClient


async def main():
    client = WeChatClient.from_saved_keys()
    if client is None:
        client = WeChatClient()
        result = await client.login_with_qr(verbose=True)
        if not result.connected:
            print("Login failed")
            return
        print(f"Logged in as {result.user_id}")

    target_user = "target_user_id"

    await client.send_text(target_user, "Hello from imchat!")

    await client.send_image(target_user, "path/to/image.jpg", text="Check this image")

    await client.send_video(target_user, "path/to/video.mp4", text="Check this video")

    await client.send_file(target_user, "path/to/document.pdf", text="Check this file")

    print("All messages sent")

    await client.close()


if __name__ == "__main__":
    asyncio.run(main())