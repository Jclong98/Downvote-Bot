"""
a collection of functions for dvb.py to use to react to 
things and interact with the database
"""


import json
import random
import re
import sqlite3
from datetime import datetime
from tempfile import TemporaryDirectory
from time import time
import os
import subprocess

import discord
import praw
import requests

# loading credentials from file
creds = json.load(open("./credentials.json"))

# setting up a reddit instance for vreddit downlaoding
reddit = praw.Reddit(
    client_id=creds['reddit_client_id'],
    client_secret=creds['reddit_client_secret'], 
    user_agent='script', 
)

def create_database(con):
    """gets the sql queries to create a dvb database 
    from db.sql and executes them separately"""

    with open("db.sql", 'r') as db_f:
        create_db_string = db_f.read()

    # executing each table creation separately
    for query in create_db_string.split(";"):
        with con as c:
            # print(query)
            c.execute(query)


def add_action(message, action, con):
    """
    any time dvb responds to something, it is considered an action. 
    this is will log that action to the database and return the action id.

    message: a discord.Message object. this will give the author, channel, and server

    action: the action dvb performed
    
    con: an sqlite database connection
    """

    # inserting a record into the db
    with con as c:
        c.execute(
            f"insert into actions (action_time, action, author, author_id, channel, channel_id, guild, guild_id) values (:action_time, :action, :author, :author_id, :channel, :channel_id, :guild, :guild_id)",
            {
                "action_time":datetime.now(), 
                "action":action, 
                "author":str(message.author), 
                "author_id":message.author.id, 
                "channel":str(message.channel), 
                "channel_id":message.channel.id, 
                "guild":str(message.channel.guild),
                "guild_id":message.channel.guild.id,
            }
        )

        # getting the actionid for this entry
        action_id = c.execute("select max(action_id) from actions").fetchall()[0][0]

        print(f"{datetime.now()}\t{action}\t{message.author}\t{message.channel}\t{message.channel.guild}")

    return action_id


def add_voteable(message, phrase, vote, con):
    """
    adding a voteable to the database for a certain server

    message: a discord.Message object

    phrase: a string that will be reacted to with an upvote or a downvote

    vote: 'up' or 'down'
    """

    # print(type(phrase))
    # print(phrase)

    # getting an action id to relate to the actions table
    action_id = add_action(message, f"added {phrase} to the {vote}votelist", con)

    with con as c:
        c.execute(
            f"insert into voteables (phrase, vote, action_id) values (:phrase, :vote, :action_id)",
            {
                "phrase":phrase.lower(),
                "vote":vote,
                "action_id":action_id,
            }
        )

        # print(f"Added {phrase} to {vote}vote list")


def remove_voteable(message, phrase, vote, con):
    """
    adding a voteable to the database for a certain server

    message: a discord.Message object

    phrase: a string that will be reacted to with an upvote or a downvote

    vote: 'up' or 'down'
    """

    # getting an action id to relate to the actions table
    add_action(message, f"removed {phrase} from {vote}votables", con)

    with con as c:

        a_ids = c.execute(
            """
            select v.action_id
            from actions a, voteables v
            where a.action_id = v.action_id
            and v.phrase = :phrase
            and guild_id = :guild_id
            and v.vote = :vote
            """,
            {
                "phrase":phrase,
                "guild_id":message.channel.guild.id,
                "vote":vote
            }
        ).fetchall()

        # iterating over the returned action ids
        for a_id in [row[0] for row in a_ids]:
            c.execute("delete from voteables where action_id = :a_id", {"a_id":a_id})
    
    # print(f"removed {phrase} from the {vote}votelist for {message.channel.guild}")


async def votelist(message, vote, con):
    """
    display the votelist or add/remove items from it
    """

    # splitting the message on spaces to parse arguments
    content = message.content.split()

    # displaying the downvotelist
    if len(content) == 1:
        with con as c:
            phrases = c.execute(
                """
                select v.phrase
                from actions a, voteables v
                where a.action_id = v.action_id
                and a.guild_id = :guild_id
                and vote = :vote
                """, 
                {
                    "guild_id":message.channel.guild.id,
                    "vote":vote
                }
            ).fetchall()

        # collecting the phrases from the query with a list comprehension
        phrases = [row[0] for row in phrases]

        if len(phrases) == 0:
            await message.channel.send(f"No phrases to {vote}vote! Try saying `#{vote}votelist add <phrase>`")

        else:
            # building a message to display to the user
            m = ""
            for phrase in phrases:
                m += phrase + '\n'

            await message.channel.send(f"```{m}```")

        return

    # reconstructing the message without the command or argument
    phrase = ' '.join(content[2:])

    if content[1] == 'add':
        add_voteable(message, phrase, vote, con)
        await message.channel.send(f"added `{phrase}` to the {vote}votelist")

    elif content[1] == 'remove':
        remove_voteable(message, phrase, vote, con)
        await message.channel.send(f"removed `{phrase}` from the {vote}votelist")

    else:
        await message.channel.send(f"Invalid argument: `{content[1]}`.\n please try `add` or `remove`")


async def vote(message, con):
    """react to a message with an up/downvote 
    based on what is in the votelists for that server"""

    with con as c:
        voteables = c.execute(
            """
            select v.phrase, v.vote
            from actions a, voteables v
            where a.action_id = v.action_id
            and a.guild_id = :guild_id
            """,
            {
                "guild_id":message.channel.guild.id
            }
        ).fetchall()

    for v in voteables:
        if v[0] in message.content.lower():
            if v[1] == 'down':
                await message.add_reaction("<:downvote:596443285606760449>")
            else:
                await message.add_reaction("<:upvote:596443285656961044>")


async def owo(message, con):
    """sends a response from a list of owo's to a message containing owo"""
    with open("static/owolist.txt", 'r', encoding='utf-8') as f:
        owos = f.read().splitlines()

    if random.random() > 0.7:
        await message.channel.send("OwO")
    else:
        await message.channel.send(random.choice(owos))
    

async def upvote(message, con):
    """if a user is mentioned, send a message with upvotes 
    around their name, otherwise just send an upvote"""
    if message.mentions:
        for user in message.mentions:
            await message.channel.send(f"<:upvote:596443285656961044>{user.mention}<:upvote:596443285656961044>")
    else:
        await message.channel.send("<:upvote:596443285656961044>")
    add_action(message, "upvoted", con)


async def downvote(message, con):
    """if a user is mentioned, send a message with downvotes 
    around their name, otherwise just send an downvote"""
    if message.mentions:
        for user in message.mentions:
            await message.channel.send(f"<:downvote:596443285606760449>{user.mention}<:downvote:596443285606760449>")
    else:
        await message.channel.send("<:downvote:596443285606760449>")
    add_action(message, "downvoted", con)


async def superupvote(message, con):
    """sends a large upvote as an image"""
    for user in message.mentions:
        await message.channel.send(f"<:upvote:596443285656961044>😁{user.mention}😁<:upvote:596443285656961044>")
    await message.channel.send(file=discord.File('static/upvote.png'))
    add_action(message, "superupvoted", con)


async def superdownvote(message, con):
    """sends a large downvote as an image"""
    for user in message.mentions:
        await message.channel.send(f"<:downvote:596443285606760449>😡{user.mention}😡<:downvote:596443285606760449>")
    await message.channel.send(file=discord.File('static/downvote.png'))
    add_action(message, "superdownvoted", con)


async def mega(message, con):
    """searches a message for custom emojis and sends the 
    link to them in chat. This effectively enlarges them if 
    their resolution is high enough"""

    # regex pattern to find animated emojis
    gif_pattern = re.compile(r"<a:[\w\d]+:\d+>")
    gif_matches = gif_pattern.findall(message.content)

    for match in gif_matches:
        # print(match)

        emoji_id_pattern = re.compile(r":\d+>")

        gif_id_matches = emoji_id_pattern.findall(match)

        for gif_id in gif_id_matches:
            # print(f"https://cdn.discordapp.com/emojis/{gif_id}.gif")
            # the id is [1:-1] to get rid of the : and > that are part of the regex
            await message.channel.send(f"https://cdn.discordapp.com/emojis/{gif_id[1:-1]}.gif")
            add_action(message, f"mega'd https://cdn.discordapp.com/emojis/{gif_id}.gif", con)

    png_pattern = re.compile(r"<:[\w\d]+:\d+>")
    png_matches = png_pattern.findall(message.content)

    for match in png_matches:
        # print(match)

        emoji_id_pattern = re.compile(r":\d+>")

        png_id_matches = emoji_id_pattern.findall(match)

        for png_id in png_id_matches:
            # print(f"https://cdn.discordapp.com/emojis/{png_id}.png")
            # the id is [1:-1] to get rid of the : and > that are part of the regex
            await message.channel.send(f"https://cdn.discordapp.com/emojis/{png_id[1:-1]}.png")
            add_action(message, f"mega'd https://cdn.discordapp.com/emojis/{png_id}.png", con)


async def conga(message, con):
    """sends a message with a given number of congas"""

    content = message.content.split()

    try:
        conganum = int(content[1])

        if conganum > 50:
            conganum = 50

        congas = "<a:partyblobconga:447536664072552448>" * conganum

        await message.channel.send(congas)
        add_action(message, "conga'd", con)

    except:
        pass

# the list of emoji keys for the below function
emoji_keys = {'a':'🇦', 'b':'🅱️', 'c':'🇨', 'd':'🇩', 'e':'🇪', 'f':'🇫', 'g':'🇬', 'h':'🇭', 'i':'🇮', 'j':'🇯', 'k':'🇰', 'l':'🇱', 'm':'🇲',
                'n':'🇳','o':'🇴', 'p':'🇵', 'q':'🇶', 'r':'🇷', 's':'🇸', 't':'🇹', 'u':'🇺', 'v':'🇻', 'w':'🇼', 'x':'🇽', 'y':'🇾', 'z':'🇿', 
                '!':'❗', '?':'❓', '0':':zero:', '1':':one:', '2':':two:', '3':':three:', '4':':four:', '5':':five:','6':':six:', 
                '7':':seven:', '8':':eight:', '9':':nine:', '*':':asterisk:', '#':'hash', '$':'💲', '-':'⛔', '+':'➕', '=':'➡'}

async def emojify(message, con):
    """takes a message and turns all of the characters 
    into their emoji counterparts"""

    # getting rid of the #emojify at the beginning of the command
    split = message.content.lower().split()
    m = ' '.join(split[1:])

    new_message = []
    for character in m:
        if character in emoji_keys:
            character = emoji_keys[character]

            new_message.append(character)
        else:
            new_message.append(character)

    new_message = ' '.join(new_message)

    await message.channel.send(new_message)
    add_action(message, "emojified", con)


async def party(message, con):
    """reacts to a message with a random party emoji"""

    party_list = [
        "<a:partyblobconga:447536664072552448>",
        "<a:chika:555222709102051353>",
        "<a:robodance:413911569248944139>",
        "<a:partyditto:436282463317131285>",
        "<a:partyparrot:436282474029645845>",
        "<a:wiggleparrot:522317230151827476>",
        "<a:blobdance:433437351025573888>",
        "<a:partyparrotcookie:436282437522423808>",
    ]

    try:
        await message.add_reaction(random.choice(party_list))
    except:
        await message.add_reaction(party_list[2])

    add_action(message, "party'd", con)


async def download_vreddit(message, con, url):
    """takes a reddit link, downloads the vreddit inside it, sends it in the channel"""

    # getting post with praw
    post = reddit.submission(url=url)

    # making sure the given url has a video
    try:
        video_url = post.media['reddit_video']['fallback_url']
    except TypeError as e:
        print("no video for given post")
        return

    # opening a temporary directory so that ffmpeg can output and work with files
    with TemporaryDirectory() as temp_dir:

        # getting video and downloading it
        video_request = requests.get(video_url)
        video_path = os.path.join(temp_dir, 'video.mp4')
        with open(video_path, 'wb') as f:
            f.write(video_request.content)

        # getting audio
        audio_url = post.url + '/audio'
        audio_request = requests.get(audio_url)

        # if there is audio, we want to combine it and compress the combined video
        if audio_request.status_code == 200:
            # downloading audio
            audio_path = os.path.join(temp_dir, 'audio.mp4')
            with open(audio_path, 'wb') as f:
                f.write(audio_request.content)

            # combining audio and video into one file
            print("combining audio and video into one file")
            uncompressed_path = os.path.join(temp_dir, 'uncompressed.mp4')
            subprocess.call(f"ffmpeg -i {video_path} -i {audio_path} -c copy {uncompressed_path}", shell=True)
            
            # pointing the video path to the newly combined video
            video_path = uncompressed_path

        # compressing the video
        print("compressing the video")
        compressed_path = os.path.join(temp_dir, f'{post.title}.mp4').replace(' ', '_')
        subprocess.call(f"ffmpeg -i {video_path} -crf 30 {compressed_path}", shell=True)


        # creating a discord embed to send from the user
        embed = discord.Embed(
            colour=0x8080FF,
        )
        embed.add_field(name=post.title, value=f"[Jump!]({message.jump_url})", inline=True)
        embed.set_footer(text=f"Requested by: {message.author}", icon_url=message.author.avatar_url)

        # sending the message with the created embed and file
        await message.channel.send(
            embed=embed,
            file=discord.File(compressed_path),
        )
        add_action(message, "sent vreddit", con)

async def send_vreddit(message, con):
    """searches a message for reddit links, and for
    each on it will try to download and send a vreddit video"""

    # splitting the message and searching each word for a reddit link
    for word in message.content.split():
        if 'www.reddit.com' in word or 'v.redd.it' in word:
            await download_vreddit(message, con, word)

async def invite(message, con):
    await message.channel.send("Use this link to invite me to other servers https://discordapp.com/api/oauth2/authorize?client_id=412495164200714251&permissions=54000704&scope=bot")
    add_action(message, "invited", con)


async def help_message(message, con):
    help_message = f"""

Commands: (prefix: #)
---------------------

`invite`
  -sends a link to invite me to other servers!

`downvotelist` <add/remove> <word>
  -downvotelist by itself will show the list of downvotable items

`upvotelist` <add/remove> <word>
  -upvotelist by itself will show the list of upvotable items

`downvote` <user>
  -downvote by itself will send one downvote
  -more than one user can be input

`upvote` <user>
  -upvote by itself will send one upvote

`superdownvote` <user>
  -superdownvote by itself will send one superdownvote
  -more than one user can be input

`superupvote` <user>
  -superupvote by itself will send one superupvote
  -more than one user can be input

`owolist` 
  -shows a list of owos that the bot will react with when owo is seen in a message

`mega` <custom emoji>
  -gets the link for that emoji and sends it in chat so that it appears larger
  -more than one emoji can be input

`conga` <number of congas>
  -sends a number of conga emojis (up to 50)

`emojify` <message>
  -turns an entire message into emoji letters and numbers

`numberfifteen`
  -burger king foot lettuce

"""

# removed functionalities
# `randomword` <number of letters>
#   -creates a brand new word with a number of input random letters
#   -if no number is input, the amount of letters defaults to 4

# `ss`
#   -Secret Santa!
#   -react to the present on the message that gets sent to join a secret santa
#   -Downvote Bot will send you a message with the name of who you got


    embed = discord.Embed(
        description = help_message,
        color=0x8080ff
    )

    embed.set_footer(text=f"Requested by: {message.author}", icon_url=message.author.avatar_url)

    await message.channel.send(embed=embed)
    add_action(message, "helped", con)

if __name__ == "__main__":

    conn = sqlite3.connect("db.sqlite")
    # conn = sqlite3.connect(":memory:")

    with conn as c:

        actions = c.execute(
        """
            select a.guild, a.guild_id, v.* 
            from actions a, voteables v
            where a.action_id = v.action_id
            and v.phrase = 'oof'
            and guild_id = '412495298707849216'

        """
        ).fetchall()

        for record in actions:
            print(record)

        c.execute(
            """
            
            
            """
        )
