import tkinter as tk
import math
from models import Graph, Zone, Drone


class Visualizer:
    """Draws the simulation in a graphical window, turn bby turn.

    A Visualizer is only created when the user runs the program
    with --visual. It owns a tkinter window with two parts: a
    canvas on the left showing the zones as hexagons, the
    connections between them, and the drones moving around, and a
    side panel on the right showing the current turn, how many
    drones have arrived, a speed slider, and a pause/replay button.

    Unlike the Simulator, thhis class does not decide how drones
    move - it only reads the state of the drones it is given (see
    run) and redras the canvas after every turn. The actual turn
    logic still lives in Simulatro.step, which this class calls
    through a callback.

    Attributes:
        graph (Graph): The full drone network being visualized.
        paths (list[list[Zone]]): Every distinct path computed by
            the Pathfinder. Kept for future use (for example,
            higlighting each drone's own route); the current
            drawing code does not read from it directly, since
            zone and connection positions already come from graph.
        drones (list[Drone]): The drones being simulated. Set later,
            when run is called, not in the constructor.
        current_turn (int): How many turns have been simulated so
            far in this run.
        speed (int): The delay, in milliseconds, between turns,
            controlled by the speed slider. Defaults to 800.
        paused (bool): Whether the simmulation is currently paused.
        finished (bool): True once every drone has arrived and the
            simulation has stopped advancing.
        panel_width (int): THe width, in pixels, of the side panels.
        arrived_turn (dict[int, int]): For each droneid that has
            arrived, the turn number in which it arrived. Used so
            a drone is still drawn at its final zone for exactly
            one extra frame, instead of disappearing instantly.
    """
    def __init__(self, graph: Graph, paths: list[list[Zone]]) -> None:
        """Creates the tkinter windiw and lays out its widgets.

        This builds the whole window up fornt: ir maximizes it,
        creates the canvas and the sid panel, and computes where
        eacch zone should be drawn on screen. It does not draw
        anything yet, and it does not start the simulaton - that
        only happens once run is called.

        Args:
            graph (Graph): The full drone network to visualize.
            paths (list[list[Zone]]): Every distinct path computed
                by the Pathfinder, kept for possible future use.
        """
        self.graph: Graph = graph
        self.paths: list[list[Zone]] = paths
        self.drones: list[Drone] = []
        self.current_turn: int = 0
        self.speed: int = 800
        self.paused: bool = False
        self.finished: bool = False
        self.panel_width: int = 285
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
        """Resizes the window to fill the whole screen.

        Different operating systems handle "maximize" differently,
        so this first sets an explicit geometry matching the
        screen size, then tries the Linux-style "-zoomed" attribute,
        and falls back to the "zoomed" state (used on windows) if
        that is not supported. If neither works, the window simply
        stays at the geometry already set.
        """
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
        """Creates every widget in the right-hand side panel.

        This builds, from top to bottom: a title label, the turn
        counter label, the "arrived" status label, a speed slider,
        the pause/replay button, and a text box listing every
        drone's current status. Al of these are stored as
        attributes (self.turn_label, self.status_label, and so on)
        so other methods can update them later, as the simulation
        progresses.
        """
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
        """Updates the simulation speed from the slider.

        Called automatically by tkiter every time the user moves
        the speed slider. The slider gives its value as a string,
        so it has to be converted to an int before being stored.

        Args:
            val (str): The slider's new value, as text.
        """
        self.speed = int(val)

    def _toggle_pause(self) -> None:
        """Handles a click on the pause/replay button.

        This button does two different jos dpending on the
        simulation's state: while the simulation is still running,
        it pauses or resumes it, and once every drone has arrived,
        it restarts the whole simulation from scratch instead.
        """
        if self.finished:
            self._restart_simulation()
            return
        self.paused = not self.paused
        self.pause_btn.config(
            text="▶ PLAY" if self.paused else "⏸ PAUSE"
        )

    def _restart_simulation(self) -> None:
        """Resets every drne and starts the simulation over.

        Called when the user clicks "REPLAY" after the simulation
        has finished. Every drone is sent back to the start zone,
        its path_index reset to 0, and every turn counter is
        cleared, so the whole run behaves exactly like a fresh
        start.
        """
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
        """Works out where to draw every zone on the canvas.

        Zones are placed on the map using their own (x, y)
        coordinates from the map file, but those coordinates can be
        any range of numbers - this method rescales them to fit
        neatly inside the canvas, with a fixed margin around the
        edges, no matter how big or small the original coordinates
        were. THe result is stored in self.positions, a dict
        mapping each zone's name to its (pixel_x, pixel_y)
        position on screen.
        """
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
        """Calculates the six corner points of a hexagon.

        Zones are drawn as hexagons rather than plain circles or
        squares, purely for visual style. This method works out
        the (x, y) position of each of the six corners, spaced 60
        egrees apart around the given center point.

        Args:
            cx (float): The x coordinate of the hexagon's center.
            cy (float): The y coordinate of the hexagon's center.
            r (float): THe distance from the center to each corner.

        Returns:
            list[float]: The six corners, flattened into a single
                list as [x1, y1, x2, y2, ..., x6, y6], which is the
                format tkinter's crete_polygon expects.
        """
        points: list[float] = []
        for i in range(6):
            angle = math.pi / 180 * (60 * i - 30)
            points.append(cx + r * math.cos(angle))
            points.append(cy + r * math.sin(angle))
        return points

    def _zone_color(self, zone:  Zone) -> str:
        """Works out which color to fill a zone with.

        If the zone has a color set in the map file, this checks
        that tkinter actually recognizes it as a valid color name
        (using winfo_rgb, which raises an error for anything it
        cannot understand). If the zone has no color, or its color
        is not valid, a neutral gey is used instead.

        Args:
            zone (Zone): The zone to ffind a color for.

        Returns:
            str: A color tkinter can use directly - either the
                zone's own color, or the fallbacck grey ("#898989").
        """
        if zone.color:
            try:
                self.root.winfo_rgb(zone.color)
                return zone.color
            except tk.TclError:
                return "#898989"
        return "#898989"

    def _text_color_for(self, bg_color: str) -> str:
        """Picks a readable text color for a given backgrround color.

        Works out how bright a background color is (its luminance),
        and returns dark text for bright backgrounds or white text
        for dark backgrounds, so the drone id labels drawn on top
        of each zone stay readable no matter what color it is.

        Args:
            bg_color (str): The background color the text will sit
                on top of.

        Returns:
            str: Either a dark color ("#1a1a2e") or white,
                whichever is mre readable on top of bg_color.
        """
        try:
            r, g, b = self.root.winfo_rgb(bg_color)
            luminance = (r * 299 + g * 587 + b * 114) / (1000 * 65535)
            return "#1a1a2e" if luminance > 0.5 else "white"
        except tk.TclError:
            return "white"

    def _draw(self) -> None:
        """Redraws the entire canvas for the current turn.

        This clears the canvas ccompletely and draws everythhing
        from scratch: every connection as a dashed line, every zone
        as a colored hexagon with its name, every drone that is
        sitting in a zone (grouped and spaced out if several share
        the same zone), and every drone currently mid-flight toward
        a restricted zone, drawn halfway along its connection.

        Drones that just arrived tis turn are drawn one last time
        at their final zone, using arrived_turn to tell "just
        arrived" apart from "arrived a while ago" -ater that one
        extra frame, they stop being drawn entirely.
        """
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
        """Recomputes zone position when the window is resized.

        Called automatically by tkinter whenever the canvas
        changes size. Tinny size changes (smaler than 100x100,
        which can happen briefly while the window is first being
        built) are ignored, to avoid recalculating positions based
        on a canvas that has not settled into its rea size yet.

        Args:
            event (tk.Event): The resize event tkinter passes in,
                containing the canvas's new width and height.
        """
        if event.width > 100 and event.height > 100:
            self._compute_positions()
            self._draw()

    def _draw_drone(self, cx: float, cy: float) -> None:
        """Draws a single small drone icon at the given position.

        The icon is a simple quadcopter shape: a body in the
        center, with four arms going out to four rotors. Everything
        is scaled down automatically on maps with a lot of zones,
        so the icons don not end up overlapping each other or the
        zone hexagons.

        Args:
            cx (float): The x coordinate where the drone's center
                should be drawn.
            cy (float): The y coordinate where the drone's center
                should be drawn.
        """
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
        """Refreshes the side panel's text after a turn

        Updates the turn counter label, the "arrived" count, and
        the whole per-drone status list in the text box, replacing
        its revious contents completely with the current status
        of every drone (either "zone: <name>" or "arrived").

        Args:
            arrived (int): How many drones have reached the end
                zone so far, used for the "Arrived: X/Y" label.
        """
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
        """Starts the graphical simulation loop.

        Stores the drones to display and the callback that should
        be called once per turn (normally Simulator.step), then
        schedules the first turn and hands control over completely
        to tkinter's main loop - this method does not return until
        the window is closed.

        Args:
            drones (list[Drone]): The drones to simulate and draw.
            turn_callback (object): The function to call once per
                turn to advance the simulation by one step.
                Declared as object, and checked with callable ()
                before use, purely to keep the type hint simple.
        """
        self.drones = drones
        self.turn_callback = turn_callback
        self._schedule_next()
        self.root.mainloop()

    def _schedule_next(self) -> None:
        """Advances one turn, redraws, and schedules the next call.

        This is the method taht actually drives the simulation
        forward while --visual is active, called repeatedly through
        tkinter's root.after (which is how tkinter handles "do this
        again after N milliseconds" without freezong the window).

        On every call: if paused, it just reschedules itself
        without doing anything else. Otherwise, if drones are still
        missing, it calls turn_callback (Simulator.step) to advance
        one turn, redraws the canvas, updates the side panel, and
        schedules itself again after self.speed milliseconds. Once
        every drone has arrived, it draws one final frame, shows
        the total number of turns taken, and changes the button to
        "REPLAY" instead of scheduling anything further.
        """
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
