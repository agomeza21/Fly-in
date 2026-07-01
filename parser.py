import sys
from models import Zone, Connection, Graph


class Parser:
    def __init__(self) -> None:
        self.nb_drones: int = 0
        self.zones: dict[str, dict[str, int | dict[str, str]]] = {}
        self.start_hub_name: str = ""
        self.end_hub_name: str = ""
        self.connections: list[dict[str, str | dict[str, str]]] = []
        self.connection_names: set[tuple[str, str]] = set()

    def _parse_zone_line(self, line: str, line_number: int,
                         zone_type: str) -> tuple[str, int, int,
                                                  dict[str, str]]:
        _, data = line.split(":", 1)
        data = data.strip()
        found = data.find("[")
        if found != -1:
            new_data, metadata = data.split("[", 1)
        else:
            new_data = data
            metadata = ""
        parts = new_data.split()
        if len(parts) != 3:
            raise ValueError(f"line {line_number}: {zone_type} "
                             f"must have name, x and y, "
                             f"got '{data}'")
        name, x, y = parts
        try:
            x_int = int(x)
            y_int = int(y)
        except ValueError:
            raise ValueError(f"line {line_number}: x and y "
                             f"must be valid integers, "
                             f"got '{x}', '{y}'")
        metadata = metadata.rstrip("]")
        metadata_pairs = metadata.split()
        meta_dict = {}
        for pair in metadata_pairs:
            if "=" not in pair:
                raise ValueError(f"line {line_number}: invalid"
                                 f" metadata format '{pair}'")
            key, value = pair.split("=", 1)
            meta_dict[key] = value
        if ("zone" in meta_dict and meta_dict["zone"]
                not in Zone.VALID_ZONE_TYPES):
            raise ValueError(f"line {line_number}: invalid zone type "
                             f"'{meta_dict['zone']}'")
        if name in self.zones:
            raise ValueError(f"line {line_number}: zone name"
                             f" '{name}' is already used")
        return name, x_int, y_int, meta_dict

    def parse(self, filepath: str) -> Graph:
        try:
            with open(filepath, "r") as file:
                for line_number, line in enumerate(file, start=1):
                    line = line.strip()
                    if line == "":
                        continue
                    elif line.startswith("#"):
                        continue
                    elif line.startswith("nb_drones:"):
                        _, num = line.split(":", 1)
                        num = num.strip()
                        if num.isdigit() and int(num) > 0:
                            self.nb_drones = int(num)
                        else:
                            raise ValueError(f"line {line_number}: nb_drones "
                                             f"must be a positive integer, "
                                             f"got '{num}'")
                    elif line.startswith("start_hub:"):
                        name, x_int, y_int, meta_dict = self._parse_zone_line(
                            line, line_number, "start_hub")
                        if self.start_hub_name != "":
                            raise ValueError(f"line {line_number}: start_hub"
                                             f" is already defined")
                        self.zones[name] = {"x": x_int, "y": y_int,
                                            "metadata": meta_dict}
                        self.start_hub_name = name
                    elif line.startswith("end_hub:"):
                        name, x_int, y_int, meta_dict = self._parse_zone_line(
                            line, line_number, "end_hub")
                        if self.end_hub_name != "":
                            raise ValueError(f"line {line_number}: end_hub is "
                                             f"already defined")
                        self.zones[name] = {"x": x_int, "y": y_int,
                                            "metadata": meta_dict}
                        self.end_hub_name = name
                    elif line.startswith("hub:"):
                        name, x_int, y_int, meta_dict = self._parse_zone_line(
                            line, line_number, "hub")
                        self.zones[name] = {"x": x_int, "y": y_int,
                                            "metadata": meta_dict}
                    elif line.startswith("connection:"):
                        _, data = line.split(":", 1)
                        data = data.strip()
                        found = data.find("[")
                        if found != -1:
                            new_data, metadata = data.split("[", 1)
                        else:
                            new_data = data
                            metadata = ""
                        new_data = new_data.strip()
                        conn_parts = new_data.split("-", 1)
                        if (len(conn_parts) != 2 or conn_parts[0] == ""
                                or conn_parts[1] == ""):
                            raise ValueError(f"line {line_number}: connection "
                                             f"must have two zone names "
                                             f"separated by '-', "
                                             f"got '{new_data}'")
                        zone1, zone2 = conn_parts
                        if zone1 not in self.zones:
                            raise ValueError(f"line {line_number}: zone "
                                             f"'{zone1}' is not defined")
                        if zone2 not in self.zones:
                            raise ValueError(f"line {line_number}: zone "
                                             f"'{zone2}' is not defined")
                        if ((zone1, zone2) in self.connection_names
                                or (zone2, zone1) in self.connection_names):
                            raise ValueError(f"line {line_number}: connection "
                                             f"'{zone1}-{zone2}' is already "
                                             f"defined")
                        metadata = metadata.rstrip("]")
                        metadata_pairs = metadata.split()
                        meta_dict = {}
                        for pair in metadata_pairs:
                            if "=" not in pair:
                                raise ValueError(f"line {line_number}: invalid"
                                                 f" metadata format '{pair}'")
                            key, value = pair.split("=", 1)
                            meta_dict[key] = value
                        self.connection_names.add((zone1, zone2))
                        self.connections.append({"zone1": zone1,
                                                 "zone2": zone2,
                                                 "metadata": meta_dict})
                    else:
                        raise ValueError(f"line {line_number}: format is "
                                         f"incorrect: '{line}'")
            if self.nb_drones == 0:
                raise ValueError("nb_drones is not defined or is missing")
            if self.start_hub_name == "":
                raise ValueError("start_hub is not defined")
            if self.end_hub_name == "":
                raise ValueError("end_hub is not defined")
            zones_obj: dict[str, Zone] = {}
            for name, zone_data in self.zones.items():
                zone_meta = zone_data["metadata"]
                x_val = zone_data["x"]
                y_val = zone_data["y"]
                if (isinstance(zone_meta, dict) and isinstance(x_val, int)
                        and isinstance(y_val, int)):
                    zone = Zone(
                        name=name,
                        x=x_val,
                        y=y_val,
                        zone_type=zone_meta.get("zone", "normal"),
                        color=zone_meta.get("color", None),
                        max_drones=int(zone_meta.get("max_drones", 1))
                    )
                    zones_obj[name] = zone
            connections_obj: list[Connection] = []
            for conn in self.connections:
                zone1_obj = zones_obj[str(conn["zone1"])]
                zone2_obj = zones_obj[str(conn["zone2"])]
                conn_meta = conn["metadata"]
                if isinstance(conn_meta, dict):
                    connection = Connection(
                        zone1_obj=zone1_obj,
                        zone2_obj=zone2_obj,
                        max_link_capacity=int(
                            conn_meta.get("max_link_capacity", 1))
                    )
                    connections_obj.append(connection)
            graph = Graph(
                nb_drones=self.nb_drones,
                zones=zones_obj,
                connections=connections_obj,
                start_hub=zones_obj[self.start_hub_name],
                end_hub=zones_obj[self.end_hub_name]
            )
            return graph
        except (FileNotFoundError, PermissionError, ValueError) as e:
            if isinstance(e, FileNotFoundError):
                print(f"Error: file '{filepath}' not found")
            elif isinstance(e, PermissionError):
                print(f"Error: you don't have reading permission "
                      f"in {filepath}")
            else:
                print(f"Error: {e}")
            sys.exit(1)
