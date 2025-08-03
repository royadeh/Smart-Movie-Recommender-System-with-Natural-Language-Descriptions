from discord.ext import commands

from surprise import Dataset, Reader, SVD

import os
import pandas as pd
from openai import OpenAI
from dotenv import load_dotenv
from fuzzywuzzy import process

load_dotenv()  # Loads environment variables from a .env file

# Set your OpenAI API key from an environment variable
OPEN_AI_API_KEY = os.getenv('OPEN_AI_API_KEY')
openAI_client = OpenAI(
    api_key=OPEN_AI_API_KEY,
)

DATASET_FOLDER = "ml-100k"

next_user_id = 0
discord_user_mapping = {}
movie_title_mapping = {}

instruction = "You are acting as a middle-man type interface between the front end user typing in discord to a discord bot, and a backend machine learning algorithm that recommends movies. Your job is to listen to what the users are asking and then provide an output in the format with essentially one thing and that is the movie title that they are curious about. If someone asks anything different than whether they would like a movie, ignore and say 'I can only provide assistance finding out information about movie recommendations'."

def get_movie_name_from_ai(incomplete_movie_name):
    instruction = "You are acting as a middle-man type interface between the front end user typing in discord to a discord bot, and a backend machine learning algorithm that recommends movies. Your job is to listen to what the users are asking and then provide an output in the format with essentially one thing and that is the movie title that they are curious about. If someone asks anything different than whether they would like a movie, ignore and say 'I can only provide assistance finding out information about movie recommendations'."

    response = openAI_client.chat.completions.create(
        model="gpt-3.5-turbo",
    messages=[
            {"role": "system", "content": instruction},
            {"role": "user", "content": f"What's the full name of the following movie: {incomplete_movie_name}"},
        ],
    )

    return response.choices[0].message.content


def ask_openai_about_movies(incomplete_movie_name):
    """
    Send a message to the OpenAI ChatCompletion API and return the response.
    """
    print(f"the incomple movie name is: {incomplete_movie_name}")
    response = openAI_client.chat.completions.create(
        model="gpt-4",  # Or "gpt-4" if available
        messages=[
            {"role": "system", "content": instruction},
            {"role": "user", "content": f"What's the full name of the following movie: {incomplete_movie_name}"}
        ]
    )
    return response.choices[0].message.content

def load_users():
    global next_user_id

    df_users = pd.read_csv(f"{DATASET_FOLDER}/u.user",
                           sep="|",
                           names=["userID", "age", "gender", "username", "discordID"])

    # dprint("Dataset users loaded")
    discord_users = df_users[df_users["gender"] == "D"]
    for index, row in discord_users.iterrows():
        discord_user_mapping[int(row['discordID'])] = row['userID']

    next_user_id = max(df_users["userID"].tolist(), default=0) + 1

load_users()

def load_movies():
    # Read the movies data from the u.item file
    df_movies = pd.read_csv(f"./{DATASET_FOLDER}/u.item",
                            usecols=[0, 1],
                            sep="|",
                            names=["movieID", "title"],
                            encoding='ISO-8859-1')

    print(df_movies.head())
    # Populate the movie_title_mapping dictionary
    for index, row in df_movies.iterrows():
        movie_title_mapping[int(row['movieID'])] = row['title']

    print("Movies loaded")

load_movies()
@commands.command(name="add_user", description="Register a new user to the MovieLens dataset", help="This command registers the user in the MovieLens dataset. Usage: !!add_user")
async def add_user(ctx: commands.Context) -> None:
    global next_user_id
    # Check if the user is already registered
    if ctx.author.id in discord_user_mapping:
        return await ctx.send(
            f"user {ctx.author.name} is already registered with id {discord_user_mapping[ctx.author.id]}")
    # Register the new user
    discord_user_mapping[ctx.author.id] = next_user_id
    # Append the new user data to the u.user file
    with open('./ml-100k/u.user', 'a') as file:
        file.write(f"{next_user_id}|18|D|{ctx.author.name}|{ctx.author.id}\n")
    # Inform the user about the successful registration
    await ctx.send(f"user {ctx.author.name} has been registered with id {discord_user_mapping[ctx.author.id]}")
    next_user_id += 1  # Increment the next user id for the next registration

@commands.command(name="rec", description="Recommend a movie", help="This command generates an estimated rating for a movie using SVD. Usage: !!rec <movie_id>")
async def recommend(ctx, movie_id: int):
    # Check if the user is registered
    if ctx.author.id not in discord_user_mapping:
        return await ctx.send("You must register using !!add_user before getting recommendations")

    # Check if the movie id is valid
    if movie_id not in movie_title_mapping:
        return await ctx.send("Invalid movie id")
    # We are going to use SVD to predict the user rating for a movie

    user_id = discord_user_mapping[ctx.author.id]

    # Load the ratings data from the u.data file
    df_ratings = pd.read_csv("ml-100k/u.data",
                           sep="\t",
                           names=["userID", "itemID", "rating", "timestamp"])
    # Create a Surprise Dataset from our pandas DataFrame
    reader = Reader(rating_scale=(1, 5))
    dataset = Dataset.load_from_df(df_ratings[["userID", "itemID", "rating"]], reader)

    # Factor and epochs

    # Train the SVD alorithm
    trainset = dataset.build_full_trainset()

    algo = SVD(
        n_factors=5,
        n_epochs=200,
        biased=False
    )
    algo.fit(trainset)

    prediction = algo.predict(uid=user_id, iid=movie_id)

    # Check if the prediction was possible
    if prediction.details["was_impossible"]:
        return await ctx.send("Not enough data to make a prediction")

    # Send the estimated rating to the user
    return await ctx.send(f"Estimated rating is {prediction.est} for {movie_title_mapping[movie_id]}")

# Command for a registered Discord user to post a rating for a movie
@commands.command(name="rate", description="Post a rating for a movie with given movie_id and rating", help="This command posts a rating for a movie. Usage: !!rate <movie_id> <rating>")
async def rate(ctx: commands.Context, movie_id: int = commands.parameter(default=-1, description="Movie ID"),
               rating: int = commands.parameter(default=-1, description="Rating between 1 and 5")) -> None:
    # Check if the user is registered
    if ctx.author.id not in discord_user_mapping:
        return await ctx.send("You must first register yourself with !!add_user")
    # Check if the movie id is valid
    if movie_id not in movie_title_mapping:
        return await ctx.send("Invalid movie id")
    # Check if the rating is within the valid range
    if rating < 1 or rating > 5:
        return await ctx.send("Ratings must be between 1 and 5 inclusive")
    # Register the rating
    user_id = discord_user_mapping[ctx.author.id]
    with open('./ml-100k/u.data', 'a') as file:
        file.write(f"{user_id}\t{movie_id}\t{rating}\t0\n")
    # Inform the user about the successful rating submission
    return await ctx.send(f"Your rating of {rating} has been registered for {movie_title_mapping[movie_id]}")

# Command to search the movie list for matching movies and return their ids
@commands.command(name="search_old", description="Search for movies by title", help="This command searches for movies that match the given text. Usage: !!search <search_text>")
async def search(ctx: commands.Context, *, search_text: str) -> None:
    print("Searching for:", search_text)
    # Find matching movies
    matches = [(id, title) for id, title in movie_title_mapping.items() if search_text.lower() in title.lower()]
    # Check if there are any matches
    if len(matches) == 0:
        return await ctx.send("Could not find any titles that match your search")
    # Limit results to at most 10 matches
    matches = matches[:10]
    # Format the results
    output = "\n".join([f"{id}: {title}" for id, title in matches])
    # Send the results to the user, truncated to 2000 characters
    return await ctx.send(output[:2000])

def find_closest_match(partial_movie_name: str, movie_title_mapping: dict) -> tuple:
    """
    Find the closest matching movie title based on the provided partial movie name.

    Args:
        partial_movie_name (str): The partial movie name to search for.
        movie_title_mapping (dict): The dictionary mapping movie IDs to movie titles.

    Returns:
        tuple: A tuple containing the closest matching movie ID and movie title.
               Returns (None, None) if no match is found.
    """
    movie_titles = list(movie_title_mapping.values())

    closest_match, confidence = process.extractOne(partial_movie_name, movie_titles)

    # Find the movie ID that corresponds to the closest match.
    closest_match_id = next((movie_id for movie_id, title in movie_title_mapping.items() if title == closest_match),
                            None)

    return closest_match_id, closest_match

@commands.command(name="search", description="Search for movies by title", help="This command searches for movies that match the given text. Usage: !!search <search_text>")
async def search_with_ai(ctx: commands.Context, *, search_text: str):
    print("Received the name:", search_text)
    movie_name = get_movie_name_from_ai(search_text)
    print(f"The ai response for {search_text} was {movie_name}")
    # Find the closest matching movie in the dataset based on the AI's response.
    closest_match_id, closest_match = find_closest_match(movie_name, movie_title_mapping)
    print(f"The movie most similar to {movie_name} is {closest_match}. ")
    return await ctx.send(f"You are searching for: {movie_name}. We found {closest_match} with id {closest_match_id}")
