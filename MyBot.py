import copy
import hlt
import itertools
import logging
import time
from collections import Counter
from collections import defaultdict
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
    order_unused_ships_start_time = time.time()
    logging.info("{} ships without orders".format(len(ships)))
    # This is lame and there must be a better way to get a reference to DockingStatus
    ship_ref = game_map.get_me().all_ships()[0]

    target_ships = list()
    for enemy in game_map.all_enemy_players():
        target_ships += enemy.all_ships()

        
    if target_ships:
        for ship in ships:
            if time.time() > start_time + _TIME_THRESHOLD:
                logging.info("Out of time, sent commands for {} of {} ships".format(
                    len(command_queue),
                    len(game_map.get_me().all_ships())))
                logging.info("Spent {} ordering unused ships".format(
                    time.time() - order_unused_ships_start_time))
                return
            # Everyone attacks their nearest ship
            navigate_command = ship.navigate(
                ship.closest_point_to(ship.get_nearest(target_ships)),
                game_map,
                max_corrections=45,
                angular_step=2)
            if navigate_command:
                command_queue.append(navigate_command)
    logging.info("Spent {} ordering unused ships".format(
        time.time() - order_unused_ships_start_time))
            
def remove_destroyed_ships_from_incoming_settlers(planet_map, all_ships):
    ship_ids = set([ship.id for ship in all_ships])
    for planet_id, incoming_settlers in planet_map.items():
        planet_map[planet_id] = incoming_settlers & ship_ids

def remove_unordered_ships_from_incoming_settlers(planet_map, unordered_ships):
    ship_ids = set([ship.id for ship in unordered_ships])
    for planet_id, incoming_settlers in planet_map.items():
        planet_map[planet_id] = incoming_settlers - ship_ids

# Return a map of ship.id -> ship
def find_attacked_ships(game_states, turn_number):
    last = {ship.id : ship for ship in game_states[turn_number - 1].get_me().all_ships()}
    attacked = {}
    for ship in game_states[turn_number].get_me().all_ships():
        if ship.id in last and last[ship.id].health != ship.health:
            attacked[ship.id] = ship

    logging.info("Attacked: {}".format(attacked))
    return attacked
    
# Ships that are docked just stay docked
def stay_docked(ship):
    if ship.docking_status != ship.DockingStatus.UNDOCKED:
        return True

# Defend ships under attack that are within this distance (3 turns move away)
defense_distance_threshold = 21

# If a nearby ship is under attack, go help
def defend_nearby_ships(ship, ships_under_attack, game_map, command_queue):
    nearest_ship = ship.get_nearest([ship for ship in ships_under_attack.values() if ship.docking_status == ship.DockingStatus.DOCKED])
    if nearest_ship and ship.dist_to(nearest_ship) <= defense_distance_threshold:
        # TODO: precalc and cache this
        nearest_attacking_enemy = nearest_ship.get_nearest([enemy_ship for enemy_ship in game_map.all_enemy_ships() if enemy_ship.docking_status == ship.DockingStatus.UNDOCKED])
            
        navigate_command = ship.navigate(
            ship.closest_point_to(nearest_attacking_enemy),
            game_map,
            max_corrections=45,
            angular_step=2)
        if navigate_command:
            logging.info("Sending {} to defend {} by attacking {}".format(ship.id, nearest_ship.id, nearest_attacking_enemy.id))
            command_queue.append(navigate_command)
            return True
                                    
        
# Lazy Attacker 1 - Once all planets are claimed, send ships to attack something
# Lazy Attacker 3 - attack nearest docked ship
# Lazy Attacker 4 - attack nearest ship
# Lazy Attacker 5 - don't ignore ships when navigating
# LA 6 - Be willing to dock multiple ships on a planet
# Navigator 1 - Cut max_corrections to 45 and angular_step to 2 in an attempt to avoid timeouts.
#   - Cut off command queue after 1.5 seconds
# Settler 5 - Only send enough settlers to each planet to fully colonize it
# LA 7 - target any nearest ship, not just winning player's
# Defender 1 - Make some attempt to defend docked ships.  Prefer defending docked ships over settling or attacking.
bot_name = "Defender 1"
game = hlt.Game(bot_name)
logging.info("Starting my {} bot!".format(bot_name))

turn_number = 0

# What the heck, memory is cheap.  Keep a history of the entire game.  Index == turn_number
game_states = []

# Multimap of planet IDs to incoming settler IDs
incoming_settlers = defaultdict(set)

while True:
    logging.info("Turn number: {}".format(turn_number))
    # TURN START
    # Update the map for the new turn and get the latest version
    game_map = game.update_map()
    start_time = time.time()

    # Shallow copy seems good enough
    game_states.append(copy.copy(game_map))

    # Here we define the set of commands to be sent to the Halite engine at the end of the turn
    command_queue = []

    # Log counts of all ships and statuses
    my_ships = game_map.get_me().all_ships()
    logging.info("{} ships, {}".format(len(my_ships), Counter([ship.docking_status.name for ship in my_ships])))

    # Find ships that have lots health since last turn
    ships_under_attack = find_attacked_ships(game_states, turn_number)
    
    # Update settlers map by removing ships that were destroyed last turn
    remove_destroyed_ships_from_incoming_settlers(incoming_settlers, my_ships)
    logging.info("Took {} to update incoming settlers".format(time.time() - start_time))
    
    ships_without_orders = set()

    settler_start_time = time.time()
    
    # For every ship that I control
    for ship in game_map.get_me().all_ships():
        if time.time() > start_time + _TIME_THRESHOLD:
            logging.info("Out of time, sent commands for {} of {} ships".format(
                len(command_queue),
                len(game_map.get_me().all_ships())))
            break

        has_order = False

        # TODO: Iterate through these options in a better way
        has_order = has_order or stay_docked(ship)
        
        if not has_order:
            has_order = has_order or defend_nearby_ships(ship, ships_under_attack, game_map, command_queue)

        if has_order:
            continue
        
        # For each planet in the game (only non-destroyed planets are included)
        # Try closer planets first
        for planet in sorted(game_map.all_planets(), key=ship.dist_to):
            logging.info("{} for ship {} to planet {}".format(ship.dist_to(planet), ship.id, planet.id))
            # If the planet is owned by someone else or is full
            if planet.is_owned() and not (planet.owner == game_map.get_me() and not planet.is_full()):
                if planet.is_owned():
                    logging.info("owned")
                    if planet.owner == game_map.get_me():
                        logging.info("by me")
                        if planet.is_full():
                            logging.info("is full")
                # Skip this planet
                continue

            incoming_settler_count = len(incoming_settlers[planet.id])
            # Count will be too high if it includes the current ship
            if ship.id in incoming_settlers[planet.id]:
                incoming_settler_count -= 1
            if planet.num_docking_spots <= incoming_settler_count:
                logging.info("Planet {}(fits {}) already has {} incoming".format(
                    planet.id, planet.num_docking_spots, incoming_settler_count))
                # Planet has enough settlers on the way, skip this planet
                continue
            
            # If we can dock, let's (try to) dock. If two ships try to dock at once, neither will be able to.
            if ship.can_dock(planet):
                # We add the command by appending it to the command_queue
                command_queue.append(ship.dock(planet))
                incoming_settlers[planet.id].add(ship.id)
                logging.info("Ship {} settling planet {}".format(ship.id, planet.id))
                has_order = True
            else:
                incoming_settlers[planet.id].add(ship.id)
                logging.info("Ship {} traveling to settle planet {}".format(ship.id, planet.id))
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
                else:
                    logging.info("navigate failed")
            break
        if not has_order:
            ships_without_orders.add(ship)

    logging.info("Spent {} ordering settlers".format(
        time.time() - settler_start_time))
    # Ships may have switched from heading to a planet to doing something else
    # - remove them from the incoming settlers map
    remove_unordered_ships_from_incoming_settlers(incoming_settlers, ships_without_orders)

    order_unused_ships(ships_without_orders, game_map, command_queue, start_time)

    logging.info(command_queue)
        
    # Send our set of commands to the Halite engine for this turn
    game.send_command_queue(command_queue)
    turn_number += 1
    # TURN END
# GAME END
