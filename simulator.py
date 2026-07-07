from models import Graph, Zone, Drone, Connection

class Simulator:
    def __init__(self, graph: Graph, path: list[Zone]) -> None:
        self.graph: Graph = graph
        self.path: list[Zone] = path
        self.drones: list[Drone] = []
        for i in range(graph.nb_drones):
            drone = Drone(
                drone_id=i + 1,
                current_zone=graph.start_hub
            )
            self.drones.append(drone)


    def run(self) -> None:
        while not all(drone.arrived for drone in self.drones):
            movements: list[str] = []
            zone_occupancy: dict[str, int] = {}
            for zone_name in self.graph.zones:
                zone_occupancy[zone_name] = 0
            conn_occupancy: dict[tuple[str, str], int] = {}
            for conn in self.graph.connections:
                conn_occupancy[(conn.zone1.name, conn.zone2.name)] = 0
            for drone in self.drones:
                if drone.arrived:
                    continue
                if drone.path_index + 1 < len(self.path):
                    next_zone = self.path[drone.path_index + 1]
                if zone_occupancy[next_zone.name] < next_zone.max_drones:
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
                        if ((conn.zone1.name == drone.current_zone
                             and conn.zone2.name == next_zone.name)
                             or (conn.zone2.name == drone.current_zone.name
                             and conn.zone1.name == next_zone.name)):
                            conn_capacity = conn.max_link_capacity
                            break
                    if conn_capacity.get(key, 0) < conn_capacity:
