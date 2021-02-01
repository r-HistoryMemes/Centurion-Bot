import discord
from discord.ext import commands, menus
from utils.urlshortner import make_tiny
from datetime import datetime
import logging
from utils import BaseCog
from google.cloud import datastore

logger = logging.getLogger('discord.LogCog')


class LogMenu(menus.ListPageSource):
    def __init__(self, data):
        super().__init__(data, per_page=1)

    async def format_page(self, menu, entries):
        res = entries[0]
        author = entries[1]

        embed = discord.Embed(title="Log Entry", colour=discord.Colour(0xff4500),
                              description="Log entry of action done by bot",
                              timestamp=datetime.utcnow())

        embed.set_footer(text=f"requested by {author.name}", icon_url=author.avatar_url)

        embed.add_field(name="Mod", value=res["MOD"])
        embed.add_field(name="Action", value=res["ACTION"])
        embed.add_field(name="Type", value=res["TYPE"])
        embed.add_field(name="URL", value=make_tiny(res["LINK"]))
        embed.add_field(name="Time", value=res["TIME"].strftime("%d/%m/%y %H:%M"))

        return embed


class Logs(BaseCog.Base):
    def __init__(self, bot):
        super().__init__(bot)
        self.client = datastore.Client()

    @commands.command()
    async def getlog(self, ctx, id):
        """
        :param id:
        """
        try:
            query = list(self.client.query(kind="Action").add_filter('ID', '=', id).fetch())
            if len(query) == 0:
                await ctx.send("no logs with such an ID")
                return

            if len(query) == 1:
                res = query[0]
                embed = discord.Embed(title="Log Entry", colour=discord.Colour(0xff4500),
                                      description="Log entry of action done by bot",
                                      timestamp=datetime.utcnow())

                embed.set_footer(text=f"requested by {ctx.author.name}", icon_url=ctx.author.avatar_url)

                embed.add_field(name="Mod", value=res["MOD"])
                embed.add_field(name="Action", value=res["ACTION"])
                embed.add_field(name="Type", value=res["TYPE"])
                embed.add_field(name="URL", value=make_tiny(res["LINK"]))
                embed.add_field(name="Time", value=res["TIME"].strftime("%d/%m/%y %H:%M"))

                await ctx.send(embed=embed)

            else:  # This does paging, from https://github.com/Rapptz/discord-ext-menus
                res_list = [(query[i], ctx.author) for i in range(len(query))]
                page = menus.MenuPages(source=LogMenu(res_list), clear_reactions_after=True)
                await page.start(ctx)

        except Exception as e:
            logger.exception("Exception occured while trying to get log entry", exc_info=e)
            await ctx.send("error occurred while retrieving log")

    # @commands.command()
    # async def count(self, ctx, type=None, action=None):
    #     # TODO: https://cloud.google.com/datastore/docs/concepts/stats
    #     count = self.count_log(type, action)
    #     await ctx.send("""number of such actions: {0}""".format(count[0]))


def setup(bot):
    bot.add_cog(Logs(bot))
