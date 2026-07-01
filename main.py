from parser import Parser

p = Parser()
p.parse("map.txt")
print("nb_drones:", p.nb_drones)
print("start_hub:", p.start_hub_name)
print("end_hub:", p.end_hub_name)
print("zones:", p.zones)
print("connections:", p.connections)
