from models import Graph, Zone, Connection
import heapq


class Pathfinder:
    def __init__(self) -> None:
        pass

    def find_paths(self, graph: Graph) -> list[list[Zone]]:
        adjacency = self._build_adjacency(graph)
        zone_usage: dict[str, int] = {name: 0 for name in graph.zones}
        conn_usage: dict[Connection, int] = {
            conn: 0 for conn in graph.connections}

        paths: list[list[Zone]] = []
        max_paths = graph.nb_drones
        previous_names: list[str] | None = None
        while len(paths) < max_paths:
            path = self._dijkstra(graph, adjacency, zone_usage, conn_usage)
            if not path:
                break
            path_names = [zone.name for zone in path]
            if path_names == previous_names:
                break
            paths.append(path)
            self._record_usage(graph, path, zone_usage, conn_usage)
            previous_names = path_names
        return paths

    def _build_adjacency(
            self,
            graph: Graph) -> dict[str,
                                  list[tuple[Zone, Connection]]]:
        adjacency: dict[str, list[tuple[Zone, Connection]]] = {}
        for zone_name in graph.zones:
            adjacency[zone_name] = []
        for conn in graph.connections:
            adjacency[conn.zone1.name].append((conn.zone2, conn))
            adjacency[conn.zone2.name].append((conn.zone1, conn))
        return adjacency

    def _dijkstra(self, graph: Graph,
                  adjacency: dict[str, list[tuple[Zone, Connection]]],
                  zone_usage: dict[str, int],
                  conn_usage: dict[Connection, int]) -> list[Zone]:
        start_key = (0, 0, 0)
        queue: list[tuple[tuple[int, int, int], str]] = [
            (start_key, graph.start_hub.name)]

        costs: dict[str, tuple[int, int, int]] = {}
        for zone_name in graph.zones:
            costs[zone_name] = (10 ** 9, 10 ** 9, 10 ** 9)
        costs[graph.start_hub.name] = start_key

        came_from: dict[str, str] = {}
        visited: set[str] = set()

        while queue:
            current_key, current_name = heapq.heappop(queue)
            current_cost, current_hops, current_usage = current_key
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
                move_hop = 0 if neighbor_zone.zone_type == "priority" else 1
                move_usage = (zone_usage[neighbor_zone.name]
                              + conn_usage[conn])
                new_key = (current_cost + move_cost,
                           current_hops + move_hop,
                           current_usage + move_usage)
                if new_key < costs[neighbor_zone.name]:
                    costs[neighbor_zone.name] = new_key
                    came_from[neighbor_zone.name] = current_name
                    heapq.heappush(queue, (new_key, neighbor_zone.name))

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

    def _record_usage(self, graph: Graph, path: list[Zone],
                      zone_usage: dict[str, int],
                      conn_usage: dict[Connection, int]) -> None:
        for zone in path:
            if zone is graph.start_hub or zone is graph.end_hub:
                continue
            zone_usage[zone.name] += 1
        for i in range(len(path) - 1):
            conn = graph.get_connection(path[i].name, path[i + 1].name)
            if conn is not None:
                conn_usage[conn] += 1
