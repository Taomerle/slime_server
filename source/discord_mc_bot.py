import discord, asyncio, os, sys, server_functions
from discord.ext import commands, tasks
from server_functions import lprint, use_rcon, format_args, mc_command, get_server_status

# Exits script if no token.
if os.path.isfile(server_functions.bot_token_file):
    with open(server_functions.bot_token_file, 'r') as file:
        TOKEN = file.readline()
else: print("Missing Token File:", server_functions.bot_token_file), exit()

# Make sure this doesn't conflict with other bots.
bot = commands.Bot(command_prefix='?')

@bot.event
async def on_ready():
    await bot.wait_until_ready()
    lprint("Bot PRIMED.")


# ========== Basics: Say, whisper, online players, server command pass through.
class Basics(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @commands.command(aliases=['command', '/', 'c'])
    async def server_command(self, ctx, *args):
        """
        Pass command directly to server.

        Args:
            command: Server command, do not include the slash /.

        Usage:
            ?command broadcast Hello Everyone!
            ?/ list

        Note: You will get the latest 2 lines from server output, if you need more use ?log.
        """

        args = format_args(args)
        mc_command(f"{args}")
        lprint(ctx, "Sent command: " + args)
        await ctx.invoke(self.bot.get_command('serverlog'), lines=2)

    @commands.command(aliases=['broadcast', 's'])
    async def say(self, ctx, *msg):
        """
        Broadcast message to online players.

        Args:
            msg: Message to broadcast.

        Usage:
            ?s Hello World!
        """

        msg = format_args(msg, return_empty=True)
        mc_command('say ' + msg)
        if not msg:
            await ctx.send("Usage example: `?s Hello everyone!`")
        else: await ctx.send("Message circulated to all active players!")
        lprint(ctx, f"Server said: {msg}")

    @commands.command(aliases=['whisper', 't'])
    async def tell(self, ctx, player, *msg):
        """
        Message online player directly.

        Args:
            player: Player name, casing does not matter.
            msg: The message, no need for quotes.

        Usage:
            ?tell Steve Hello there!
            ?t Jesse Do you have diamonds?
        """

        msg = format_args(msg)
        mc_command(f"tell {player} {msg}")
        await ctx.send("Communiqué transmitted to: `{player}`.")
        lprint(ctx, f"Messaged {player} : {msg}")

    @commands.command(aliases=['pl'])
    async def players(self, ctx):
        """
        Show list of online players and how many out of server limit.
        """

        response = mc_command("list")

        if use_rcon: log_data = response
        else:
            await asyncio.sleep(1)
            log_data = server_functions.get_output('players online')

        if not log_data:
            await ctx.send("**Error:** Trouble fetching player list.")
            return

        log_data = log_data.split(':')
        text = log_data[-2]
        player_names = log_data[-1]
        # If there's no players active, player_names will still contain some anso escape characters.
        if len(player_names.strip()) < 5:
            await ctx.send(text + '.')
        else:
            # Outputs player names in special discord format. If using RCON, need to clip off 4 trailing unreadable characters.
            players_names = [f"`{i.strip()[:-4]}`\n" if use_rcon else f"`{i.strip()}`\n" for i in (log_data[-1]).split(',')]
            await ctx.send(text + ':\n' + ''.join(players_names))
        lprint(ctx, "Fetched player list.")


# ========== Player: gamemode, kill, tp, etc
class Player(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @commands.command(aliases=['pk'])
    async def kill(self, ctx, player, *reason):
        """
        Kill a player.

        Args:
            player: Target player, casing does not matter.
            reason [Optional]: Reason for kill, do not put in quotes.

        Usage:
            ?kill Steve Because he needs to die!
            ?pk Steve
        """

        reason = format_args(reason)
        mc_command(f"say WARNING | {player} will be EXTERMINATED! | {reason}.")
        mc_command(f'kill {player}')
        await ctx.send(f"`{player}` assassinated!")
        lprint(ctx, f"Killed: {player}")

    @commands.command(aliases=['delaykill', 'dk'])
    async def delayedkill(self, ctx, player, delay=5, *reason):
        """
        Kill player after time elapsed.

        Args:
            player: Target player.
            delay: Wait time in seconds.
            reason [Optional]: Reason for kill.

        Usage:
            ?delayedkill Steve 5 Do I need a reason?
            ?pk Steve 15
        """

        reason = format_args(reason)
        mc_command(f"say WARNING | {player} will self-destruct in {delay}s | {reason}.")
        await ctx.send(f"Killing {player} in {delay}s!")
        await asyncio.sleep(delay)
        mc_command(f'kill {player}')
        await ctx.send(f"`{player}` soul has been freed.")
        lprint(ctx, f"Delay killed: {player}")

    @commands.command(aliases=['tp'])
    async def teleport(self, ctx, player, target, *reason):
        """
        Teleport player to another player.

        Args:
            player: Player to teleport.
            target: Destination, player to teleport to.
            reason [Optional]: Reason for teleport.

        Usage:
            ?teleport Steve Jesse I wanted to see him
            ?tp Jesse Steve
        """

        reason = format_args(reason)
        mc_command(f"say INFO | Flinging {player} towards {target} in 5s | {reason}.")
        await asyncio.sleep(5)
        mc_command(f"tp {player} {target}")
        await ctx.send(f"`{player}` and {target} touchin real close now.")
        lprint(ctx, f"Teleported {player} to {target}")

    @commands.command(alises=['gm'])
    async def gamemode(self, ctx, player, state, *reason):
        """
        Change player's gamemode.

        Args:
            player: Target player.
            state: Game mode survival|adventure|creative|spectator.
            reeason [Optional]: Optional reason for gamemode change.

        Usage:
            ?gamemode Steve creative In creative for test purposes.
            ?gm Jesse survival
        """

        reason = format_args(reason)
        mc_command(f"say {player} now in {state} | {reason}.")
        mc_command(f"gamemode {state} {player}")
        await ctx.send(f"`{player}` is now in `{state}` indefinitely.")
        lprint(ctx, f"Set {player} to: {state}")

    @commands.command(aliases=['gamemodetimed', 'tgm', 'gmt'])
    async def timedgamemode(ctx, player, state, duration=None, *reason):
        """
        Change player's gamemode for specified amount of seconds, then will change player back to survival.

        Args:
            player: Target player.
            state: Game mode survival|adventure|creative|spectator.
            duration: Duration in seconds.
            *reason [Optional]: Reason for change.

        Usage:
            ?timedgamemode Steve spectator Steve needs a time out!
            ?tgm Jesse adventure Jesse going on a adventure.
        """

        try: duration = int(duration)
        except:
            await ctx.send("You buffoon, I need a number to set the duration!")
            return

        reason = format_args(reason)
        mc_command(f"say {player} set to {state} for {duration}s | {reason}.")
        await ctx.send(f"`{player}` set to `{state}` for {duration}s, then will revert to survival.")
        mc_command(f"gamemode {state} {player}")
        await asyncio.sleep(duration)
        mc_command(f"gamemode survival {player}")
        await ctx.send(f"`{player}` is back to survival.")
        lprint(ctx, f"Set gamemode: {player} for {duration}")


# ========== Permissions: Ban, Kick, OP.
class Permissions(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @commands.command()
    async def kick(self, ctx, player, *reason):
        """
        Kick player from server.

        Args:
            player: Player to kick.
            reason [Optional]: Optional reason for kick.

        Usage:
            ?kick Steve Because he was trolling
            ?kick Jesse
        """

        reason = format_args(reason)
        mc_command(f'say WARNING | {player} will be ejected from server in 5s | {reason}.')
        await asyncio.sleep(5)
        mc_command(f"kick {player}")
        await ctx.send(f"`{player}` is outta here!")
        lprint(ctx, f"Kicked {player}")

    @commands.command()
    async def ban(self, ctx, player, *reason):
        """
        Ban player from server.

        Args:
            player: Player to ban.
            reason [Optional]: Reason for ban.

        Usage:
            ?ban Steve Player killing
            ?ban Jesse
        """

        reason = format_args(reason)
        mc_command(f"say WARNING | Banishing {player} in 5s | {reason}.")
        await asyncio.sleep(5)
        mc_command(f"kick {player}")
        mc_command(f"ban {player} {reason}")
        await ctx.send(f"Dropkicked and exiled: `{player}`.")
        lprint(ctx, f"Banned {player} : {reason}")

    @commands.command(aliases=['unban'])
    async def pardon(self, ctx, player, *reason):
        """
        Pardon (unban) player.

        Args:
            player: Player to pardon.
            reason [Optional]: Reason for pardon.

        Usage:
            ?pardon Steve He has turn over a new leaf.
            ?unban Jesse
        """

        reason = format_args(reason)
        mc_command(f"say INFO | {player} has been vindicated! | {reason}.")
        mc_command(f"pardon {player}")
        await ctx.send(f"Cleansed `{player}`.")
        lprint(ctx, f"Pardoned {player} : {reason}")

    # Gets online players, formats output for Discord depending on using RCON or reading from server log.
    @commands.command(aliases=['bl', 'bans'])
    async def banlist(self, ctx):
        """
        Show list of current bans.
        """

        banned_players = ''
        response = mc_command("banlist")

        if use_rcon:
            if 'There are no bans' in response:
                banned_players = 'No exiles!'
            else:
                data = response.split(':', 1)
                for line in data[1].split('.'):
                    line = line.split(':')
                    reason = server_functions.remove_ansi(line[-1].strip())  # Sometimes you'll get ansi escape chars in your reason.
                    player = line[0].split(' ')[0].strip()
                    banner = line[0].split(' ')[-1].strip()
                    banned_players += f"`{player}` banned by `{banner}`: `{reason}`\n"

                banned_players += data[0] + '.'  # Gets line that says 'There are x bans'.

        else:
            for line in filter(None, server_functions.get_output('banlist').split('\n')):  # Filters out blank lines you sometimes get.
                print(line)
                if 'There are no bans' in line:
                    banned_players = 'No exiles!'
                    break
                elif 'There are' in line:
                    banned_players += line.split(':')[-2]
                    break

                # Gets relevant data from current log line, and formats it for Discord output.
                # Example line: Slime was banned by Server: No reason given
                # Extracts Player name, who banned the player, and the reason.
                ban_log_line = line.split(':')[-2:]
                reason = ban_log_line[-1][:-2].strip()
                player = ban_log_line[0].split(' ')[1].strip()
                banner = ban_log_line[0].split(' ')[-1].strip()
                banned_players += f"`{player}` banned by `{banner}`: `{reason}`\n"

        await ctx.send(banned_players)
        lprint(ctx, f"Fetched banned list.")

    @commands.command()
    async def oplist(self, ctx):
        """
        Show list of current server operators.
        """

        op_players = [f"`{i['name']}`" for i in server_functions.get_json('ops.json')]
        await ctx.send('\n'.join(op_players))
        lprint(ctx, f"Fetched server operators list.")

    @commands.command()
    async def opadd(self, ctx, player, *reason):
        """
        Add server operator (OP).

        Args:
            player: Player to make server operator.
            reason [Optional]: Optional reason for new OP status.

        Usage:
            ?opadd Steve Testing purposes
            ?opadd Jesse
        """

        reason = format_args(reason)
        mc_command(f"say INFO | {player} has become a God! | {reason}")
        mc_command(f"op {player}")
        await ctx.send(f"`{player}` too op now. ||Please nerf soon rito!||")
        lprint(ctx, f"New server op: {player}")

    @commands.command()
    async def opremove(self, ctx, player, *reason):
        """
        Remove player OP status (deop).

        Args:
            player: Target player.
            reason [Optional]: Reason for deop.

        Usage:
            ?opremove Steve abusing goodhood.
            ?opremove Jesse
        """

        reason = format_args(reason)
        mc_command(f"say INFO | {player} fell from grace! | {reason}")
        mc_command(f"deop {player}")
        await ctx.send(f"`{player}` stripped of Godhood!")
        lprint(ctx, f"Removed server op: {player}")

    @commands.command(aliases=['optimed', 'top'])
    async def timedop(self, ctx, player, time_limit=1):
        """
        Set player as OP for a set amount of seconds.

        Args:
            player: Target player.
            time_limit: Time limit in seconds.

        Usage:
            ?timedop Steve 30 Need to check something real quick.
            ?top jesse 60
        """

        await ctx.send(f"Granting `{player}` OP status for {time_limit}m!")
        mc_command(f"say INFO | {player} granted God status for {time_limit}m!")
        mc_command(f"op {player}")
        lprint(ctx, f"OP {player} for {time_limit}.")
        await asyncio.sleep(time_limit * 60)
        await ctx.send(f"Removed `{player}` OP status!")
        mc_command(f"say INFO | {player} is back to being a mortal.")
        mc_command(f"deop {player}")
        lprint(ctx, f"Remove OP {player}")


# ========== World weather, time.
class World(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @commands.command(aliases=['sa'])
    async def saveall(self, ctx):
        """Save current world, just sends save-all command to server."""

        mc_command('save-all')
        await ctx.send("I saved the world!")
        await ctx.send("**NOTE:** This is not the same as making a backup using `?backup`.")
        lprint(ctx, "Saved world.")

    @commands.command(aliases=['weather'])
    async def setweather(self, ctx, state, duration=0):
        """
        Set weather.

        Args:
            state: <clear|rain|thunder>: Weather to change to.
            duration [Optional]: Duration in seconds.

        Usage:
            ?setweather rain
            ?weather thunder 60
        """

        mc_command(f'weather {state} {duration * 60}')
        if duration:
            await ctx.send(f"I see some `{state}` in the near future.")
        else: await ctx.send(f"Forecast entails `{state}`.")
        lprint(ctx, f"Weather set to: {state} for {duration}")

    @commands.command(aliases=['time'])
    async def settime(self, ctx, set_time=None):
        """
        Set time.

        Args:
            set_time: Set time either using day|night|noon|midnight or numerically.

        Usage:
            ?settime day
            ?time 12
        """

        if set_time:
            mc_command(f"time set {set_time}")
            await ctx.send("Time updated!")
        else: await ctx.send("Need time input, like: `12`, `day`")
        lprint(ctx, f"Timed set: {set_time}")


# ========== Server: Start, Stop, Status, edit property, server log.
class Server(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @commands.command(aliases=['info', 'stat', 'stats'])
    async def status(self, ctx, show_players=True):
        """Shows server active status, version, motd, and online players"""

        stats = get_server_status()
        if stats:
            await ctx.send("Server is now __**ACTIVE**__.")
            await ctx.send(f"version: `{stats['version']}`")
            await ctx.send(f"motd: `{stats['motd']}`")
            if show_players: await ctx.invoke(self.bot.get_command('players'))
        else: await ctx.send("Server is __**INACTIVE**__.")
        lprint(ctx, "Fetched server status.")

    @commands.command(aliases=['log'])
    async def serverlog(self, ctx, lines=5):
        """
        Show server log.

        Args:
            lines [5:Optional]: How many most recent lines to show.

        Usage:
            ?serverlog
            ?log 10
        """

        log_data = server_functions.get_output(file_path=server_functions.server_log_file, lines=lines)
        await ctx.send(f"`{log_data}`")
        lprint(ctx, f"Fetched {lines} lines from bot log.")

    @commands.command()
    async def start(self, ctx):
        """Start server."""

        if server_functions.start_minecraft_server():
            await ctx.send("***Booting Server...***")
        else: await ctx.send("**Error** starting server, contact administrator!")
        await asyncio.sleep(5)
        await ctx.send("***Fetching server status...***")
        await ctx.invoke(self.bot.get_command('status'), show_players=False)
        lprint(ctx, "Starting server.")

    @commands.command()
    async def stop(self, ctx):
        """Stop server, gives players 15s warning."""

        mc_command('say WARNING | Server will halt in 15s!')
        await ctx.send("***Halting in 15s...***")
        await asyncio.sleep(10)
        mc_command('say WARNING | 5s left!')
        await asyncio.sleep(5)
        mc_command('stop')
        await ctx.send("World Saved. Server __**HALTED**__")
        lprint(ctx, "Stopping server.")

    @commands.command(aliases=['reboot'])
    async def restart(self, ctx):
        """Messages player that the server will restart in 15s, then will stop and startup server."""

        lprint(ctx, "Restarting server.")
        if get_server_status():
            await ctx.invoke(self.bot.get_command('stop'))
        await asyncio.sleep(5)
        await ctx.invoke(self.bot.get_command('start'))

    # Edit server properties.
    @commands.command(aliases=['property', 'p'])
    async def properties(self, ctx, target_property='', *value):
        """
        Check or change a server.properties property.

        Note: Passing in 'all' for target property argument (with nothing for value argument) will show all the properties.

        Args:
            target_property: Target property to change, must be exact in casing and spelling and some may include a dash -.
            value: New value. For some properties you will need to input a lowercase true or false, and for others you may input a string (quotes not needed).

        Usage:
            ?property motd
            ?property spawn-protection 2
            ?property all
        """

        if not target_property:
            await ctx.send("Need at leat property name, optionally input new value to change property.\nUsage example: `?property motd`, `?property motd Hello World!`")
            return

        if not value: value = ''
        else: value = ' '.join(value)

        get_property = server_functions.edit_properties(target_property, value)[1]
        await ctx.send(get_property)
        lprint(ctx, f"Server property: {get_property[1:][:-1]}")

    @commands.command(aliases=['omode'])
    async def onlinemode(self, ctx, mode=''):
        """
        Check or enable/disable onlinemode property.

        Args:
            mode <true|false>: Update onlinemode property in server.properties file. Must be in lowercase.

        Usage:
            ?onlinemode true
            ?omode false
        """

        await ctx.send(server_functions.edit_properties('online-mode', mode)[1])
        lprint(ctx, "Online-mode: " + mode)

    @commands.command()
    async def motd(self, ctx, *message):
        """
        Check or Update motd property.

        Args:
            message: New message for message of the day for server. No quotes needed.

        Usage:
            ?motd
            ?motd YAGA YEWY!
        """

        if message:
            message = format_args(message)
            server_functions.edit_properties('motd', message)
            await ctx.send("Message of the day updates!")
            lprint("Updated motd: " + message)
        else: await ctx.send(server_functions.edit_properties('motd')[1])

    @commands.command()
    async def rcon(self, ctx, state=''):
        """
        Check RCON staatus or enable/disable enable-rcon property.

        Args:
            state <true|false>: Set enable-rcon property in server.properties file, true or false must be in lowercase.

        Usage:
            ?rcon
            ?rcon true
            ?rcon false

        """

        response = server_functions.edit_properties('enable-rcon', state)[1]
        await ctx.send(response)


# ========== World backup/restore functions.
class World_Saves(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=['backups', 'worldsaves'])
    async def saves(self, ctx, amount=5):
        """
        Show world folder backups.

        Args:
            amount [5:Optional]: Number of most recent backups to show.

        Usage:
            ?saves
            ?saves 10
        """

        embed = discord.Embed(title='World Backups')
        worlds = server_functions.fetch_worlds(amount)
        for save in worlds:
            embed.add_field(name=worlds.index(save), value=f"`{save}`", inline=False)

        await ctx.send(embed=embed)
        await ctx.send("Use `?restore <index>` to restore world save.")
        await ctx.send("**WARNING:** Restore will overwrite current world. Make a backup using `?backup <codename>`.")
        lprint(ctx, f"Fetched {amount} most recent world saves.")

    @commands.command(aliases=['backupworld', 'worldbackup'])
    async def backup(self, ctx, *name):
        """
        Backup current world save folder.

        Args:
            name [Optional]: Keywords or codename for new save. No quotes needed.

        Usage:
            ?backup everything not on fire
            ?backup Jan checkpoint
        """

        if not name:
            await ctx.send("Hey! I need a name or keywords to make a backup!")
            return False
        name = format_args(name)

        mc_command(f"say INFO | Standby, world is currently being archived. Codename: {name}")
        await ctx.send("***Saving current world...***")
        mc_command(f"save-all")
        await asyncio.sleep(5)

        new_backup = server_functions.backup_world(name)
        if new_backup:
            await ctx.send(f"Cloned and archived your world to:\n`{new_backup}`.")
        else: await ctx.send("**Error** saving the world! || it's doomed!||")

        await ctx.invoke(self.bot.get_command('saves'))
        lprint(ctx, "New backup: " + new_backup)

    @commands.command(aliases=['restoreworld', 'worldrestore'])
    async def restore(self, ctx, index=None):
        """
        Restore from world backup.

        Note: This will not make a backup beforehand, suggest doing so with ?backup command.

        Args:
            index: Get index with ?saves command.

        Usage:
            ?restore 3
        """

        try: index = int(index)
        except:
            await ctx.send("I need a index number of world to restore, use `?saves` to get list of saves")
            return False

        fetched_restore = server_functions.get_world_from_index(index)
        lprint(ctx, "Restoring to: " + fetched_restore)
        await ctx.send(f"***Restoring...*** `{fetched_restore}`")
        mc_command(f"say WARNING | Initiating jump to save point in 5s! | {fetched_restore}")
        await asyncio.sleep(5)

        if get_server_status(): await ctx.invoke(self.bot.get_command('stop'))  # Stops if server is running.

        server_functions.restore_world(restore)  # Gives computer time to move around world files.
        await asyncio.sleep(3)

        await ctx.invoke(self.bot.get_command('start'))

    @commands.command('deleteworld')
    async def delete(self, ctx, index):
        """
        Delete a world backup.

        Args:
            index: Get index with ?saves command.

        Usage:
            ?delete 0
        """

        try: index = int(index)
        except:
            await ctx.send("Need a index number of world to obliterate, use `?saves` to get list of saves")
            return False

        to_delete = server_functions.get_world_from_index(index)
        server_functions.delete_world(to_delete)
        await ctx.send(f"World as been incinerated!")
        await ctx.invoke(self.bot.get_command('saves'))
        lprint(ctx, "Deleted: " + to_delete)

    @commands.command(aliases=['rebirth', 'hades'])
    async def newworld(self, ctx):
        """
        Deletes current world save folder (does not touch other server files).

        Note: This will not make a backup beforehand, suggest doing so with ?backup command.
        """

        mc_command("say WARNING | Project Rebirth will commence in T-5s!")
        await ctx.send(":fire:**INCINERATED:**:fire:")
        await ctx.send("**NOTE:** Next startup will take longer, to generate new world. Also, server settings will be preserved, this does not include data like player's gamemode status, inventory, etc.")

        if get_server_status(): await ctx.invoke(self.bot.get_command('stop'))

        server_functions.restore_world(reset=True)
        await asyncio.sleep(3)

        await ctx.invoke(self.bot.get_command('start'))
        lprint(ctx, "World Reset.")

    @commands.command(aliases=['serverupdate'])
    async def update(self, ctx):
        """
        Updates server.jar file by downloading latest from official Minecraft website.

        Note: This will not make a backup beforehand, suggest doing so with ?serverbackup command.
        """

        lprint(ctx, "Updating server.jar...")
        await ctx.send("***Updating...***")

        if get_server_status(): await ctx.invoke(self.bot.get_command('stop'))
        await asyncio.sleep(5)

        await ctx.send("***Downloading latest server.jar***")
        server = server_functions.download_new_server()

        if server:
            await ctx.send(f"Downloaded latest version: `{server}`")
            await asyncio.sleep(3)
            await ctx.invoke(self.bot.get_command('start'))
        else: await ctx.send("**Error:** Updating server. Suggest restoring from a backup.")
        lprint(ctx, "Server Updated.")


# ========== Server backup/restore functions.
class Server_Saves(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(aliases=['serverbackups'])
    async def serversaves(self, ctx, amount=5):
        """
        Show server backups.

        Args:
            amount [5:Optional]: How many most recent backups to show.

        Usage:
            ?serversaves
            ?serversaves 10
        """

        embed = discord.Embed(title='Server Backups')
        servers = server_functions.fetch_servers(amount)
        for save in servers:
            embed.add_field(name=servers.index(save), value=f"`{save}`", inline=False)

        await ctx.send(embed=embed)
        await ctx.send("Use `?serverrestore <index>` to restore server.")
        await ctx.send("**WARNING:** Restore will overwrite current server. Make a backup using `?serverbackup <codename>`.")
        lprint(ctx, f"Fetched latest {amount} world saves.")

    @commands.command(aliases=['backupserver'])
    async def serverbackup(self, ctx, *name):
        """
        Create backup of server files (not just world save folder).

        Args:
            name [Optional]: Keyword or codename for save.

        Usage:
            ?serverbackup Dec checkpoint
        """

        if not name:
            await ctx.send("Hey! I need a name or keywords to make a backup!")
            return False

        name = format_args(name)
        await ctx.send("***Backing Up...***")

        mc_command(f"save-all")
        await asyncio.sleep(5)
        new_backup = server_functions.backup_server(name)

        if new_backup:
            await ctx.send(f"New backup:\n`{new_backup}`.")
        else: await ctx.send("**Error** saving server!")

        await ctx.invoke(self.bot.get_command('servers'))
        lprint(ctx, "New backup: " + new_backup)

    @commands.command(aliases=['restoreserver'])
    async def serverrestore(self, ctx, index=None):
        """
        Restore server backup.

        Args:
            index: Get index number from ?serversaves command.

        Usage:
            ?serverrestore 0
        """

        try: index = int(index)
        except:
            await ctx.send("I need a index number of world to restore, use `?saves` to get list of saves")
            return False

        fetched_restore = server_functions.get_server_from_index(index)
        lprint(ctx, "Restoring to: " + fetched_restore)
        await ctx.send(f"***Restoring...*** `{fetched_restore}`")
        mc_command(f"say WARNING | Initiating jump to save point in 5s! | {fetched_restore}")
        await asyncio.sleep(5)

        if get_server_status(): await ctx.invoke(self.bot.get_command('stop'))

        if server_functions.restore_server(restore):
            await ctx.send("Server **Restored!**")
        else: await ctx.send("**Error:** Could not restore server!")

        await asyncio.sleep(3)
        await ctx.invoke(self.bot.get_command('start'))

    @commands.command(aliases=['serverremove', 'serverrm'])
    async def serverdelete(self, ctx, index):
        """
        Delete a server backup.

        Args:
            index: Index of server save, get with ?serversaves command.

        Usage:
            ?serverdelete 0
            ?serverrm 5
        """

        try: index = int(index)
        except:
            await ctx.send("Need a index number of world to obliterate, use `?saves` to get list of saves")
            return False

        to_delete = server_functions.get_server_from_index(index)
        server_functions.delete_server(to_delete)
        await ctx.send(f"Server backup deleted!")
        await ctx.invoke(self.bot.get_command('servers'))
        lprint(ctx, "Deleted: " + to_delete)

    @commands.command(aliases=['resetserver'])
    async def serverreset(self, ctx):
        """Deletes all current server files, keeps world and server backups."""

        mc_command("say WARNING | Resetting server in 5s!")
        await ctx.send("**Resetting Server...**")
        await ctx.send("**NOTE:** Next startup will take longer, to setup server and generate new world. Also `server.properties` file will reset!")

        if get_server_status(): await ctx.invoke(self.bot.get_command('stop'))
        server_functions.restore_server(reset=True)
        lprint(ctx, "Server Reset.")


# ========== Bot: Restart, botlog, help2.
class Bot_Functions(commands.Cog):
    def __init__(self, bot): self.bot = bot

    # Restarts this bot script.
    @commands.command(aliases=['rbot', 'rebootbot'])
    async def restartbot(self, ctx):
        """Restart this bot."""

        os.chdir(server_functions.server_functions_path)
        await ctx.send("***Rebooting Bot...***")
        lprint(ctx, "Restarting bot.")
        os.execl(sys.executable, sys.executable, *sys.argv)

    @commands.command()
    async def botlog(self, ctx, lines=5):
        log_data = server_functions.get_output(file_path=server_functions.bot_log_file, lines=lines)
        await ctx.send(f"`{log_data}`")
        lprint(ctx, f"Fetched {lines} lines from log.")

    @commands.command()
    async def help2(self, ctx):
        """Shows help page with embed format."""

        lprint(ctx, "Fetched help page.")
        current_command, embed_page, contents = 0, 1, []
        pages, current_page, page_limit = 3, 1, 15

        def new_embed(page):
            return discord.Embed(title=f'Help Page {page}/{pages}')

        embed = new_embed(embed_page)
        for command in server_functions.get_csv('command_info.csv'):
            if not command: continue

            embed.add_field(name=command[0], value=f"{command[1]}\n{', '.join(command[2:])}", inline=False)
            current_command += 1
            if not current_command % page_limit:
                embed_page += 1
                contents.append(embed)
                embed = new_embed(embed_page)
        contents.append(embed)

        # getting the message object for editing and reacting
        message = await ctx.send(embed=contents[0])
        await message.add_reaction("◀️")
        await message.add_reaction("▶️")

        # This makes sure nobody except the command sender can interact with the "menu"
        def check(reaction, user):
            return user == ctx.author and str(reaction.emoji) in ["◀️", "▶️"]

        while True:
            try:
                # waiting for a reaction to be added - times out after x seconds, 60 in this
                reaction, user = await bot.wait_for("reaction_add", timeout=60, check=check)
                if str(reaction.emoji) == "▶️" and current_page != pages:
                    current_page += 1
                    await message.edit(embed=contents[current_page - 1])
                    await message.remove_reaction(reaction, user)
                elif str(reaction.emoji) == "◀️" and current_page > 1:
                    current_page -= 1
                    await message.edit(embed=contents[current_page - 1])
                    await message.remove_reaction(reaction, user)

                # removes reactions if the user tries to go forward on the last page or backwards on the first page
                else: await message.remove_reaction(reaction, user)

            # end loop if user doesn't react after x seconds
            except asyncio.TimeoutError:
                await message.delete()
                break


# Adds functions to bot.
cogs = [Basics, Player, Permissions, World, Server, World_Saves, Server_Saves, Bot_Functions]
for i in cogs: bot.add_cog(i(bot))

if __name__ == '__main__': bot.run(TOKEN)