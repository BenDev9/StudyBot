import discord
from discord.ext import commands
from github import Github
import github
from contextlib import closing
import studybot


async def check_prev_inv(discord_user):
    """
    Checks the database to see if/who a specific discord user has invited to the github organization.
    :param discord_user: discord.User object.
    :return: tuple containing the id of the github account the user invited, or None.
    """
    with closing(studybot.db_conn.cursor()) as conn:
        async with studybot.lock:
            query = 'SELECT github_id FROM github_invites WHERE discord_id = ?'
            conn.execute(query, (discord_user.id,))
            db_output = conn.fetchone()
            return db_output


class GitHubIntegration(commands.Cog, name='GitHub Integration'):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='github-join', help=studybot.help_dict.get('github-join'))
    async def join(self, ctx: commands.Context, github_name=None) -> None:
        # Make sure they included the github_name arg, and send a response.
        if not github_name:
            msg = 'You need to include your GitHub Username like this: '
            msg += '`!github-join StudyBot`'
            await ctx.message.reply(msg)
            return
        else:
            github_session = Github(studybot.TOKENS.get('GITHUB_API_KEY'))
            # Get the user object.
            try:
                github_user = github_session.get_user(github_name)
            except github.UnknownObjectException:
                await ctx.message.reply('The GitHub user you requested cannot be found. Double-Check your spelling.')
                return
            # Get the organization object.
            try:
                placement_org = github_session.get_organization(studybot.github_org_name)
            except github.UnknownObjextException:
                msg = 'The GitHub organization you are trying to join cannot be found.'
                msg += ' Please try again later, and contact a mod if the issue persists.'
                await ctx.message.reply(msg)
                return

            # Verify that the user has not already invited a GitHub account to the org.
        if await check_prev_inv(ctx.author) is None:
            # Verify that the user is not already in the org.
            if placement_org.has_in_members(github_user):
                await ctx.message.reply('That user is already in the organization, and cannot be invited.')
                return
            # Invite the user to the organization.
            else:
                placement_org.invite_user(github_user)

            # Add the Discord ID and the GitHub ID to the database table
            with closing(studybot.db_conn.cursor()) as conn:
                async with studybot.lock:
                    query = 'INSERT INTO github_invites (discord_id, github_id) VALUES (?, ?)'
                    conn.execute(query, (ctx.author.id, github_user.id))
                    studybot.db_conn.commit()

            # Send a confirmation message in Discord.
            await ctx.message.reply(f'Invited {github_user.login} to the GitHub Organization.')
        else:
            msg = f'Cannot invite {github_user.login} to the organization, because you have already invited '
            msg += 'another GitHub account. Please contact a moderator if this is a mistake.'
            await ctx.message.reply(msg)

    @commands.command(name='github-reset', help=studybot.help_dict.get('github-reset'))
    @commands.has_role(studybot.admin_role_id)
    async def reset_user(self, ctx: commands.Context, discord_user: discord.User = None) -> None:
        if not discord_user:
            await ctx.message.reply('You need to tag the user to reset their abilities.')
            return

        # Find who the user previously invited to the org.
        db_output = await check_prev_inv(discord_user)
        # If the user hasn't invited anyone
        if db_output is None:
            await ctx.message.reply('This user has not invited anyone to the org.')
            return

        g = Github(studybot.TOKENS.get('GITHUB_API_KEY'))
        # Get the GitHub user object.
        try:
            g_user = g.get_user_by_id(int(db_output[0]))
        except github.UnknownObjextException:
            g_user = None
        # Get the GitHub organization object.
        try:
            g_org = g.get_organization(studybot.github_org_name)
        except github.UnknownObjectException:
            msg = 'The GitHub organization cannot be found. Please try again later.'
            await ctx.message.reply(msg)
            return

        # Revoke the GitHub account's invite or remove them from the Organization (if the user exists).
        if g_user:
            g_org.remove_from_membership(g_user)

        # Delete the Database entry showing that the user invited someone
        with closing(studybot.db_conn.cursor()) as conn:
            async with studybot.lock:
                query = 'DELETE FROM github_invites WHERE discord_id = ?'
                conn.execute(query, (discord_user.id, ))
                studybot.db_conn.commit()
        await ctx.message.reply(f'Successfully reset {discord_user.mention}s ability to invite users')


def setup(bot):
    bot.add_cog(GitHubIntegration(bot))