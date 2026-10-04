import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import discord

# 1. Mini webszerver, hogy a Render Web Service ne lője le a botot
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

# Szerver indítása külön szálon
server_thread = threading.Thread(target=run_server)
server_thread.daemon = True
server_thread.start()

# 2. Discord bot indítása
intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'Sikeres bejelentkezés mint: {client.user}')

token = os.getenv('DISCORD_TOKEN')
client.run(token)
