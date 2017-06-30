import datetime
import asyncio
import discord
import inspect
import uuid
import sys
import io
import os

from discord.ext import commands
from utils import config

bot = commands.Bot(command_prefix='==')

linking_dict = {}

links = config.Config('links.json')

@bot.event
async def on_ready():
    await bot.change_presence(game=discord.Game(name='==link'))
    print('ready')

@bot.command(no_pm=True)
@commands.has_permissions(manage_guild=True)
async def link(ctx, identifier : str=None):
    """Starts the linking process.

    If an identifier is provided, this ends the linking process."""

    link_dict = links.get('links', {})

    if ctx.channel.id in link_dict.keys() or ctx.channel.id in link_dict.values():
        em = discord.Embed()
        em.color = 0xc10ba0
        em.title = f'#{ctx.channel.name} is already linked to another channel!'
        em.description = 'You can type `==unlink` to break the link in that channel.'

        return await ctx.send(embed=em)

    if not identifier:

        if ctx.channel.id in linking_dict:
            code = linking_dict[ctx.channel.id]
        else:
            code = str(uuid.uuid1())

        linking_dict[ctx.channel.id] = code

        em = discord.Embed()
        em.color = 0xc10ba0
        em.description = f'Your ID is: **{code}**\n' \
                        'Copy and paste this identifier into another channel\n' \
                        'that the bot can access using `==link <code here>`.'

        return await ctx.send(embed=em)

    identifier = identifier.replace('<', '').replace('>', '') # for the people who just don't get it

    if identifier not in linking_dict.values():
        em = discord.Embed()
        em.color = 0xc10ba0
        em.title = 'Identifier not found!'
        em.description = 'Are you sure you copy-pasted the whole thing?'

        return await ctx.send(embed=em)

    for cid, code in linking_dict.items():
        if code == identifier:
            to_link = bot.get_channel(cid)
        else:
            continue

    if to_link is None:
        em = discord.Embed()
        em.color = 0xc10ba0
        em.title = 'Original channel not found.'

        return await ctx.send(embed=em)

    if to_link.id == ctx.channel.id:
        em = discord.Embed()
        em.color = 0xc10ba0
        em.title = 'You can\'t link a channel to itself!'

        return await ctx.send(embed=em)

    if to_link.id in link_dict.keys() or to_link.id in link_dict.values():
        em = discord.Embed()
        em.color = 0xc10ba0
        em.title = f'{to_link.name} is already linked to another channel!'
        em.description = 'You can type `==unlink` to break the link in that channel.'

        return await ctx.send(embed=em)

    link_dict[ctx.channel.id] = to_link.id
    await links.put('links', link_dict)

    em = discord.Embed()
    em.color = 0xc10ba0
    em.title = 'Successfully linked!'
    em.description = f'Linked #{to_link.name} in {to_link.guild.name} to' \
                    f' #{ctx.channel.name} in {ctx.channel.guild.name}.'

    try:
        await ctx.send(embed=em)
    except:
        pass # couldn't send the message for some reason

    try:
        await to_link.send(embed=em)
    except:
        pass # couldn't send the message for some reason

@bot.command(no_pm=True)
async def unlink(ctx):
    """Breaks the link between the current channel and another."""

    link_dict = links.get('links', {})
    link_dict = {int(k):int(v) for k,v in link_dict.items()} # fuck json for not storing ints as keys

    if ctx.channel.id not in link_dict.keys() and ctx.channel.id not in link_dict.values():
        em = discord.Embed()
        em.color = 0xc10ba0
        em.title = 'This channel is not linked to any other channel.'

        return await ctx.send(embed=em)

    for channel1, channel2 in link_dict.items():
        if ctx.channel.id == channel1:
            linked_cid = channel2
            break
        elif ctx.channel.id == channel2:
            linked_cid = channel1
            break

    linked_c = bot.get_channel(linked_cid)

    if ctx.channel.id in link_dict.keys():
        del link_dict[ctx.channel.id]
    elif ctx.channel.id in link_dict.values():
        del link_dict[linked_cid]

    await links.put('links', link_dict)

    em = discord.Embed()
    em.color = 0xc10ba0
    em.title = 'Link broken successfully.'
    em.description = f'Link broken between #{ctx.channel.name} in {ctx.guild.name} ' \
                    f'and #{linked_c.name} in {linked_c.guild.name}.'

    try:
        await ctx.send(embed=em)
    except:
        pass # couldn't send the message for some reason

    if linked_c:
        try:
            await linked_c.send(embed=em)
        except:
            pass # couldn't send the message for some reason


@bot.event
async def on_message(message):
    channel = message.channel

    if message.author.id == bot.user.id:
        return

    link_dict = links.get('links', {})
    link_dict = {int(k):int(v) for k,v in link_dict.items()} # fuck json for not storing ints as keys

    if channel.id not in link_dict.keys() and channel.id not in link_dict.values():
        await bot.process_commands(message)
        return

    for channel1, channel2 in link_dict.items():
        if channel.id == channel1:
            linked_cid = channel2
            break
        elif channel.id == channel2:
            linked_cid = channel1
            break

    linked_c = bot.get_channel(linked_cid)

    if not linked_c:
        await bot.process_commands(message)
        return

    em = discord.Embed()
    em.color = 0x41c105
    em.timestamp = message.created_at

    author = message.author
    guild = message.guild
    channel = message.channel
    a_name = author.nick if author.nick else author.name
    a_icon = author.avatar_url_as(format='png')
    g_icon = guild.icon_url

    em.set_author(name=a_name, icon_url=a_icon)

    if g_icon:
        em.set_footer(text=f'#{channel.name} in {guild.name}', icon_url=g_icon)
    else:
        em.set_footer(text=f'#{channel.name} in {guild.name}')

    em.description = message.content

    if message.attachments:
        attachment = message.attachments[0]
        b = io.BytesIO()
        await attachment.save(b)
        b.seek(0)
        if attachment.height:
            em.set_image(url=f'attachment://{attachment.filename}')

        try:
            await linked_c.send(file=discord.File(b, attachment.filename), embed=em)
        except:
            pass

        await bot.process_commands(message)
        return

    try:
        await linked_c.send(embed=em)
    except:
        pass # couldn't send the message for some reason

    await bot.process_commands(message)

@bot.command(hidden=True)
@commands.is_owner()
async def logout(ctx):
    await bot.logout()

@commands.command(hidden=True)
@commands.is_owner()
async def debug(self, ctx, *, code: str):
    """Evaluates code."""

    code = code.strip('` ')
    python = '```py\n{}\n```'
    result = None

    env = {
        'bot': self.bot,
        'ctx': ctx,
        'message': ctx.message,
        'guild': ctx.guild,
        'channel': ctx.channel,
        'author': ctx.author
    }

    env.update(globals())

    try:
        result = eval(code, env)
        if inspect.isawaitable(result):
            result = await result
    except Exception as e:
        await ctx.send(python.format(type(e).__name__ + ': ' + str(e)))
        return

    await ctx.send(python.format(result))

creds = config.Config('credentials.json')
bot.run(creds['token'])
