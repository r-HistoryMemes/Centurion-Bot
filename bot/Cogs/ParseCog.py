import logging
from utils import BaseCog
import argparse
from configparser import ConfigParser
from discord.ext import commands
import re

logger = logging.getLogger('discord.ParseCog')


class StrArgParse(argparse.ArgumentParser):
    def exit(self, status=0, message=None):
        if message:
            raise Exception(message)

    def error(self, message):
        raise Exception(message)


class ParserCog(BaseCog.Base):
    def __init__(self, bot):
        super().__init__(bot)
        self.arg_help = """```usage: 
        t!change
        [--T|--Turn [on|off]]
        [--i|--id ID]
        [--m|--msg MESSAGE]

        change settings for reddit bot replies

        optional arguments:
          --h, --help            show this help message
          --T [on/off], --Turn [on/off]
                                whether to turn replies on or off
          --i ID, --id ID       ID of the SoTS
          --m MESSAGE, --msg MESSAGE
                                message to reply with to posts```"""
        self.confobj = ConfigParser()
        self.parser = StrArgParse(
                        prog="t!change",
                        description="change settings for reddit bot replies",
                        usage="t!change\n[--T|--Turn [on|off]]\n[--i|--id ID]\n[--m|--msg MESSAGE]",
                        add_help=False
                    )

        self.parser.add_argument(
            "--T", "--Turn",
            choices=["on", "off"],
            help="whether to turn replies on or off",
            metavar="[on/off]",
            dest="status"
        )

        self.parser.add_argument(
            "--i", "--id",
            help="ID of the SoTS",
            metavar="ID",
            dest="id"
        )

        self.parser.add_argument(
            "--m", "--msg",
            nargs="*",
            help="message to reply with to posts",
            dest="message"
        )

        self.parser.add_argument(
            "--h", "--help",
            help="shows this help message",
            action='store_true',
            dest="help"
        )

    @commands.command()
    async def change(self, ctx, *, args):
        """
        Make bot reply to posts. For usage, write "t!change --help"
        """
        config_dict = {}

        try:
            options = self.parser.parse_args(
                re.sub(r"\n--", " --", args).strip().split(" "))  # make string readable for argpasrse

            if vars(options)['help']:
                await ctx.send(self.arg_help)
                return

            for option, value in vars(options).items():
                if value:
                    if option == "message":
                        value = " ".join(value)  # turn message from list to string
                    config_dict[option] = value  # make sure only set values get in

            self.confobj.read("/home/alwin/bot/utils/reddit_config.cfg")  # read from existing settings to not override them

            if not self.confobj.sections():  # if making a completely new file
                self.confobj["REPLY"] = {}

            for option, value in config_dict.items():  # add new settings to configparser
                self.confobj["REPLY"][option] = value

            with open("/home/alwin/bot/utils/reddit_config.cfg", 'w+') as conf:  # write settings to config file
                self.confobj.write(conf)

            await ctx.send("settings changed, restarting")
            self.bot.reload_extension("Cogs.RedditCog")
        except Exception as e:
            logger.exception("error while parsing setting change", exc_info=e)
            await ctx.send(e)


def setup(bot):
    bot.add_cog(ParserCog(bot))
