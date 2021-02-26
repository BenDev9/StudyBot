#!/home/user/dev/StudyBot/venv/bin/python3
from discord.ext import commands
from discord import Status
import sqlite3
import asyncio
from contextlib import closing
from typing import Union


def get_tokens():
    import os
    from dotenv import load_dotenv
    load_dotenv()
    return os.getenv('DISCORD_TOKEN'), os.getenv('DISCORD_GUILD')


command_list = []
help_dict = {"add-time": "Add the personal amount of study time in minutes.",
             "get-time": "Retrieves the personal amount of hours studied.",
             "all-time": "Retrieves the total amount of study time.",
             "shutdown": "Shuts down the Bot. Need bot-admin."}


def _command_list_adder(func):
    command_list.append(func)
    return func


class StudyBot(commands.Bot):
    _command_list = command_list

    def __init__(self, *args, **kwargs):
        self._db_conn = sqlite3.connect("server.db")
        self._lock = asyncio.Lock()
        super().__init__(*args, **kwargs)
        with closing(self._db_conn.cursor()) as conn:
            table = 'CREATE TABLE IF NOT EXISTS study_time '
            table += '(name text, minutes integer)'
            conn.execute(table)
            self._db_conn.commit()
        for func in self._command_list:
            self.add_command(func)
        try:
            self.obj = commands.Context()
        except KeyError:
            pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self._db_conn.commit()
        self._db_conn.close()
        if not self.is_closed():
            self.logout()

    async def on_ready(self):
        await self.change_presence(status=Status.online)

    @_command_list_adder
    @commands.command(help=help_dict.get('shutdown'))
    async def shutdown(self):
        allowd = False
        # Commands are context objects and have bot as an object
        for role in self.author.roles:
            if "bot-admin" in role.name:
                allowd = True
        if allowd:
            text = "Okay. I, {}, am shutting down"
            await self.bot.change_presence(status=Status.offline)
            await self.reply(text.format(self.bot.user))
            await self.bot.logout()
            return
        msg = "Sorry, you must have the bot-admin role to shutdown this bot."
        await self.reply(msg)

    @_command_list_adder
    @commands.command(name="add-time", help=help_dict.get('add-time'))
    async def add_time(self, minutes: Union[int, str] = 0):
        if isinstance(minutes, str):
            if not minutes.isdigit():
                await self.reply("'{}' is not a proper value".format(minutes))
                return
            minutes = int(minutes)
        msg = "Added {} hours and {} minutes."
        username = str(self.message.author)
        with closing(self.bot._db_conn.cursor()) as conn:
            async with self.bot._lock:
                query = 'SELECT minutes FROM study_time WHERE name = ?'
                conn.execute(query, (username,))
                if conn.fetchone() is None:
                    query = 'INSERT INTO study_time (name, minutes) '
                    query += ' VALUES (?, ?)'
                    conn.execute(query, (username, 0))
                query = 'UPDATE study_time SET minutes = minutes + ? WHERE name = ?'  # noqa: E501
                conn.execute(query, (minutes, username))
                self.bot._db_conn.commit()
        await self.reply(msg.format(*divmod(minutes, 60)), delete_after=120)
        await self.message.delete(delay=120)

    @_command_list_adder
    @commands.command(name="get-time", help=help_dict.get('get-time'))
    async def get_time(self):
        username = str(self.message.author)
        with closing(self.bot._db_conn.cursor()) as conn:
            async with self.bot._lock:
                query = 'SELECT minutes FROM study_time WHERE name = ?'
                conn.execute(query, (username,))
                value = conn.fetchone()
                if value is None:
                    query = 'INSERT INTO study_time (name, minutes) '
                    query += 'VALUES (?, ?)'
                    conn.execute(query, (username, 0))
                    query = 'SELECT minutes FROM study_time WHERE name = ?'  # noqa: E501
                    conn.execute(query, (username,))
                    value = conn.fetchone()[0]
                else:
                    value = value[0]
                msg = "You have contributed {} hours and {} minutes to total."
                await self.reply(msg.format(*divmod(value, 60)))
                self.bot._db_conn.commit()

    @_command_list_adder
    @commands.command(name="all-time", help=help_dict.get('all-time'))
    async def all_time(self):
        with closing(self.bot._db_conn.cursor()) as conn:
            async with self.bot._lock:
                query = 'SELECT minutes FROM study_time'
                conn.execute(query)
                value = sum(i[0] for i in conn.fetchall())
                msg = "The total amount of time studying is {} hours"
                msg += " and {} minutes."
                await self.reply(msg.format(*divmod(value, 60)))
                self.bot._db_conn.commit()


if __name__ == "__main__":
    with StudyBot("!") as bot:
        bot.run(get_tokens()[0])
