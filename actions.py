"""
a collection of functions for dvb.py to use to react to 
things and interact with the database
"""

import asyncio
import json
import os
import random
import re
import sqlite3
import subprocess
from datetime import datetime
from tempfile import TemporaryDirectory
from time import time

import discord
import praw
import requests

from tools import img_to_ascii

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

    # no logging on dms. database isnt set up right for it
    if type(message.channel) == discord.channel.DMChannel:
        return

    # inserting a record into the db
    with con as c:
        c.execute(
            "insert into actions (action_time, action, author, author_id, channel, channel_id, guild, guild_id) values (:action_time, :action, :author, :author_id, :channel, :channel_id, :guild, :guild_id)",
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

    # no reactions in dms
    if type(message.channel) == discord.channel.DMChannel:
        return

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

    downvoted = False
    upvoted = False
    
    for row in voteables:
        if row[0] in message.content.lower():
            if row[1] == 'down':
                await message.add_reaction("<:downvote:596443285606760449>")
                downvoted = True
            else:
                await message.add_reaction("<:upvote:596443285656961044>")
                upvoted = True

    if downvoted:
        add_action(message, "downvoted", con)
    if upvoted:
        add_action(message, "upvoted", con)
    

async def owo(message, con):
    """sends a response from a list of owo's to a message containing owo"""
    with open("static/owolist.txt", 'r', encoding='utf-8') as f:
        owos = f.read().splitlines()

    if random.random() > 0.7:
        await message.channel.send("OwO")
    else:
        await message.channel.send(random.choice(owos))

    add_action(message, "owo'd", con)


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

    custom_emojis = re.findall(r'<:\w*:\d*>', message.content)
    custom_animated_emojis = re.findall(r'<a:\w*:\d*>', message.content)

    for e in custom_emojis:
        e_id = e.split(":")[2].replace('>', '')

        await message.channel.send(f"https://cdn.discordapp.com/emojis/{e_id}.png")
        add_action(message, "mega'd", con)

    for e in custom_animated_emojis:
        e_id = e.split(":")[2].replace('>', '')

        await message.channel.send(f"https://cdn.discordapp.com/emojis/{e_id}.gif")
        add_action(message, "mega'd", con)
 

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
            color=discord.Color.from_rgb(128,128,255),
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


async def sans(message, con):
    """dvb joins the channel of whoever sent the command 
    and play sans talking for a given number of seconds."""

    # checking to see if dvb can join the channel
    try:
        channel = message.author.voice.channel
    except:
        await message.channel.send(f"If you aren't there {message.author.mention}, I can't join!")
        return

    # VoiceClient
    vc = await channel.connect()
    vc.play(discord.FFmpegPCMAudio("./static/Just Sans talking.mp3"))
    
    # getting duration
    try:
        duration = int(message.content.split()[1])
    except:
        duration = 2
    
    # 121 is the length of the audio file in seconds.
    # this is here so that it doesn't try to loop or anything weird
    if duration > 121:
        duration = 2

    # sleeping for the input duration
    await asyncio.sleep(duration)

    # when the player is done, disconnect from the channel
    await vc.disconnect()
    add_action(message, "sans'd", con)


async def send_user_stats(user, channel, con):
    """
    send stats in a specific channel for a certain user
    """
    embed = discord.Embed(
        title=f"{user.display_name}'s Stats:",
        color=discord.Color.from_rgb(128,128,255)
    )
    embed.set_thumbnail(url=user.avatar_url)

    with con as c:
        total_actions = c.execute(
            """
            select count(*) from actions
            where guild_id = :guild_id
            and author_id = :author_id
            """,
            {                
                "guild_id":channel.guild.id,
                "author_id":user.id,
            }
        ).fetchall()[0][0]
        print(total_actions)
        embed.add_field(name="Total Actions", value=total_actions, inline=True)

        # top 5 actions
        top_actions = c.execute(
            """
            select action, count(action) from actions
            where guild_id = :guild_id
            and author_id = :author_id
            group by action
            order by 2 desc
            limit 5
            """,
            {                
                "guild_id":channel.guild.id,
                "author_id":user.id,
            }                
        ).fetchall()
        print(top_actions)

        if top_actions:
            top_actions_str = ""
            for action, count in top_actions:
                top_actions_str += f"{action}:\t{count}\n"
            embed.add_field(name="Top Actions", value=top_actions_str, inline=True)

    await channel.send(embed=embed)
    

async def stats(message, con):
    """
    send stats about a server
    if users are mentiond, send stats about them
    """
    if message.mentions:
        for user in message.mentions:
            await send_user_stats(user, message.channel, con)

    else:
        
        with con as c:

            # getting the total amount of times dvb has reacted to things
            total_actions = c.execute(
                """
                select count(*) from actions
                where guild_id = :guild_id
                """,
                {                
                    "guild_id":message.channel.guild.id,
                }
            ).fetchall()[0][0]

            # top 5 actions
            top_actions = c.execute(
                """
                select action, count(action) from actions
                where guild_id = :guild_id
                group by action
                order by 2 desc
                limit 5
                """,
                {                
                    "guild_id":message.channel.guild.id,
                }                
            ).fetchall()

            top_actions_str = ""
            for action, count in top_actions:
                top_actions_str += f"{action}:\t{count}\n"


        embed = discord.Embed(
            title=f"{message.guild.name}'s Stats:",
            color=discord.Color.from_rgb(128,128,255)
        )
        embed.set_thumbnail(url=message.channel.guild.icon_url)
        embed.add_field(name="Total Actions", value=total_actions, inline=True)
        embed.add_field(name="Top Actions", value=top_actions_str, inline=True)

        await message.channel.send(embed=embed)

    add_action(message, "stats", con)
    

def get_ss_embed(description, max_price=None):
    """a function used by secret_santa to get the same embed every time"""
    e = discord.Embed(
        title="🎅 Secret Santa! 🎅",
        color=discord.Color.from_rgb(0, 255, 0),
        description=description
    )

    if max_price:
        e.add_field(name="Max Price", value=f"${max_price:,.02f}")
    
    return e

async def secret_santa(message, con):
    """
    1. send message
    2. get participants
    3. pair up participants and recipients
    4. send each user a message telling them who they got 
    """


    wait_time = 30
    try:
        wait_time = int(message.content.split()[1])
    except:
        pass

    max_price = None
    try:
        max_price = float(message.content.split()[2])
    except:
        pass

    # 1. send message
    embed = get_ss_embed(f"Secret santa sign up ends in {wait_time}")
    m = await message.channel.send(embed=embed)
    await m.add_reaction("🎁")

    for i in range(wait_time, 0, -1):

        await m.edit(embed=get_ss_embed(f"Secret santa sign up ends in {i}", max_price))
        await asyncio.sleep(1)

    # 2. get participants
    m = await message.channel.fetch_message(m.id)
    for reaction in m.reactions:
        if reaction.emoji == "🎁":
            users = await reaction.users().flatten()
    

    # 3. pair up participants and recipients
    users = [user for user in users if not user.bot]

    # checking if there are enough people
    if len(users) < 2:
        # there weren't enough
        await m.edit(embed=get_ss_embed("There were not enough participants :("))
        return

    else:
        # there were enough
        await m.edit(embed=get_ss_embed(f"Times up! There are {len(users)} participants!", max_price))

    recipients = users.copy()
    random.shuffle(recipients)

    pairs = {}
    for user in users:
        
        recipient = recipients.pop()
        pairs[user] = recipient

        # if the user matches with themself, draw a different user
        if pairs[user] == user:
            
            # getting a new recipient
            pairs[user] = recipients.pop()

            # adding the original recipient back into the pool
            recipients.append(recipient)


    # 4. send each user a message telling them who they got
    for user, recipient in pairs.items():
      
        await user.send(embed=get_ss_embed(
            f"You got {recipient.mention} for secret santa! Make sure you get them a good gift!", 
            max_price
        ))

    add_action(message, "secret santa'd", con)
    

async def asciify(message, con, max_width=100):
    """
    1. finds an image from a given url
    2. converts it to ascii color blocks
    3. sends messages containing the image
    """

    try:
        url = message.content.split()[1]
    except:
        await message.channel.send("Could not find a specified image. `#asciify <url to image>`")
        return

    try:
        ascii_img = img_to_ascii(url, max_width=max_width)
    except:
        await message.channel.send("I couldn't find that image 😔")
        return
    
    # send rows of characters 20 lines at a time.
    # each message can be 2000 characters long and each line has 100 characters
    while len(ascii_img) > 0:
        msg = '```'

        for row in ascii_img[:20]:
            msg += ''.join(row) + '\n'

        msg += '```'
        await message.channel.send(msg)

        del ascii_img[:20]
                
    add_action(message, "asciified", con)


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

`sans` <seconds>
  - sans undertale will come to your server for a number of seconds :o

`stats` <user>
  -Sends some stats about how many times downvotebot has reacted to a user
  -calling stats without a user will send server stats

`secretsanta` or `ss` <duration> <max price>
  -Secret Santa!
  -react to the present on the message that gets sent to join a secret santa
  -Downvote Bot will send you a message with the name of who you got

`asciify` <url to image>
  -Sends the given image in chat as a series of ascii shade blocks

`asciifym` <url to image>
  -Same as asciify but limits the width to 40 characters for mobile
"""

    embed = discord.Embed(
        description = help_message,
        color=discord.Color.from_rgb(128,128,255)
    )

    embed.set_footer(text=f"Requested by: {message.author}", icon_url=message.author.avatar_url)

    await message.channel.send(embed=embed)
    add_action(message, "helped", con)
