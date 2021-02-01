import discord
from discord.ext import commands
from os import getenv
from datetime import datetime
import logging
import random
import re
import asyncio
import subprocess
import contextlib
import io
import traceback
import textwrap

intents = discord.Intents.all()

logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename='/home/alwin/botlog/discord.log', mode='a+')
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s",
                                       datefmt="%d/%m/%Y %H:%M:%S"))
logger.addHandler(handler)

TOKEN = getenv("TOKEN")
bot_url = "https://discordapp.com/oauth2/authorize?client_id=652490092539281418&permissions=116800&scope=bot"
bot = commands.Bot(command_prefix="t!", intents=intents)


insults = ["That traitorous bastard {0} left us. Good.",
           "I hope {0} stubs their toe when they get up from their desk",
           "{0}'s mother was a hamster and their father smelled of elderberries",
           "{0}’s head is so minute, that if a hungry cannibal cracked his head open,"
           " there wouldn't be enough to cover a small water biscuit",
           "{0} left the server, I hope they misplace their phone charger",
           "{0} left the server, I hope they get covered in water as they wash a spoon",
           "{0} left the server. They would bore the leggings off a village idiot",
           "{0} left the server. They ride a horse rather less well than another horse would",
           "{0} left the server, I hope they get a minor static zap when they next open a car door",
           "{0} left the server, I hope the wires for their headphones get tangled when they next pull "
           "it out of their pocket",
           "{0} left the server. They look like a bird who swallowed a plate",
           "{0} left the server, I hope they struggle to find matching socks "
           "when they next get dressed in the morning",
           "I hope {0} accidentally presses the restart button "
           "when they try to shut down their computer",
           "I hope someone puts an empty tub of ice cream in {0}'s freezer",
           "{0} left the server, I hope ants invade their bowl of freshly baked scones",
           "{0} left the server, I hope they go to get a spoon from their drawer only to "
           "find they all need to be washed",
           "{0} left the server, I hope when they next go to sleep they find it too hot for"
           " a blanket but too cold to not have a blanket",
           "{0} left the server, I hope someone has a clicky mechanical keyboard when they are next in a voice chat",
           "{0} left the server, I hope they wake up tomorrow morning to find their phone was "
           "not charging over night and is out of battery",
           "{0} left the server, I hope one day they don't plug their earbuds into their "
           "phone correctly and it plays an embarrassing song in public",
           "{0} left the server. They're so uncivilised that even Obi-Wan "
           "Kenobi didn't want to throw his blaster over their dead body",
           "I bet that {0} is way more unfunny than the people of r/okbuddyretard and r/dankmemes",
           "I hope {0} stubs their toe real hard against the table"]


async def convert(ctx, argument):
    try:  # Check if we receive a user
        user = await commands.UserConverter().convert(ctx, argument)
        if not user.dm_channel:  # If bot doesn't have DM channel with user
            await user.create_dm()  # Open new DM channel
        return user.dm_channel  # Return DM channel
    except commands.BadArgument:
        try:  # Check if we receive a local text channel
            text = await commands.TextChannelConverter().convert(ctx, argument)
            return text
        except commands.BadArgument:  # Try and get a global text channel
            text = ctx.bot.get_channel(int(argument))
            if text:
                return text


def mention_convert(match):
    try:
        if "&" in match.group(1):  # Role mention
            return match.group(2)
        elif "@" in match.group(1):  # User mention
            user = bot.get_user(int(match.group(2)))
            return f"({user.name}:{user.id})"
        elif "#" in match.group(1):  # Channel mention
            channel = bot.get_channel(int(match.group(2)))
            return f"({channel.name}:{channel.id})"
    except AttributeError:
        return f"{match.group(2)}"


class LinkCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.linked_channels = {}

    def is_linked(self, channel_id):
        if channel_id in self.linked_channels.keys():
            return True
        if channel_id in self.linked_channels.values():
            return True
        return False

    def get_link(self, channel_id):  # the bool is whether or not it's the dict key (the channel that I'm using)
        if channel_id in self.linked_channels.keys():
            return self.bot.get_channel(self.linked_channels[channel_id]), True
        for key in self.linked_channels.keys():
            if self.linked_channels[key] == channel_id:
                return self.bot.get_channel(key), False

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return
        if self.is_linked(message.channel.id):
            if self.get_link(message.channel.id)[1]:
                if message.content.startswith(self.bot.command_prefix):
                    return
                try:
                    channel = self.get_link(message.channel.id)[0]
                    if not channel:
                        channel = await self.bot.fetch_user(self.linked_channels[message.channel.id])
                    await channel.send(message.content)
                    await message.add_reaction("✅")
                except discord.Forbidden:
                    await message.add_reaction("❎")
            else:
                channel = self.get_link(message.channel.id)[0]
                if not channel:
                    channel = await self.bot.fetch_user(self.linked_channels[message.channel.id])
                fixed_message = re.sub(r"<(@!?|#|&)(\d+)>", mention_convert, message.content, flags=re.MULTILINE)
                await channel.send(f"{message.author}({message.author.id}): {fixed_message}")

        elif isinstance(message.channel, discord.DMChannel):
            if message.content.startswith(self.bot.command_prefix):
                return

            fixed_message = re.sub(r"<(@!?|#|&)(\d+)>", mention_convert, message.content, flags=re.MULTILINE)

            piped = bot.get_channel(690520896473137162)
            await piped.send(f"{message.author}({message.author.id}): {fixed_message}")

    @commands.command(aliases=["pipe"])
    @commands.is_owner()
    async def link(self, ctx, channel):
        channel = await convert(ctx, channel)
        print("type of channel: " + str(type(channel)))
        self.linked_channels[ctx.channel.id] = channel.id
        await ctx.send("done!")

    @commands.command(aliases=["unpipe"])
    @commands.is_owner()
    async def unlink(self, ctx):
        if self.linked_channels[ctx.channel.id]:
            del self.linked_channels[ctx.channel.id]
            await ctx.send("done!")
        else:
            await ctx.send("not linked!")


class EvalCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_result = None

    @staticmethod
    def cleanup_code(content):
        """Automatically removes code blocks from the code."""
        # remove ```py\n```
        if content.startswith('```') and content.endswith('```'):
            return '\n'.join(content.split('\n')[1:-1])

        # remove `foo`
        return content.strip('` \n')

    async def run_process(self, command):
        try:
            process = await asyncio.create_subprocess_shell(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            result = await process.communicate()
        except NotImplementedError:
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            result = await self.bot.loop.run_in_executor(None, process.communicate)

        return [output.decode() for output in result]

    @commands.is_owner()
    @commands.command(name='eval', aliases=['python', 'run'], hidden=True)
    async def _eval(self, ctx, *, body: str):
        """Runs arbitrary python code"""

        env = {
            'bot': self.bot,
            'ctx': ctx,
            'channel': ctx.channel,
            'author': ctx.author,
            'guild': ctx.guild,
            'message': ctx.message,
            '_ret': self._last_result
        }

        env.update(globals())

        body = self.cleanup_code(body)
        stdout = io.StringIO()

        to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

        try:
            exec(to_compile, env)
        except Exception as e:
            return await ctx.send(f'```py\n{e.__class__.__name__}: {e}\n```')

        func = env['func']
        try:
            with contextlib.redirect_stdout(stdout):
                ret = await func()
        except Exception as e:
            value = stdout.getvalue()
            await ctx.send(f'```py\n{value}{traceback.format_exc()}\n```')
        else:
            value = stdout.getvalue()
            try:
                await ctx.message.add_reaction('😎')
            except:
                pass

            if ret is None:
                if value:
                    await ctx.send(f'```py\n{value}\n```')
            else:
                self._last_result = ret
                await ctx.send(f'```py\n{value}{ret}\n```')


@bot.command()
@commands.is_owner()
async def ping(ctx):
    """
    sends the time at which command was run
    """
    now = datetime.now()
    await ctx.send(now)


@bot.command()
@commands.is_owner()
async def reply(ctx, user: discord.User, *, msg):
    try:
        await user.send(msg)
        await ctx.message.add_reaction("✅")
    except discord.Forbidden:
        await ctx.message.add_reaction("❎")


@bot.command()
@commands.is_owner()
async def rld_log(ctx):
    bot.reload_extension("Cogs.LogCog")
    await ctx.send("reloaded LogCog!")


@bot.command()
@commands.is_owner()
async def rld_reddit(ctx):
    bot.reload_extension("Cogs.RedditCog")
    await ctx.send("reloaded RedditCog!")


@bot.command()
@commands.is_owner()
async def rld_parse(ctx):
    bot.reload_extension("Cogs.ParseCog")
    await ctx.send("reloaded ParseCog!")

@bot.command()
@commands.is_owner()
async def coglist(ctx):
    await ctx.send(bot.cogs.keys())


@bot.event
async def on_ready():
    logging.info("logged in")


@bot.event
async def on_member_remove(member):
    msg = random.choice(insults)
    name = member.display_name

    asyncio.sleep(0.5)
    welcome = discord.utils.get(member.guild.channels, name="welcome")

    await welcome.send(msg.format(name))


bot.add_cog(LinkCog(bot))
bot.add_cog(EvalCog(bot))

bot.load_extension("Cogs.LogCog")
bot.load_extension("Cogs.ParseCog")
bot.load_extension("Cogs.RedditCog")

print("logged in!")
bot.run(TOKEN)
