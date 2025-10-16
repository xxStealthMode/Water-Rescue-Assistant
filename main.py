import os
import asyncio
import aiohttp
import discord
from discord.ext import commands
from typing import Optional, List

# Bot configuration
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
bot = commands.Bot(command_prefix='/', intents=intents)

# Environment variables
DISCORD_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
PERPLEXITY_API_KEY = os.getenv('PERPLEXITY_API_KEY')
SOP_DOC_URL = os.getenv('SOP_DOC_URL')  # Public Google Doc export URL (text/plain or HTML)
SOP_REFRESH_SECONDS = int(os.getenv('SOP_REFRESH_SECONDS', '900'))  # default 15 minutes

# Bot state management
active_channels = set()

# In-memory SOP cache
_sop_cache: str = ''
_last_sop_fetch_ok: bool = False

def chunk_message(text: str, limit: int = 2000) -> List[str]:
    """Split text into chunks <= limit, preferring to break on paragraph or line boundaries."""
    if text is None:
        return [""]
    if len(text) <= limit:
        return [text]
    chunks = []
    remaining = text
    sep_candidates = ['\n\n', '\n', '. ']
    while remaining:
        if len(remaining) <= limit:
            chunks.append(remaining)
            break
        # Take a window and try to split at a nice boundary
        window = remaining[:limit]
        split_idx = -1
        for sep in sep_candidates:
            idx = window.rfind(sep)
            if idx != -1 and idx > split_idx:
                split_idx = idx + len(sep)
        if split_idx == -1 or split_idx == 0:
            # No good split point found; hard cut
            split_idx = limit
        chunks.append(remaining[:split_idx])
        remaining = remaining[split_idx:]
    return chunks

async def fetch_sop_from_doc(session: aiohttp.ClientSession) -> Optional[str]:
    """Fetch latest SOP text from Google Doc or given URL.
    Expect SOP_DOC_URL to be an export URL such as:
    https://docs.google.com/document/d/<doc_id>/export?format=txt
    """
    url = SOP_DOC_URL
    if not url:
        return None
    try:
        async with session.get(url, timeout=30) as resp:
            if resp.status == 200:
                # Prefer plain text; if HTML, still return as-is (Perplexity can handle)
                return await resp.text()
            else:
                print(f'SOP fetch failed: {resp.status} {await resp.text()}')
                return None
    except Exception as e:
        print(f'SOP fetch exception: {e}')
        return None

async def refresh_sop_cache_periodically():
    global _sop_cache, _last_sop_fetch_ok
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            async with aiohttp.ClientSession() as session:
                latest = await fetch_sop_from_doc(session)
                if latest and latest.strip():
                    _sop_cache = latest.strip()
                    _last_sop_fetch_ok = True
                    print(f'Refreshed SOP cache ({len(_sop_cache)} chars)')
                else:
                    _last_sop_fetch_ok = False
                    print('SOP cache refresh skipped or failed (no content)')
        except Exception as e:
            _last_sop_fetch_ok = False
            print(f'SOP periodic refresh error: {e}')
        await asyncio.sleep(max(60, SOP_REFRESH_SECONDS))

def build_sop_context() -> str:
    """Compose the system/user preface for SOP answers, using cached SOP if present."""
    header = (
        "You are providing guidance based strictly on the Hollywood Hills EMS Standard Operating Procedures (S.O.P's).\n"
        "Always prioritize safety and recommend calling 911 for immediate life-threatening emergencies.\n"
    )
    if _sop_cache:
        return f"{header}\nSOP Document (latest fetched):\n\n{_sop_cache}"
    else:
        # Fallback minimal context if cache unavailable
        return header

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is in {len(bot.guilds)} guilds')
    await bot.tree.sync()
    print('Slash commands synced')
    # Start SOP refresher task
    bot.loop.create_task(refresh_sop_cache_periodically())

@bot.tree.command(name='activate', description='Activate the LSFD Assistant bot for fire, EMS, and rescue support in this channel')
async def activate(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.manage_channels:
        await interaction.response.send_message('❌ You need "Manage Channels" permission to activate the bot.', ephemeral=True)
        return
    channel_id = interaction.channel_id
    if channel_id in active_channels:
        await interaction.response.send_message('⚠️ LSFD Assistant is already active in this channel.', ephemeral=True)
        return
    active_channels.add(channel_id)
    await interaction.response.send_message(
        f'✅ **Los Santos Fire Department Assistant Activated!**\n'
        f'🚒 I\'m now monitoring <#{channel_id}> for SOP queries.',
        ephemeral=False
    )

@bot.tree.command(name='deactivate', description='Deactivate the LSFD Assistant bot in this channel')
async def deactivate(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.manage_channels:
        await interaction.response.send_message('❌ You need "Manage Channels" permission to deactivate the bot.', ephemeral=True)
        return
    channel_id = interaction.channel_id
    if channel_id not in active_channels:
        await interaction.response.send_message('⚠️ LSFD Assistant is not active in this channel.', ephemeral=True)
        return
    active_channels.remove(channel_id)
    await interaction.response.send_message(
        f'✅ **LSFD Assistant Deactivated**\nThe bot will no longer respond in <#{channel_id}>.',
        ephemeral=False
    )

async def send_chunked_followup(interaction: discord.Interaction, content: str):
    """Send content in <=2000 char chunks via followup messages."""
    chunks = chunk_message(content, 2000)
    # Send first chunk normally; subsequent chunks chained
    for i, c in enumerate(chunks):
        if i == 0 and interaction.response.is_done():
            await interaction.followup.send(c)
        elif i == 0:
            await interaction.response.send_message(c)
        else:
            await interaction.followup.send(c)

async def send_chunked_reply(message: discord.Message, content: str):
    chunks = chunk_message(content, 2000)
    for i, c in enumerate(chunks):
        if i == 0:
            await message.reply(c)
        else:
            await message.channel.send(c, reference=message.to_reference(fail_if_not_exists=False))

@bot.tree.command(name='sop', description='Ask any question about EMS, fire, rescue, or operational procedures')
async def sop(interaction: discord.Interaction, question: str):
    await interaction.response.defer()
    try:
        # Build context dynamically from latest SOP cache
        context = build_sop_context()
        enhanced_query = f"{context}\n\nUser Question: {question}"
        response = await query_perplexity_sop(enhanced_query)
        if response:
            await send_chunked_followup(interaction, response)
        else:
            await interaction.followup.send('⚠️ Unable to process your query at the moment. Please try again.')
    except Exception as e:
        print(f'Error in /sop command: {str(e)}')
        await interaction.followup.send('⚠️ An error occurred while processing your question. Please try again.')

@bot.tree.command(name='help', description='Get information about LSFD Assistant commands and capabilities')
async def help_command(interaction: discord.Interaction):
    help_text = (
        '🚒 **Los Santos Fire Department Assistant (LSFD Assistant)**\n\n'
        '• `/activate` - Activate in this channel (Manage Channels required)\n'
        '• `/deactivate` - Deactivate in this channel (Manage Channels required)\n'
        '• `/sop <question>` - Ask any question about procedures\n'
    )
    await interaction.response.send_message(help_text, ephemeral=True)

@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user:
        return
    if message.channel.id not in active_channels:
        return
    keywords = ['rescue', 'emergency', 'drowning', 'water', 'safety', 'help', 'fire', 'ems', 'medical', 'sop', 'protocol', 'hazmat', 'firefighter', 'paramedic', 'incident']
    is_mentioned = bot.user in message.mentions
    has_keyword = any(keyword in message.content.lower() for keyword in keywords)
    if is_mentioned or has_keyword:
        async with message.channel.typing():
            context = build_sop_context()
            enhanced_query = f"{context}\n\nUser Question: {message.content}"
            response = await query_perplexity_sop(enhanced_query)
            if response:
                await send_chunked_reply(message, response)
            else:
                await message.reply('⚠️ Unable to process your query at the moment. Please try again.')

async def query_perplexity_sop(query: str) -> Optional[str]:
    if not PERPLEXITY_API_KEY:
        return '⚠️ Perplexity API key not configured.'
    url = 'https://api.perplexity.ai/chat/completions'
    headers = {
        'Authorization': f'Bearer {PERPLEXITY_API_KEY}',
        'Content-Type': 'application/json'
    }
    system_content = (
        'You are a helpful, experienced first responder providing guidance on emergency procedures. '
        'Talk like a normal person having a conversation, not like a textbook or manual. '
        'Do NOT use bullet points, numbered lists, or dictionary-style formatting. '
        'Do NOT structure your responses with sections, headers, or formatted lists. '
        'Instead, write in flowing paragraphs using natural, conversational language as if you\'re explaining something to a colleague over coffee. '
        'Respond in a helpful, human, and emotionally supportive tone. '
        'Do NOT mention you are an AI or language model. '
        'Answer questions based strictly on the provided SOP context. '
        'Show empathy and understanding while providing clear, accurate procedural information in a natural speaking style. '
        'Always prioritize safety and recommend calling 911 for actual emergencies.'
    )
    payload = {
        'model': 'sonar',
        'messages': [
            {'role': 'system', 'content': system_content},
            {'role': 'user', 'content': query}
        ],
        'max_tokens': 800,
        'temperature': 0.8
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers, timeout=30) as response:
                if response.status == 200:
                    data = await response.json()
                    return f"🚒 **LSFD Assistant**\n{data['choices'][0]['message']['content']}"
                else:
                    error_text = await response.text()
                    print(f'Perplexity API error: {response.status} - {error_text}')
                    return None
    except asyncio.TimeoutError:
        print('Perplexity API timeout')
        return None
    except Exception as e:
        print(f'Perplexity API exception: {str(e)}')
        return None

if __name__ == '__main__':
    if not DISCORD_TOKEN:
        print('ERROR: DISCORD_BOT_TOKEN environment variable not set!')
        exit(1)
    print('Starting Los Santos Fire Department Assistant (LSFD Assistant)...')
    bot.run(DISCORD_TOKEN)
