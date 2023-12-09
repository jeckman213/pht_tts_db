"""_summary_
"""
import asyncio
import discord
from discord.ext import commands
import os
from .play_ht import PlayHTModule


class AIVoiceQueue:
    def __init__(self, guild_id: int):
        self.guild_id = guild_id
        self.is_running = False
        self.queue = []
        self.channel_name = None
        self.vc = None

    async def start(self):
        self.is_running = True

        while len(self.queue) > 0:
            current = self.queue.pop(0)
            await self.play(current)

        await self.vc.disconnect()
        self.vc = None
        self.channel_name = None
        self.is_running = False

    async def play(self, sound_info):
        channel = sound_info["channel"]
        filename = sound_info["filename"]

        if not self.channel_name == channel.name:
            if self.vc is not None:
                await self.vc.disconnect()

            self.vc = await channel.connect()
            self.channel_name = channel.name

        source = discord.FFmpegPCMAudio(filename)

        self.vc.play(source)
        while self.vc.is_playing():
            await asyncio.sleep(1.0)

        os.remove(filename)


class AIVoice(commands.Cog):
    """_summary_

    Args:
        commands (_type_): _description_
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.play_ht = PlayHTModule()
        self.guild_queues = {}

    @commands.command(name="voice_sync")
    @commands.is_owner()
    async def voice_sync(self, ctx: commands.Context, sync_type: str) -> None:
        """Sync the application commands"""

        async with ctx.typing():
            if sync_type == "guild":
                self.bot.tree.copy_global_to(guild=ctx.guild)
                await self.bot.tree.sync(guild=ctx.guild)
                await ctx.reply("Synced guild !")
                return

            await self.bot.tree.sync()
            await ctx.reply("Synced global !")

    @commands.command(name="voice_unsync")
    @commands.is_owner()
    async def voice_unsync(self, ctx: commands.Context, unsync_type: str) -> None:
        """Unsync the application commands"""

        async with ctx.typing():
            if unsync_type == "guild":
                self.bot.tree.clear_commands(guild=ctx.guild)
                await self.bot.tree.sync(guild=ctx.guild)
                await ctx.reply("Un-Synced guild !")
                return

            self.bot.tree.clear_commands()
            await self.bot.tree.sync()
            await ctx.reply("Un-Synced global !")

    @discord.app_commands.command(
        name="say", description="Say something with AI voice name and text"
    )
    async def say(self, interaction: discord.Interaction, voice_name: str, text: str):
        """Stops all and clears queue

        Args:
            interaction (_type_): Discord interaction
        """
        await interaction.response.defer()

        guild_id = interaction.user.guild.id

        try:
            channel = interaction.user.voice.channel
            # guild = interaction.user.guild
            # channel = next(channel for channel in guild.channels if channel.name == "General")
        except Exception:
            embed = discord.Embed(title="Error: Please join voice channel")
            embed.set_author(
                name=interaction.user.display_name,
                icon_url=interaction.user.display_avatar.url,
            )
            await interaction.followup.send(embed=embed)
            return

        text_chunks = split_text(text)
        print(text_chunks)
        
        if guild_id not in self.guild_queues:
                self.guild_queues[guild_id] = AIVoiceQueue(guild_id)

        filenames = []
        for chunk in text_chunks:
            filename = self.play_ht.say_and_download(voice_name, chunk)
            if filename is None:
                # Create embed
                embed = discord.Embed(title="Failed to enqueue")
                embed.set_author(
                    name=interaction.user.display_name,
                    icon_url=interaction.user.display_avatar.url,
                )
                await interaction.followup.send(embed=embed)
                return
            
            filenames.append(filename)

        for filename in filenames:
            self.guild_queues[guild_id].queue.append(
                {"channel": channel, "filename": filename}
            )
            
        # Create embed
        embed = discord.Embed(title="Queued")
        embed.set_author(
            name=interaction.user.display_name,
            icon_url=interaction.user.display_avatar.url,
        )
        await interaction.followup.send(embed=embed)

        if not self.guild_queues[guild_id].is_running:
            await self.guild_queues[guild_id].start()

    @discord.app_commands.command(
        name="voices", description="Get current supported voices"
    )
    async def voices(self, interaction: discord.Interaction):
        """Get all currently supported voices

        Args:
            interaction (discord.Interaction): Discord interaction
        """
        await interaction.response.defer()

        voices = self.play_ht.get_voices()

        embed = discord.Embed(title="Voices")
        embed.set_author(
            name=interaction.user.display_name,
            icon_url=interaction.user.display_avatar.url,
        )
        for voice in voices:
            embed.add_field(name=voice["name"], value=voice["id"], inline=False)

        await interaction.followup.send(embed=embed)

    @discord.app_commands.command(name="voice_upload", description="Upload voice")
    async def voice_upload(
        self,
        interaction: discord.Interaction,
        voice_name: str,
        file_upload: discord.Attachment,
    ):
        """Upload voice using voice name and file

        Args:
            interaction (discord.Interaction): Discord interaction
            voice_name (str): Voice name
            file (discord.File): File to upload
        """
        await interaction.response.defer()

        try:
            file_contents = await file_upload.read()

            with open(file_upload.filename, "wb") as file:
                file.write(file_contents)

            with open(file_upload.filename, "rb") as file:
                self.play_ht.upload(voice_name, file_upload.filename, file)

            os.remove(file_upload.filename)

            embed = discord.Embed(title="Uploaded")
            embed.set_author(
                name=interaction.user.display_name,
                icon_url=interaction.user.display_avatar.url,
            )
            embed.add_field(name=voice_name, value=file_upload.filename)

            await interaction.followup.send(embed=embed)
        except Exception as ex:
            print(ex)
            embed = discord.Embed(title="Failed to Upload")
            embed.set_author(
                name=interaction.user.display_name,
                icon_url=interaction.user.display_avatar.url,
            )
            embed.add_field(name=voice_name, value=file_upload.filename)

            await interaction.followup.send(embed=embed)

    @discord.app_commands.command(
        name="voice_delete", description="Delete voice by voice name"
    )
    async def voice_delete(self, interaction: discord.Interaction, voice_name: str):
        """Delete voice by voice name

        Args:
            interaction (discord.Interaction): Discord interaction
            voice_name (str): Voice name
        """
        await interaction.response.defer()

        if self.play_ht.delete(voice_name):
            embed = discord.Embed(title="Successfully deleted")
            embed.set_author(
                name=interaction.user.display_name,
                icon_url=interaction.user.display_avatar.url,
            )
            embed.add_field(name="Voice Name", value=voice_name)
        else:
            embed = discord.Embed(title="Failed to delete")
            embed.set_author(
                name=interaction.user.display_name,
                icon_url=interaction.user.display_avatar.url,
            )
            embed.add_field(name="Voice Name", value=voice_name)

        await interaction.followup.send(embed=embed)


def split_text(text, max_length=400):
    """Splits text by max_length or closes space

    Args:
        text (str): Text
        max_length (int, optional): Max length of chunks. Defaults to 400.

    Returns:
        list: List of chunks
    """
    words = text.split()
    result = []
    current_chunk = ""

    for word in words:
        if len(current_chunk) + len(word) + 1 <= max_length:
            # Add word to the current chunk
            current_chunk += " " + word if current_chunk else word
        else:
            # Start a new chunk
            result.append(current_chunk)
            current_chunk = word

    # Add the last chunk
    if current_chunk:
        result.append(current_chunk)

    return result


async def setup(bot: commands.Bot):
    """Setup for cog

    Args:
        bot (commands.Bot): Discord Commands Bot
    """
    await bot.add_cog(AIVoice(bot))
