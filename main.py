import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import discord
from discord.ext import commands
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

# 2. Discord bot beállítása
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

MY_GUILD = discord.Object(id=1396852655908720830)

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # Perzisztens nézetek regisztrálása
        self.add_view(TicketView())
        self.add_view(CloseTicketView())
        self.add_view(GiveAwayView())

        # Parancsok szinkronizálása a szerverrel
        self.tree.copy_global_to(guild=MY_GUILD)
        await self.tree.sync(guild=MY_GUILD)
        print("Minden parancs és nézet sikeresen szinkronizálva!")

bot = MyBot()

@bot.event
async def on_ready():
    print(f'Sikeres bejelentkezés mint: {bot.user}')

# --- TICKET BEZÁRÓ GOMB ---
class CloseTicketView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Ticket Bezárása", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="close_ticket_btn")
    async def close_ticket(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("A ticket 5 másodperc múlva bezáródik...", ephemeral=True)
        import asyncio
        await asyncio.sleep(5)
        try:
            await interaction.channel.delete()
        except Exception:
            pass

# --- TICKET LENYÍLÓ MENÜ ---
class TicketSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Technikai hiba", description="Problémád akadt a szerverrel vagy a bottal", emoji="🛠️"),
            discord.SelectOption(label="Játékos jelentése", description="Szabályszegő játékos jelentése", emoji="⚠️"),
            discord.SelectOption(label="Egyéb kérdés", description="Minden más jellegű kérdés", emoji="❓")
        ]
        super().__init__(placeholder="Válassz indokot...", min_values=1, max_values=1, options=options, custom_id="ticket_select_menu_unique")

    async def callback(self, interaction: discord.Interaction):
        guild = interaction.guild
        user = interaction.user
        channel_name = f"ticket-{user.name.lower()}"

        # 1. Ellenőrzés, hogy van-e már nyitott ticketje
        existing_channel = discord.utils.get(guild.text_channels, name=channel_name)
        if existing_channel:
            # Visszaállítjuk a menüt, hogy ne maradjon kiválasztva
            await interaction.response.edit_message(view=TicketView())
            await interaction.followup.send(f"Már van egy nyitott ticketed: {existing_channel.mention}!", ephemeral=True)
            return

        # Azonnali válasz, hogy ne fusson ki az időből (3mp limit)
        await interaction.response.defer(thinking=True, ephemeral=True)

        category = discord.utils.get(guild.categories, name="Tickets")
        if not category:
            category = await guild.create_category("Tickets")

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        for role in guild.roles:
            if role.permissions.administrator:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        ticket_channel = await guild.create_text_channel(channel_name, overwrites=overwrites, category=category)

        embed = discord.Embed(
            title="🎟️️ Ticket Létrehozva",
            description=(
                "💬 **Köszönjük, hogy ticketet nyitottál!**\n"
                "A csapatunk hamarosan felveszi veled a kapcsolatot, kérjük maradj türelmes.\n\n"
                "🚩 **Mit tegyél most?**\n"
                "▶️ Írd le részletesen a problémát vagy kérdést\n"
                "▶️ Csatolj képet / videót ha szükséges\n"
                "▶️ Ne pingelj staff tagokat – érkezni fognak!"
            ),
            color=discord.Color.from_rgb(119, 178, 85)
        )

        await ticket_channel.send(content=user.mention, embed=embed, view=CloseTicketView())
        
        # 2. Üzenet szerkesztése, hogy a lenyíló menü alaphelyzetbe (üresre) álljon vissza
        await interaction.message.edit(view=TicketView())
        await interaction.followup.send(f"A hibajegy szobád elkészült: {ticket_channel.mention}", ephemeral=True)

class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())


# --- NYEREMÉNYJÁTÉK GOMB ---
class GiveAwayView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Csatlakozz a nyereményjátékhoz 🎉", style=discord.ButtonStyle.blurple, custom_id="giveaway_join_btn")
    async def join_giveaway(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message("Sikeresen jelentkeztél a nyereményjátékra! Sok szerencsét! 🍀", ephemeral=True)


# --- SLASH PARANCSOK ---

@bot.tree.command(name="koszont", description="A bot köszönt téged!", guild=MY_GUILD)
async def koszont(interaction: discord.Interaction):
    await interaction.response.send_message(f"Szia {interaction.user.mention}! Örülök, hogy itt vagy!")

@bot.tree.command(name="ticket", description="Hibajegy nyitó panel kiírása", guild=MY_GUILD)
@app_commands.default_permissions(administrator=True)
async def ticket(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎟️ Hibajegy nyitása",
        description="Válassz indokot a segítségkéréshez!",
        color=discord.Color.blue()
    )
    await interaction.channel.send(embed=embed, view=TicketView())
    await interaction.response.send_message("A ticket panel sikeresen elküldve!", ephemeral=True)

@bot.tree.command(name="javaslat", description="Küldj be egy javaslatot a szerverre", guild=MY_GUILD)
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

@bot.tree.command(name="nyeremenyjatek", description="Indíts nyereményjátékot (Csak Admin/Owner)", guild=MY_GUILD)
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
    await interaction.response.send_message("Nyereményjáték elindítva!", ephemeral=True)

# -----------------------------------------------

token = os.getenv('DISCORD_TOKEN')
bot.run(token)
