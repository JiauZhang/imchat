import asyncio
import logging

from imchat.qq import QQClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


async def main():
    client = QQClient.from_saved_keys()
    if client is None:
        print("QQ credentials not configured.")
        print("Run qq_api_only.py first to configure credentials:")
        print("  python examples/qq_api_only.py --app-id <app_id> --client-secret <client_secret>")
        return

    @client.on_c2c_message
    async def handle_c2c(msg):
        content = msg.content.lower()

        if content == "image":
            await msg.reply_with_image(image_url="https://example.com/image.png")

        elif content == "image_local":
            with open("test.png", "rb") as f:
                await msg.reply_with_image(image_data=f.read())

        elif content == "voice":
            with open("voice.silk", "rb") as f:
                await client.send_c2c_voice(msg.user_openid, voice_data=f.read())

        elif content == "file":
            with open("document.pdf", "rb") as f:
                await client.send_c2c_file(
                    msg.user_openid,
                    file_data=f.read(),
                    file_name="document.pdf",
                )

        elif content == "video":
            await client.send_c2c_video(
                msg.user_openid,
                video_url="https://example.com/video.mp4",
            )

        else:
            await msg.reply("Available commands: image, image_local, voice, file, video")

    await client.start()


if __name__ == "__main__":
    asyncio.run(main())