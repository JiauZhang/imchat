import asyncio
import logging

from imchat.qq import QQClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


async def main():
    client = QQClient()

    @client.on_ready
    async def on_ready(data):
        print(f"Bot Online! Session: {data.get('session_id')}")

    @client.on_c2c_message
    async def handle_c2c(msg):
        print(f"[C2C] {msg.user_openid}: {msg.content}")
        await msg.reply(f"Echo: {msg.content}")

    @client.on_group_message
    async def handle_group(msg):
        print(f"[Group] {msg.group_openid} | {msg.author_name}: {msg.content}")
        if any(m.is_you for m in msg.mentions):
            await msg.reply(f"Echo: {msg.content}")

    @client.on_guild_message
    async def handle_guild(msg):
        print(f"[Guild] {msg.channel_id} | {msg.author_name}: {msg.content}")
        await msg.reply(f"Echo: {msg.content}")

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