from models import Graph, Zone, Connection
import heapq


class Pathfinder:
    """Finds one or more routes from the start zone to the end zone.

    THis class answers the question "how should the drones get
    from start_hub to end_hub?". It does not move any drone itself
    (that is the Simulator's job) - it only works out, on paper,
    which zones each drone should visit, in order.

    The algorithm used is Dijkstra's algorithm, a well-known way of
    finding the cheapest route through a network of connevted
    points. Here, "cheapest" is not just about distance - moving
    into a "blocked" zone is never allowed at all.

    On top of plain Dijkstra, this class adds two extra ideas to
    satisfy the subject's requirement that drones should be spread
    across different paths, not all forced onto a single one:

    1.  It does not stop after finding just one path. It keeps
        asking Dijkstra for another path, as many times as there are
        drones, so that later it can hand out several different
        routes instead of only one (see find_paths).
    2.  Every time a path is chosen, this class "remembers" that
        the zones and connections along it are now a bit more used
        (see _record_usage). The next time Dijkstra runs, zones and
        connections that are already more used are treated as
        slightly less attractive, so if there is a real alternative
        route with the same base cost, Dijkstra naturally starts
        preferring it instead of pilingevery path onto the same
        zones.
    ZOne types alo affect the search in two different ways:
    - "restricted" zones cost 2 turns to enter, instead of 1.
    - "blocked" zones can never be entered - they are skipped
      completely, as if no connection led to them.
    - "priority" zones do not cost less (still 1 turn), but the
      subject says pathfinding "should" prefer them, so this class
      counts, for every path, how many non-priority zones it uses,
      and treats a path with fewer non-priority zones as better,
      whenever two paths have the exact same base cost.
    """
    def __init__(self) -> None:
        """CReates a new Pathfinder.

        This class does not need to store anything between calls -
        every method receives the Graph it needs to work with as
        an argument. This constructor exists only so the class can
        be instantiated in the same style as the other classes in
        the project.
        """
        pass

    def find_paths(self, graph: Graph) -> list[list[Zone]]:
        """Finds every useful path from start_hub to end_hub.

        This is the method the rest of the program calls. Instead
        of returning a single path, it keeps calling _dijkstra
        again and again - once per srone, at most - and collects
        every different path it finds. Each time a path is added,
        _record_usage marks its zones and connections as "more
        used", wichnudges the next call to _dijkstra toward a
        different route, if one exists with the same base cost.

        The loop stops early, before reaching one path per drone,
        in two situations:
        - _dijkstra could not find any path at all (this only
          really happens on the very first attempt - if a route
          exists, some route will always be found, even if it
          reuses already-busy zones).
        - _dijkstra returns the exact same path as the previous
          attempt. THis means the map has no more genuinely
          different routes left to offer, so asking again would
          just find the same one over and over.

        Args:
            graph (Graph): The full drone network to search.

        Returns:
            list[list[Zone]]: A list of distinct paths, each one a
                sequence of zones from strat_hub to end_hub. This
                list can be shorter than graph.nb_drones - when
                that happens, it means several drones will have to
                shere the same path (the Simulator decides which
                drones share which path). It is empty only if there
                is no way at all to reach end_hub from start_hub.
        """
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
        """Builds a lookup table of neighbors for every zone.

        Djikstra's algorithm needs to repeatedly ask "which zones
        can i reach directly from this one, and through which
        connection?". Rather than searching through every
        connection each time that question comes up, this method
        answers it once for the whole graph, building a dict that
        maps each zone's name to a list of (neighbor zone,
        connection) pairs.

        Since every Connection in the map is two-way, each one
        produces two entries here: one from zone1's side, and one
        from zone2's side.

        Args:
            graph (Graph): The full drone network.

        Returns:
            dict[str, list[tuple[Zone, Connection]]]: For each zone
                name, the list of zones directly reachable from it,
                paired with the Connection object used to reach
                each one.
        """
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
        """Finds one cheapest path from start_hub to end_hub.

        This is a standard Dijkstra's algorithm, using a priority
        queue (heapq) so taht the zone with the smallest cost so
        far is always explored next. The only unusual part is that
        "cost" here is not a single number, but a tuple of three
        numbers, compared one after another:

        1.  The real movement cost: 1 turn pero normal or priority
            zone entered, 2 turns per restricted zone entered.
            Blocked zones are skippedentirely (they act as if they
            do not exist).
        2.  The number of non-priority zones used so far. This is
            only used to break ties; between two paths with the
            exact same real cost, the one that passes through more
            priority zones (and so has a smaller numuber here) wins,
            matching the subject's wish that priority zones "should"
            be preferred.
        3,  How "used" the zones and connections along the path
            already are, based on zone_usage and conn_usage (filled
            in by earlier calls to _record_usage, in find_paths).
            This is only used to break ties when the first two
            numbers are also equal - it is what nudges later paths
            away from zones that earlier paths añready used a lot.

        Comparing two of these tuples with Python's normal "<"
        works exactly like comparing scores in a competition with a
        first, second and third tie-breaker: Python compares the
        first numbers first, and only looks at the second (or
        third) number if the earlier ones are exactly equal.

        Args:
            graph (Graph): The full drone network.
            adjacency (dict): The neighbor lookup table built by
                _build_adjacency.
            zone_usage (dict[str, int]): HOw many times each zone
                has already been used by a previously found path.
            conn_usage (dict[Connection, int]): How many times each
                connection has already been used by a previously
                found path.

        Returns:
            list[Zone]: The cheapest path found, as a sequence of
                zones from start_hub to end_hub (both included). If
                end_hub cannot be reached at all, an empty list is
                returned instead.
        """
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
        """Marks a path's zones and connections as more "used".

        Called once, right after find_paths accepts a new path.
        This does not change anything about the path itself — it
        only updates zone_usage and conn_usage, which the next call
        to _dijkstra will read to slightly discourage reusing the
        same zones and connections again, if a real alternative
        exists.

        start_hub and end_hub are deliberately not counted here:
        every single path has to pass through both of them anyway
        (they have no real capacity limit, per the subject), so
        counting them would not help tell any path apart from any
        other.

        Args:
            graph (Graph): The full drone network, used to look up
                the Connection object between each pair of zones in
                the path.
            path (list[Zone]): The path that was just accepted by
                find_paths.
            zone_usage (dict[str, int]): Updated in place: each
                zone in the path (except start_hub and end_hub) has
                its count increased by 1.
            conn_usage (dict[Connection, int]): Updated in place:
                each connection used by the path has its count
                increased by 1.
        """
        for zone in path:
            if zone is graph.start_hub or zone is graph.end_hub:
                continue
            zone_usage[zone.name] += 1
        for i in range(len(path) - 1):
            conn = graph.get_connection(path[i].name, path[i + 1].name)
            if conn is not None:
                conn_usage[conn] += 1
