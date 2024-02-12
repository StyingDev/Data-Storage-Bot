import os
import discord
import asyncio
import json
from typing import Union
from discord.ext import commands

# Bot configuration
UPLOAD_FOLDER = 'uploads'  # Main folder to store uploaded files
USER_DATA_FILE = 'user_data.json'  # File to store user data (user IDs and usage)

# Define intents
intents = discord.Intents.default()

# Specify which intents your bot will use
intents.messages = True
intents.guilds = True
intents.guild_messages = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Ensure the main upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Ensure the user data file exists
if not os.path.exists(USER_DATA_FILE):
    with open(USER_DATA_FILE, 'w') as file:
        json.dump({}, file)

# Function to load user data from JSON
def load_user_data():
    with open(USER_DATA_FILE, 'r') as file:
        return json.load(file)

# Function to save user data to JSON
def save_user_data(user_data):
    with open(USER_DATA_FILE, 'w') as file:
        json.dump(user_data, file)

# Function to create user folder if it doesn't exist
def create_user_folder(user_id):
    user_folder = os.path.join(UPLOAD_FOLDER, str(user_id))
    if not os.path.exists(user_folder):
        os.makedirs(user_folder)






# Function to create user folder if it doesn't exist
def create_user_folder(user_id):
    user_folder = os.path.join(UPLOAD_FOLDER, str(user_id))
    if not os.path.exists(user_folder):
        os.makedirs(user_folder)

# Event: Bot is ready
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')

# Event: Bot receives a command
@bot.event
async def on_command(ctx):
    user_id = ctx.author.id
    create_user_folder(user_id)

# Command: Upload
@bot.hybrid_command(name='upload', help='Upload the file to the storage.')
async def upload(ctx):
    if not ctx.message.attachments:
        await ctx.send('Please upload one or more files.')
        return

    user_id = ctx.author.id
    user_name = ctx.author.name  # Get Discord username
    create_user_folder(user_id)

    total_size_mb = 0
    for attachment in ctx.message.attachments:
        file_name = attachment.filename
        file_size_mb = attachment.size / (1024 * 1024)

        # Check user's storage limit
        user_data = load_user_data()
        user_info = user_data.get(str(user_id), {'usage': 0, 'limit': 500, 'username': user_name})
        user_usage = user_info.get('usage', 0)
        user_limit = user_info.get('limit', 500)  # Default limit is 500 MB

        if user_usage + file_size_mb > user_limit:
            await ctx.send(f'You have exceeded your storage limit of {user_limit} MB.')
            return

        file_path = os.path.join(UPLOAD_FOLDER, str(user_id), file_name)

        await ctx.send(f'Are you sure you want to upload "{file_name}"? Type "yes" or "no".')

        def check(message):
            return message.author == ctx.author and message.channel == ctx.channel and message.content.lower() in ['yes', 'no']

        try:
            message = await bot.wait_for('message', timeout=60.0, check=check)

            if message.content.lower() == 'yes':
                await attachment.save(file_path)
                total_size_mb += file_size_mb
                user_info['usage'] = user_usage + file_size_mb
                user_data[str(user_id)] = user_info
                save_user_data(user_data)
                await ctx.send(f'File "{file_name}" uploaded successfully.')
            else:
                await ctx.send(f'Uploading of "{file_name}" cancelled.')
        except asyncio.TimeoutError:
            await ctx.send(f'Uploading of "{file_name}" cancelled due to inactivity.')

    await ctx.send(f'Total size of uploaded files: {total_size_mb:.2f} MB')

# Command: List uploaded files
@bot.hybrid_command(name='files', help='Lists the following files uploaded to the database.')
async def files(ctx):
    user_id = ctx.author.id
    user_folder = os.path.join(UPLOAD_FOLDER, str(user_id))

    if not os.path.exists(user_folder):
        await ctx.send('No files uploaded yet.')
        return

    files_list = os.listdir(user_folder)
    if not files_list:
        await ctx.send('No files uploaded yet.')
        return

    # Create embedded message
    embed = discord.Embed(title='Uploaded Files', color=discord.Color.blue())
    total_size_mb = 0
    for index, file_name in enumerate(files_list, start=1):
        file_path = os.path.join(user_folder, file_name)
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        total_size_mb += file_size_mb
        embed.add_field(name=f'{index}. {file_name}', value=f'Size: {file_size_mb:.2f} MB', inline=False)

    # Add total size information to the description
    embed.description = f'Total size: {total_size_mb:.2f} MB'

    await ctx.send(embed=embed)

# Command: Download a file
@bot.hybrid_command(name='download', help='Download the files uploaded in the database.')
async def download(ctx, file_identifier):
  user_id = str(ctx.author.id)
  user_folder = os.path.join(UPLOAD_FOLDER, user_id)

  try:
      if user_folder:
          file_index = int(file_identifier)
          files_list = os.listdir(user_folder)
          if 1 <= file_index <= len(files_list):
              file_name = files_list[file_index - 1]
              file_path = os.path.join(user_folder, file_name)

              file_size = os.path.getsize(file_path)
              max_file_size = 25 * 1024 * 1024  # 25 MB limit for Discord
              if file_size > max_file_size:
                  await ctx.send('File size exceeds the maximum allowed limit of 25 MB.')
                  return

              with open(file_path, 'rb') as file:
                  file_data = discord.File(file, filename=file_name)
                  await ctx.send(f'Downloading file "{file_name}"...', file=file_data)
          else:
              await ctx.send('Invalid file index.')
      else:
          await ctx.send('No files uploaded yet.')
  except ValueError:
      files_list = os.listdir(user_folder)
      if file_identifier in files_list:
          file_path = os.path.join(user_folder, file_identifier)

          file_size = os.path.getsize(file_path)
          max_file_size = 25 * 1024 * 1024  # 25 MB limit for Discord
          if file_size > max_file_size:
              await ctx.send('File size exceeds the maximum allowed limit of 25 MB.')
              return

          with open(file_path, 'rb') as file:
              file_data = discord.File(file, filename=file_identifier)
              await ctx.send(f'Downloading file "{file_identifier}"...', file=file_data)
      else:
          await ctx.send('File not found.')


@bot.hybrid_command()
async def delete(ctx, file_identifier, name='delete', help='Delete the file listed in the database.'):
  user_id = str(ctx.author.id)
  user_folder = os.path.join(UPLOAD_FOLDER, user_id)

  try:
      if user_folder:
          file_index = int(file_identifier)
          files_list = os.listdir(user_folder)
          if 1 <= file_index <= len(files_list):
              file_name = files_list[file_index - 1]
              file_path = os.path.join(user_folder, file_name)

              os.remove(file_path)
              await ctx.send(f'File "{file_name}" deleted successfully.')
          else:
              await ctx.send('Invalid file index.')
      else:
          await ctx.send('No files uploaded yet.')
  except ValueError:
      files_list = os.listdir(user_folder)
      if file_identifier in files_list:
          file_path = os.path.join(user_folder, file_identifier)

          os.remove(file_path)
          await ctx.send(f'File "{file_identifier}" deleted successfully.')
      else:
          await ctx.send('File not found.')
  except MissingRequiredArgument:
      await ctx.send("Please provide the file index or filename to delete.")


# Run the bot
bot.run("ODU1MDY2MjcwMzc0MDM1NDU3.GZXP1b.l3CAK9OFrQ9I0jKVe-BUssv0YPJIQA6FR_kDzc")
