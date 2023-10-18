import streamlit as st
import itertools
import random
import os
import pandas as pd
import numpy as np
from collections import defaultdict


# Model for a player
class Player:
    def __init__(self, name, gender, level):
        self.name = name
        self.gender = gender
        self.level = level

    def __str__(self):
        return f"{self.name} ({self.gender}, {self.level})"

# Functions to save and load state
def save_state():
    # Convert players and scheduled games to dictionaries for saving in CSV
    player_dicts = [{"name": player.name, "gender": player.gender, "level": player.level} for player in st.session_state.all_players]
    scheduled_game_dicts = [[{"name": player.name, "gender": player.gender, "level": player.level} for player in game] for game in st.session_state.scheduled_games]

    df = pd.DataFrame({
        'players': [str(player_dicts)],
        'scheduled_games': [str(scheduled_game_dicts)],
        'inprogress_game': [st.session_state.get("inprogress_game")]
    })

    df.to_csv("scheduler_state.csv", index=False)

def load_state():
    if os.path.exists("scheduler_state.csv"):
        df = pd.read_csv("scheduler_state.csv")
        players_data = eval(df['players'].iloc[0])
        games_data = eval(df['scheduled_games'].iloc[0])

        players = [Player(data['name'], data['gender'], data['level']) for data in players_data]
        scheduled_games = [[Player(player_data['name'], player_data['gender'], player_data['level']) for player_data in game] for game in games_data]

        st.session_state.all_players = players
        st.session_state.scheduled_games = scheduled_games
        st.session_state.inprogress_game = df['inprogress_game'].iloc[0]


# Function to get possible teams based on levels
def get_possible_teams(level, players):
    level_players = [player for player in players if player.level == level]
    
    adjacent_levels = {
        'C': ['D+'],
        'D+': ['C', 'D'],
        'D': ['D+', 'E+'],
        'E+': ['D']
    }
    
    for combination in itertools.combinations(level_players, 4):
        yield list(combination)
    
    for adj_level in adjacent_levels[level]:
        combined_players = level_players + [player for player in players if player.level == adj_level]
        if len(combined_players) >= 4:
            for combination in itertools.combinations(combined_players, 4):
                yield list(combination)

st.title("Badminton Scheduler")
load_state()  # Load the state first

# At the beginning of your app, after load_state()

if 'all_players' not in st.session_state:
    st.session_state.all_players = []

if 'scheduled_games' not in st.session_state:
    st.session_state.scheduled_games = []

if 'inprogress_game' not in st.session_state:
    st.session_state.inprogress_game = None


# Tabs
tabs = ["Add Player", "View Players", "Schedule", "In-Progress Games", "Reshuffle & Clear"]
selected_tab = st.selectbox("Choose a tab", tabs)

# Initialize state variables if not present
all_players = st.session_state.get("all_players", [])
scheduled_games = st.session_state.get("scheduled_games", [])

# Add Player Tab
if selected_tab == "Add Player":
    st.subheader("Add Player")
    player_name = st.text_input("Name")
    player_gender = st.radio("Gender", ["Male", "Female"])
    player_level = st.selectbox("Level", ["C+", "C", "D+", "D", "E+"])

    if st.button("Add Player"):
        new_player = Player(player_name, player_gender, player_level)
        all_players.append(new_player)
        st.session_state.all_players = all_players
        st.toast("New player "+ new_player.name + " added successfully")
        save_state()

elif selected_tab == "View Players":
    st.subheader("All Players")

    # Convert the list of Player objects to a DataFrame
    data = {
        "Name": [player.name for player in all_players],
        "Gender": [player.gender for player in all_players],
        "Level": [player.level for player in all_players]
    }
    df = pd.DataFrame(data)

    # Create a dictionary to store the count of games for each player
    player_game_counts = {player.name: 0 for player in all_players}

    # Update the count of games for each player
    for game in scheduled_games:
        for player in game:
            player_game_counts[player.name] += 1

    # Add the "Games Played" column to the DataFrame
    df["Games Played"] = df["Name"].map(player_game_counts)

    # Sort the DataFrame by Name
    df = df.sort_values(by="Name")

    # Reset the index
    df = df.reset_index(drop=True)

    # Display the sorted DataFrame in a table format
    st.table(df)


# Schedule Tab
elif selected_tab == "Schedule":
    st.subheader("Generate Schedule")

    if st.button("Generate Schedule"):
        possible_teams = []

        # Extracting all players who are already scheduled
        scheduled_players = [player for game in scheduled_games for player in game]

        # Extracting players in the in-progress game
        inprogress_players = []
        if st.session_state.get("inprogress_game") is not None:
            inprogress_game_idx = st.session_state.get("inprogress_game", -1)
            if not np.isnan(inprogress_game_idx) and inprogress_game_idx >= 0:
                inprogress_players = scheduled_games[int(inprogress_game_idx)]

        # Getting the list of players who are yet to be scheduled and not in in-progress games
        unscheduled_players = [player for player in all_players if player not in scheduled_players and player not in inprogress_players]

        new_games = []
        for _ in range(6):
            for level in ["C", "D+", "D", "E+"]:
                possible_teams.extend(get_possible_teams(level, unscheduled_players))
            
            if possible_teams:
                new_game = random.choice(possible_teams)
                new_games.append(new_game)
                # Remove scheduled players from the unscheduled list
                for player in new_game:
                    unscheduled_players.remove(player)
                possible_teams.clear()
            else:
                break
        
        scheduled_games.extend(new_games)
        st.session_state.scheduled_games = scheduled_games
        save_state()
       
    
    # Button to clear all scheduled games
    if st.button("Clear All Scheduled Games"):
        scheduled_games.clear()  # Clear the list of scheduled games
        st.session_state.scheduled_games = []
        st.session_state.inprogress_game = None  # Reset in-progress game
        save_state()

    st.subheader("Current Schedules")
    inprogress_game = st.session_state.get("inprogress_game", None)
    for idx, game in enumerate(scheduled_games):
        if inprogress_game == idx:
            st.write(f"Court {idx + 1} (In Progress): {', '.join(str(player) for player in game)}")
        else:
            st.write(f"Court {idx + 1}: {', '.join(str(player) for player in game)}")


# In-Progress Games Tab
elif selected_tab == "In-Progress Games":
    st.subheader("Manage In-Progress Games")
    inprogress_game = st.session_state.get("inprogress_game", None)
    if inprogress_game is not None:
        st.write(f"Court {inprogress_game + 1} is currently in progress!")
    else:
        st.write("No games are currently in progress.")

# Reshuffle & Clear Tab
elif selected_tab == "Reshuffle & Clear":
    st.subheader("Clear Local Storage")
    if st.button("Clear State"):
        if os.path.exists("scheduler_state.csv"):
            os.remove("scheduler_state.csv")
        st.session_state.clear()