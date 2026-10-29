"""3D simulator (Panda3D): a car you can drive, with a virtual ECU you can break.

Run: python -m dmedoc sim      (needs: pip install panda3d panda3d-gltf)
Models: Kenney "Starter Kit Racing" (CC0), see assets/models/CREDITS.txt.
"""

from __future__ import annotations

import math
import os
import sys

from . import __version__
from .i18n import load_saved_lang, set_lang, t
from .binfile import analyse_file
from .sim import SimSource, SimState, diagnose_sim, query_real_ecu
from .diagnose import format_findings

CAR_LENGTH = 4.2  # world units (~metres)
TILE_LENGTH = 12.0
TILES_AHEAD, TILES_BEHIND = 7, 3
CRANK_TIME = 1.4
MAX_SPEED = 45.0  # m/s
CAR_FORWARD_FLIP = True  # set True if the model drives backwards


def _assets_dir() -> str:
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, "assets")


def _make_app(shot: bool):
    from panda3d.core import loadPrcFileData

    loadPrcFileData("", "window-title DMEDoc 3D")
    loadPrcFileData("", "win-size 1180 700")
    loadPrcFileData("", "sync-video 1")
    loadPrcFileData("", "audio-library-name null")
    if shot:
        loadPrcFileData("", "window-type offscreen")
    from direct.showbase.ShowBase import ShowBase

    return ShowBase()


class Simulator:
    def __init__(self, shot: bool = False, source: SimSource | None = None) -> None:
        from direct.gui.DirectGui import DGG, DirectButton, DirectFrame
        from direct.gui.OnscreenText import OnscreenText
        from panda3d.core import (
            AmbientLight,
            CardMaker,
            DirectionalLight,
            Filename,
            TextNode,
            WindowProperties,
        )

        self.DGG = DGG
        self.base = base = _make_app(shot)
        self.Filename = Filename
        self.source = source or SimSource()
        self.base_flash = self.source.flash_fault()  # verdict of the loaded .bin
        self.base_power = self.source.power_fault()  # real ECU that does not answer
        self.state = SimState(fault_flash=self.base_flash, fault_power=self.base_power)
        self.mode = "off"  # off | ign | crank | run | fail
        self.crank_t = 0.0
        self.speed = 0.0
        self.steer_angle = 0.0
        self.keys = {"w": False, "s": False, "a": False, "d": False}

        # .glb files load through panda3d-gltf's "panda3d.loaders" plugin (no patching needed).

        props = WindowProperties()
        ico = os.path.join(_assets_dir(), "dmedoc.ico")
        if os.path.exists(ico):
            props.setIconFilename(Filename.fromOsSpecific(ico))
        props.setTitle(t("sim_title"))
        if not shot:  # offscreen buffers have no window properties
            base.win.requestProperties(props)

        base.setBackgroundColor(0.55, 0.75, 0.95)
        base.disableMouse()

        # lights
        amb = AmbientLight("amb")
        amb.setColor((0.55, 0.55, 0.6, 1))
        base.render.setLight(base.render.attachNewNode(amb))
        sun = DirectionalLight("sun")
        sun.setColor((0.9, 0.88, 0.8, 1))
        sun_np = base.render.attachNewNode(sun)
        sun_np.setHpr(-35, -55, 0)
        base.render.setLight(sun_np)

        self._build_world(CardMaker)
        self._build_gui(DirectButton, DirectFrame, OnscreenText, TextNode)

        for k in self.keys:
            base.accept(k, self.set_key, [k, True])
            base.accept(k + "-up", self.set_key, [k, False])
        base.accept("arrow_up", self.set_key, ["w", True])
        base.accept("arrow_up-up", self.set_key, ["w", False])
        base.accept("arrow_down", self.set_key, ["s", True])
        base.accept("arrow_down-up", self.set_key, ["s", False])
        base.accept("arrow_left", self.set_key, ["a", True])
        base.accept("arrow_left-up", self.set_key, ["a", False])
        base.accept("arrow_right", self.set_key, ["d", True])
        base.accept("arrow_right-up", self.set_key, ["d", False])

        base.taskMgr.add(self.update, "update")
        self.refresh_ui()

    # ------------------------------------------------------------------ world
    def _load(self, name):
        path = os.path.join(_assets_dir(), "models", name)
        return self.base.loader.loadModel(self.Filename.fromOsSpecific(path))

    def _build_world(self, CardMaker) -> None:
        base = self.base
        self.world = base.render.attachNewNode("world")

        # ground follows the car
        cm = CardMaker("ground")
        cm.setFrame(-300, 300, -300, 300)
        self.ground = self.world.attachNewNode(cm.generate())
        self.ground.setP(-90)
        self.ground.setZ(-0.05)
        self.ground.setColor(0.32, 0.55, 0.28, 1)
        self.ground.setLightOff()

        # road tiles: normalise the straight piece to TILE_LENGTH along Y
        road = self._load("track-straight.glb")
        mn, mx = road.getTightBounds()
        size = mx - mn
        along_x = size.x > size.y
        length = size.x if along_x else size.y
        self.road_scale = TILE_LENGTH / length
        self.road_width = (size.y if along_x else size.x) * self.road_scale
        self.tiles = []
        forest = self._load("decoration-forest.glb")
        fmn, fmx = forest.getTightBounds()
        fscale = 9.0 / max(fmx.x - fmn.x, fmx.y - fmn.y)
        n = TILES_AHEAD + TILES_BEHIND
        for i in range(n):
            holder = self.world.attachNewNode(f"tile{i}")
            piece = road.copyTo(holder)
            piece.setScale(self.road_scale)
            if along_x:
                piece.setH(90)
            c = (mn + mx) * 0.5 * self.road_scale
            cx, cy = (c.y, -c.x) if along_x else (c.x, c.y)
            piece.setPos(-cx, -cy, -mn.z * self.road_scale * 0)
            for side in (-1, 1):
                deco = forest.copyTo(holder)
                deco.setScale(fscale)
                fc = (fmn + fmx) * 0.5 * fscale
                deco.setPos(side * (self.road_width / 2 + 7) - fc.x, -fc.y, -fmn.z * fscale)
                deco.setH(90 * (i % 4))
            self.tiles.append(holder)

        # the car: pivot (position) > model (scale / orientation)
        self.car = self.world.attachNewNode("car")
        model = self._load("vehicle-truck-red.glb")
        cmn, cmx = model.getTightBounds()
        csize = cmx - cmn
        long_x = csize.x > csize.y
        scale = CAR_LENGTH / (csize.x if long_x else csize.y)
        self.car_model = self.car.attachNewNode("model")
        model.reparentTo(self.car_model)
        model.setScale(scale)
        cc = (cmn + cmx) * 0.5 * scale
        model.setPos(-cc.x, -cc.y, -cmn.z * scale)
        self.car_model.setH((-90 if long_x else 0) + (180 if CAR_FORWARD_FLIP else 0))
        self.car.setPos(0, 0, 0.05)

        base.camera.setPos(0, -10, 4.5)

    # -------------------------------------------------------------------- gui
    def _build_gui(self, DirectButton, DirectFrame, OnscreenText, TextNode) -> None:
        base = self.base
        DGG = self.DGG
        font = None
        win_font = r"C:\Windows\Fonts\segoeui.ttf"
        if os.path.exists(win_font):
            font = base.loader.loadFont(self.Filename.fromOsSpecific(win_font).getFullpath())
            font.setPixelsPerUnit(64)
        self.font = font

        panel = DirectFrame(
            parent=base.a2dTopLeft,
            frameColor=(0, 0, 0, 0.55),
            frameSize=(0, 0.72, -1.95, 0),
            pos=(0.03, 0, -0.03),
        )
        self.panel = panel

        def btn(text, z, cmd, color=(0.2, 0.3, 0.45, 1)):
            b = DirectButton(
                parent=panel,
                text=text,
                text_font=font,
                text_fg=(1, 1, 1, 1),
                text_align=TextNode.ALeft,
                text_pos=(0.0, -0.012),
                scale=0.042,
                pos=(0.03, 0, z),
                frameSize=(-0.5, 15.5, -0.8, 1.2),
                frameColor=color,
                relief=DGG.FLAT,
                pressEffect=1,
                command=cmd,
            )
            return b

        z = -0.09
        self.b_ign = btn("", z, self.toggle_ignition)
        z -= 0.075
        self.b_start = btn(t("sim_start"), z, self.start_engine, (0.15, 0.5, 0.25, 1))
        z -= 0.075
        self.b_diag = btn(t("sim_diag"), z, self.show_diag, (0.5, 0.4, 0.15, 1))
        z -= 0.095
        OnscreenText(
            parent=panel, text=t("sim_faults"), font=font, fg=(1, 1, 1, 1), scale=0.04,
            pos=(0.03, z), align=TextNode.ALeft,
        )
        z -= 0.07
        self.fault_buttons = {}
        for name in ("power", "flash", "crank", "ews"):
            self.fault_buttons[name] = btn("", z, lambda n=name: self.toggle_fault(n))
            z -= 0.075
        z -= 0.02
        OnscreenText(
            parent=panel, text=t("sim_critical"), font=font, fg=(1, 0.6, 0.5, 1), scale=0.036,
            pos=(0.03, z), align=TextNode.ALeft,
        )
        z -= 0.065
        for name in SimState.CRITICAL:
            self.fault_buttons[name] = btn("", z, lambda n=name: self.toggle_fault(n))
            z -= 0.075
        btn(t("sim_clear"), z, self.clear_faults, (0.4, 0.2, 0.2, 1))
        z -= 0.095
        self.b_accel = btn(t("sim_accel"), z, None, (0.25, 0.25, 0.3, 1))
        self.b_accel.bind(DGG.B1PRESS, lambda e: self.set_key("w", True))
        self.b_accel.bind(DGG.B1RELEASE, lambda e: self.set_key("w", False))
        z -= 0.075
        self.b_brake = btn(t("sim_brake"), z, None, (0.25, 0.25, 0.3, 1))
        self.b_brake.bind(DGG.B1PRESS, lambda e: self.set_key("s", True))
        self.b_brake.bind(DGG.B1RELEASE, lambda e: self.set_key("s", False))

        self.t_state = OnscreenText(
            parent=base.a2dTopRight, text="", font=font, fg=(1, 1, 1, 1), shadow=(0, 0, 0, 1),
            scale=0.06, pos=(-0.05, -0.1), align=TextNode.ARight,
        )
        self.t_speed = OnscreenText(
            parent=base.a2dTopRight, text="", font=font, fg=(1, 1, 1, 1), shadow=(0, 0, 0, 1),
            scale=0.05, pos=(-0.05, -0.18), align=TextNode.ARight,
        )
        self.t_bin = OnscreenText(
            parent=base.a2dTopRight, text=self.source.summary(), font=font, fg=(0.85, 0.95, 1, 1),
            bg=(0, 0, 0, 0.55), scale=0.036, pos=(-0.05, -0.27), align=TextNode.ARight, wordwrap=30,
        )
        self.t_halt = OnscreenText(
            parent=base.a2dTopCenter, text="", font=font, fg=(1, 1, 1, 1), bg=(0.75, 0.05, 0.05, 0.95),
            scale=0.06, pos=(0, -0.45), align=TextNode.ACenter, wordwrap=26,
        )
        self.t_hint = OnscreenText(
            parent=base.a2dBottomRight, text=t("sim_hint"), font=font, fg=(1, 1, 1, 1),
            shadow=(0, 0, 0, 1), scale=0.036, pos=(-0.05, 0.05), align=TextNode.ARight, wordwrap=40,
        )
        self.t_diag = OnscreenText(
            parent=base.a2dBottomLeft, text="", font=font, fg=(1, 1, 1, 1), bg=(0, 0, 0, 0.7),
            scale=0.042, pos=(0.05, 0.42), align=TextNode.ALeft, wordwrap=34,
        )

    # --------------------------------------------------------------- actions
    def set_key(self, k: str, down: bool) -> None:
        self.keys[k] = down and self.mode != "halt"

    def toggle_ignition(self) -> None:
        if self.mode == "halt":
            return
        self.state.ignition = not self.state.ignition
        self.mode = "ign" if self.state.ignition else "off"
        self.t_diag.setText("")
        self.refresh_ui()

    def halt(self) -> None:
        """Critical fault: cut power, freeze the simulation, explain."""
        self.mode = "halt"
        self.state.ignition = False
        self.speed = 0.0
        self.crank_t = 0.0
        for k in self.keys:
            self.keys[k] = False
        self.car.setZ(0.05)
        self.show_diag()
        self.t_halt.setText(t("sim_halt_banner") + "\n" + t("sim_halt_help"))
        self.refresh_ui()

    def toggle_fault(self, name: str) -> None:
        if self.mode == "halt":
            return  # frozen: only "Clear faults" is accepted
        attr = "fault_" + name
        setattr(self.state, attr, not getattr(self.state, attr))
        if self.state.critical():
            self.halt()
        elif self.mode == "run" and not self.state.can_run():
            self.mode = "fail"  # engine stalls
            self.show_diag()
        self.refresh_ui()

    def clear_faults(self) -> None:
        for n in SimState.FAULTS + SimState.CRITICAL:
            setattr(self.state, "fault_" + n, False)
        self.state.fault_flash = self.base_flash  # the loaded .bin keeps its own verdict
        self.state.fault_power = self.base_power  # so does an unresponsive real ECU
        if self.mode == "halt":
            self.mode = "off"  # power stays off: restart manually
            self.t_halt.setText("")
            self.t_diag.setText("")
        self.refresh_ui()

    def start_engine(self) -> None:
        if self.mode == "halt" or not self.state.ignition or self.mode in ("crank", "run"):
            return
        self.mode = "crank"
        self.crank_t = 0.0
        self.t_diag.setText("")
        self.refresh_ui()

    def show_diag(self) -> None:
        self.t_diag.setText(format_findings(diagnose_sim(self.state)))

    def refresh_ui(self) -> None:
        self.b_ign["text"] = t("sim_ign_off") if self.state.ignition else t("sim_ign_on")
        self.b_ign["frameColor"] = (0.6, 0.2, 0.2, 1) if self.state.ignition else (0.2, 0.3, 0.45, 1)
        for name, b in self.fault_buttons.items():
            on = getattr(self.state, "fault_" + name)
            b["text"] = ("[x] " if on else "[  ] ") + t("sim_fault_" + name)
            b["frameColor"] = (0.7, 0.25, 0.1, 1) if on else (0.2, 0.3, 0.45, 1)
        self.t_state.setText(t("sim_state_" + self.mode))

    # ------------------------------------------------------------------ loop
    def update(self, task):
        from direct.task.Task import Task
        from panda3d.core import ClockObject

        dt = min(ClockObject.getGlobalClock().getDt(), 0.1)
        car = self.car

        if self.mode == "halt":  # simulation frozen; only the camera stays alive
            self._update_camera(dt)
            self.t_speed.setText(t("sim_speed", v=0))
            return Task.cont

        if self.mode == "crank":
            self.crank_t += dt
            car.setZ(0.05 + 0.03 * math.sin(self.crank_t * 55))
            if self.crank_t >= CRANK_TIME:
                if self.state.can_run():
                    self.mode = "run"
                else:
                    self.mode = "fail"
                    self.show_diag()
                car.setZ(0.05)
                self.refresh_ui()
        elif self.mode == "run":
            car.setZ(0.05 + 0.012 * math.sin(self.base.clock.getFrameTime() * 70))

        # longitudinal
        if self.mode == "run" and self.keys["w"]:
            self.speed += 14.0 * dt
        elif self.keys["s"]:
            self.speed -= 24.0 * dt
        else:
            self.speed -= (3.0 if self.mode == "run" else 6.0) * dt
        self.speed = max(0.0, min(self.speed, MAX_SPEED))

        # lateral
        steer = (1 if self.keys["d"] else 0) - (1 if self.keys["a"] else 0)
        half = self.road_width / 2 - 0.9
        if self.speed > 0.5:
            nx = car.getX() + steer * 6.0 * dt * min(1.0, self.speed / 8)
            car.setX(max(-half, min(half, nx)))
        target = -steer * 12.0 if self.speed > 0.5 else 0.0
        self.steer_angle += (target - self.steer_angle) * min(1.0, 8 * dt)
        car.setY(car.getY() + self.speed * dt)
        self.car_model.setR(self.steer_angle * 0.0)
        car.setH(self.steer_angle)

        self._update_world()
        self._update_camera(dt)
        self.t_speed.setText(t("sim_speed", v=int(self.speed * 3.6)))
        return Task.cont

    def _update_world(self) -> None:
        cy = self.car.getY()
        base_idx = math.floor(cy / TILE_LENGTH) - TILES_BEHIND
        for i, tile in enumerate(self.tiles):
            tile.setPos(0, (base_idx + i) * TILE_LENGTH + TILE_LENGTH / 2, 0)
        self.ground.setPos(0, cy, -0.05)

    def _update_camera(self, dt: float) -> None:
        from panda3d.core import Vec3

        car = self.car
        want = Vec3(car.getX() * 0.6, car.getY() - 9.5 - self.speed * 0.06, 4.2 + self.speed * 0.02)
        cam = self.base.camera
        k = 1.0 - math.exp(-6.0 * dt)
        cam.setPos(cam.getPos() + (want - cam.getPos()) * k)
        cam.lookAt(car.getX() * 0.9, car.getY() + 6.0, 1.0)

    def run(self) -> None:
        self.base.run()


def ask_source() -> tuple[bool, SimSource | None]:
    """Startup dialog: normal / load a .bin / use the real ECU. Returns (continue?, source)."""
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    from .gui import list_ports, set_window_icon

    root = tk.Tk()
    root.title(t("sim_ask_title"))
    root.resizable(False, False)
    set_window_icon(root)
    choice = tk.StringVar(value="default")
    path_var = tk.StringVar(value="")
    result: dict = {"source": None}

    body = ttk.Frame(root, padding=14)
    body.pack()
    ttk.Radiobutton(body, text=t("sim_src_default"), variable=choice, value="default").grid(
        row=0, column=0, columnspan=3, sticky="w", pady=3
    )
    ttk.Radiobutton(body, text=t("sim_src_bin"), variable=choice, value="bin").grid(
        row=1, column=0, columnspan=3, sticky="w", pady=3
    )

    def browse() -> None:
        p = filedialog.askopenfilename(
            parent=root, title=t("sim_ask_bin"), filetypes=[("ECU dump", "*.bin"), ("All", "*.*")]
        )
        if p:
            path_var.set(p)
            choice.set("bin")

    ttk.Button(body, text=t("sim_src_browse"), command=browse).grid(row=2, column=0, sticky="w", padx=(22, 6))
    ttk.Label(body, textvariable=path_var, width=46).grid(row=2, column=1, columnspan=2, sticky="w")
    ttk.Radiobutton(body, text=t("sim_src_ecu"), variable=choice, value="ecu").grid(
        row=3, column=0, columnspan=3, sticky="w", pady=(10, 3)
    )
    ttk.Label(body, text=t("sim_src_port")).grid(row=4, column=0, sticky="e", padx=(22, 6))
    port = ttk.Combobox(body, values=list_ports(), width=10)
    port.grid(row=4, column=1, sticky="w")
    if port["values"]:
        port.current(0)
    ttk.Label(body, text=t("sim_ecu_note"), foreground="gray").grid(row=5, column=0, columnspan=3, sticky="w", pady=(4, 10))

    def ok() -> None:
        c = choice.get()
        if c == "default":
            result["source"] = SimSource()
        elif c == "bin":
            if not path_var.get():
                messagebox.showwarning(t("sim_ask_title"), t("sim_src_nofile"), parent=root)
                return
            try:
                result["source"] = SimSource(bin_report=analyse_file(path_var.get()))
            except OSError as e:
                messagebox.showerror(t("sim_ask_title"), t("read_error", err=e), parent=root)
                return
        else:
            if not port.get().strip():
                messagebox.showwarning(t("sim_ask_title"), t("sim_src_noport"), parent=root)
                return
            root.config(cursor="watch")
            root.update()
            result["source"] = SimSource(real_ecu=query_real_ecu(port.get().strip()))
        root.destroy()

    row = ttk.Frame(body)
    row.grid(row=6, column=0, columnspan=3, sticky="e")
    ttk.Button(row, text=t("sim_src_cancel"), command=root.destroy).pack(side="right")
    ttk.Button(row, text=t("sim_src_ok"), command=ok).pack(side="right", padx=6)

    root.mainloop()
    return result["source"] is not None, result["source"]


def run_sim(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--lang" in argv:
        set_lang(argv[argv.index("--lang") + 1])
    else:
        set_lang(load_saved_lang() or "en")
    try:
        import panda3d  # noqa: F401
        import gltf  # noqa: F401
    except ImportError:
        print(t("sim_unavailable"))
        return 1

    shot = argv[argv.index("--shot") + 1] if "--shot" in argv else None
    bin_path = argv[argv.index("--bin") + 1] if "--bin" in argv else None
    ecu_port = argv[argv.index("--ecu") + 1] if "--ecu" in argv else None
    if bin_path:
        source = SimSource(bin_report=analyse_file(bin_path))
    elif ecu_port:
        source = SimSource(real_ecu=query_real_ecu(ecu_port))
    elif shot:
        source = SimSource()
    else:
        ok, source = ask_source()
        if not ok:
            return 0
    sim = Simulator(shot=bool(shot), source=source)
    if shot:
        _dev_shot(sim, shot, argv)
        return 0
    sim.run()
    return 0


def _dev_shot(sim: Simulator, path: str, argv: list[str]) -> None:
    """Developer helper: render a scenario offscreen and save a PNG."""
    from panda3d.core import ClockObject, Filename

    faults = argv[argv.index("--faults") + 1].split(",") if "--faults" in argv else []
    seconds = float(argv[argv.index("--seconds") + 1]) if "--seconds" in argv else 4.0
    clock = ClockObject.getGlobalClock()
    clock.setMode(ClockObject.MNonRealTime)
    clock.setDt(1 / 30)
    sim.toggle_ignition()
    for f in faults:
        if f:
            sim.toggle_fault(f)
    sim.start_engine()
    sim.set_key("w", True)
    for _ in range(int(seconds * 30)):
        sim.base.taskMgr.step()
    sim.base.graphicsEngine.renderFrame()
    sim.base.win.saveScreenshot(Filename.fromOsSpecific(path))


if __name__ == "__main__":
    sys.exit(run_sim())
