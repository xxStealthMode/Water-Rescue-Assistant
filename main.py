import discord
from discord.ext import commands
import os
import aiohttp
import asyncio

# Bot configuration
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
bot = commands.Bot(command_prefix='/', intents=intents)

# Environment variables
DISCORD_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
PERPLEXITY_API_KEY = os.getenv('PERPLEXITY_API_KEY')

# Bot state management
active_channels = set()

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is in {len(bot.guilds)} guilds')
    await bot.tree.sync()
    print('Slash commands synced')

@bot.tree.command(name='activate', description='Activate the Water Rescue Assistant bot in this channel')
async def activate(interaction: discord.Interaction):
    """Activate the bot in the current channel with permission checks"""
    
    # Check if user has manage_channels permission
    if not interaction.user.guild_permissions.manage_channels:
        await interaction.response.send_message(
            '❌ You need "Manage Channels" permission to activate the bot.',
            ephemeral=True
        )
        return
    
    channel_id = interaction.channel_id
    
    if channel_id in active_channels:
        await interaction.response.send_message(
            '⚠️ Water Rescue Assistant is already active in this channel.',
            ephemeral=True
        )
        return
    
    active_channels.add(channel_id)
    await interaction.response.send_message(
        f'✅ **Water Rescue Assistant Activated!**\n'
        f'🌊 I\'m now monitoring <#{channel_id}> for water rescue queries.\n'
        f'💡 Ask me anything about water safety, rescue operations, or emergency procedures!',
        ephemeral=False
    )
    print(f'Bot activated in channel {channel_id} by {interaction.user}')

@bot.tree.command(name='deactivate', description='Deactivate the Water Rescue Assistant bot in this channel')
async def deactivate(interaction: discord.Interaction):
    """Deactivate the bot in the current channel with permission checks"""
    
    # Check if user has manage_channels permission
    if not interaction.user.guild_permissions.manage_channels:
        await interaction.response.send_message(
            '❌ You need "Manage Channels" permission to deactivate the bot.',
            ephemeral=True
        )
        return
    
    channel_id = interaction.channel_id
    
    if channel_id not in active_channels:
        await interaction.response.send_message(
            '⚠️ Water Rescue Assistant is not active in this channel.',
            ephemeral=True
        )
        return
    
    active_channels.remove(channel_id)
    await interaction.response.send_message(
        f'🛑 **Water Rescue Assistant Deactivated!**\n'
        f'The bot is no longer monitoring <#{channel_id}>.',
        ephemeral=False
    )
    print(f'Bot deactivated in channel {channel_id} by {interaction.user}')

@bot.event
async def on_message(message):
    """Handle messages in active channels with Perplexity integration"""
    
    # Ignore bot's own messages
    if message.author == bot.user:
        return
    
    # Only respond in active channels
    if message.channel.id not in active_channels:
        return
    
    # Skip if message is a command
    if message.content.startswith('/'):
        await bot.process_commands(message)
        return
    
    # Check if bot is mentioned or message contains water rescue keywords
    keywords = ['rescue', 'emergency', 'drowning', 'water', 'safety', 'help']
    is_mentioned = bot.user in message.mentions
    has_keyword = any(keyword in message.content.lower() for keyword in keywords)
    
    if is_mentioned or has_keyword:
        async with message.channel.typing():
            response = await query_perplexity(message.content)
            if response:
                await message.reply(response)
            else:
                await message.reply('⚠️ Unable to process your query at the moment. Please try again.')

async def query_perplexity(query: str) -> str:
    """Query Perplexity API for intelligent responses"""
    
    if not PERPLEXITY_API_KEY:
        return '⚠️ Perplexity API key not configured.'
    
    url = 'https://api.perplexity.ai/chat/completions'
    headers = {
        'Authorization': f'Bearer {PERPLEXITY_API_KEY}',
        'Content-Type': 'application/json'
    }
    
    payload = {
        'model': 'llama-3.1-sonar-small-128k-online',
        'messages': [
            {
                'role': 'system',
                'content': 'You are a Water Rescue Assistant. Provide concise, accurate information about water safety, rescue operations, emergency procedures, and drowning prevention. Always prioritize safety and recommend calling emergency services (911) for immediate emergencies.'
            },
            {
                'role': 'user',
                'content': query
            }
        ],
        'max_tokens': 500,
        'temperature': 0.7
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers, timeout=30) as response:
                if response.status == 200:
                    data = await response.json()
                    return f"🌊 **Water Rescue Assistant**\n{data['choices'][0]['message']['content']}"
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
    
    print('Starting Water Rescue Assistant bot...')
    bot.run(DISCORD_TOKEN)
