import os
import threading
import asyncio
import random
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

# 2. Discord bot beállítása (Globális mód)
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.add_view(TicketView())
        self.add_view(CloseTicketView())

        # Globális szinkronizálás (minden szerveren működik)
        await self.tree.sync()
        print("Minden parancs globálisan szinkronizálva!")

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

        existing_channel = discord.utils.get(guild.text_channels, name=channel_name)
        if existing_channel:
            await interaction.response.edit_message(view=TicketView())
            await interaction.followup.send(f"Már van egy nyitott ticketed: {existing_channel.mention}!", ephemeral=True)
            return

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
            title="🎟 Ticket Létrehozva",
            description=(
                "💬 **Köszönjük, hogy ticketet nyitottál!**\n"
                "A csapatunk hamarosan felveszi veled a kapcsolatot, kérjük maradj türelmes.\n\n"
                "🚩 **Mit tegyél most?**\n"
                "▶️ Írd le részletesen a problémát vagy kérdést\n"
                "▶️ Csatolj képet / videót ha szükséges\n"
                "▶️️ Ne pingelj staff tagokat – érkezni fognak!"
            ),
            color=discord.Color.from_rgb(119, 178, 85)
        )

        await ticket_channel.send(content=user.mention, embed=embed, view=CloseTicketView())
        await interaction.message.edit(view=TicketView())
        await interaction.followup.send(f"A hibajegy szobád elkészült: {ticket_channel.mention}", ephemeral=True)

class TicketView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketSelect())


# --- NYEREMÉNYJÁTÉK VIEW ÉS LOGIKA ---
class GiveAwayView(View):
    def __init__(self, nyeremeny: str, organizer: str, duration_minutes: int):
        super().__init__(timeout=duration_minutes * 60)
        self.nyeremeny = nyeremeny
        self.organizer = organizer
        self.participants = set()
        self.message = None

    @discord.ui.button(label="Csatlakozz (0)", style=discord.ButtonStyle.blurple, emoji="🎉", custom_id="giveaway_join_dynamic")
    async def join_giveaway(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id in self.participants:
            await interaction.response.send_message("Már csatlakoztál a nyereményjátékhoz! 🍀", ephemeral=True)
        else:
            self.participants.add(interaction.user.id)
            button.label = f"Csatlakozz ({len(self.participants)})"
            await interaction.response.edit_message(view=self)
            await interaction.followup.send("Sikeresen jelentkeztél a nyereményjátékra! Sok szerencsét! 🍀", ephemeral=True)

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True

        if self.message:
            try:
                embed = self.message.embeds[0]
                if self.participants:
                    winner_id = random.choice(list(self.participants))
                    winner = self.message.guild.get_member(winner_id)
                    winner_text = winner.mention if winner else f"<@{winner_id}>"
                    embed.color = discord.Color.green()
                    embed.add_field(name="🏆 Nyertes", value=f"Gratulálunk! 🎉 {winner_text}", inline=False)
                else:
                    embed.color = discord.Color.red()
                    embed.add_field(name="🏆 Nyertes", value="Senki sem csatlakozott a játékhoz!", inline=False)

                await self.message.edit(embed=embed, view=self)
                if self.participants:
                    await self.message.channel.send(f"🎉 **A nyereményjáték véget ért!** A nyertes: {winner.mention if winner else 'Ismeretlen'}! Gratulálunk a(z) **{self.nyeremeny}** megnyeréséhez!")
            except Exception as e:
                print(f"Hiba a sorsoláskor: {e}")


# --- SLASH PARANCSOK (Globális) ---

@bot.tree.command(name="ticket", description="Hibajegy nyitó panel kiírása")
@app_commands.default_permissions(administrator=True)
async def ticket(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎟️ Hibajegy nyitása",
        description="Válassz indokot a segítségkéréshez!",
        color=discord.Color.blue()
    )
    await interaction.channel.send(embed=embed, view=TicketView())
    await interaction.response.send_message("A ticket panel sikeresen elküldve!", ephemeral=True)

@bot.tree.command(name="javaslat", description="Küldj be egy javaslatot a szerverre")
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

@bot.tree.command(name="nyeremenyjatek", description="Indíts nyereményjátékot időzítővel és sorsolással")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(nyeremeny="Mi a nyeremény?", ido="Mennyi ideig tartson (percben)?")
async def nyeremenyjatek(interaction: discord.Interaction, nyeremeny: str, ido: int):
    embed = discord.Embed(
        title="🎁 Új Nyereményjáték!",
        description=(
            f"**Nyeremény:** {nyeremeny}\n"
            f"⏳ **Időtartam:** {ido} perc\n\n"
            "Kattints az alábbi gombra a jelentkezéshez!"
        ),
        color=discord.Color.purple()
    )
    embed.set_footer(text=f"Szervező: {interaction.user.name}")

    view = GiveAwayView(nyeremeny=nyeremeny, organizer=interaction.user.name, duration_minutes=ido)
    
    await interaction.response.send_message("Nyereményjáték elindítva!", ephemeral=True)
    message = await interaction.channel.send(embed=embed, view=view)
    view.message = message

# -----------------------------------------------

token = os.getenv('DISCORD_TOKEN')
bot.run(token)
