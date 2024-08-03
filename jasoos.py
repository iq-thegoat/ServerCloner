import discord
from discord.ext import commands
from db.db import BotDb,DbStruct  # Assuming BotDb is a class to manage the database
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv
import loguru
import os
import json
from loguru import logger
import sys 
logger.add("logs.log")
load_dotenv()
import requests
import asyncio
import pickle
import string
from discord_webhook import DiscordWebhook, DiscordEmbed


cloned_list = [] #list of servers
session = BotDb().session
CACHE_FILE = "webhooks_cache.pkl"

# Load cache from file
def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'rb') as file:
            return pickle.load(file)
    return {}

# Save cache to file
def save_cache():
    with open(CACHE_FILE, 'wb') as file:
        pickle.dump(webhooks_dict, file)


webhooks_dict= load_cache()

def rgb_to_hex(rgb):
    return '#%02x%02x%02x' % rgb

bot = discord.Client(command_prefix='selfbotdude', self_bot=True)
db = BotDb().session  # Initialize your database connection

token = os.environ.get("self_bot_token")
async def create_roles(guild:discord.Guild,clone_guild:discord.Guild):
    for role in guild.roles:
        try:
            if role.name in [x.name for x in clone_guild.roles]:
                pass
            else:
                new_role = await clone_guild.create_role(name=role.name,color=role.color,permissions=role.permissions,display_icon=role.display_icon,mentionable=role.mentionable)
        except Exception as e:
            logger.error(e)

async def create_categories(guild,server_dict={}):
        try:
            clone_guild = discord.utils.get(bot.guilds,name=get_new_guild_name(guild.name))
            print(clone_guild)
        except:
            return {"Categories"}
        cats = {} # Original Category: Clone Category
        for category in guild.categories:
            if category.name not in [x.name for x in clone_guild.categories]:
                new_cat:discord.CategoryChannel = await clone_guild.create_category(name=category.name)
                if new_cat:
                    cats[category] = new_cat
                else:
                    cats[category] = None
        
        server_dict["Categories"] = cats
        return server_dict

async def create_channels(guild:discord.Guild,server_dict={}):
    try:
            clone_guild = discord.utils.get(bot.guilds,name=get_new_guild_name(guild.name))
    except:
            return {}
    channels_dict = {}
    cats = server_dict["Categories"]
    print(cats)
    channels_temp = [x.channels for x in list(cats.keys())]
    channels = []
    for l in channels_temp:
        channels.extend(l)

    print(channels)
    for channel in channels:
        print(type(channel))
        if type(channel) == discord.TextChannel:
            is_news = channel.is_news()
            is_nswf = channel.is_nsfw()
            chan = await clone_guild.create_text_channel(name=channel.name,category=cats[channel.category],news=is_news,topic=channel.topic,nsfw=is_nswf)
            channels_dict[channel]=chan

        elif type(channel) == discord.VoiceChannel:
            channel:discord.VoiceChannel
            chan = await clone_guild.create_voice_channel(name=channel.name,category=cats[channel.category],user_limit=channel.user_limit,rtc_region=channel.rtc_region,video_quality_mode=channel.video_quality_mode,bitrate=channel.bitrate)
            channels_dict[channel]=chan

        elif type(channel) == discord.StageChannel:
            channel:discord.StageChannel
            chan = await clone_guild.create_stage_channel(name=channel.name,category=cats[channel.category],user_limit=channel.user_limit,rtc_region=channel.rtc_region,video_quality_mode=channel.video_quality_mode,bitrate=channel.bitrate) 
            channels_dict[channel]=chan
        elif type(channel) == discord.ForumChannel:
            channel:discord.ForumChannel
            chan = await clone_guild.create_forum(name=channel.name,category=cats[channel.category],default_sort_order=channel.default_sort_order,default_reaction_emoji=channel.default_reaction_emoji,default_layout=channel.default_layout,available_tags=channel.available_tags)
            channels_dict[channel]=chan
        else:
            continue
        
    server_dict["Channels"] = channels


def is_messaage_in_db(messasge_id:int):
    x = db.query(DbStruct.messages).filter(DbStruct.messages.message_id == int(messasge_id)).first()
    return bool(x) #True if OBJECT False if None 

def get_new_guild_name(guild_name):
    return str(guild_name)+f"_clone"

@bot.event
async def on_ready():
    print(bot.user.name)
    guilds_to_create = []
    for guild in bot.guilds:
        if get_new_guild_name(guild_name=guild.name) in bot.guilds or "_clone" in guild.name:
            pass 
        else:
            guilds_to_create.append((get_new_guild_name(guild_name=guild.name),guild)) # (NAME,GUILD OBJECT)
    for guild in guilds_to_create:
        guild:discord.Guild = guild
        obj:discord.Guild = guild[1]
        
        clone_guild = discord.utils.get(bot.guilds,name=get_new_guild_name(guild_name=obj.name))
        if len(sys.argv) > 2 and sys.argv[1] == "clean" and int(sys.argv[2]) == int(clone_guild.id):
            for channel in clone_guild.channels:
                    await channel.delete()   
            for role in clone_guild.roles:
                try:
                    await role.delete()
                except:
                    continue
        elif len(sys.argv) > 2  and sys.argv[1] == "clear" and int(sys.argv[2]) == int(clone_guild.id):
            for channel in clone_guild.channels:
                if type(channel) != discord.CategoryChannel:
                    async for message in channel.history(limit=500):
                        await message.delete()


        await create_roles(guild=obj,clone_guild=clone_guild)
        cats = await create_categories(guild=obj,server_dict={})
        chans = await create_channels(guild=obj,server_dict=cats)
        webhooks_dict  = await webhook_manage(clone_guild)
        #await scrape_old() 

    print("Bot is ready")


def webhook_from_url(webhook_url,thread_id=None):
    if not thread_id:
        return DiscordWebhook(url=webhook_url)
    else:
        return DiscordWebhook(url=webhook_url,thread_id=str(thread_id))

def webhook_add_embeds(webhook:DiscordWebhook,embeds:list[discord.Embed]):

    for embed in embeds:
        try:
            '''
            embed_clone = DiscordEmbed(title=embed.title,description=embed.description,color="363636")
            embed_clone.description = embed.description
            embed_clone.set_author(name=embed.author.name,icon_url=embed.author.icon_url)
            embed_clone.set_image(url=embed.image.url)
            embed_clone.set_thumbnail(url=embed.thumbnail.url)
            embed_clone.set_footer(text=embed.footer.text,icon_url=embed.footer.icon_url)
            for field in embed.fields:
                embed_clone.add_embed_field(name=field.name,value=field.value)
            webhook.add_embed(embed_clone)
            '''
            webhook.add_embed(embed=embed.to_dict())
        except Exception as e:
            logger.error(f"Error in adding embed : Error -> {e} || Embed -> {str(embed)}")
    return webhook

def add_fake_avatar(webhook,username):
    seed = username if username else "UserCantGetAfuckingPfp"
    webhook.avatar_url = f"https://api.dicebear.com/9.x/glass/png?seed={seed}"
    return webhook

async def webhok_add_content(webhook:DiscordWebhook,username:str=None, content:str=".",embeds:list[discord.Embed]=None,files:list[discord.Attachment]=None,avatar_url:str=None):
    try:
        webhook.content = None
        webhook.avatar_url = None
        webhook.clear_attachments()
        webhook.remove_embeds()
        webhook.remove_files()
    except Exception as e:
        logger.error(e)

    if files:
        for file in files:
            try:
                bytes_obj = await file.read()
                webhook.add_file(file=bytes_obj,filename=file.filename)
            except Exception as e:
                logger.error(f"Erorr in adding file: Error -> {e} || File -> {str(file)}")
    if embeds:
       webhook =  webhook_add_embeds(webhook=webhook,embeds=embeds)

    if avatar_url:
        webhook.avatar_url = avatar_url
        print("WEBHOOK AVATAR -> "+webhook.avatar_url)
        if webhook.avatar_url:
            r = requests.get(webhook.avatar_url)
            if int(r.status_code) != 200:
                webhook  = add_fake_avatar(webhook=webhook,username=username)
        else:
            webhook  = add_fake_avatar(webhook=webhook,username=username)

        
    if username:
        webhook.username = str(username)
    else:
        webhook.username = "UnknownUserName"
    if content:
        webhook.content = content
        if not webhook.content:
            webhook.content = "."
    else:
        content = "."

    return webhook    
async def webhook_manage(guild: discord.Guild=None,channel=None): # TODO MAKE THIS CHECK FOR A SEPCIFIC CHANNEL
    async def check_for_channel(channel):
        if not isinstance(channel, discord.CategoryChannel):
                # Check if webhook ID is already cached
                try:
                    is_cached = webhooks_dict[channel.id]
                except:
                    is_cached = False
                    
                print(is_cached)
                if is_cached:
                    print(f"Using cached webhook for channel {channel.name}")
                else:
                    print(f"Fetching/Creating webhook for channel {channel.name}")
                    await asyncio.sleep(5)  # To avoid hitting rate limits
                    webhooks = await channel.webhooks()

                    if len(webhooks) > 0:
                        webhook = webhooks[0]
                        webhooks_dict[channel.id] = webhook.url  # Cache only the url
                        save_cache() 

                    else:
                        try:
                            webhook = await channel.create_webhook(name=channel.name + "_webhook")
                            webhooks_dict[channel.id] = webhook.url
                            save_cache() 

                            await asyncio.sleep(1.2)  # Avoid hitting rate limits
                        except Exception as e:
                            print(e)
    if not channel:
        for channel in guild.channels:
            try:
                await check_for_channel(channel=channel)
            except Exception as e:
                logger.error(f"Erorr in adding/checking webhook: Erorr -> {e} || Channel -> {str(channel.name)} | {str(channel.id)}")
            
    else:
        await check_for_channel(channel=channel)

    save_cache() 
    return load_cache()

async def send_message(message,delete_message=False):
    guild = message.guild
    channel = message.channel
    try:
            clone_guild = discord.utils.get(bot.guilds,name=get_new_guild_name(guild.name))
            clone_channel = discord.utils.get(clone_guild.channels,name=channel.name)

    except:
            return None

    if delete_message:
        async for message in clone_channel.history(limit=500):
            try:
                await message.delete()
            except:
                continue



    webhooks_dict = await webhook_manage(channel=clone_channel)
    channel_webhook = webhook_from_url(webhooks_dict[clone_channel.id])

    in_db  = session.query(DbStruct.messages).filter(DbStruct.messages.message_id==message.id).first()
    if not in_db:
        message:discord.Message
        content = message.content
        username = message.author.display_name
        avatar_url = message.author.avatar.url if message.author.avatar else None
        embeds = message.embeds
        files = message.attachments
        print(type(message))
        obj = DbStruct.messages(message_id=message.id)
        session.add(obj)
        session.commit()
        # Send the message
        channel_webhook = await webhok_add_content(webhook=channel_webhook,username=username,content=content,embeds=embeds,files=files,avatar_url=avatar_url)
        message2 = None
        channel_webhook.execute()
        await asyncio.sleep(.2)
        clone_channel = discord.utils.get(clone_guild.channels,name=channel.name)
        message2  = clone_channel.last_message
        thread = guild.get_thread(message.id)
        if thread:
            print("IN THREAD")
            if message2:

                try:
                    try:
                        t = await message2.create_thread(name=thread.name)
                        print("CREATED THREAD: "+str(t.id))
                    except Exception as e:
                        thread_webhook = None
                except Exception as e:
                    print(e)
                try:
                    thread_webhook = webhook_from_url(webhooks_dict[clone_channel.id],thread_id=t.id)
                except Exception as e:
                    print(e)
                    thread_webhook = None
                if thread_webhook:
                    messages = []
                    async for message in thread.history(limit=500):
                        try:
                            messages.append(message)
                        except Exception as e:
                            logger(f"Error in sending message: Error -> {e} || Message -> {str(message.id)}")

                    messages.reverse() # making it oldest to newest
                    unique_messages = []
                    seen = set()
                    for message in messages:
                        if message not in seen:
                            unique_messages.append(message)
                            seen.add(message)
                    for message in unique_messages:
                        try:       
                            in_db = session.query(DbStruct.messages).filter(DbStruct.messages.message_id== message.id).first()
                            if not in_db:
                                    try:
                                        content = message.content
                                        username = message.author.display_name
                                        avatar_url = message.author.avatar.url if message.author.avatar else None
                                        embeds = message.embeds
                                        files = message.attachments
                                        if not content:
                                            content = ""
                                        obj = DbStruct.messages(message_id=message.id)
                                        session.add(obj)
                                        session.commit()
                                        thread_webhook = await webhok_add_content(webhook=thread_webhook,content=content,username=username,avatar_url=avatar_url,embeds=embeds,files=files)
                                        thread_webhook.execute()

                                    except Exception as e:
                                        print(e)
                            else:
                                continue
                        except Exception as e:
                            logger.error(f"Error in sending message: Error -> {e}")
    else:
        return True
async def scrape_old():
    for guild in bot.guilds:
        try:
            if "_clone" in guild.name:
                pass
            else:


                for channel in guild.channels:
                    try:
                        if not isinstance(channel,discord.CategoryChannel):
                        
                            channel_messages = []
                            async for message in channel.history(limit=500):
                                channel_messages.append(message)

                            unique_messages = []
                            seen = set()
                            
                            for message in channel_messages:
                                if message not in seen:
                                    unique_messages.append(message)
                                    seen.add(message)

                            unique_messages.reverse() # making it oldest to newest
                            x = 132
                            for message in unique_messages:
                                if message.id == x:
                                    print(message)
                                    exit()
                                else:
                                    x = message.id
                                await send_message(message=message)
                    except Exception as e:
                        logger.error(f"Error in checking channel in scrape_old: Error -> {e}")
        except Exception as e:
            logger.error(f"Error in scrape_old: Error -> {e}")
                       
@bot.event
async def on_message(message: discord.Message):
        print(message.content)
        if message.guild.id in cloned_list:
            print(message.content) 
            d = await create_categories(guild=message.guild,server_dict={})
            chan = await create_channels(guild=message.guild,server_dict=d)
            await send_message(message=message)


bot.run(token)
