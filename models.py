class Zone:
    VALID_ZONE_TYPES = frozenset({"normal", "blocked",
                                  "restricted", "priority"})

    def __init__(self, name: str, x: int, y: int, zone_type: str = "normal",
                 color: str | None = None, max_drones: int = 1) -> None:
        if zone_type not in Zone.VALID_ZONE_TYPES:
            raise ValueError(f"invalid zone type '{zone_type}'")
        self.name: str = name
        self.x: int = x
        self.y: int = y
        self.zone_type: str = zone_type
        self.color: str | None = color
        self.max_drones: int = max_drones


class Connection:
    def __init__(self, zone1_obj: Zone, zone2_obj: Zone,
                 max_link_capacity: int = 1) -> None:
        self.zone1: Zone = zone1_obj
        self.zone2: Zone = zone2_obj
        self.max_link_capacity: int = max_link_capacity


class Graph:
    def __init__(self, nb_drones: int, zones: dict[str, Zone],
                 connections: list[Connection], start_hub: Zone,
                 end_hub: Zone) -> None:
        self.nb_drones: int = nb_drones
        self.zones: dict[str, Zone] = zones
        self.connections: list[Connection] = connections
        self.start_hub: Zone = start_hub
        self.end_hub: Zone = end_hub


class Drone:
    def __init__(self, drone_id: int, current_zone: Zone,
                 path_index: int = 0, arrived: bool = False,
                 turns_in_transit: int = 0) -> None:
        self.drone_id: int = drone_id
        self.current_zone: Zone = current_zone
        self.path_index: int = path_index
        self.arrived: bool = arrived
        self.turns_in_transit: int = turns_in_transit
