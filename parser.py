import sys
from models import Zone, Connection, Graph


class Parser:
    """Reads a map file and turns it into a Graph object.

    The map file format is described in the subject: it has one
    "nb_drones" line, one line per zone (start_hub, end_hub, hub),
    and one line per connection between two zones. This class reads
    the file line by line, checks that everything is written
    correctly, and builds the Zone, Connection and Graph objects
    that the rest of the program needs.

    If anything in the file is wrong (a missing field, a bad
    number, a zone used before it is defined, and son on), parsing
    stops and a clear error message is printed, with the line
    number where the problem is, and the whole program exits.

    Attributes:
        nb_drones (int): The number of drones read from the map
            file. Stays 0 until "nb_drones:" line is read.
        zones (dict[str, dict]): The zones read so far, keyed by
            their name. Each value is a small dict with the zone's
            x, y and metadata, kept in tjis "raw" form until
            parse() finishes reading the whole file and turns them
            into real Zone objects.
        start_hub_name (str): The name of the start_hub zone, or an
            empty string if it has not been found yet.
        end_hub_name (str): The name of the end_hub_zone, or an
            empty string if it has not been found yet.
        connections (list[dict]): The connections read so far, kept
            in the same "raw" form as zones, before they are turned
            into real Connection objects.
        connection_names (set[tuple[str, str]]): Te (zone1, zone2)
            name pairs already used by a connection. Used to detect
            duplicate connections, since "a-b" and "b-a" both count
            as the same connection.
    """
    def __init__(self) -> None:
        """Creates a new, empty Parser, ready to read a map file.

        All the counters and containers start empty. The two
        private flags (_any_zone_parsed and _nb_drones_set) are
        used only to enforce two rules from the subject: nb_drones
        must be the first line, and it can only be defined once.
        """
        self.nb_drones: int = 0
        self.zones: dict[str, dict[str, int | dict[str, str]]] = {}
        self.start_hub_name: str = ""
        self.end_hub_name: str = ""
        self.connections: list[dict[str, str | dict[str, str]]] = []
        self.connection_names: set[tuple[str, str]] = set()
        self._any_zone_parsed: bool = False
        self._nb_drones_set: bool = False

    def _parse_metadata(self, data: str,
                        line_number: int) -> tuple[str, dict[str, str]]:
        """Splits a line into its main part and its metadata part.

        Metadata is the optional part written inside square
        brackets, for example "[zone=restricted color=red]". This
        method finds that part (if there is one), checks that it is
        written correctly, and turns it into a dict of key-value
        pairs. To be correct, the metadata block must:
        - End with a closing "]".
        -Have every entry written as key=value, separated by
        spaces (for example "zone=restricted color=red").

        Args:
            data (str): The part of the line after the "type:"
                prefix (for example, everything after "hub:").
            line_number (int): THe line number in the map file,
                used only to build clear error messages.
        
        Returns:
            tuple[str, dict[str, str]]: A pair with two values:
                first,the text that came before the "[" (still not
                split into name/x/y or zone1/zone2, that happens
                later); second, a dict with the metadata keys and
                values. If there was no "[" at all in data, the
                dict is simply empty.

        Raises:
            ValueError: If the metadata block does not end with
                "]", or if one of its entries is not written as
                key=value.
        """
        found = data.find("[")
        if found == -1:
            return data, {}
        new_data, metadata = data.split("[", 1)
        metadata = metadata.strip()
        if not metadata.endswith("]"):
            raise ValueError(f"line {line_number}: metadata block is "
                             f"missing a closing ']'")
        metadata = metadata[:-1]
        metadata_pairs = metadata.split()
        meta_dict = {}
        for pair in metadata_pairs:
            if "=" not in pair:
                raise ValueError(f"line {line_number}: invalid metadata"
                                 f" format '{pair}'")
            key, value = pair.split("=", 1)
            meta_dict[key] = value
        return new_data, meta_dict

    def _parse_zone_line(self, line: str, line_number: int,
                         zone_type: str) -> tuple[str, int, int,
                                                  dict[str, str]]:
        """Parses one zone line: "strat_hub:", "end_hub:" or "hub:".

        This method handles the part that is common to all three
        zone line types: reading the name, x and y, splitting off
        the metadata (using _parse_metadata), and checking that
        the zone type and max_drones metadata (if present) are
        valid. It does NOT decide what to do with the parsed data
        (that is done by the caller, in parse()) - it only reads
        and validates a single line.

        Args:
            line (str): The full line from the map file, including
                its "start_hub:", "end_hub:" or "hub:" prefix.
            line_number (int): The line number in the map file,
                used to build clear error messages.
            zone_type (str): Which kind of zone line this is:
                "start_hub", "end_hub" or "hub". Used both in error
                messages and to decide whether the max_drones
                metadata should be validated (it is ignored, and
                so not validated, for start_hub and end_hub, as the
                subject requires).

        Returns:
            tuple[str, int, dict[str, str]]: The zone's name,
                its x coordinate, its y coordinate, and its
                metadata dict (which may be empty).

        Raises:
            ValueError: If the line does not have exactly a name,
                an x and a y; if the name contains a dash; if x or
                y is not a valid integer; if the zone metadata has
                an invalid "zone" type; if max_drones is present
                (on a plain "hub") and is not a positive integer;
                or if this zone name was already used before.
        """
        _, data = line.split(":", 1)
        data = data.strip()
        new_data, meta_dict = self._parse_metadata(data, line_number)
        parts = new_data.split()
        if len(parts) != 3:
            raise ValueError(f"line {line_number}: {zone_type} "
                             f"must have name, x and y, "
                             f"got '{data}'")
        name, x, y = parts
        if "-" in name:
            raise ValueError(f"line {line_number}: zone name "
                             f"'{name}' cannot contain dashes")
        try:
            x_int = int(x)
            y_int = int(y)
        except ValueError:
            raise ValueError(f"line {line_number}: x and y "
                             f"must be valid integers, "
                             f"got '{x}', '{y}'")
        if ("zone" in meta_dict and meta_dict["zone"]
                not in Zone.VALID_ZONE_TYPES):
            raise ValueError(f"line {line_number}: invalid zone type "
                             f"'{meta_dict['zone']}'")
        if (zone_type == "hub" and "max_drones" in meta_dict
            and not (meta_dict["max_drones"].isdigit()
                     and int(meta_dict["max_drones"]) > 0)):
            raise ValueError(f"line {line_number}: max_drones must be a "
                             f"positive integer, got "
                             f"'{meta_dict['max_drones']}'")
        if name in self.zones:
            raise ValueError(f"line {line_number}: zone name"
                             f" '{name}' is already used")
        return name, x_int, y_int, meta_dict

    def parse(self, filepath: str) -> Graph:
        """Reads the whole map file and builds the final Graph.

        This is the main entry point of the Parser: it opens the
        file, reads it line by line (skipping blank lines and
        comments strating with "#"), and dispatches each line to
        the right handling code based on its prefix ("nb_drones:",
        "start_hub:", "end_hub:", "hub:" or "connection:"). It
        collects everything in "raw" form first (in self.zones and
        self.connections), and only builds the real Zone,
        Connection and Graph objects at the very end, once it knows
        the whole file was valid.

        This method never lets an exception reach the caller. Any
        problem - the file not existing, a folder given by
        mistake, no read permission, or any other file-system
        problem (all grouped under Python's OSError), as well as
        any rule from the subject's parser constraints being
        broken (raised inside this class as ValueError) - is
        caught, printed as a clear "Error:..." message (with the
        line number, whenever one is available), and the whole
        program exits whith sys.exit(1).

        Args:
            filepath (str): The path to the map file to read, as
                given on the command line.

        Returns:
            Graph: The fully built graph, ready to be used by the
                Pathfinder and the Simulator. This is the object
                the rest of the program relies on.
        """
        try:
            with open(filepath, "r") as file:
                for line_number, line in enumerate(file, start=1):
                    line = line.strip()
                    if line == "":
                        continue
                    elif line.startswith("#"):
                        continue
                    elif line.startswith("nb_drones:"):
                        if self._any_zone_parsed:
                            raise ValueError(f"line {line_number}: "
                                             f"nb_drones must be the"
                                             f" first line")
                        if self._nb_drones_set:
                            raise ValueError(f"line {line_number}: "
                                             f"nb_drones is already "
                                             f"defined")
                        _, num = line.split(":", 1)
                        num = num.strip()
                        if num.isdigit() and int(num) > 0:
                            self.nb_drones = int(num)
                            self._nb_drones_set = True
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
                        self._any_zone_parsed = True
                    elif line.startswith("end_hub:"):
                        name, x_int, y_int, meta_dict = self._parse_zone_line(
                            line, line_number, "end_hub")
                        if self.end_hub_name != "":
                            raise ValueError(f"line {line_number}: end_hub is "
                                             f"already defined")
                        self.zones[name] = {"x": x_int, "y": y_int,
                                            "metadata": meta_dict}
                        self.end_hub_name = name
                        self._any_zone_parsed = True
                    elif line.startswith("hub:"):
                        name, x_int, y_int, meta_dict = self._parse_zone_line(
                            line, line_number, "hub")
                        self.zones[name] = {"x": x_int, "y": y_int,
                                            "metadata": meta_dict}
                        self._any_zone_parsed = True
                    elif line.startswith("connection:"):
                        _, data = line.split(":", 1)
                        data = data.strip()
                        new_data, meta_dict = self._parse_metadata(
                            data, line_number)
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
                        self.connection_names.add((zone1, zone2))
                        if ("max_link_capacity" in meta_dict
                            and not (meta_dict["max_link_capacity"].isdigit()
                                     and int(meta_dict["max_link_capacity"])
                                     > 0)):
                            raise ValueError(
                                f"line {line_number}: max_link_capacity "
                                f"must be a positive integer, got "
                                f"'{meta_dict['max_link_capacity']}'")
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
                    is_start_or_end = (name == self.start_hub_name
                                       or name == self.end_hub_name)
                    zone = Zone(
                        name=name,
                        x=x_val,
                        y=y_val,
                        zone_type=zone_meta.get("zone", "normal"),
                        color=zone_meta.get("color", None),
                        max_drones=1 if is_start_or_end else int(
                            zone_meta.get("max_drones", 1))
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
        except (OSError, ValueError) as e:
            if isinstance(e, FileNotFoundError):
                print(f"Error: file '{filepath}' not found")
            elif isinstance(e, PermissionError):
                print(f"Error: you don't have reading permission "
                      f"in {filepath}")
            else:
                print(f"Error: {e}")
            sys.exit(1)
