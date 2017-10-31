import copy
import hlt
import logging
import time
from collections import Counter
from collections import Set

_TIME_THRESHOLD = 1.5

# Find player with most ships
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

def order_unused_ships(ships, game_map, command_queue, start_time):
    logging.info("{} ships without orders".format(len(ships)))
    # This is lame and there must be a better way to get a reference to DockingStatus
    ship_ref = game_map.get_me().all_ships()[0]
    target_player = find_winning_player(game_map)
    target_ships = target_player.all_ships()
    if target_ships:
        for ship in ships:
            if time.time() > start_time + _TIME_THRESHOLD:
                logging.info("Out of time, sent commands for {} of {} ships".format(
                    len(command_queue),
                    len(game_map.get_me().all_ships())))
                return
            # Everyone attacks their nearest ship
            navigate_command = ship.navigate(
                ship.closest_point_to(ship.get_nearest(target_ships)),
                game_map,
                max_corrections=45,
                angular_step=2)
            if navigate_command:
                command_queue.append(navigate_command)
            
    


# Lazy Attacker 1 - Once all planets are claimed, send ships to attack something
# Lazy Attacker 3 - attack nearest docked ship
# Lazy Attacker 4 - attack nearest ship
# Lazy Attacker 5 - don't ignore ships when navigating
# LA 6 - Be willing to dock multiple ships on a planet
# Navigator 1 - Cut max_corrections to 45 and angular_step to 2 in an attempt to avoid timeouts.
#   - Cut off command queue after 1.8 seconds

bot_name = "Navigator 1"
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
    start_time = time.time()
    
    # Here we define the set of commands to be sent to the Halite engine at the end of the turn
    command_queue = []

    # Log counts of all ships and statuses
    my_ships = game_map.get_me().all_ships()
    logging.info("{} ships, {}".format(len(my_ships), Counter([ship.docking_status.name for ship in my_ships])))

    ships_without_orders = set()
    
    # For every ship that I control
    for ship in game_map.get_me().all_ships():
        if time.time() > start_time + _TIME_THRESHOLD:
            logging.info("Out of time, sent commands for {} of {} ships".format(
                len(command_queue),
                len(game_map.get_me().all_ships())))
            break
        has_order = False
        # If the ship is docked
        if ship.docking_status != ship.DockingStatus.UNDOCKED:
            # Skip this ship
            has_order = True
            continue

        # For each planet in the game (only non-destroyed planets are included)
        # Try closer planets first
        for planet in sorted(game_map.all_planets(), key=ship.dist_to):
            # If the planet is owned by someone else or is full
            if planet.is_owned() and not (planet.owner == game_map.get_me() and not planet.is_full()):
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
                navigate_command = ship.navigate(
                    ship.closest_point_to(planet),
                    game_map,
                    max_corrections=45,
                    angular_step=2)
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
        order_unused_ships(ships_without_orders, game_map, command_queue, start_time)
    except Exception as e:
        logging.info(e)

    # Send our set of commands to the Halite engine for this turn
    game.send_command_queue(command_queue)
    # TURN END
# GAME END
