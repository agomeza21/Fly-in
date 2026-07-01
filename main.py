from parser import Parser

p = Parser()
graph = p.parse("map.txt")
print("nb_drones:", graph.nb_drones)
print("start_hub:", graph.start_hub.name)
print("end_hub:", graph.end_hub.name)
print("zones:", [z for z in graph.zones])
print("connections:", [(c.zone1.name, c.zone2.name)
                       for c in graph.connections])
