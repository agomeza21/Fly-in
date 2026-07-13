from parser import Parser
from pathfinder import Pathfinder
from simulator import Simulator
import sys

p = Parser()
if len(sys.argv) < 2:
    print("Usage: python3 main.py <map_file>")
    sys.exit(1)
graph = p.parse(sys.argv[1])

pathfinder = Pathfinder()
path = pathfinder.find_path(graph)

if not path:
    print("Error: no path found between start and end hub")
    sys.exit(1)

simulator = Simulator(graph, path)
if "--visual" in sys.argv:
    from visualizer import Visualizer
    viz = Visualizer(graph, path)
    simulator.run_visual(viz)
else:
    simulator.run()
