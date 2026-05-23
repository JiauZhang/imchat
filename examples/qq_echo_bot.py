import asyncio
import logging

from imchat.qq import QQClient
from imchat.keystore import load_keys, save_keys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

async def main():
    keys = load_keys("qq")
    user_openid = keys.get("user_openid", "")

    client = QQClient.from_saved_keys()
    if client is None:
        print("QQ credentials not configured.")
        print("Run qq_api_only.py first to configure credentials:")
        print("  python examples/qq_api_only.py --app-id <app_id> --client-secret <client_secret>")
        return

    @client.on_ready
    async def on_ready(data):
        print(f"Bot Online! Session: {data.get('session_id')}")
        if user_openid:
            print(f"Sending proactive greeting to {user_openid}...")
            await client.send_c2c_message(user_openid, "imchat online.")
            print("Proactive greeting sent")
        else:
            print("No user_openid saved yet. Send me a C2C message to register yours.")

    @client.on_c2c_message
    async def handle_c2c(msg):
        print(f"[C2C] id={msg.id} openid={msg.user_openid} content={msg.content} author_bot={msg.author_bot}")
        if not user_openid:
            save_keys("qq", {**load_keys("qq"), "user_openid": msg.user_openid})
            print(f"Saved user_openid={msg.user_openid}")
        await client.send_c2c_message(msg.user_openid, f"Echo: {msg.content}")

    @client.on_group_message
    async def handle_group(msg):
        print(f"[Group] {msg.group_openid} | {msg.author_name}: {msg.content}")
        if any(m.is_you for m in msg.mentions):
            await client.send_c2c_message(msg.author_id, f"Echo: {msg.content}")

    @client.on_guild_message
    async def handle_guild(msg):
        print(f"[Guild] {msg.channel_id} | {msg.author_name}: {msg.content}")
        await client.send_c2c_message(msg.author_id, f"Echo: {msg.content}")

    @client.on_interaction
    async def handle_interaction(interaction):
        print(f"[Interaction] button={interaction.button_id}, data={interaction.button_data}")
        await interaction.acknowledge()

    @client.on_error
    async def handle_error(error):
        print(f"[Error] {error}")

    await client.start()


if __name__ == "__main__":
    asyncio.run(main())