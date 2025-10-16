import os
import asyncio
import aiohttp
import discord
from discord.ext import commands
from typing import Optional, List, Tuple

# Bot configuration
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
bot = commands.Bot(command_prefix='/', intents=intents)

# Environment variables
DISCORD_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
PERPLEXITY_API_KEY = os.getenv('PERPLEXITY_API_KEY')
# Authoritative SOP source URLs
FIRE_SOP_VIEW_URL = 'https://docs.google.com/document/d/1PNfx8IKvyLX1mqb-wJWcw_JGH2sJzOAPFGk0XmecJBc/edit?tab=t.1vnx26sszwbz'
EMS_SOP_VIEW_URL = 'https://docs.google.com/document/d/1PNfx8IKvyLX1mqb-wJWcw_JGH2sJzOAPFGk0XmecJBc/edit?tab=t.0'
# Export URLs (txt) for reliable fetching
FIRE_SOP_EXPORT_URL = 'https://docs.google.com/document/d/1PNfx8IKvyLX1mqb-wJWcw_JGH2sJzOAPFGk0XmecJBc/export?format=txt'
EMS_SOP_EXPORT_URL = 'https://docs.google.com/document/d/1PNfx8IKvyLX1mqb-wJWcw_JGH2sJzOAPFGk0XmecJBc/export?format=txt'
SOP_REFRESH_SECONDS = int(os.getenv('SOP_REFRESH_SECONDS', '900'))  # default 15 minutes

# Bot state management
active_channels = set()

# In-memory SOP cache
_fire_sop_cache: str = ''
_ems_sop_cache: str = ''
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
        window = remaining[:limit]
        split_idx = -1
        for sep in sep_candidates:
            idx = window.rfind(sep)
            if idx != -1 and idx > split_idx:
                split_idx = idx + len(sep)
        if split_idx == -1 or split_idx == 0:
            split_idx = limit
        chunks.append(remaining[:split_idx])
        remaining = remaining[split_idx:]
    return chunks


async def fetch_url_text(session: aiohttp.ClientSession, url: str) -> Optional[str]:
    try:
        async with session.get(url, timeout=30) as resp:
            if resp.status == 200:
                return await resp.text()
            else:
                print(f'Fetch failed {url}: {resp.status} {await resp.text()}')
                return None
    except Exception as e:
        print(f'Fetch exception {url}: {e}')
        return None


async def refresh_sop_cache_periodically():
    global _fire_sop_cache, _ems_sop_cache, _last_sop_fetch_ok
    await bot.wait_until_ready()
    while not bot.is_closed():
        try:
            async with aiohttp.ClientSession() as session:
                fire = await fetch_url_text(session, FIRE_SOP_EXPORT_URL)
                ems = await fetch_url_text(session, EMS_SOP_EXPORT_URL)
                ok = False
                if fire and fire.strip():
                    _fire_sop_cache = fire.strip()
                    ok = True
                if ems and ems.strip():
                    _ems_sop_cache = ems.strip()
                    ok = True or ok
                _last_sop_fetch_ok = ok
                print(f'Refreshed SOP caches. Fire={len(_fire_sop_cache)} chars, EMS={len(_ems_sop_cache)} chars')
        except Exception as e:
            _last_sop_fetch_ok = False
            print(f'SOP periodic refresh error: {e}')
        await asyncio.sleep(max(60, SOP_REFRESH_SECONDS))


def build_sop_context() -> Tuple[str, str]:
    """Return combined authoritative SOP context string and a brief provenance footer."""
    header = (
        "You provide guidance based strictly on the Los Santos Fire Department SOPs.\n"
        "Always prioritize safety and advise calling 911 for real emergencies.\n"
        "Use only the Fire SOP and EMS SOP text below as authoritative sources.\n"
    )
    fire = _fire_sop_cache or ''
    ems = _ems_sop_cache or ''
    combined = f"{header}\nFIRE SOP (authoritative):\n\n{fire}\n\nEMS SOP (authoritative):\n\n{ems}"
    provenance = (
        f"Sources: Fire SOP {FIRE_SOP_VIEW_URL} | EMS SOP {EMS_SOP_VIEW_URL}"
    )
    return combined, provenance


@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is in {len(bot.guilds)} guilds')
    await bot.tree.sync()
    print('Slash commands synced')
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
    chunks = chunk_message(content, 2000)
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
        sop_context, provenance = build_sop_context()
        enhanced_query = f"{sop_context}\n\nUser Question: {question}\n\nRemember to base your answer strictly on the SOP text above."
        response = await query_perplexity_sop(enhanced_query, provenance)
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
            sop_context, provenance = build_sop_context()
            enhanced_query = f"{sop_context}\n\nUser Question: {message.content}\n\nRemember to base your answer strictly on the SOP text above."
            response = await query_perplexity_sop(enhanced_query, provenance)
            if response:
                await send_chunked_reply(message, response)
            else:
                await message.reply('⚠️ Unable to process your query at the moment. Please try again.')


async def query_perplexity_sop(query: str, provenance: str) -> Optional[str]:
    if not PERPLEXITY_API_KEY:
        return '⚠️ Perplexity API key not configured.'
    url = 'https://api.perplexity.ai/chat/completions'
    headers = {
        'Authorization': f'Bearer {PERPLEXITY_API_KEY}',
        'Content-Type': 'application/json'
    }
    system_content = (
        'You are a seasoned first responder providing guidance based solely on the authoritative Fire and EMS SOP excerpts provided in the user message. '
        'Talk like a normal person having a conversation, not like a textbook or manual. '
        'Do NOT use bullet points, numbered lists, or dictionary-style formatting. '
        'Do NOT structure responses with sections, headers, or formatted lists. '
        'Write in short, flowing paragraphs using natural, conversational language as if you\'re explaining this to a colleague. '
        'Only use information present in the provided SOP context; if something is not in the SOPs, say you cannot confirm it. '
        'Respond in a helpful, human, and supportive tone. '
        'Do NOT mention you are an AI or language model. '
        'Always prioritize safety and recommend calling 911 for actual emergencies.'
    )
    payload = {
        'model': 'sonar',
        'messages': [
            {'role': 'system', 'content': system_content},
            {'role': 'user', 'content': query}
        ],
        'max_tokens': 800,
        'temperature': 0.6
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers, timeout=30) as response:
                if response.status == 200:
                    data = await response.json()
                    content = data['choices'][0]['message']['content']
                    # Append provenance links subtly so users can verify
                    content = f"🚒 **LSFD Assistant**\n{content}\n\n(Reference: {provenance})"
                    return content
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
