# Downvote-Bot ![downvotebot icon](./static/dvb_icon.png "dvb icon")


This is a side project that uses the python discord api to make a bot that can react to some stuff and do a couple other commands. It's original intent was to just downvote some things, but here is a full list of commands:

## Commands: (prefix: #)

```
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
```

---
## Getting Started

create `credentials.json`

it should look something like this:
```
{
    "discord_secret_key":"actual_stuff_here",
    "reddit_client_id":"actual_stuff_here",
    "reddit_client_secret":"actual_stuff_here"
}
```

set up virtual environment:

`python -m venv venv`

`venv\Scripts\activate`

`pip install -r requirements.txt`

`python dvb.py`

OR

use docker:
`docker-compose up -d`

NOTE: I'm not sure why, but when using docker-compose without -d, no text is output to the terminal. I am not familiar enough with docker to debug this, so its a bit weird for now.