class Zone:
    """A single point in the drone network map.

    A Zone represents one location that drones can visit. Every zone
    has a name, a position (x, y), a type that controls how drones
    can move through it, and a maximum number of drones it can hold
    at the same time.

    Attributes:
        VALID_ZONE_TYPES (frozenset[str]): The only zone types the
            project accepts: "normal", "blocked", "restricted", and
            "priority". Any other value is not allowed.
        name (str): The unique name of this zone.
        x (int): The x coordinate of this zone on the map.
        y (int): The y coordinate of this zone on the map.
        zone_type (str): The type of this zone. It controls movement
            rules: "normal" costs 1 turn, "restricted" costs 2 turns
            and drones cannot wait mid-way, "priority" costs 1 turn
            but pathfinding should prefer it, and "blocked" zones
            can never be entered.
        color (str | None): An optional color used only for the
            visual representation. Has no effect on the simulation logic.
        max_drones (int): The maximum number of drones that can be
            inside this zone at the same time. Defaults to 1.
    """
    VALID_ZONE_TYPES = frozenset({"normal", "blocked",
                                  "restricted", "priority"})

    def __init__(self, name: str, x: int, y: int, zone_type: str = "normal",
                 color: str | None = None, max_drones: int = 1) -> None:
        """Creates a new Zone and checks that its type is valid.

        Args:
            name (str): The unique name of this zone.
            x (int): The x coordinate of this zone on the map.
            y (int): The y coordinate of this zone on the map.
            zone_type (str): The type of this zone. Must be one of
                the values in VALID_ZONE_TYPES. Defaults to "normal".
            color (str | None): An optional color for display
                purposes. Defaults to None.
            max_drones (int): How many drones can be in tjis zone at
            once. Defaults to 1.

        Raises:
            ValueError: If zone_type is not one of the values in
                VALID_ZONE_TYPES.
        """
        if zone_type not in Zone.VALID_ZONE_TYPES:
            raise ValueError(f"invalid zone type '{zone_type}'")
        self.name: str = name
        self.x: int = x
        self.y: int = y
        self.zone_type: str = zone_type
        self.color: str | None = color
        self.max_drones: int = max_drones


class Connection:
    """A link between two zones that drones can travel through.

    A Connection is always two-way: drones can travel from zone1 to
    zone2, or from zone2 to zone1, using the same Connection object.

    Attributes:
        zone1 (Zone): One end of the connection.
        zone2 (Zone): The other end of the connection.
        max_link_capacity (int): The maximum number of drones that
            can travel through this connection at the same time.
            Defaults to 1.
    """
    def __init__(self, zone1_obj: Zone, zone2_obj: Zone,
                 max_link_capacity: int = 1) -> None:
        """Creates a new Connection between two zones.

        Args:
            zone1_obj (Zone): One end of the connection.
            zone2_obj (Zone): The other end of the connection.
            max_link_capacity (int): How many drones can travel
                through this connection at once. Defaults to 1.
        """
        self.zone1: Zone = zone1_obj
        self.zone2: Zone = zone2_obj
        self.max_link_capacity: int = max_link_capacity


class Graph:
    """The full drone network: every zone and every connection.

    A Graph is built once by the Parser after it reads a map file.
    It stores all the zones and connections, plus wich zone is the
    start and wich one is the end, so the Pathfinder and the
    Simulator can use it.

    Attributes:
        nb_drones (int): How many drones must travel from start_hub
            to end_hub.
        zones (dict[str, Zone]): All zones in the map, idexed by
            their name, so any zone can be found quickly by name.
        connections (list[Connection]): Every connection in the map.
        start_hub (Zone): The zone where all drones begin.
        end_hub (Zone): THe zone every drone must reach.
    """
    def __init__(self, nb_drones: int, zones: dict[str, Zone],
                 connections: list[Connection], start_hub: Zone,
                 end_hub: Zone) -> None:
        """Creates a new graph from already parsed data.

        Args:
            nb_drones (int): How many drones must travel from
                start_hub to end_hub.
            zones (dict[str, Zone]): All zones in the map, indexed
                by their name.
            connections (list[Connection]): Every connection in the
                map.
            start_hub (Zone): The zone where all drones begin.
            end_hub (Zone): THe zone every drone must reach.
        """
        self.nb_drones: int = nb_drones
        self.zones: dict[str, Zone] = zones
        self.connections: list[Connection] = connections
        self.start_hub: Zone = start_hub
        self.end_hub: Zone = end_hub

    def get_connection(self, zone_a_name: str,
                       zone_b_name: str) -> Connection | None:
        """Finds the connection between two zones, in any direction.

        A Connection can be stored as (zone_a, zone_b) or as
        (zone_b, zone_a) - this method checks both directions, so
        the caller does not need to know which order it was created
        in.

        Args:
            zone_a_name (str): The name of one of the two zones.
            zone_b_name (str): The name of the other zone.

        Returns:
            Connection | None: The connection between the two zones,
                or None if no such connection exists in this graph.
        """
        for conn in self.connections:
            if ((conn.zone1.name == zone_a_name
                 and conn.zone2.name == zone_b_name)
                or (conn.zone2.name == zone_a_name
                    and conn.zone1.name == zone_b_name)):
                return conn
        return None


class Drone:
    """One drone moving from the start zone to the end zone.

    Each Drone follows its own path (a list of zones), one step at
    a time. A drone can be sitting in a zone (current_zone), or it
    can be flying through a connection toward a restricted zone
    (in_transit_to), which takes two turns to complete.

    Attributes:
        drone_id (int): The unique number used to identify this
            drone in the simulation output (for example, "D1").
        current_zone (Zone): The zone where the drone currently is.
            While the drone is in transit towards a restricted zone,
            this still holds the zone it departed from.
        path (list[Zone]); The full sequence of zones this drone
            will follow, from the start zone to the end zone.
        path_index (int): A pointer into path that marks the
            zone the drone is currently at. For example, if
            path_index is 2, the drone is at path[2]. Moving to
            the next zone in the route means increasing this
            number by 1, so this is how the drone keeps track of
            how far along its route it has traveled.
        arrived (bool): True once the drone has reached the end
            zone. Arrived drones are no longer moved by the
            simulation.
        in_transit_to (Zone | None): The restricted zone this drone
            is currently flying toward, or None if the drone is not
            in the middle of a multi-turn move.
    """
    def __init__(self, drone_id: int, current_zone: Zone,
                 path: list[Zone], path_index: int = 0,
                 arrived: bool = False) -> None:
        """Creates a new Drone at the start of its path.

        Args:
            drone_id (int): The unique number used to identify this
                drone (for example, "D1").
            current_zone (Zone): The zone where the drone starts.
                This is normally the graph's start_hub.
            path (list[Zone]); The full sequence of zones this drone
                will follow.
            path_index (int): The starting position of the drone
                inside path (see the class doctsrings above for
                how this pointer works). Defaults to 0, meaning the
                drone starts at the very first zone in its path.
            arrived (bool): Wether the drone has already reached
                the end zone. Defauls to False.
        """
        self.drone_id: int = drone_id
        self.current_zone: Zone = current_zone
        self.path: list[Zone] = path
        self.path_index: int = path_index
        self.arrived: bool = arrived
        self.in_transit_to: Zone | None = None
