from discord.ext import commands


class Base(commands.Cog):
    def __init__(self, bot):
        # this is just for perms
        self.mods = [
            145022157385105408,  # thedelta
            212824235993726976,  # AoYJ
            239257324362006532,  # Fliminch
            247821911357128705,  # Marco9711
            271067059163496448,  # Leon Trotsky
            275100868083318796,  # Adam Gilchrist
            310939008870121483,  # Torven
            314321520111517697,  # WogBat
            320817721245827073,  # Tensoll
            320989312390922240,  # twarqulas
            333287495351402518,  # ItCameFromSpace
            344018701856800778,  # GreenPitchforks
            344421108528971776,  # BronzeLeagueHero
            440592707304554496,  # Alwin
            474063831690248202,  # NobleForward
            772550579062440007,  # brigadoon
            320663210225303552,  # DomCie
            758125013361885194,  # EquivalentInflation
            772548523416879144,  # miserablemembership
            772558696403173396,  # Rum
            532210844436529184   # wonderb0lt
        ]
        self.bot = bot

    # checks that the person running the command is a mod
    async def cog_check(self, ctx):
        return ctx.author.id in self.mods
