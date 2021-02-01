import praw
from utils import BaseCog
from discord.ext import tasks, commands
import logging
from os import getenv
import re
from datetime import datetime
from configparser import ConfigParser
from google.cloud import datastore
from asyncio import sleep

logger = logging.getLogger('reddit')
logger.setLevel(logging.WARNING)
handler = logging.FileHandler(filename='/home/alwin/botlog/reddit.log', mode='a+')
handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s",
                                       datefmt="%d/%m/%Y %H:%M:%S"))
logger.addHandler(handler)


class RedditCog(BaseCog.Base):
    def __init__(self, bot):
        super().__init__(bot)
        self.r = praw.Reddit(  # log into reddit
            username=getenv("REDUSER"),
            password=getenv("REDPASSWD"),
            client_id=getenv("REDID"),
            client_secret=getenv("REDSEC"),
            user_agent="Tim the Centurion v5.1"
        )
        self.pattern = re.compile('REMOVED: (RULE (\d{1,2}))')  # regex to detect flairs

        config_obj = ConfigParser()  # thing that deals with comment reply settings
        config_obj.read("/home/alwin/bot/utils/reddit_config.cfg")
        reply_info = config_obj["REPLY"]

        self.sots_status = reply_info.getboolean("status")
        self.post_message = reply_info["message"]
        self.sots_id = reply_info["id"]

        self.SUB = 'HistoryMemes'
        self.removal_message = "your comment has been removed because it contained a link to a political " \
                               "website/sub: {0}\n\nif you think this was a mistake, please reply to this message"
        self.ban_message = """{0}\n\nPost in question: {1}"""
        BAN_1 = "Rule 1: Post is not about historical event (see extended rules for clarification)"
        BAN_2 = "Rule 2: No reposts, or posts with the same format and joke, are allowed"
        BAN_4 = "Rule 4: Topic falls within 20 year exclusion period, covers a hot topic, or is a meta loophole " \
                "(see extended rules for examples)"
        BAN_5 = "Rule 5: Post is a banned format (see extended rules for a list of banned formats)"
        BAN_9 = "Rule 9: Meme is a banned topic/low quality post (see extended rules for a list and definition)"
        BAN_10 = "Rule 10: Post is karmawhoring (asking for upvotes/interaction or has no humorous intent)"
        BAN_11 = "Rule 11: Post has a lazy title, or the meme depends on the title to work"
        BAN_12 = "Rule 12: No WW2 memes during the weekend (Saturday-Sunday EST), and no complaining about WW2 memes"

        # A general list of infractions and their messages - named "ban" since previously all of them were bannable offenses
        # to be refactored :)
        self.BANS = {
            "1": BAN_1,
            "2": BAN_2,
            "4": BAN_4,
            "5": BAN_5,
            "9": BAN_9,
            "10": BAN_10,
            "11": BAN_11,
            "12": BAN_12
        }

        # Offenses that are bannable
        self.BANNABLE_OFFENSES = {
            "2": {"duration": 1}
        }

        # list of banned sites
        self.banned_sites = [
    "factcheck.org",
    "drudgereport.com",
    "michellemalkin.com",
    "nationalreview.com",
    "townhall.com",
    "weeklystandard.com",
    "dailykos.com",
    "huffingtonpost.com",
    "liberaloasis.com",
    "moveon.org",
    "thenation.com",
    "politicalbase.com",
    "votesmart.org",
    "spot-on.com",
    "alaraby.co.uk",
    "dailytimes.com.pk",
    "theconversation.com",
    "washingtonpost.com",
    "theguardian.com",
    "reddit.com/r/politics",
    "reddit.com/r/the_Donald",
    "reddit.com/r/worldpolitics",
    "infowars.com",
    "aljazeera.net",
    "theblaze.com",
    "bitchute.com"
]

        self.client = datastore.Client()  # connect to the database

        self.main_loop.start()  # this is some weird stuff for async loops I think

    async def comment_remove(self, limit=50):
        """
        this function is responsible for removing all comments
        with banned websites in them. It does not ban the users, just
        removes the comments
        """
        for comment in self.r.subreddit(self.SUB).comments(limit=limit):  # Go through comments
            query = self.client.query(kind="Action").add_filter('TYPE', '=', 'comment')\
                .add_filter("ID", '=', comment.id)
            await sleep(1)
            if list(query.fetch()) is not []:
                continue

            # Check if comment has not allowed website
            sites = [site for site in self.banned_sites if(site in comment.body)]
            if len(sites) > 0:  # if there's at least 1
                try:
                    comment.mod.remove()  # remove comment
                    comment.mod.send_removal_message(self.removal_message.format(sites[0]),
                                                     "political site", type="private")

                    with self.client.transaction():  # add action to database
                        comment_entity = datastore.Entity(key=self.client.key("Action"))
                        comment_entity["ID"] = comment.id
                        comment_entity["ACTION"] = "remove"
                        comment_entity["TYPE"] = "comment"
                        comment_entity["LINK"] = "reddit.com" + comment.permalink
                        comment_entity["MOD"] = "CenturionBot"
                        comment_entity["TIME"] = datetime.utcnow()

                        self.client.put(comment_entity)

                    logger.warning("removed comment with id %s", comment.id)

                except Exception as e:
                    logger.exception("unable to remove comment with id %s", comment.id, exc_info=e)

    async def post_remove(self, limit=20):
        """
        this function is responsible for removing posts
        which have been flaired as rulebreaking
        """
        for log in self.r.subreddit(self.SUB).mod.log(action='editflair', limit=limit):
            # go through flair edits in modlog
            try:
                post = self.r.submission(url="https://www.reddit.com" + log.target_permalink)  # try and get the post
            except TypeError:
                # this happens if the log was editing flair settings and not post flairs
                logger.critical("tried to remove post with URL of None")
                continue

            query = self.client.query(kind="Action").add_filter('TYPE', '=', 'post') \
                .add_filter('ACTION', '=', 'remove').add_filter('ID', '=', post.id)

            await sleep(1)
            # check if the post has already been removed
            if list(query.fetch()) != [] or post.removed or post.link_flair_text is None:
                continue

            post_entity = datastore.Entity(key=self.client.key('Action'))
            post_entity["ID"] = post.id
            post_entity["ACTION"] = "remove"
            post_entity["TYPE"] = "post"
            post_entity["LINK"] = "reddit.com" + post.permalink
            post_entity["MOD"] = f"{log.mod}"
            post_entity["TIME"] = datetime.utcnow()

            # remove post, and ban user if necessary
            match = self.pattern.match(post.link_flair_text)
            if match:
                try:
                    rule_broken = match.group(2)
                    if rule_broken in self.BANNABLE_OFFENSES:
                        self.ban_user(
                            post.author,
                            note=match.group(1),
                            message=self.ban_message.format(
                                self.BANS[match.group(2)],
                                "https://www.reddit.com" + log.target_permalink),
                            duration=self.BANNABLE_OFFENSES[rule_broken].duration
                        )
                    else:
                        with self.client.transaction():
                            comment_entity = datastore.Entity(key=self.client.key("Action"))
                            comment_entity["ID"] = post.id
                            comment_entity["ACTION"] = "reply"
                            comment_entity["TYPE"] = "post"
                            comment_entity["LINK"] = url
                            comment_entity["MOD"] = "CenturionBot"
                            comment_entity["TIME"] = datetime.utcnow()
                            self.client.put(comment_entity)
                        
                        reply = post.reply("""Your post has been removed.
                        
                        It breaks the following rule: {0}""".format(self.BANS[match.group(2)]))
                        reply.mod.distinguish(sticky=True)  # Sticky the comment
                        reply.mod.lock()  # lock reply

                    post.mod.remove()
                    logger.warning("removed post with id %s", post.id)
                    with self.client.transaction():  # add to database
                        self.client.put(post_entity)
                except AttributeError as e:
                    logger.error("Error", e)
                    continue 


    async def ban_user(self, user, note, message, duration=1):
        if not any(self.r.subreddit(self.SUB).banned(redditor=post.author.name)):
            self.r.subreddit(self.SUB).banned.add(note, 
                user,
                note=note,
                ban_message=message,
                duration=duration)

    async def post_reply(self, limit=40):
        """
        this function is responsible for replying to posts to announce
        the new SOTS every month:tm:
        """
        for post in self.r.subreddit(self.SUB).new(limit=limit):
            try:
                url = "https://www.reddit.com" + post.permalink
            except TypeError:
                logger.critical("tried to reply to post with URL of None")
                continue
            if post.id == self.sots_id:
                continue
            query = self.client.query(kind="Action").add_filter('TYPE', '=', 'post') \
                .add_filter('ACTION', '=', 'reply').add_filter('ID', '=', post.id)
            await sleep(1)
            if list(query.fetch()) != [] or post.removed:
                continue

            with self.client.transaction():
                comment_entity = datastore.Entity(key=self.client.key("Action"))
                comment_entity["ID"] = post.id
                comment_entity["ACTION"] = "reply"
                comment_entity["TYPE"] = "post"
                comment_entity["LINK"] = url
                comment_entity["MOD"] = "CenturionBot"
                comment_entity["TIME"] = datetime.utcnow()

                self.client.put(comment_entity)
            reply = post.reply(self.post_message)
            reply.mod.distinguish(sticky=True)  # Sticky the comment
            reply.mod.lock()  # lock reply

            logger.warning("replied to post with id %s", post.id)

    @commands.command()
    async def repost(self, ctx, remove, original):
        """Removes a repost with the ban message containing the original post.
        Remove - Link to the post to remove
        Original - Link to the original post

        WIP please do not use without Alwin's approval, still in testing
        """
        remove_sub = self.r.submission(remove)
        try:
            logger.warning(f"post to remove is {remove} and remove_sub is of type {str(type(remove_sub))}")
            remove_sub.mod.flair(text="REMOVED: RULE 2", flair_template_id="c82f4ea8-117d-11ea-9785-0eb4bbd49045")
            remove_sub.mod.remove()
            logger.warning(f"removed the sub")
        except Exception as e:
            logger.exception(e)
            await ctx.send(e)
        self.r.subreddit(self.SUB).banned.add(
            remove_sub.author,
            note="Rule 2",
            ban_message=self.ban_message.format(self.BANS[2] + f". Original can be found here: {original}", remove),
            duration=2)
        logger.warning(f"banned the user")

        with self.client.transaction():
            post_entity = datastore.Entity(key=self.client.key('Action'))
            post_entity["ID"] = remove_sub.id
            post_entity["ACTION"] = "remove"
            post_entity["TYPE"] = "post"
            post_entity["LINK"] = remove
            post_entity["MOD"] = f"{ctx.author.nick}"
            post_entity["TIME"] = datetime.utcnow()

            self.client.put(post_entity)
        logger.warning("removed post with id %s", remove_sub.id)

        await ctx.send(f"removed post!")

    @commands.command()
    async def check(self, ctx):
        await ctx.send(f"{self.sots_status}\n{self.post_message}\n{self.sots_id}")

    @tasks.loop(seconds=5)
    async def main_loop(self):
        try:
            await self.comment_remove()
            await self.post_remove()

            if self.sots_status:
                await self.post_reply()

        except Exception as e:
            logger.exception("exception occured while running the reddit bot", exc_info=e)

    def cog_unload(self):
        self.main_loop.stop()


def setup(bot):
    bot.add_cog(RedditCog(bot))
