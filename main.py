from parser import Parser
from pathfinder import Pathfinder
from simulator import Simulator
import sys


class FlyInApp:
    def __init__(self, argv: list[str]) -> None:
        self.argv: list[str] = argv

    def _validate_args(self) -> str:
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
        map_file = self._validate_args()

        graph = Parser().parse(map_file)

        path = Pathfinder().find_path(graph)
        if not path:
            print("Error: no path found between start and end hub")
            sys.exit(1)

        simulator = Simulator(graph, path)
        if "--visual" in self.argv:
            from visualizer import Visualizer
            viz = Visualizer(graph, path)
            simulator.run_visual(viz)
        else:
            simulator.run()


if __name__ == "__main__":
    FlyInApp(sys.argv).run()
