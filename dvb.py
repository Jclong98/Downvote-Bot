"""
The main portion of Downvote bot. 
Implements functions from actions.py to react to things.
"""

import json
import os
import random
import sqlite3
from datetime import datetime

import discord
from discord.ext import commands

from actions import *
from tools import has_keywords

# spawns connections to the database
conn = sqlite3.connect("db.sqlite")

# creating a database if one does not exist already
create_database(conn)

print("created database")

bot = commands.Bot(
    command_prefix="#", 
    status=discord.Status.idle, 
    activity=discord.Game(name='Booting...')
)


@bot.event
async def on_ready():
    await bot.change_presence(
        status=discord.Status.online, 
        activity=discord.Game(name='#help for commands')
    )
    print(f"Logged in as: {bot.user.name}")
    print(f"User id: {bot.user.id}")
    print("Ready to downvote!")
    print("------------------")


@bot.event
async def on_message(message):
    
    # making sure the bot does not respond to itself
    if message.author.id == bot.user.id:
        return

    # REACTIONS/COMMANDS

    # ayylmao
    if "ayylmao" in message.content.lower():
        await message.add_reaction("<:ayylmao:244178991563538432>")
        add_action(message, "ayy'd", conn)

    # interacting with the downvotelist
    if message.content.lower().startswith("#downvotelist"):
        await votelist(message, 'down', conn)

    # interacting with the upvotelist
    elif message.content.lower().startswith("#upvotelist"):
        await votelist(message, 'up', conn)

    # upvote
    elif message.content.lower().startswith("#upvote"):
        await upvote(message, conn)

    # downvote
    elif message.content.lower().startswith("#downvote"):
        await downvote(message, conn)

    # voting on all other messages
    else:
        await vote(message, conn)

    if 'owo' in message.content.lower():
        await owo(message, conn)

    # doot
    if 'doot' in message.content.lower():
        await message.add_reaction("<:doot:243931943736049674>")
        add_action(message, "dooted", conn)

    # thumbs up
    if has_keywords(message.content.lower(), ['downvotebot', 'downvote bot', 'dvb']):
        await message.add_reaction("👍")
        add_action(message, "Thumbs Upped", conn)

    # no u
    if 'no u' in message.content.lower():
        await message.channel.send("no u")
        add_action(message, "no u'd", conn)

    # mega
    if message.content.lower().startswith("#mega"):
        await mega(message, conn)
        add_action(message, "mega'd", conn)

    # party
    if 'party' in message.content.lower():
        await party(message, conn)

    # send_vreddit
    if has_keywords(message.content.lower(), ['redd.it', 'www.reddit.com']):
        await send_vreddit(message, conn)
        
    # superupvote
    if message.content.lower().startswith("#superupvote"):
        await superupvote(message, conn)

    # superdownvote
    if message.content.lower().startswith("#superdownvote"):
        await superdownvote(message, conn)

    # conga
    if message.content.lower().startswith("#conga"):
        await conga(message, conn)

    # emojify
    if message.content.lower().startswith("#emojify"):
        await emojify(message, conn)

    # numberfifteen
    if message.content.lower().startswith("#numberfifteen"):
        with open('static/numberfifteen.txt') as f:
            await message.channel.send(f.read())
        add_action(message, "number fifteen'd", conn)

    # invite
    if message.content.lower().startswith("#invite"):
        await invite(message, conn)

    # help
    if message.content.lower().startswith("#help"):
        await help_message(message, conn)

    # trap
    if has_keywords(message.content.lower(), ['traps']):
        await message.add_reaction("🇹")
        await message.add_reaction("🇷")
        await message.add_reaction("🇦")
        await message.add_reaction("🇵")
        await message.add_reaction("🇸")
        await message.add_reaction("🚫")
        await message.add_reaction("🇬")
        await message.add_reaction("🅰")
        await message.add_reaction("🇾")
        await message.add_reaction(":trapsarenotgay:351822466504589334")
        add_action(message, "trapped", conn)

    # zoop
    if 'zoop' in message.content.lower():
        await message.add_reaction("👈")
        await message.add_reaction("😎")
        await message.add_reaction("👉")
        add_action(message, "zooped", conn)

    # sans
    if message.content.lower().startswith("#sans"):
        await sans(message, conn)

    # stats
    if message.content.lower().startswith("#stats"):
        await stats(message, conn)

    # secret santa
    if message.content.lower().startswith(("#secretsanta", '#ss')):
        await secret_santa(message, conn)

    # asciify
    if message.content.lower().startswith("#asciifym"):
        await asciify(message, conn, max_width=40)
    elif message.content.lower().startswith("#asciify"):
        await asciify(message, conn)



if __name__ == "__main__":
    
    # loading credentials
    creds = json.load(open("./credentials.json"))

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--debug', action='store_true')
    args = parser.parse_args()

    if args.debug:
        # testbot
        print("DEBUG MODE")
        bot.run(creds['discord_secret_key_testbot'])

    else:
        # downvotebot
        bot.run(creds['discord_secret_key'])
