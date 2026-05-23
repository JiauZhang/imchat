import asyncio
import logging

from imchat.qq import QQClient, QQInlineKeyboard, QQKeyboardRow, QQKeyboardButton

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
        if msg.content.lower() == "menu":
            keyboard = QQInlineKeyboard(rows=[
                QQKeyboardRow(buttons=[
                    QQKeyboardButton(
                        id="btn_like",
                        label="Like",
                        style=1,
                        action_type=1,
                        data="action:like",
                    ),
                    QQKeyboardButton(
                        id="btn_dislike",
                        label="Dislike",
                        style=3,
                        action_type=1,
                        data="action:dislike",
                    ),
                ]),
                QQKeyboardRow(buttons=[
                    QQKeyboardButton(
                        id="btn_help",
                        label="Help",
                        style=4,
                        action_type=1,
                        data="action:help",
                    ),
                ]),
            ])
            await msg.reply("Choose an action:", inline_keyboard=keyboard)
        else:
            await msg.reply('Send "menu" to see the button menu')

    @client.on_interaction
    async def handle_interaction(interaction):
        button_data = interaction.button_data or ""

        if button_data == "action:like":
            await interaction.acknowledge()
            if interaction.user_openid:
                await client.send_c2c_message(
                    interaction.user_openid,
                    "Thanks for your like!",
                )

        elif button_data == "action:dislike":
            await interaction.acknowledge()
            if interaction.user_openid:
                await client.send_c2c_message(
                    interaction.user_openid,
                    "We will keep improving!",
                )

        elif button_data == "action:help":
            await interaction.acknowledge()
            if interaction.user_openid:
                await client.send_c2c_message(
                    interaction.user_openid,
                    'This is a keyboard interaction demo.\nSend "menu" to see the button menu.',
                )

        else:
            await interaction.acknowledge()

    await client.start()


if __name__ == "__main__":
    asyncio.run(main())