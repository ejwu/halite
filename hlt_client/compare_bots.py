import subprocess
import re

_WINNING_RANK_STRING = "rank #1"
_LOSING_RANK_STRING = "rank #2"
_SPACE_DELIMITER = ' '
_BOT_ID_POSITION = 1
_COMMA_DELIMITER = ','

def _determine_winner(game_result):
    """
    From the game result string, extract the winner's id.
    :param game_result: The result of running a game on the Halite binary
    :return:
    """
    return next(line for line in game_result.splitlines()
                if re.compile(_WINNING_RANK_STRING).search(line)).split(_COMMA_DELIMITER)[_BOT_ID_POSITION].strip()

def _determine_loser(game_result):
    """
    From the game result string, extract the loser's id.
    :param game_result: The result of running a game on the Halite binary
    :return:
    """
    return next(line for line in game_result.splitlines()
                if re.compile(_LOSING_RANK_STRING).search(line)).split(_COMMA_DELIMITER)[_BOT_ID_POSITION].strip()


def _play_game(binary, map_width, map_height, bot_commands):
    """
    Plays one game considering the specified bots and the game and map constraints.
    :param binary: The halite binary
    :param map_width: The map width
    :param map_height: The map height
    :param bot_commands: The commands to run each of the bots
    :return: The game's result string
    """
    game_run_command = '\"{}\" -d "{} {}" '.format(binary, map_width, map_height)
    for bot_command in bot_commands:
        game_run_command += " \"{}\"".format(bot_command)
    return subprocess.check_output(game_run_command, shell=True).decode()


def supergym(binary, bot_commands, iterations):
    print("Supergym! {} rounds!".format(iterations))
    if not len(bot_commands) > 2:
        raise IndexError("Must have more than 2 bots")
    winners = {}
    losers = {}
    for i in range(0, len(bot_commands)):
        for j in range(i + 1, len(bot_commands)):
            for k in range(0, iterations):
                match_output = _play_game(binary, 240, 160, [bot_commands[i], bot_commands[j]])
                winner = _determine_winner(match_output)
                loser = _determine_loser(match_output)
                winners[winner][loser] = winners.setdefault(winner, {}).setdefault(loser, 0) + 1
                losers[loser][winner] = losers.setdefault(loser, {}).setdefault(winner, 0) + 1
                print("Winners")
                print(winners)
                print("Losers")
                print(losers)
    bots = set(winners.keys())
    bots = bots.union(losers.keys())
    for hero in sorted(bots):
        for villain in sorted(bots):
            if hero == villain:
                continue
            winners[hero][villain] = winners.setdefault(hero, {}).setdefault(villain, 0)
            losers[hero][villain] = losers.setdefault(hero, {}).setdefault(villain, 0)
            print("{} vs {}: {}-{}".format(hero, villain, winners[hero][villain], losers[hero][villain]))
        print()

def play_games(binary, map_width, map_height, bot_commands, number_of_runs):
    """
    Runs number_of_runs games using the designated bots and binary, recording the tally of wins per player
    :param binary: The Halite binary.
    :param map_width: The map width
    :param map_height: The map height
    :param bot_commands: The commands to run each of the bots (must be either 2 or 4)
    :param number_of_runs: How many runs total
    :return: Nothing
    """
    print("Comparing Bots!")
    result = {}
    if not(len(bot_commands) == 4 or len(bot_commands) == 2):
        raise IndexError("The number of bots specified must be either 2 or 4.")
    for current_run in range(0, number_of_runs):
        try:
            match_output = _play_game(binary, map_width, map_height, bot_commands)
        except Exception as e:
            print(e.output)
        winner = _determine_winner(match_output)
        result[winner] = result.setdefault(winner, 0) + 1
        print("Finished {} runs.".format(current_run + 1))
        print("Win Ratio: {}".format(result))
