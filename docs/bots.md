# Using it in a bot

Keep one `Cards` for the whole bot instead of making one per message, it holds akef's game data and the
[caches](caching.md). Drawing runs in a worker thread, so the bot keeps answering other messages while a card
is made.

```py
cards = akef_cards.Cards(max_renders=3)    # max 3 cards drawing at once, the rest wait
```

## Tips

- `render_bytes()` gives a named `BytesIO`, ready to send
- `format="JPEG"` makes still cards a lot smaller
- `hidden=True` blurs the UID, nice for public chats
- pass user uploads as bytes, never their text as a path, see [Custom art](custom-art.md)
- animated cards: `fit_under()` keeps them under an upload limit
- catch `akef.PlayerNotFound`, `akef.ShowcaseEmpty` and `akef_cards.CardError`, see [Errors](errors.md)

## discord.py

```py
import discord
from discord import app_commands

import akef
import akef_cards

bot = discord.Client(intents=discord.Intents.default())
tree = app_commands.CommandTree(bot)
cards = akef_cards.Cards(max_renders=3)


@tree.command(description="operator card from an Enka UID")
async def card(interaction: discord.Interaction, uid: str, operator: str, dark: bool = False):
    await interaction.response.defer()
    try:
        build = (await cards.enka(uid)).build(operator)
    except akef.PlayerNotFound:
        return await interaction.followup.send("cant find that UID")
    except akef.ShowcaseEmpty:
        return await interaction.followup.send("their showcase is empty")
    if build is None:
        return await interaction.followup.send(f"{operator} isnt in their showcase")
    file = await cards.render_bytes(build, template=2 if dark else 1, hidden=True, format="JPEG")
    await interaction.followup.send(file=discord.File(file, filename=file.name))


@tree.command(description="operator card with your gif as the art")
async def animated(interaction: discord.Interaction, uid: str, operator: str, gif: discord.Attachment):
    await interaction.response.defer()
    build = (await cards.enka(uid)).build(operator)
    if build is None:
        return await interaction.followup.send(f"{operator} isnt in their showcase")
    try:
        clip = await cards.animated_card(build, await gif.read(), fit="auto", hidden=True)
        file = await clip.fit_under(10)
    except akef_cards.CardError as e:
        return await interaction.followup.send(str(e))
    await interaction.followup.send(file=discord.File(file, filename=file.name))


@bot.event
async def on_ready():
    await tree.sync()


bot.run("your bot token")
```

## aiogram (Telegram)

```py
from aiogram import Bot, Dispatcher
from aiogram.filters import Command, CommandObject
from aiogram.types import BufferedInputFile, Message

import akef_cards

dp = Dispatcher()
cards = akef_cards.Cards(max_renders=3)


@dp.message(Command("card"))
async def card(message: Message, command: CommandObject):
    uid, _, operator = (command.args or "").partition(" ")
    build = (await cards.enka(uid)).build(operator)
    if build is None:
        return await message.answer(f"{operator} isnt in their showcase")
    file = await cards.render_bytes(build, hidden=True, format="JPEG")
    await message.answer_photo(BufferedInputFile(file.getvalue(), filename=file.name))


@dp.message(Command("animated"))
async def animated(message: Message, command: CommandObject, bot: Bot):
    # reply to a gif or webp sent as a file with /animated <uid> <operator>
    gif = message.reply_to_message and message.reply_to_message.document
    if not gif:
        return await message.answer("send the gif as a file, then reply to it with /animated <uid> <operator>")
    uid, _, operator = (command.args or "").partition(" ")
    build = (await cards.enka(uid)).build(operator)
    if build is None:
        return await message.answer(f"{operator} isnt in their showcase")
    data = await bot.download(gif)
    try:
        clip = await cards.animated_card(build, data.read(), fit="auto", hidden=True)
        file = await clip.fit_under(20, "GIF")
    except akef_cards.CardError as e:
        return await message.answer(str(e))
    await message.answer_animation(BufferedInputFile(file.getvalue(), filename=file.name))
```

Gifs picked from Telegram's gif search are really mp4 videos, which can't be read, so ask users to send a real
gif or webp as a file. Send the result as `GIF` with `answer_animation`, a webp would show up as a sticker or a
plain file.

Neither example is tested end to end, treat them as a starting point.
