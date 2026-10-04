import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import discord
from discord import app_commands

# 1. Mini webszerver a Render számára (hogy ne lője le a service-t)
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

server_thread = threading.Thread(target=run_server)
server_thread.daemon = True
server_thread.start()

# 2. Discord bot beállítása intents-el és parancsfával
intents = discord.Intents.default()
intents.message_content = True

class MyBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        # Szinkronizálja a parancsokat a Discord felé
        await self.tree.sync()
        print("Slash parancsok szinkronizálva!")

client = MyBot()

@client.event
async def on_ready():
    print(f'Sikeres bejelentkezés mint: {client.user}')

# --- ITT HOZHATSZ LÉTRE ÚJ SLASH PARANCSOKAT ---

@client.tree.command(name="koszont", description="A bot köszönt téged!")
async def koszont(interaction: discord.Interaction):
    await interaction.response.send_message(f"Szia {interaction.user.mention}! Örülök, hogy itt vagy!")

# -----------------------------------------------

token = os.getenv('DISCORD_TOKEN')
client.run(token)
