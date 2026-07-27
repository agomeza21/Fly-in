*This project has been created as part of the 42 curriculum by agomez-a.*

# Fly-in

Autonomous drone routing and turn-by-turn simulation engine.

## Description

**Fly-in** routes a fleet of drones across a network of zones, from a `start_hub`
to an `end_hub`, and then simulates their movement turn by turn until every
drone has arrived.

The map (zones, connections, zone types, capacities) is described in a custom
text file format (see [Map file format](#map-file-format) below). Given such a
file, the program:

1. **Parses** the map into an in-memory graph (`Parser`, `models.py`).
2. **Computes** one or more distinct paths from `start_hub` to `end_hub`
   (`Pathfinder`), using a capacity- and usage-aware variant of Dijkstra's
   algorithm so that drones get spread across several routes instead of
   piling onto a single one.
3. **Simulates** the drones moving simultaneously, turn by turn, respecting
   zone occupancy, connection capacity, and multi-turn "restricted zone"
   flights (`Simulator`).
4. **Displays** the result either as plain text in the terminal or as an
   animated graphical window (`Visualizer`, built with `tkinter`).

The goal of the routing/scheduling algorithm is to deliver **all** drones to
the end zone in the **fewest possible simulation turns**, while never
violating a zone's `max_drones` or a connection's `max_link_capacity`.

The whole project is written in pure, type-safe, object-oriented Python — no
graph library (`networkx`, `graphlib`, etc.) is used anywhere; every graph
structure and algorithm (Dijkstra, adjacency lists, path scheduling) is
implemented from scratch in `models.py` and `pathfinder.py`.

## Instructions

### Requirements

- Python 3.10+
- `tkinter` (only required for `--visual` mode — installed automatically by
  `make install` on Debian/Ubuntu via `python3-tk`)
- `flake8` and `mypy` (only required to run the lint targets)

### Installation

```bash
make install
```

Installs `python3-tk` (needed for the graphical visualizer) and the
`flake8`/`mypy` dev dependencies.

### Running the simulation

```bash
make run MAP=<path_to_map_file>
```

Runs the simulation in plain text mode and prints the turn-by-turn drone
movements to the terminal.

### Running with the graphical visualizer

```bash
make run-visual MAP=<path_to_map_file>
```

Opens a `tkinter` window animating the zones, connections and drones (see
[Visual representation](#visual-representation) below).

### Running without `make`

```bash
python3 main.py <map_file>            # text mode
python3 main.py <map_file> --visual   # graphical mode
```

### Debugging

```bash
make debug MAP=<path_to_map_file>
```

Runs `main.py` under Python's built-in debugger (`pdb`).

### Linting

```bash
make lint          # flake8 + mypy (project's required flags)
make lint-strict    # flake8 + mypy --strict
```

### Cleaning

```bash
make clean
```

Removes `__pycache__`, `.mypy_cache` and `.pytest_cache`.

## Map file format

```
nb_drones: 5

start_hub: hub 0 0 [color=green]
end_hub: goal 10 10 [color=yellow]
hub: roof1 3 4 [zone=restricted color=red]
hub: roof2 6 2 [zone=normal color=blue]
hub: corridorA 4 3 [zone=priority color=green max_drones=2]
hub: tunnelB 7 4 [zone=normal color=red]
hub: obstacleX 5 5 [zone=blocked color=gray]
connection: hub-roof1
connection: hub-corridorA
connection: roof1-roof2
connection: roof2-goal
connection: corridorA-tunnelB [max_link_capacity=2]
connection: tunnelB-goal
```

- `nb_drones: <positive_integer>` must be the first line and defines how many
  drones need to travel from `start_hub` to `end_hub`.
- Zones are declared with `start_hub:`, `end_hub:` or `hub:`, each followed by
  `<name> <x> <y>` and optional `[zone=... color=... max_drones=...]`
  metadata. Zone names cannot contain dashes or spaces.
- Zone types: `normal` (1 turn, default), `restricted` (2 turns, and the
  drone cannot wait mid-flight), `priority` (1 turn, preferred by the
  pathfinder), `blocked` (never entered).
- `connection: <zone1>-<zone2> [max_link_capacity=...]` declares a
  bidirectional link. A connection can only be declared once between two
  zones (in either direction).
- Lines starting with `#` and blank lines are ignored.
- Any malformed line raises a clear parsing error naming the line number and
  the cause, and the program exits.

## Expected output format
Example:

```
D1-corridorA
D1-tunnelB D2-corridorA
D1-goal D2-tunnelB D3-corridorA
D2-goal D3-tunnelB D4-corridorA
D3-goal D4-tunnelB D5-corridorA
D4-goal D5-tunnelB
D5-goal
```

## Algorithm choices and implementation strategy

### Parsing (`Parser`)

The map file is read line by line. Zones and connections are first collected
in a "raw" form (name, coordinates, metadata as strings), validated (unknown
zone types, non-integer coordinates, duplicate names/connections, invalid
`max_drones`/`max_link_capacity` values, etc.), and only turned into real
`Zone`/`Connection`/`Graph` objects once the whole file has been read
successfully. `max_drones` is explicitly ignored (forced to unlimited) on
`start_hub` and `end_hub`, as required by the subject. Any error stops the
program with `sys.exit(1)` and a message identifying the offending line.

### Pathfinding (`Pathfinder`)

Routes are computed with a custom implementation of **Dijkstra's algorithm**
(via `heapq`), run repeatedly (once per drone, at most) to build a list of
*distinct* paths instead of a single shortest path:

- **Cost model**: entering a `normal` or `priority` zone costs 1 turn,
  entering a `restricted` zone costs 2 turns, and `blocked` zones are simply
  never expanded (they behave as if no connection led to them).
- **Priority preference**: since `priority` zones cost the same as `normal`
  zones but should still be preferred, the algorithm minimizes, as a
  tie-breaker, the number of *non*-priority zones on the path.
- **Load spreading**: after each path is accepted, the zones and connections
  it uses have their "usage counters" incremented. These counters are used as
  a final tie-breaker in the next Dijkstra run, so that when several routes
  have the same real cost, the search naturally drifts toward the
  least-used one — spreading drones across multiple disjoint or
  overlapping paths instead of stacking them all on one route.
- The search stops once as many paths as drones have been found, once no
  path exists at all, or once Dijkstra starts returning the same path again
  (meaning the map has no further genuinely different route to offer).

Each candidate zone/edge is compared using a 3-tuple
`(real_cost, non_priority_hops, usage)`, so Python's native tuple ordering
does all three levels of tie-breaking for free.

**Complexity**: each drone triggers one full run of Dijkstra's algorithm over
the whole map (all zones and connections), so the total work grows with both
the size of the map (more zones/connections means each run explores more) and
the number of drones (more drones means more runs). No paths are cached
between runs, since the usage counters change after every accepted path and
would make a cached path stale — but the adjacency list (each zone's
neighbors) is built only once, at the very start, and reused by every run
instead of being recomputed each time.

### Drone-to-path assignment and simulation (`Simulator`)

Drones are distributed across the computed paths with a **weighted
round-robin**: each path's weight is its narrowest bottleneck (the smallest
`max_drones`/`max_link_capacity` found along it), so wider paths receive
proportionally more drones instead of splitting them evenly.

Every simulation turn (`step`):

1. The current (and reserved, for in-flight drones) occupancy of every zone
   and connection is computed first.
2. Drones already mid-flight toward a `restricted` zone complete their
   arrival unconditionally (they must land — they can never wait on a
   connection).
3. Remaining drones attempt to move to the next zone on their path: a
   one-turn move if there is free capacity on the destination zone and the
   connection, or the start of a two-turn flight if the destination is
   `restricted`. A drone that cannot move simply waits and retries next
   turn.
4. All moves made in a turn are printed on a single line
   (`D<id>-<zone_or_connection>`), skipping drones that did not move; the
   line is omitted entirely if nobody moved.

The simulation ends once every drone has reached `end_hub`.

## Visual representation

Running with `--visual` (or `make run-visual`) opens a `tkinter` window
(`Visualizer`) that redraws the whole map after every simulated turn:

- Zones are drawn as hexagons, colored according to their `color` metadata
  (or a default color derived from their `zone_type` when no color is
  given), positioned according to their map `x`/`y` coordinates.
- Connections are drawn as lines between zones, and drones are drawn as
  small markers that move along them, including a visible mid-flight state
  for two-turn moves toward `restricted` zones.
- A side panel shows the current turn number, how many drones have arrived,
  a speed slider to control the delay between turns, and a pause/replay
  control.

This turns an otherwise abstract log of `D<id>-<zone>` lines into something
that can be watched live: bottlenecks, waiting drones and path choices
become immediately visible, which makes it much easier to sanity-check the
pathfinder's and simulator's behavior on complex maps than by reading text
output alone.

Text mode (no `--visual`) instead prints the exact turn-by-turn movement log
required by the subject directly to the terminal, one line per turn.

## Resources

- [Dijkstra's algorithm — Wikipedia](https://en.wikipedia.org/wiki/Dijkstra%27s_algorithm)
- [`tkinter` documentation](https://docs.python.org/3/library/tkinter.html)

### AI usage

AI assistance was used during this project as a support tool, not as a
replacement for understanding the code:

- Reviewing and rewording docstrings across `models.py`, `parser.py`,
  `pathfinder.py`, `simulator.py`, `main.py` and `visualizer.py` for clarity
  and PEP 257 compliance.
- Discussing the tie-breaking strategy used in `Pathfinder._dijkstra` (the
  3-tuple cost model combining real cost, priority-zone preference and
  usage-based load spreading) before implementing it by hand.
- Generating this `README.md` from the final source files and the project
  subject.

All algorithmic logic (parsing rules, Dijkstra adaptation, drone assignment,
turn-by-turn simulation rules) was implemented and understood by me, and reviewed with peers as recommended by the subject.