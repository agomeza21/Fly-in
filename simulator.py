from models import Graph, Zone, Drone


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

    def step(self) -> None:
        movements: list[str] = []
        zone_occupancy: dict[str, int] = {}
        for zone_name in self.graph.zones:
            zone_occupancy[zone_name] = 0
        for drone in self.drones:
            if not drone.arrived:
                zone_occupancy[drone.current_zone.name] += 1
        conn_occupancy: dict[tuple[str, str], int] = {}
        for conn in self.graph.connections:
            conn_occupancy[(conn.zone1.name, conn.zone2.name)] = 0
        for drone in self.drones:
            if drone.arrived:
                continue
            if drone.path_index + 1 < len(self.path):
                next_zone = self.path[drone.path_index + 1]
            else:
                continue
            if drone.current_zone.zone_type == "restricted":
                if drone.turns_in_transit < 1:
                    drone.turns_in_transit += 1
                    continue
                else:
                    drone.turns_in_transit = 0
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
        from visualizer import Visualizer
        if isinstance(visualizer, Visualizer):
            visualizer.run(self.drones, self.step)

    def run(self) -> None:
        total_turns: int = 0
        while not all(drone.arrived for drone in self.drones):
            total_turns += 1
            movements: list[str] = []
            zone_occupancy: dict[str, int] = {}
            for zone_name in self.graph.zones:
                zone_occupancy[zone_name] = 0
            for drone in self.drones:
                if not drone.arrived:
                    zone_occupancy[drone.current_zone.name] += 1
            conn_occupancy: dict[tuple[str, str], int] = {}
            for conn in self.graph.connections:
                conn_occupancy[(conn.zone1.name, conn.zone2.name)] = 0
            for drone in self.drones:
                if drone.arrived:
                    continue
                if drone.path_index + 1 < len(self.path):
                    next_zone = self.path[drone.path_index + 1]
                else:
                    continue
                if drone.current_zone.zone_type == "restricted":
                    if drone.turns_in_transit < 1:
                        drone.turns_in_transit += 1
                        continue
                    else:
                        drone.turns_in_transit = 0
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
        print(f"Simulation completed in {total_turns} turns")
