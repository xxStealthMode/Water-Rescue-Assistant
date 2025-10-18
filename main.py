import os
import json
import asyncio
import aiohttp
import discord
from discord.ext import commands
from typing import Optional, List, Tuple, Dict

# Bot configuration
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True  # needed for member join/leave events

bot = commands.Bot(command_prefix='/', intents=intents)

# Environment variables
discord_token_env = 'DISCORD_BOT_TOKEN'
DISCORD_TOKEN = os.getenv(discord_token_env)
PERPLEXITY_API_KEY = os.getenv('PERPLEXITY_API_KEY')

# Knowledge base source URLs
FIRE_SOP_VIEW_URL = 'https://docs.google.com/document/d/1PNfx8IKvyLX1mqb-wJWcw_JGH2sJzOAPFGk0XmecJBc/edit?tab=t.1vnx26sszwbz'
EMS_SOP_VIEW_URL = 'https://docs.google.com/document/d/1PNfx8IKvyLX1mqb-wJWcw_JGH2sJzOAPFGk0XmecJBc/edit?tab=t.0'
ROSTER_VIEW_URL = 'https://docs.google.com/spreadsheets/d/1WaUQF1mMBxno5zuyMuP6OB_7JvXnLT3s3epBoTI5dRw/edit?gid=705786844#gid=705786844'

# Export URLs (txt) for reliable fetching
FIRE_SOP_EXPORT_URL = 'https://docs.google.com/document/d/1PNfx8IKvyLX1mqb-wJWcw_JGH2sJzOAPFGk0XmecJBc/export?format=txt'
EMS_SOP_EXPORT_URL = 'https://docs.google.com/document/d/1PNfx8IKvyLX1mqb-wJWcw_JGH2sJzOAPFGk0XmecJBc/export?format=txt'
ROSTER_EXPORT_URL = 'https://docs.google.com/spreadsheets/d/1WaUQF1mMBxno5zuyMuP6OB_7JvXnLT3s3epBoTI5dRw/export?format=csv&gid=705786844'

KNOWLEDGE_REFRESH_SECONDS = int(os.getenv('SOP_REFRESH_SECONDS', '900'))  # default 15 minutes

# Bot state management
active_channels = set()

# Welcome channel mapping per guild (in-memory) + basic file persistence
WELCOME_MAP_FILE = 'welcome_channels.json'
welcome_channels: Dict[int, int] = {}

def load_welcome_channels():
    global welcome_channels
    try:
        if os.path.exists(WELCOME_MAP_FILE):
            with open(WELCOME_MAP_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # keys saved as str -> convert back to int
                welcome_channels = {int(k): int(v) for k, v in data.items()}
        else:
            welcome_channels = {}
    except Exception as e:
        print(f'Failed to load {WELCOME_MAP_FILE}: {e}')
        welcome_channels = {}

def save_welcome_channels():
    try:
        with open(WELCOME_MAP_FILE, 'w', encoding='utf-8') as f:
            # convert keys to str for JSON compatibility
            json.dump({str(k): v for k, v in welcome_channels.items()}, f, indent=2)
    except Exception as e:
        print(f'Failed to save {WELCOME_MAP_FILE}: {e}')

# Knowledge base storage
knowledge_base = {
    'fire_sop': '',
    'ems_sop': '',
    'roster': ''
}

async def fetch_knowledge():
    """Fetch knowledge base docs from Google Docs/Sheets."""
    async with aiohttp.ClientSession() as session:
        tasks = [
            fetch_doc(session, 'fire_sop', FIRE_SOP_EXPORT_URL),
            fetch_doc(session, 'ems_sop', EMS_SOP_EXPORT_URL),
            fetch_doc(session, 'roster', ROSTER_EXPORT_URL)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success_count = sum(1 for r in results if not isinstance(r, Exception))
        if success_count < len(results):
            print(f'Knowledge base refresh incomplete: {success_count}/{len(results)} sources loaded')
        else:
            print('Knowledge base refreshed successfully')

async def fetch_doc(session, key, url):
    """Fetch a single document."""
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            if resp.status == 200:
                content = await resp.text()
                knowledge_base[key] = content
                print(f'Loaded {key} ({len(content)} chars)')
            else:
                print(f'Failed to fetch {key}: HTTP {resp.status}')
                raise Exception(f'HTTP {resp.status}')
    except Exception as e:
        print(f'Error fetching {key} from {url}: {e}')
        raise

async def refresh_knowledge_loop():
    """Background task to refresh knowledge base periodically."""
    await bot.wait_until_ready()
    while not bot.is_closed():
        await fetch_knowledge()
        await asyncio.sleep(KNOWLEDGE_REFRESH_SECONDS)

@bot.event
async def on_ready():
    print(f'Bot logged in as {bot.user}')
    load_welcome_channels()
    print(f'Loaded {len(welcome_channels)} welcome channel mappings')
    
    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        print(f'Synced {len(synced)} slash commands')
    except Exception as e:
        print(f'Failed to sync commands: {e}')
    
    # Initial knowledge fetch
    await fetch_knowledge()

@bot.event
async def on_member_join(member):
    """Send welcome message when a member joins."""
    guild_id = member.guild.id
    if guild_id in welcome_channels:
        channel_id = welcome_channels[guild_id]
        channel = bot.get_channel(channel_id)
        if channel:
            await channel.send(f'Welcome {member.mention} to {member.guild.name}!')

@bot.tree.command(name='ask', description='Ask a question about Fire/EMS SOPs or roster')
async def ask(interaction: discord.Interaction, question: str):
    """Answer questions using Perplexity API with knowledge base context."""
    await interaction.response.defer(thinking=True)
    
    # Build context from knowledge base
    context = f"""Fire SOP:
{knowledge_base['fire_sop'][:3000]}

EMS SOP:
{knowledge_base['ems_sop'][:3000]}

Roster:
{knowledge_base['roster'][:2000]}
"""
    
    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                'model': 'llama-3.1-sonar-large-128k-online',
                'messages': [
                    {'role': 'system', 'content': f'You are a helpful assistant. Use this knowledge base to answer questions:\n\n{context}'},
                    {'role': 'user', 'content': question}
                ]
            }
            
            headers = {
                'Authorization': f'Bearer {PERPLEXITY_API_KEY}',
                'Content-Type': 'application/json'
            }
            
            async with session.post('https://api.perplexity.ai/chat/completions', 
                                   json=payload, headers=headers, 
                                   timeout=aiohttp.ClientTimeout(total=60)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    answer = data['choices'][0]['message']['content']
                    
                    # Split long responses
                    if len(answer) > 2000:
                        chunks = [answer[i:i+2000] for i in range(0, len(answer), 2000)]
                        await interaction.followup.send(chunks[0])
                        for chunk in chunks[1:]:
                            await interaction.channel.send(chunk)
                    else:
                        await interaction.followup.send(answer)
                else:
                    error_text = await resp.text()
                    await interaction.followup.send(f'Error: API returned status {resp.status}\n{error_text[:500]}')
    except Exception as e:
        await interaction.followup.send(f'Error: {str(e)}')

@bot.tree.command(name='roster', description='View the current roster')
async def roster(interaction: discord.Interaction):
    """Display the roster link."""
    await interaction.response.send_message(
        f'View the roster here: {ROSTER_VIEW_URL}\n\nCached roster data ({len(knowledge_base["roster"])} chars)'
    )

@bot.tree.command(name='firesop', description='View Fire SOP document')
async def firesop(interaction: discord.Interaction):
    """Display the Fire SOP link."""
    await interaction.response.send_message(f'Fire SOP: {FIRE_SOP_VIEW_URL}')

@bot.tree.command(name='emssop', description='View EMS SOP document')
async def emssop(interaction: discord.Interaction):
    """Display the EMS SOP link."""
    await interaction.response.send_message(f'EMS SOP: {EMS_SOP_VIEW_URL}')

@bot.tree.command(name='welcomechannel', description='Set the channel for welcome messages')
@discord.app_commands.checks.has_permissions(administrator=True)
async def welcomechannel(interaction: discord.Interaction, channel: discord.TextChannel):
    """Set welcome channel for this server."""
    guild_id = interaction.guild.id
    welcome_channels[guild_id] = channel.id
    save_welcome_channels()
    await interaction.response.send_message(f'Welcome channel set to {channel.mention}')

@welcomechannel.error
async def welcomechannel_error(interaction: discord.Interaction, error):
    if isinstance(error, discord.app_commands.MissingPermissions):
        await interaction.response.send_message('You need Administrator permission to use this command.', ephemeral=True)

# Start the bot
if __name__ == '__main__':
    if not DISCORD_TOKEN:
        raise ValueError(f'Missing {discord_token_env} environment variable')
    if not PERPLEXITY_API_KEY:
        raise ValueError('Missing PERPLEXITY_API_KEY environment variable')
    
    # Start background task
    bot.loop.create_task(refresh_knowledge_loop())
    
    # Run the bot
    bot.run(DISCORD_TOKEN)
