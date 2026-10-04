import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import discord
from discord import app_commands
from discord.ui import Select, View, Button

# 1. Mini webszerver a Render számára
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

# 2. Discord bot beállítása intents-el
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

class MyBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        MY_GUILD = discord.Object(id=1396852655908720830)
        self.tree.clear_commands(guild=None) # Kitakarítja a régi duplikált globális parancsokat
        self.tree.copy_global_to(guild=MY_GUILD)
        await self.tree.sync(guild=MY_GUILD)
        print("Minden parancs frissítve és szinkronizálva a szerverre!")

client = MyBot()

@client.event
async def on_ready():
    print(f'Sikeres bejelentkezés mint: {client.user}')

# --- TICKET RENDSZER (Privát szoba létrehozása) ---
class TicketSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Technikai hiba", description="Problémád akadt a szerverrel vagy a bottal", emoji="🛠️"),
            discord.SelectOption(label="Játékos jelentése", description="Szabályszegő játékos jelentése", emoji="⚠️"),
            discord.SelectOption(label="Egyéb kérdés", description="Minden más jellegű kérdés", emoji="❓")
        ]
        super().__init__(placeholder="Válassz indokot...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user
        category = discord.utils.get(guild.categories, name="Tickets") # Opcionális: ha van 'Tickets' kategória

        # Jogosultságok: csak a user és az adminok láthatják
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        # Admin rang vagy Administrator jogosultság hozzáférése a szobához
        for role in guild.roles:
            if role.permissions.administrator:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        # Létrehozzuk a privát csatornát
        channel_name = f"ticket-{user.name}"
        ticket_channel = await guild.create_text_channel(channel_name, overwrites=overwrites, category=category)

        embed = discord.Embed(
            title=f"🎟️ Hibajegy: {self.values[0]}",
            description=f"Szia {user.mention}! Köszönjük a megkeresést. Az adminisztrátorok hamarosan válaszolnak.\nA bezáráshoz írd be, hogy lezárás.",
            color=discord.Color.green()
        )
        await ticket_channel.send(embed=embed)
        await interaction.response.send_message(f"A hibajegy szobád elkészült: {ticket_channel.mention}", ephemeral=True)

class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())


# --- NYEREMÉNYJÁTÉK GOMB ---
class GiveAwayView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Csatlakozz a nyereményjátékhoz 🎉", style=discord.ButtonStyle.blurple)
    async def join_giveaway(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("Sikeresen jelentkeztél a nyereményjátékra! Sok szerencsét! 🍀", ephemeral=True)


# --- SLASH PARANCSOK ---

@client.tree.command(name="koszont", description="A bot köszönt téged!")
async def koszont(interaction: discord.Interaction):
    await interaction.response.send_message(f"Szia {interaction.user.mention}! Örülök, hogy itt vagy!")

@client.tree.command(name="ticket", description="Hibajegy nyitó panel kiírása")
@app_commands.default_permissions(administrator=True)
async def ticket(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎟️ Hibajegy nyitása",
        description="Válassz indokot a segítségkéréshez!",
        color=discord.Color.blue()
    )
    await interaction.channel.send(embed=embed, view=TicketView())
    await interaction.response.send_message("A ticket panel sikeresen elküldve!", ephemeral=True)

@client.tree.command(name="javaslat", description="Küldj be egy javaslatot a szerverre")
@app_commands.describe(szoveg="A javaslatod tartalma")
async def javaslat(interaction: discord.Interaction, szoveg: str):
    embed = discord.Embed(
        title=f"Javaslat - {interaction.user.name}",
        description=szoveg,
        color=discord.Color.gold()
    )
    embed.set_thumbnail(url=interaction.user.display_avatar.url)
    msg = await interaction.channel.send(embed=embed)
    await msg.add_reaction("👍")
    await msg.add_reaction("👎")
    await interaction.response.send_message("A javaslatod sikeresen beküldve!", ephemeral=True)

@client.tree.command(name="nyeremenyjatek", description="Indíts nyereményjátékot (Csak Owner/Admin)")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(nyeremeny="Mi a nyeremény?")
async def nyeremenyjatek(interaction: discord.Interaction, nyeremeny: str):
    embed = discord.Embed(
        title="🎁 Új Nyereményjáték!",
        description=f"**Nyeremény:** {nyeremeny}\n\nKattints az alábbi gombra a jelentkezéshez!",
        color=discord.Color.purple()
    )
    embed.set_footer(text=f"Szervező: {interaction.user.name}")
    await interaction.channel.send(embed=embed, view=GiveAwayView())
    await interaction.response.send_message("A nyereményjáték elindítva!", ephemeral=True)

# -----------------------------------------------

token = os.getenv('DISCORD_TOKEN')
client.run(token)
