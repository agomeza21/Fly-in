from parser import Parser
from pathfinder import Pathfinder

p = Parser()
graph = p.parse("map.txt")

pathfinder = Pathfinder()
path = pathfinder.find_path(graph)

if not path:
    print("No path found")
else:
    print("Path found:")
    for zone in path:
        print(f"  {zone.name} (type={zone.zone_type})")

""" print("nb_drones:", graph.nb_drones)
print("start_hub:", graph.start_hub.name)
print("end_hub:", graph.end_hub.name)
print("zones:", [z for z in graph.zones])
print("connections:", [(c.zone1.name, c.zone2.name)
                       for c in graph.connections])
print("start max_drones:", graph.start_hub.max_drones)
print("end max_drones:", graph.end_hub.max_drones) """
