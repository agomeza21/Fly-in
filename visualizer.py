import tkinter as tk
import math
from models import Graph, Zone, Drone


class Visualizer:
    def __init__(self, graph: Graph, path: list[Zone]) -> None:
        self.graph: Graph = graph
        self.path: list[Zone] = path
        self.drones: list[Drone] = []
        self.current_turn: int = 0
        self.speed: int = 800
        self.paused: bool = False

        self.root = tk.Tk()
        self.root.title("Fly-in Simulator")
        self.root.geometry("1200x700")
        self.root.configure(bg="#1a1a2e")

        self.canvas = tk.Canvas(self.root, bg="#1a1a2e",
                                highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._build_side_panel()
        self._compute_positions()

    def _build_side_panel(self) -> None:
        panel = tk.Frame(self.root, bg="#16213e", width=250)
        panel.pack(side=tk.RIGHT, fill=tk.Y)
        panel.pack_propagate(False)

        tk.Label(panel, text="FLY-IN SIMULATOR",
                 bg="#16213e", fg="#e94560",
                 font=("Courier", 14, "bold")).pack(pady=20)

        self.turn_label = tk.Label(panel, text="Turn: 0",
                                   bg="#16213e", fg="white",
                                   font=("Courier", 12))
        self.turn_label.pack(pady=5)

        self.status_label = tk.Label(panel, text="Drones: 0 arrived",
                                     bg="#16213e", fg="#a8dadc",
                                     font=("Courier", 10))
        self.status_label.pack(pady=5)

        tk.Label(panel, text="Speed",
                 bg="#16213e", fg="white",
                 font=("Courier", 10)).pack(pady=(20, 0))

        self.speed_slider = tk.Scale(
            panel, from_=200, to=2000,
            orient=tk.HORIZONTAL,
            bg="#16213e", fg="white",
            highlightthickness=0,
            command=self._on_speed_change
        )
        self.speed_slider.set(800)
        self.speed_slider.pack(padx=20)

        self.pause_btn = tk.Button(
            panel, text="⏸ PAUSE",
            bg="#e94560", fg="white",
            font=("Courier", 11, "bold"),
            relief=tk.FLAT,
            command=self._toggle_pause
        )
        self.pause_btn.pack(pady=20, padx=20, fill=tk.X)

        self.drone_info = tk.Text(
            panel, bg="#0f3460", fg="#a8dadc",
            font=("Courier", 9),
            relief=tk.FLAT, state=tk.DISABLED
        )
        self.drone_info.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    def _on_speed_change(self, val: str) -> None:
        self.speed = int(val)

    def _toggle_pause(self) -> None:
        self.paused = not self.paused
        self.pause_btn.config(
            text="▶ PLAY" if self.paused else "⏸ PAUSE"
        )

    def _compute_positions(self) -> None:
        self.positions: dict[str, tuple[float, float]] = {}
        coords = [(z.x, z.y) for z in self.graph.zones.values()]
        min_x = min(c[0] for c in coords)
        max_x = max(c[0] for c in coords)
        min_y = min(c[1] for c in coords)
        max_y = max(c[1] for c in coords)

        margin = 100
        w = 950 - 2 * margin
        h = 700 - 2 * margin

        for name, zone in self.graph.zones.items():
            if max_x == min_x:
                px = 950 / 2
            else:
                px = margin + (zone.x - min_x) / (max_x - min_x) * w
            if max_y == min_y:
                py = 700 / 2
            else:
                py = margin + (zone.y - min_y) / (max_y - min_y) * h
            self.positions[name] = (px, py)

    def _hex_points(self, cx: float, cy: float,
                    r: float) -> list[float]:
        points: list[float] = []
        for i in range(6):
            angle = math.pi / 180 * (60 * i - 30)
            points.append(cx + r * math.cos(angle))
            points.append(cy + r * math.sin(angle))
        return points

    def _zone_color(self, zone:  Zone) -> str:
        if zone.color:
            color_map: dict[str, str] = {
                "red": "#e94560",
                "green": "#2d6a4f",
                "blue": "#1d3557",
                "yellow": "#f4a261",
                "gray": "#6c757d",
                "orange": "#e76f51",
                "purple": "#7b2d8b",
            }
            return color_map.get(zone.color, "#0f3460")
        type_map: dict[str, str] = {
            "normal": "#0f3460",
            "restricted": "#e94560",
            "priority": "#2d6a4f",
            "blocked": "#333333",
        }
        return type_map.get(zone.zone_type, "#0f3460")

    def _draw(self) -> None:
        self.canvas.delete("all")

        for conn in self.graph.connections:
            x1, y1 = self.positions[conn.zone1.name]
            x2, y2 = self.positions[conn.zone2.name]
            width = 1 + conn.max_link_capacity
            self.canvas.create_line(
                x1, y1, x2, y2,
                fill="#a8dadc", width=width, dash=(6, 4)
            )
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            self.canvas.create_oval(
                mx - 3, my - 3, mx + 3, my + 3,
                fill="#e94560", outline=""
            )

        for name, zone in self.graph.zones.items():
            cx, cy = self.positions[name]
            color = self._zone_color(zone)
            pts = self._hex_points(cx, cy, 35)
            self.canvas.create_polygon(
                pts, fill=color,
                outline="#a8dadc", width=2
            )
            self.canvas.create_text(
                cx, cy, text=name,
                fill="white",
                font=("Courier", 8, "bold")
            )

        drones_by_zone: dict[str, list[Drone]] = {}
        for drone in self.drones:
            if not drone.arrived:
                zn = drone.current_zone.name
                if zn not in drones_by_zone:
                    drones_by_zone[zn] = []
                drones_by_zone[zn].append(drone)

        for zone_name, zone_drones in drones_by_zone.items():
            cx, cy = self.positions[zone_name]
            for i, drone in enumerate(zone_drones):
                offset_x = (i - len(zone_drones) / 2) * 15
                dx = cx + offset_x
                dy = cy - 45
                self.canvas.create_polygon(
                    [dx, dy - 10, dx - 7, dy + 7, dx + 7, dy + 7],
                    fill="white", outline="#e94560", width=1
                )
                self.canvas.create_text(
                    dx, dy + 15,
                    text=f"D{drone.drone_id}",
                    fill="#e94560",
                    font=("Courier", 7, "bold")
                )

    def _update_panel(self, arrived: int) -> None:
        self.turn_label.config(text=f"Turn: {self.current_turn}")
        self.status_label.config(
            text=f"Arrived: {arrived}/{len(self.drones)}"
        )
        self.drone_info.config(state=tk.NORMAL)
        self.drone_info.delete("1.0", tk.END)
        for drone in self.drones:
            status = "✓ arrived" if drone.arrived else (
                f"zone: {drone.current_zone.name}"
            )
            self.drone_info.insert(
                tk.END, f"D{drone.drone_id}: {status}\n"
            )
        self.drone_info.config(state=tk.DISABLED)

    def run(self, drones: list[Drone],
            turn_callback: object) -> None:
        self.drones = drones
        self.turn_callback = turn_callback
        self._schedule_next()
        self.root.mainloop()

    def _schedule_next(self) -> None:
        if self.paused:
            self.root.after(100, self._schedule_next)
            return
        arrived = sum(1 for d in self.drones if d.arrived)
        if arrived < len(self.drones):
            self.current_turn += 1
            if callable(self.turn_callback):
                self.turn_callback()
            self._draw()
            self._update_panel(arrived)
            self.root.after(self.speed, self._schedule_next)
        else:
            self._draw()
            self._update_panel(arrived)
            self.turn_label.config(
                text=f"Done! {self.current_turn} turns"
            )
