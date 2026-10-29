"""PyInstaller entry point: GUI by default, 3D simulator with --sim."""

import sys

if __name__ == "__main__":
    if "--sim" in sys.argv:
        from dmedoc.sim3d import run_sim

        sys.exit(run_sim([a for a in sys.argv[1:] if a != "--sim"]))
    from dmedoc.gui import main

    main()
