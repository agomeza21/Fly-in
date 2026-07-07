from models import Graph, Zone, Connection
import heapq


class Pathfinder:
    def __init__(self) -> None:
        pass

    def find_path(self, graph: Graph) -> list[Zone]:
        adjacency: dict[str, list[tuple[Zone, Connection]]] = {}
        for zone_name in graph.zones:
            adjacency[zone_name] = []
        for conn in graph.connections:
            adjacency[conn.zone1.name].append((conn.zone2, conn))
            adjacency[conn.zone2.name].append((conn.zone1, conn))

        queue: list[tuple[int, str]] = [(0, graph.start_hub.name)]

        costs: dict[str, float] = {}
        for zone_name in graph.zones:
            costs[zone_name] = float("inf")
        costs[graph.start_hub.name] = 0

        came_from: dict[str, str] = {}

        visited: set[str] = set()

        while queue:
            current_cost, current_name = heapq.heappop(queue)
            if current_name in visited:
                continue
            visited.add(current_name)
            if current_name == graph.end_hub.name:
                break
            for neighbor_zone, conn in adjacency[current_name]:
                if neighbor_zone.zone_type == "blocked":
                    continue
                if neighbor_zone.zone_type == "restricted":
                    move_cost = 2
                else:
                    move_cost = 1
                new_cost = current_cost + move_cost
                if new_cost < costs[neighbor_zone.name]:
                    costs[neighbor_zone.name] = new_cost
                    came_from[neighbor_zone.name] = current_name
                    heapq.heappush(queue, (new_cost, neighbor_zone.name))

        if (graph.end_hub.name not in came_from
                and graph.end_hub.name != graph.start_hub.name):
            return []
        path = []
        current = graph.end_hub.name
        while current:
            path.append(graph.zones[current])
            if current in came_from:
                current = came_from[current]
            else:
                break
        return path[::-1]
