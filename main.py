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

@bot.tree.command(name='activate', description='Activate the LSFD Assistant bot for fire, EMS, and rescue support in this channel')
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
            '⚠️ LSFD Assistant is already active in this channel.',
            ephemeral=True
        )
        return
    
    active_channels.add(channel_id)
    
    await interaction.response.send_message(
        f'✅ **Los Santos Fire Department Assistant Activated!**\n'
        f'🚒 I\'m now monitoring <#{channel_id}> for queries about fire SOPs, EMS procedures, water rescue, and emergency operations.\n'
        f'💡 Ask me anything about LSFD standard operating procedures, emergency response protocols, or safety guidelines!',
        ephemeral=False
    )
    
    print(f'LSFD Assistant activated in channel {channel_id} by {interaction.user}')

@bot.tree.command(name='deactivate', description='Deactivate the LSFD Assistant bot in this channel')
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
            '⚠️ LSFD Assistant is not active in this channel.',
            ephemeral=True
        )
        return
    
    active_channels.remove(channel_id)
    
    await interaction.response.send_message(
        f'✅ **LSFD Assistant Deactivated**\n'
        f'The bot will no longer respond to messages in <#{channel_id}>.',
        ephemeral=False
    )
    
    print(f'LSFD Assistant deactivated in channel {channel_id} by {interaction.user}')

@bot.tree.command(name='help', description='Get information about LSFD Assistant commands and capabilities')
async def help_command(interaction: discord.Interaction):
    """Display help information about the LSFD Assistant"""
    
    help_text = (
        '🚒 **Los Santos Fire Department Assistant (LSFD Assistant)**\n\n'
        '**Available Commands:**\n'
        '• `/activate` - Activate the bot in this channel (requires Manage Channels permission)\n'
        '• `/deactivate` - Deactivate the bot in this channel (requires Manage Channels permission)\n'
        '• `/help` - Show this help message\n\n'
        '**Capabilities:**\n'
        '🔥 Fire SOPs and firefighting procedures\n'
        '🚑 EMS protocols and medical emergency response\n'
        '🌊 Water rescue operations and safety\n'
        '⚠️ Emergency response procedures\n'
        '📋 Standard operating procedures for LSFD\n\n'
        '**How to Use:**\n'
        '1. Activate the bot in a channel using `/activate`\n'
        '2. Mention the bot or use keywords like "fire", "ems", "rescue", "emergency", "medical", "safety"\n'
        '3. Ask your question about LSFD procedures, protocols, or operations\n\n'
        '**Example Questions:**\n'
        '• "What are the fire safety protocols for structure fires?"\n'
        '• "How do I perform CPR during a cardiac emergency?"\n'
        '• "What are the water rescue procedures for swift water?"\n'
        '• "What\'s the protocol for hazmat incidents?"\n'
    )
    
    await interaction.response.send_message(help_text, ephemeral=True)

@bot.event
async def on_message(message):
    # Ignore bot's own messages
    if message.author == bot.user:
        return
    
    # Only respond in active channels
    if message.channel.id not in active_channels:
        return
    
    # Check if bot is mentioned or message contains relevant keywords
    keywords = ['rescue', 'emergency', 'drowning', 'water', 'safety', 'help', 'fire', 'ems', 'medical', 'sop', 'protocol', 'hazmat', 'firefighter', 'paramedic', 'incident']
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
    """Query Perplexity API for intelligent responses about LSFD operations"""
    
    if not PERPLEXITY_API_KEY:
        return '⚠️ Perplexity API key not configured.'
    
    url = 'https://api.perplexity.ai/chat/completions'
    headers = {
        'Authorization': f'Bearer {PERPLEXITY_API_KEY}',
        'Content-Type': 'application/json'
    }
    
    # Enhanced system prompt with LSFD context
    system_content = (
        'You are the Los Santos Fire Department Assistant (LSFD Assistant), an expert AI assistant '
        'providing guidance on fire department standard operating procedures (SOPs), emergency medical services (EMS), '
        'and rescue operations. Your expertise covers:\n'
        '- Fire suppression tactics and firefighting SOPs\n'
        '- EMS protocols and medical emergency procedures\n'
        '- Water rescue operations and swift water safety\n'
        '- Technical rescue (confined space, high angle, collapse)\n'
        '- Hazardous materials (HAZMAT) response\n'
        '- Vehicle extrication and traffic incident management\n'
        '- Fire prevention, safety inspections, and public education\n\n'
        'Provide concise, accurate information following standard fire service and EMS best practices. '
        'Always prioritize safety and recommend calling emergency services (911) for immediate life-threatening emergencies. '
        'Reference standard operating procedures, NFPA standards, and established protocols when applicable.'
    )
    
    payload = {
        'model': 'sonar',
        'messages': [
            {
                'role': 'system',
                'content': system_content
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
