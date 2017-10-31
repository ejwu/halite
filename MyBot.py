"""
Welcome to your first Halite-II bot!

This bot's name is Settler. It's purpose is simple (don't expect it to win complex games :) ):
1. Initialize game
2. If a ship is not docked and there are unowned planets
2.a. Try to Dock in the planet if close enough
2.b If not, go towards the planet

Note: Please do not place print statements here as they are used to communicate with the Halite engine. If you need
to log anything use the logging module.
"""
import copy
# Let's start by importing the Halite Starter Kit so we can interface with the Halite engine
import hlt
# Then let's import the logging module so we can print out information
import logging
from collections import Counter
from collections import Set

def find_winning_player(game_map):
    max_ships = 0
    winning_player = None
    for player in game_map.all_enemy_players():
        if len(player.all_ships()) > max_ships:
            max_ships = len(player.all_ships())
            winning_player = player

    return winning_player

def get_ships_for_player(player, status):
    return [ship for ship in player.all_ships() if ship.docking_status == status]

def order_unused_ships(ships, game_map, command_queue):
    logging.info("{} ships without orders".format(len(ships)))
    # This is lame and there must be a better way to get a reference to DockingStatus
    ship_ref = game_map.get_me().all_ships()[0]
    target_player = find_winning_player(game_map)
    target_ships = target_player.all_ships()
    if target_ships:
        for ship in ships:
            # Everyone attacks their nearest ship
            navigate_command = ship.navigate(
                ship.closest_point_to(ship.get_nearest(target_ships)),
                game_map,
                speed=int(hlt.constants.MAX_SPEED),
                ignore_ships=True)
            if navigate_command:
                command_queue.append(navigate_command)
            
    


# GAME START
# Here we define the bot's name as Settler and initialize the game, including communication with the Halite engine.
bot_name = "Lazy Attacker 4"
game = hlt.Game(bot_name)
# Then we print our start message to the logs
logging.info("Starting my {} bot!".format(bot_name))

turn_number = 0

while True:
    logging.info("Turn number: {}".format(turn_number))
    turn_number += 1
    # TURN START
    # Update the map for the new turn and get the latest version
    game_map = game.update_map()

    # Here we define the set of commands to be sent to the Halite engine at the end of the turn
    command_queue = []

    # Log counts of all ships and statuses
    my_ships = game_map.get_me().all_ships()
    logging.info("{} ships, {}".format(len(my_ships), Counter([ship.docking_status.name for ship in my_ships])))

    ships_without_orders = set()
    
    # For every ship that I control
    for ship in game_map.get_me().all_ships():
        has_order = False
        # If the ship is docked
        if ship.docking_status != ship.DockingStatus.UNDOCKED:
            # Skip this ship
            has_order = True
            continue

        # For each planet in the game (only non-destroyed planets are included)
        # Try closer planets first
        for planet in sorted(game_map.all_planets(), key=ship.dist_to):
            # If the planet is owned
            if planet.is_owned():
                # Skip this planet
                continue

            # If we can dock, let's (try to) dock. If two ships try to dock at once, neither will be able to.
            if ship.can_dock(planet):
                # We add the command by appending it to the command_queue
                command_queue.append(ship.dock(planet))
                has_order = True
            else:
                # If we can't dock, we move towards the closest empty point near this planet (by using closest_point_to)
                # with constant speed. Don't worry about pathfinding for now, as the command will do it for you.
                # We run this navigate command each turn until we arrive to get the latest move.
                # Here we move at half our maximum speed to better control the ships
                # In order to execute faster we also choose to ignore ship collision calculations during navigation.
                # This will mean that you have a higher probability of crashing into ships, but it also means you will
                # make move decisions much quicker. As your skill progresses and your moves turn more optimal you may
                # wish to turn that option off.
                navigate_command = ship.navigate(
                    ship.closest_point_to(planet),
                    game_map,
                    speed=int(hlt.constants.MAX_SPEED),
                    ignore_ships=False)
                # If the move is possible, add it to the command_queue (if there are too many obstacles on the way
                # or we are trapped (or we reached our destination!), navigate_command will return null;
                # don't fret though, we can run the command again the next turn)
                if navigate_command:
                    command_queue.append(navigate_command)
                    has_order = True
            break
        if not has_order:
            ships_without_orders.add(ship)

    try:
        order_unused_ships(ships_without_orders, game_map, command_queue)
    except Exception as e:
        logging.info(e)

    # Send our set of commands to the Halite engine for this turn
    game.send_command_queue(command_queue)
    # TURN END
# GAME END
