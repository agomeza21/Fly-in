from models import Graph, Zone, Drone
import sys


class Simulator:
    """Runs the turn-by-turn simulation of all drones flying home.

    A Simulator owns the list of Drone objects and moves them, one
    simulation turn at a time, from the start zone to the end zone,
    following the movement, occupancy and capacity rules from the
    subject. Each drone follows its own path (one of the paths
    computed by the Pathfinder), and multiple drones can move on
    the same turn, as long as no zone or connection ends up with
    more drones than its capacity allows.

    Attributes:
        graph (Graph): The full drone network this simulation runs
            on (all zones and connections).
        paths (list[list[Zone]]): Every distinct path found by the
            Pathfinder. There can be fewer paths than drones - in
            that case, several drones share the same path.
        drones (list[Drone]): One Drone object per drone that has
            to fly from strat_hub to end_hub, each one already
            assigned to one of the paths in paths.
    """
    def __init__(self, graph: Graph, paths: list[list[Zone]]) -> None:
        """Creates all the drones and assigns each one a path.

        The number of drones to create comes from graph.nb_drones.
        Since there can be fewer computed paths than drones, this
        method call _assign_drones_to_paths to decide, for each
        drone, wich of the available paths it should follow.

        Args:
            graph (Graph): The full drone network to simulate on.
            paths (list[list[Zone]]): Every distinct path found by
                the Pathfinder, from strat_hub to end_hub.
        """
        self.graph: Graph = graph
        self.paths: list[list[Zone]] = paths
        self.drones: list[Drone] = []
        assigned_indexes = self._assign_drones_to_paths(graph, paths)
        for i, path_index in enumerate(assigned_indexes):
            drone = Drone(
                drone_id=i + 1,
                current_zone=graph.start_hub,
                path=paths[path_index]
            )
            self.drones.append(drone)

    def _path_capacity(self, graph: Graph, path: list[Zone]) -> int:
        """Finds the tightest bottleneck along one path.

        A path can only carry as many drones at once as its
        smallest capacity allows - a path is only as wide as its
        narrowest point. THis method looks at every zone's
        max_drones (ignoring the start and end zones, wich have
        no real limit) and every connection's max_link_capacity
        along the path, and returns the samllest value found.

        Args:
            graph (Graph): The full drone network, used to look up
                the Connection object between each pair of zones in
                the path.
            path (list[Zine]): One path, as a sequence of zones
                from start_hub to end_hub.

        Returns:
            int: The samllest max_drones or max_link_capacity found
                along the path. This number is used as a "weight"
                when deciding how many drones this path should get,
                compared to the other paths.
        """
        capacity = sys.maxsize
        for zone in path:
            if zone is graph.start_hub or zone is graph.end_hub:
                continue
            capacity = min(capacity, zone.max_drones)
        for i in range(len(path) - 1):
            conn = graph.get_connection(path[i].name, path[i + 1].name)
            if conn is not None:
                capacity = min(capacity, conn.max_link_capacity)
        return capacity

    def _assign_drones_to_paths(self, graph: Graph,
                                paths: list[list[Zone]]) -> list[int]:
        """Decides which path each drone should follow.

        When more than one path is available, drones should not
        all pile onto the same one - they should be spread out in
        proportion to how much traffic each path can actually
        handle (its capacity, from _path_capacity). This method
        uses a weighted round-robin: on every round, the path whose
        "credit" has grown the most gets the next drone, and then
        losses credit equal to the total weight of all paths. Over
        many rounds, this naturally spreads drones across the
        paths in proportion to ther weights, insted of grouping
        them together in bloks.

        Args:
            graph (Graph): The full drone network, passed down to
                _path_capacity.
            paths (list[list[Zone]]): Every distinct path found by
                the Pathfinder.

        Returns:
            list[int]: A list with exactly graph.nb_drones entries,
                one per drone, in order. Entry i tells you the
                index (inside paths) of the path that drone i+1
                should follow. For example, if paths has 2 entries
                and this returns [0, 1, 0, 1], it means: drone 1
                follows paths[0], drone 2 follows paths[1], drone 3
                follows paths[0], and so on.
        """
        weights = [self._path_capacity(graph, path) for path in paths]
        total_weight = sum(weights)
        current_weights = [0] * len(paths)
        assigned_indexes: list[int] = []
        for _ in range(graph.nb_drones):
            for i in range(len(paths)):
                current_weights[i] += weights[i]
            chosen = current_weights.index(max(current_weights))
            current_weights[chosen] -= total_weight
            assigned_indexes.append(chosen)
        return assigned_indexes

    def step(self) -> None:
        """Advances the simulation by exactly one turn.

        This is the heart of the simulation. ON every call, it:

        1.  Counts how many drones are (or will be) in each zone
            this turn - both drones already sitting in a zone, and
            drnones currently flying towards a restricted zone (they
            already "reserve" their seat at the destination, so a
            second drone cannot sneak into a zone that is about to
            be full).
        2.  Does the same for connections, counting drones that are
            already mid-flight toward a restricted zone.
        3.  Goes through every drone that has not arrived yet and,
            depending on its simulation, either:
            - Finishes its arrival, if it was flying toward a
            restricted zone and this is the turn it lands.
            - Starts flying toward a restricted zone, if there is
            room both on the connection and in the destination
            zone (and only if the destination is not already
            taken this same turn by an earlier drone).
            - Makes a normal, one-turn move to the next zone, again
            only if ther is room on the connection and in the
            destination zone.
            A drone that has no room to move simply stays where it
            is and tries again next turn.
        4.  Prints one line with every move made this turn, in the
            format "D<id>-<zone or connection>" (skipping drones
            that did not move), exactly as the subject requieres. If
            no drone moved this turn, nothing is printed.

        THis method takes no arguments and returns nothing - all
        of its effects are changes to the Drone objects in
        self.dornes, plus the printed line of movements.
        """
        movements: list[str] = []
        zone_occupancy: dict[str, int] = {}
        for zone_name in self.graph.zones:
            zone_occupancy[zone_name] = 0
        for drone in self.drones:
            if not drone.arrived and drone.in_transit_to is None:
                zone_occupancy[drone.current_zone.name] += 1
            if not drone.arrived and drone.in_transit_to is not None:
                zone_occupancy[drone.in_transit_to.name] += 1
        conn_occupancy: dict[tuple[str, str], int] = {}
        for conn in self.graph.connections:
            conn_occupancy[(conn.zone1.name, conn.zone2.name)] = 0
        for drone in self.drones:
            if drone.arrived or drone.in_transit_to is None:
                continue
            conn_key = (drone.current_zone.name, drone.in_transit_to.name)
            conn_key_rev = (drone.in_transit_to.name, drone.current_zone.name)
            if conn_key in conn_occupancy:
                conn_occupancy[conn_key] += 1
            else:
                conn_occupancy[conn_key_rev] += 1
        for drone in self.drones:
            if drone.arrived:
                continue
            if drone.path_index + 1 < len(drone.path):
                next_zone = drone.path[drone.path_index + 1]
            else:
                continue
            if drone.in_transit_to is not None:
                dest = drone.in_transit_to
                drone.current_zone = dest
                drone.in_transit_to = None
                movements.append(f"D{drone.drone_id}-{dest.name}")
                drone.path_index += 1
                if dest.name == self.graph.end_hub.name:
                    drone.arrived = True
                continue
            if next_zone.zone_type == "restricted":
                conn_key = (drone.current_zone.name, next_zone.name)
                conn_key_rev = (next_zone.name, drone.current_zone.name)
                key = conn_key if conn_key in conn_occupancy else conn_key_rev
                conn_capacity = 1
                for conn in self.graph.connections:
                    if ((conn.zone1.name == drone.current_zone.name
                         and conn.zone2.name == next_zone.name)
                        or (conn.zone2.name == drone.current_zone.name
                            and conn.zone1.name == next_zone.name)):
                        conn_capacity = conn.max_link_capacity
                        break
                is_end = next_zone.name == self.graph.end_hub.name
                if (conn_occupancy.get(key, 0) < conn_capacity and
                    (is_end or zone_occupancy[next_zone.name]
                     < next_zone.max_drones)):
                    conn_occupancy[key] += 1
                    zone_occupancy[drone.current_zone.name] -= 1
                    if not is_end:
                        zone_occupancy[next_zone.name] += 1
                    conn_name = f"{drone.current_zone.name}-{next_zone.name}"
                    movements.append(f"D{drone.drone_id}-{conn_name}")
                    drone.in_transit_to = next_zone
                continue
            is_end = next_zone.name == self.graph.end_hub.name
            if (is_end or zone_occupancy[next_zone.name]
                    < next_zone.max_drones):
                conn_key = (drone.current_zone.name, next_zone.name)
                conn_key_rev = (next_zone.name, drone.current_zone.name)
                if conn_key in conn_occupancy:
                    key = conn_key
                elif conn_key_rev in conn_occupancy:
                    key = conn_key_rev
                else:
                    key = conn_key
                conn_capacity = 1
                for conn in self.graph.connections:
                    if ((conn.zone1.name == drone.current_zone.name
                            and conn.zone2.name == next_zone.name)
                        or (conn.zone2.name == drone.current_zone.name
                            and conn.zone1.name == next_zone.name)):
                        conn_capacity = conn.max_link_capacity
                        break
                if conn_occupancy.get(key, 0) < conn_capacity:
                    zone_occupancy[drone.current_zone.name] -= 1
                    zone_occupancy[next_zone.name] += 1
                    conn_occupancy[key] += 1
                    movements.append(f"D{drone.drone_id}-{next_zone.name}")
                    drone.current_zone = next_zone
                    drone.path_index += 1
                    if next_zone.name == self.graph.end_hub.name:
                        drone.arrived = True
            else:
                pass
        if movements:
            print(" ".join(movements))

    def run_visual(self, visualizer: object) -> None:
        """Runs the whole simulation using the graphical interface.

        Instead of looping here, this method hands control over to
        the Visualizer, giving it the list of drones and the step
        method itself as a callback - the Visualizer will call
        step() once per turn on its own schedule (controlled by
        its speed slider), so it can redraw the map after every
        move.

        Args:
            visualizer (object): The Visualizer instance to run
                with. Declared as object (instead of Visualizer)
                so that this file does not need to import
                visualizer.py (and, with it, tkinter) unless
                --visual is actually used - the import happens
                inside this method instead, only when needed.
        """
        from visualizer import Visualizer
        if isinstance(visualizer, Visualizer):
            visualizer.run(self.drones, self.step)

    def run(self) -> None:
        """Runs the whole simulation without any graphical display.

        Calls step() over and over, once per simulation turn,
        until every drone has arrived at the end zone. Each call
        to step() prints that turns movements to the terminal, so
        by the time this method returns, the full turn-by-turn
        output required by the subject has already been printed.
        """
        total_turns: int = 0
        while not all(drone.arrived for drone in self.drones):
            total_turns += 1
            self.step()
