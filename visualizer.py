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
        self.finished: bool = False
        self.panel_width: int = 220
        self.arrived_turn: dict[int, int] = {}

        self.root = tk.Tk()
        self.root.title("Fly-in Simulator")
        self._maximize_window()
        self.root.configure(bg="#515162")

        self.canvas = tk.Canvas(self.root, bg="#1a1a2e",
                                highlightthickness=0)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._build_side_panel()
        self.canvas.bind("<Configure>", self._on_resize)
        self.root.update_idletasks()
        self._compute_positions()

    def _maximize_window(self) -> None:
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"{sw}x{sh}+0+0")
        try:
            self.root.attributes("-zoomed", True)
        except tk.TclError:
            try:
                self.root.state("zoomed")
            except tk.TclError:
                pass

    def _build_side_panel(self) -> None:
        panel = tk.Frame(self.root, bg="#16213e", width=self.panel_width)
        panel.pack(side=tk.RIGHT, fill=tk.Y)
        panel.pack_propagate(False)

        tk.Label(panel, text="FLY-IN SIMULATOR",
                 bg="#16213e", fg="#e94560",
                 font=("Courier", 11, "bold")).pack(pady=20)

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
        if self.finished:
            self._restart_simulation()
            return
        self.paused = not self.paused
        self.pause_btn.config(
            text="▶ PLAY" if self.paused else "⏸ PAUSE"
        )

    def _restart_simulation(self) -> None:
        for drone in self.drones:
            drone.current_zone = self.graph.start_hub
            drone.path_index = 0
            drone.arrived = False
            drone.in_transit_to = None
        self.arrived_turn.clear()
        self.current_turn = 0
        self.finished = False
        self.paused = False
        self.pause_btn.config(text="⏸ PAUSE")
        self._draw()
        self._update_panel(0)
        self._schedule_next()

    def _compute_positions(self) -> None:
        self.positions: dict[str, tuple[float, float]] = {}
        coords = [(z.x, z.y) for z in self.graph.zones.values()]
        min_x = min(c[0] for c in coords)
        max_x = max(c[0] for c in coords)
        min_y = min(c[1] for c in coords)
        max_y = max(c[1] for c in coords)

        self.root.update_idletasks()
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        if canvas_w <= 1:
            canvas_w = self.root.winfo_screenwidth() - self.panel_width
        if canvas_h <= 1:
            canvas_h = self.root.winfo_screenheight()

        margin = 100
        w = canvas_w - 2 * margin
        h = canvas_h - 2 * margin

        for name, zone in self.graph.zones.items():
            if max_x == min_x:
                px = canvas_w / 2
            else:
                px = margin + (zone.x - min_x) / (max_x - min_x) * w
            if max_y == min_y:
                py = canvas_h / 2
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
            try:
                self.root.winfo_rgb(zone.color)
                return zone.color
            except tk.TclError:
                return "#898989"
        return "#898989"

    def _text_color_for(self, bg_color: str) -> str:
        try:
            r, g, b = self.root.winfo_rgb(bg_color)
            luminance = (r * 299 + g * 587 + b * 114) / (1000 * 65535)
            return "#1a1a2e" if luminance > 0.5 else "white"
        except tk.TclError:
            return "white"

    def _draw(self) -> None:
        self.canvas.delete("all")

        drones_by_zone: dict[str, list[Drone]] = {}
        for drone in self.drones:
            just_arrived = (
                drone.arrived
                and drone.drone_id in self.arrived_turn
                and self.arrived_turn[drone.drone_id] == self.current_turn
            )
            if ((not drone.arrived or just_arrived) and
                    drone.in_transit_to is None):
                zn = drone.current_zone.name
                if zn not in drones_by_zone:
                    drones_by_zone[zn] = []
                drones_by_zone[zn].append(drone)

        for conn in self.graph.connections:
            x1, y1 = self.positions[conn.zone1.name]
            x2, y2 = self.positions[conn.zone2.name]
            width = 1 + conn.max_link_capacity
            self.canvas.create_line(
                x1, y1, x2, y2,
                fill="#a8dadc", width=width, dash=(6, 4)
            )

        num_zones = len(self.graph.zones)
        if num_zones > 25:
            hex_radius = 18
            font_size = 6
            text_offset = 18
        elif num_zones > 12:
            hex_radius = 28
            font_size = 8
            text_offset = 32
        else:
            hex_radius = 40
            font_size = 10
            text_offset = 48
        for name, zone in self.graph.zones.items():
            cx, cy = self.positions[name]
            color = self._zone_color(zone)
            pts = self._hex_points(cx, cy, hex_radius)
            self.canvas.create_polygon(
                pts, fill=color,
                outline="#a8dadc", width=2
            )
            drones_here = drones_by_zone.get(name, [])
            if drones_here:
                ids = " ".join(f"D{d.drone_id}" for d in drones_here)
                self.canvas.create_text(
                    cx, cy,
                    text=ids,
                    fill=self._text_color_for(color),
                    font=("Courier", 7, "bold")
                )
            text_offset = 22 if num_zones > 25 else 45
            self.canvas.create_text(
                cx, cy + text_offset, text=name,
                fill="white",
                font=("Courier", font_size, "bold")
            )

        for drone in self.drones:
            if drone.arrived:
                continue
            if drone.in_transit_to is not None:
                x1, y1 = self.positions[drone.current_zone.name]
                x2, y2 = self.positions[drone.in_transit_to.name]
                mx = (x1 + x2) / 2
                my = (y1 + y2) / 2
                self._draw_drone(mx, my)
                text_offset_transit = 25 if num_zones > 25 else 50
                self.canvas.create_text(
                    mx, my + text_offset_transit,
                    text=f"D{drone.drone_id}",
                    fill="white",
                    font=("Courier", font_size, "bold")
                )

        for zone_name, zone_drones in drones_by_zone.items():
            cx, cy = self.positions[zone_name]
            n = len(zone_drones)
            if num_zones > 25:
                spacing, y_offset = 12, 18
            elif num_zones > 12:
                spacing, y_offset = 22, 38
            else:
                spacing, y_offset = 30, 55
            for i, drone in enumerate(zone_drones):
                offset_x = (i - (n - 1) / 2) * spacing
                dx = cx + offset_x
                dy = cy - y_offset
                self._draw_drone(dx, dy)

    def _on_resize(self, event: tk.Event) -> None:
        if event.width > 100 and event.height > 100:
            self._compute_positions()
            self._draw()

    def _draw_drone(self, cx: float, cy: float) -> None:
        num_zones = len(self.graph.zones)
        if num_zones > 25:
            scale = 0.5
        elif num_zones > 12:
            scale = 0.8
        else:
            scale = 1.2
        arm = 14 * scale
        rotor = 5 * scale
        body = 6 * scale
        angles = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
        for dx, dy in angles:
            ex = cx + dx * arm
            ey = cy + dy * arm
            self.canvas.create_line(
                cx, cy, ex, ey,
                fill="white", width=max(1, int(2 * scale))
            )
            self.canvas.create_oval(
                ex - rotor, ey - rotor,
                ex + rotor, ey + rotor,
                fill="#a8dadc", outline="white", width=1
            )
        self.canvas.create_oval(
            cx - body, cy - body, cx + body, cy + body,
            fill="white", outline="#1a1a2e", width=max(1, int(2 * scale))
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
            for drone in self.drones:
                if drone.arrived and drone.drone_id not in self.arrived_turn:
                    self.arrived_turn[drone.drone_id] = self.current_turn
            self._draw()
            self._update_panel(arrived)
            self.root.after(self.speed, self._schedule_next)
        else:
            self.finished = True
            self._draw()
            self._update_panel(arrived)
            self.turn_label.config(
                text=f"Done! {self.current_turn} turns"
            )
            self.pause_btn.config(text="↻ REPLAY")
