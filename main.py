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
ROSTER_EXPORT_URL = 'https://docs.google.com/spreadsheets/d/1WaUQF1mMBxno5zuyMuP6OB_7JvXnLT3s3epBoTI5dRw/export?format=txt'

KNOWLEDGE_REFRESH_SECONDS = int(os.getenv('SOP_REFRESH_SECONDS', '900'))  # default 15 minutes

# Bot state management
active_channels = set()

# In-memory knowledge base cache
_fire_sop_cache: str = ''
_ems_sop_cache: str = ''
_roster_cache: str = ''
_last_fetch_ok: bool = False

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
        print(f'Fetch exception {url}: {str(e)}')
        return None

async def fetch_knowledge_base():
    """Fetch Fire SOP, EMS SOP, and roster data."""
    global _fire_sop_cache, _ems_sop_cache, _roster_cache, _last_fetch_ok
    async with aiohttp.ClientSession() as session:
        fire_text, ems_text, roster_text = await asyncio.gather(
            fetch_url_text(session, FIRE_SOP_EXPORT_URL),
            fetch_url_text(session, EMS_SOP_EXPORT_URL),
            fetch_url_text(session, ROSTER_EXPORT_URL),
            return_exceptions=True
        )
        if fire_text and ems_text and roster_text:
            _fire_sop_cache = fire_text
            _ems_sop_cache = ems_text
            _roster_cache = roster_text
            _last_fetch_ok = True
            print('Knowledge base refresh complete (SOPs + Roster).')
        else:
            _last_fetch_ok = False
            print('Knowledge base refresh incomplete.')

async def periodic_knowledge_refresh():
    """Periodically refresh knowledge base."""
    await bot.wait_until_ready()
    while not bot.is_closed():
        await fetch_knowledge_base()
        await asyncio.sleep(KNOWLEDGE_REFRESH_SECONDS)

def build_knowledge_context() -> Tuple[str, str]:
    """
    Returns (context_text, source_links).
    Context includes SOPs and roster info.
    """
    if not _last_fetch_ok:
        return (
            'Knowledge base not available. Please try again later.',
            'Sources temporarily unavailable.'
        )
    context = (
        f"=== Fire SOP ===\n{_fire_sop_cache[:8000]}\n\n"
        f"=== EMS SOP ===\n{_ems_sop_cache[:8000]}\n\n"
        f"=== EMS/Fire Roster ===\n{_roster_cache[:4000]}\n\n"
    )
    sources = (
        f"📋 Knowledge Sources:\n"
        f"• Fire SOP: {FIRE_SOP_VIEW_URL}\n"
        f"• EMS SOP: {EMS_SOP_VIEW_URL}\n"
        f"• Roster: {ROSTER_VIEW_URL}"
    )
    return (context, sources)

async def send_chunked_reply(message: discord.Message, text: str):
    """Send text as multiple messages if needed."""
    chunks = chunk_message(text)
    for chunk in chunks:
        await message.reply(chunk)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    await fetch_knowledge_base()
    bot.loop.create_task(periodic_knowledge_refresh())

@bot.command(name='activate')
async def activate_channel(ctx):
    """Activate the assistant in this channel."""
    active_channels.add(ctx.channel.id)
    await ctx.send('🚒 LSFD Assistant activated in this channel!')

@bot.command(name='deactivate')
async def deactivate_channel(ctx):
    """Deactivate the assistant in this channel."""
    active_channels.discard(ctx.channel.id)
    await ctx.send('🚒 LSFD Assistant deactivated in this channel.')

@bot.command(name='sources')
async def show_sources(ctx):
    """Show knowledge base sources."""
    _, sources = build_knowledge_context()
    await ctx.send(sources)

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    await bot.process_commands(message)
    if message.channel.id in active_channels and not message.content.startswith('/'):
        if not PERPLEXITY_API_KEY:
            await message.reply('⚠️ Perplexity API key not configured.')
            return
        async with message.channel.typing():
            context, sources = build_knowledge_context()
            enhanced_query = (
                f"{context}\n\n"
                f"User Question (FiveM RP context): {message.content}\n\n"
                f"Answer naturally and helpfully based on the knowledge above."
            )
            response = await query_perplexity_knowledge(enhanced_query)
            if response:
                await send_chunked_reply(message, response)
            else:
                await message.reply('⚠️ Unable to process your query at the moment. Please try again.')

async def query_perplexity_knowledge(query: str) -> Optional[str]:
    if not PERPLEXITY_API_KEY:
        return '⚠️ Perplexity API key not configured.'
    url = 'https://api.perplexity.ai/chat/completions'
    headers = {
        'Authorization': f'Bearer {PERPLEXITY_API_KEY}',
        'Content-Type': 'application/json'
    }
    system_content = (
        'You are the LSFD Assistant, a helpful and knowledgeable first responder assistant for FiveM roleplay. '
        'You have access to Fire SOPs, EMS SOPs, and the department roster. '
        'Speak naturally and conversationally—be friendly, supportive, and approachable, like a helpful colleague. '
        'Draw upon all your knowledge (SOPs and roster) when relevant, but don\'t focus excessively on procedures—provide comprehensive, practical assistance. '
        'Focus on FiveM RP context by default. Only mention real-life comparisons if explicitly asked or clearly needed for safety, and keep it brief. '
        'Use natural, flowing paragraphs—avoid bullet points, numbered lists, or overly formal structures unless specifically appropriate. '
        'Only use information from the provided knowledge base. If something isn\'t there, say you can\'t confirm it. '
        'Never mention who created you or where your knowledge comes from unless directly asked. '
        'Never mention you are an AI or language model.'
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
                    # Simple branding
                    content = f"🚒 **LSFD Assistant**\n{content}"
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
        print(f'ERROR: {discord_token_env} environment variable not set!')
        exit(1)
    print('Starting Los Santos Fire Department Assistant (LSFD Assistant)...')
    bot.run(DISCORD_TOKEN)
