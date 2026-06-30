import sys

class Parser:
    def __init__(self) -> None:
        self.nb_drones: int = 0
        self.zones: dict = {}
        self.start_hub_name: str = ""
        self.end_hub_name: str = ""

    def parse(self, filepath: str) -> None:
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
                            raise ValueError(f"line {line_number}: nb_drones must be a positive integer, got '{num}'")
                    elif line.startswith("start_hub:"):
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
                            raise ValueError(f"line {line_number}: start_hub must have name, x and y, got '{data}'")
                        name, x, y = parts
                        try:
                            x_int = int(x)
                            y_int = int(y)
                        except ValueError:
                            raise ValueError(f"line {line_number}: x and y must be valid integers, got '{x}', '{y}'")
                        metadata = metadata.rstrip("]")
                        metadata_pairs = metadata.split()
                        meta_dict = {}
                        for pair in metadata_pairs:
                            if "=" not in pair:
                                raise ValueError(f"line {line_number}: invalid metadata format '{pair}'")
                            key, value = pair.split("=", 1)
                            meta_dict[key] = value
                        if name in self.zones:
                            raise ValueError(f"line {line_number}: zone name '{name}' is already used")
                        if self.start_hub_name != "":
                            raise ValueError(f"line {line_number}: start_hub is already defined")
                        self.zones[name] = {"x": x_int, "y": y_int, "metadata": meta_dict}
                        self.start_hub_name = name
                    elif line.startswith("end_hub:"):
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
                            raise ValueError(f"line {line_number}: start_hub must have name, x and y, got '{data}'")
                        name, x, y = parts
                        try:
                            x_int = int(x)
                            y_int = int(y)
                        except ValueError:
                            raise ValueError(f"line {line_number}: x and y must be valid integers, got '{x}', '{y}'")
                        metadata = metadata.rstrip("]")
                        metadata_pairs = metadata.split()
                        meta_dict = {}
                        for pair in metadata_pairs:
                            if "=" not in pair:
                                raise ValueError(f"line {line_number}: invalid metadata format '{pair}'")
                            key, value = pair.split("=", 1)
                            meta_dict[key] = value
                        if name in self.zones:
                            raise ValueError(f"line {line_number}: zone name '{name}' is already used")
                        if self.end_hub_name != "":
                            raise ValueError(f"line {line_number}: start_hub is already defined")
                        self.zones[name] = {"x": x_int, "y": y_int, "metadata": meta_dict}
                        self.end_hub_name = name
                    elif line.startswith("hub:"):
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
                            raise ValueError(f"line {line_number}: start_hub must have name, x and y, got '{data}'")
                        name, x, y = parts
                        try:
                            x_int = int(x)
                            y_int = int(y)
                        except ValueError:
                            raise ValueError(f"line {line_number}: x and y must be valid integers, got '{x}', '{y}'")
                        metadata = metadata.rstrip("]")
                        metadata_pairs = metadata.split()
                        meta_dict = {}
                        for pair in metadata_pairs:
                            if "=" not in pair:
                                raise ValueError(f"line {line_number}: invalid metadata format '{pair}'")
                            key, value = pair.split("=", 1)
                            meta_dict[key] = value
                        self.zones[name] = {"x": x_int, "y": y_int, "metadata": meta_dict}
                    elif line.startswith("connection:"):

                    else:
                        raise ValueError(f"line {line_number}: format is incorrect: '{line}'")
        except (FileNotFoundError, PermissionError, ValueError) as e:
            if isinstance(e, FileNotFoundError):
                print(f"Error: file '{filepath}' not found")
            elif isinstance(e, PermissionError):
                print(f"Error: you don't have reading permission in {filepath}")
            else:
                print(f"Error: {e}")
            sys.exit(1)


