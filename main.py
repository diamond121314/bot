import os
import discord

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)


@client.event
async def on_ready():
  print(f'Sikeres bejelentkezés mint: {client.user}')


# A tokent automatikusan kiolvassa a Renderen megadott környezeti változóból
token = os.getenv('DISCORD_TOKEN')
client.run(token)
