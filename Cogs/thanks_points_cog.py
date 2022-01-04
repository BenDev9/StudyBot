import discord
from discord.ext import commands
import studybot
from contextlib import closing

class Thanks_Points(commands.Cog):
    """ A cog for a rewards system for helping others! """

    word_variations = ["thanks", "thx", "thank", "gracias"]

    def __init__(self, bot):
        self.bot = bot

    async def add_point(user:discord.User, guild:discord.Guild):
        with closing(studybot.db_conn.cursor()) as conn:
            async with studybot.lock:
                query = f"SELECT points FROM thanks_points WHERE id={user.id} AND server={str(guild)}"
                conn.execute(query)

                if conn.fetchone() is None:
                    query = f"INSERT INTO thanks_points (id, points, server) VALUES ({user.id}, 0, {str(guild)})"
                    conn.execute(query)

                query = f"UPDATE thanks_points SET points = points + 1 WHERE id={user.id} AND server = {str(guild)}"
                conn.execute(query)
                studybot.db_conn.commit()

    async def get_points(user:discord.User, guild:discord.Guild):
        with closing(studybot.db_conn.cursor()) as conn:
            async with studybot.lock:
                query = f"SELECT points FROM thanks_points WHERE id = {user.id} AND server = {str(guild)}"
                conn.execute(query)
                value = conn.fetchone()

                if value is None:
                    query = f"INSERT INTO thanks_points (id, points, server) VALUES ({user.id}, 0, {str(guild)})"
                    conn.execute(query)
                    value = 0
                else:
                    value = value[0]

                return value

    @commands.Cog.listener()
    async def on_message(self, message:discord.Message):
        text = message.content.lower()

        if any(item in text for item in self.word_variations):
            mentioned = message.mentions[0] if message.mentions[0] != message.author else None
            if mentioned == None: return

            await self.add_point(mentioned, message.guild)

    @commands.command(name="get-points")
    async def get_points_command(self, ctx:commands.Context, user:discord.User=None):
        if user == None: points = await self.get_points(ctx.author, ctx.guild)
        else: points = await self.get_points(user, ctx.guild)
        await ctx.reply(f"You have {points} points!")