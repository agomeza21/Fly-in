"""Entry point for the Fly-in drone routing simulator.

Running this file from the command line is how the whole program
starts: it reads the command-line arguments, parses the map file,
computes the routes, and then either prints the simulation
turn-by-turn in the terminal, or shows it in a graphical window
if --visual was given.
"""
from parser import Parser
from pathfinder import Pathfinder
from simulator import Simulator
import sys


class FlyInApp:
    """Wires together the Parser, Pathfinder and Simulator.

    This class is the "conductor" of the whole program: it does
    not parse maps, find paths, or simulate drones itself - it
    just calls, in order, the classes that do each of those jobs,
    and reacts if any step goes wrong (bad arguments, or no path
    found between the start and end zones).

    Attributes:
        argv (list[str]): The raw command-line arguments, exactly
        as Python received them (including argv[0], the script
        name itself).
    """
    def __init__(self, argv: list[str]) -> None:
        """Stores the command-line arguments for later use

        Args:
            argv (list[str]): The command-line arguments, normally
                passed in as sys.argv.
        """
        self.argv: list[str] = argv

    def _validate_args(self) -> str:
        """Checks the command-line arguments and returns the map path.

        Two rules are enforced here: a map file path must be given
        (argv must have at least 2 entries: the script name and
        the path), and every argument after the map path must be
        exactly "--visual" - nothing else is accepted. If either
        rule is broken, a usage message is printed and the whole
        program exits inmediately; this method never returns in
        that case.

        Returns:
            str: The map file path, taken from argv[1].
        """
        if len(self.argv) < 2:
            print("Usage: python3 main.py <map_file>")
            sys.exit(1)
        for arg in self.argv[2:]:
            if arg != "--visual":
                print("Usage: python3 main.py <map_file> [--visual]")
                print(f"Error: unrecognized argument '{arg}'")
                sys.exit(1)
        return self.argv[1]

    def run(self) -> None:
        """Runs the whole program, start to finish.

        The steps are always the same: validate the arguments,
        parse the map file into a Graph, ask the Pathfinder for
        every useful path between the start and end zones, and
        then hand everything over to a Simulator - either running
        it with the graphical Visualizer (if --visual was given),
        or runnung it in plain text mode.

        If the Pathfinder cannot find any path at all between the
        start and end zones, an error is printed and the program
        exits - there is nothing a Simulator could do in that
        case, since no drone could ever reach the end zone.
        """
        map_file = self._validate_args()

        graph = Parser().parse(map_file)

        paths = Pathfinder().find_paths(graph)
        if not paths:
            print("Error: no path found between start and end hub")
            sys.exit(1)

        simulator = Simulator(graph, paths)
        if "--visual" in self.argv:
            from visualizer import Visualizer
            viz = Visualizer(graph, paths)
            simulator.run_visual(viz)
        else:
            simulator.run()


if __name__ == "__main__":
    FlyInApp(sys.argv).run()
