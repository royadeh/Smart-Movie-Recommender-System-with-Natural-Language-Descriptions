import discord
import json
import random
import os
from dotenv import load_dotenv
from discord.ext import commands
from recommender cd ~/RecommenderBot
import add_user, recommend, search, rate, search_with_ai


# pull environment variables from the .env file if they cannot be found in your OS environment
load_dotenv()
DISCORD_BOT_TOKEN = os.getenv('DISCORD_TOKEN')

# intents form a list of actions that your bot may want to take on your server
# by default we enable every possible action except three special intents
# for now you can ignore this
intents = discord.Intents.default()
# message_content intent lets the bot read other user messages, this is absolutely necessary or else
# the bot cannot tell if people are using commands
intents.message_content = True

# Load the configuration file
with open('config.json', 'r') as config_file:
    config = json.load(config_file)
# Access the prefix from the config
command_prefix = config['prefix']

# Initialize the bot with the prefix from config
# bot = commands.Bot(command_prefix=command_prefix, intents=intents)
bot = commands.Bot(command_prefix=command_prefix, intents=intents)
bot.add_command(add_user)
bot.add_command(recommend)
bot.add_command(search)
bot.add_command(rate)
bot.add_command(search_with_ai)

# decorators change the functionality of functions
# this one marks it as a handler for the ready event
# this function will trigger exactly once, when the bot starts up
@bot.event
async def on_ready():
    print(f'{bot.user} is now running!')

# This decorator marks the following function as a command
# When a user types "!!ping", the bot will execute this function
# and respond with "Pong!" in the same channel
@bot.command(name="ping")
async def ping(ctx):
    # Sends a simple response back to the channel
    await ctx.send("Pong!")

@bot.command(name="hello")
async def hello(ctx):
    await ctx.send("hi")

# Create rock paper scissor command
@bot.command(name="rps")
async def rps(ctx, *, user_choice):
    print(f"User choice is {user_choice}")
    choices = ["rock", "paper", "scissors"]
    bot_choice = random.choice(choices)
    response = ""
    if user_choice.lower() not in choices:
        response = f"User choice, {user_choice}, is invalid for rock paper scissors-"
    elif user_choice.lower() == bot_choice:
        response = f"Both played {bot_choice}. It's a tie"
    elif (user_choice == "rock" and bot_choice == "scissors") or \
            (user_choice == "paper" and bot_choice == "rock") or \
            (user_choice == "scissors" and bot_choice == "paper"):
        response = f"Bot played {bot_choice}. You win!"
    else:
        response = f"Bot played {bot_choice}. You lose!"
    await ctx.send(response)



# Explanation of the @bot.command decorator:
# The @bot.command decorator registers a function as a command for the bot.
# This allows users to interact with the bot by typing a command prefix (here, !!) followed by the command name.
# In this example, the command name is "ping", so users can type "!!ping" to trigger the ping() function.
# The function can access the context (ctx), which contains details about the command invocation, like the channel.


# To see the list of possible commands : [prefix]help (ie. !!help)

# Main function to run the bot.
def main():
    bot.run(DISCORD_BOT_TOKEN)  # Run the bot with the specified token.


# If this script is run (instead of imported), start the bot.
if __name__ == '__main__':
    main()
