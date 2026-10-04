import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import discord
from discord import app_commands
from discord.ui import Select, View

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
intents.members = True
intents.presence = True

class MyBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()
        print("Slash parancsok szinkronizálva!")

client = MyBot()

@client.event
async def on_ready():
    print(f'Sikeres bejelentkezés mint: {client.user}')

# --- TICKET LENYÍLÓ MENÜ OSZTÁLY ---
class TicketSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Technikai hiba", description="Problémád akadt a szerverrel vagy a bottal", emoji="🛠️"),
            discord.SelectOption(label="Játékos jelentése", description="Szabályszegő játékos jelentése", emoji="⚠️"),
            discord.SelectOption(label="Egyéb kérdés", description="Minden más jellegű kérdés", emoji="❓")
        ]
        super().__init__(placeholder="Válassz indokot...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        # Itt hozzuk létre majd a privát csatornát a kiválasztott indok alapján
        await interaction.response.send_message(f"A hibajegyed rögzítve lett ezzel az indokkal: **{self.values[0]}**. Létrehozom a szobát...", ephemeral=True)

class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())

# --- SLASH PARANCSOK ---

@client.tree.command(name="koszont", description="A bot köszönt téged!")
async def koszont(interaction: discord.Interaction):
    await interaction.response.send_message(f"Szia {interaction.user.mention}! Örülök, hogy itt vagy!")

@client.tree.command(name="ticketpanel", description="Hibajegy nyitó panel kiírása")
@app_commands.default_permissions(administrator=True)
async def ticketpanel(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎟️ Hibajegy nyitása",
        description="Válassz indokot a segítségkéréshez!",
        color=discord.Color.blue()
    )
    await interaction.channel.send(embed=embed, view=TicketView())
    await interaction.response.send_message("A ticket panel sikeresen elküldve!", ephemeral=True)

# -----------------------------------------------

token = os.getenv('DISCORD_TOKEN')
client.run(token)
