"""
PROJECT             : Micro Canvas Editor
FILE NAME           : canvas.py
REQUIREMENT         : Python 3.x (tkinter is included in the standard library)
                      Pillow  →  pip install Pillow
VERSION             : 1.0.0
LAST MODIFICATION   : 25 APR 2026
"""

# import libraries
import tkinter as tk
from PIL import Image, ImageTk  # use to convert numpy array to tkinter format to display   
import numpy as np

# init constants parameters
COLS, ROWS = 30, 30             # drawing grid cells (30×30 pixels)
CELL = 1                        # each cell = 1 pixel in the final image

IMG_W, IMG_H = 1920, 1080       # final output image size
OFFSET_X, OFFSET_Y = 928, 468   # where the 30×30 drawing is placed in the output (928, 468)

ZOOM = 20                       # fixed display zoom (pixels per cell on screen)

OUTPUT_FILE = "microCanvas.png"

# application function
class PixelCanvas(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Micro Canvas Editor")
        self.resizable(True, True)

        # State
        self.pixels = np.zeros((ROWS, COLS), dtype=np.uint8)    # 0=black, 1=white
        self.zoom = ZOOM
        self.mode = tk.StringVar(value="draw")                  # "draw" | "erase"
        self.painting = False                                   # default mouse button released
        self.last_cell = (-1, -1)                               # clear mouse state
        self._tk_img = None                                     # keep reference to avoid GC

        self._build_ui()    # calling _build_ui function
        self._render()      # calling _render function

    # graphic user interface
    def _build_ui(self):
        # toolbar
        tb = tk.Frame(self, bg="#1a1a1a", padx=8, pady=6)
        tb.pack(fill=tk.X)

        btn_style = dict(bg="#2b2b2b", fg="#e0e0e0", relief=tk.FLAT,
                         padx=10, pady=4, cursor="hand2", font=("Courier", 10))
        act_style = {**btn_style, "bg": "#e0e0e0", "fg": "#1a1a1a"}

        self._draw_btn  = tk.Button(tb, text="● Draw", command=lambda: self._set_mode("draw"), **act_style)
        self._erase_btn = tk.Button(tb, text="○ Erase", command=lambda: self._set_mode("erase"), **btn_style)
        tk.Button(tb, text="Clear all",   command=self._clear_all, **btn_style).pack(side=tk.LEFT, padx=2)
        self._draw_btn.pack(side=tk.LEFT, padx=2)
        self._erase_btn.pack(side=tk.LEFT, padx=2)

        # stats
        self._stats_var = tk.StringVar(value="0 px white")
        tk.Label(tb, textvariable=self._stats_var, bg="#1a1a1a", fg="#888",
                 font=("Courier", 10)).pack(side=tk.LEFT, padx=14)

        # create Image button
        tk.Button(tb, text="⬇  Create Image", command=self._create_image,
                  bg="#111", fg="#fff", relief=tk.FLAT, padx=12, pady=4,
                  cursor="hand2", font=("Courier", 10, "bold")).pack(side=tk.RIGHT, padx=4)

        # information label
        ir = tk.Frame(self, bg="#111", padx=8, pady=4)
        ir.pack(fill=tk.X)
        tk.Label(ir, text=f"30×30 px drawing grid",
                 bg="#111", fg="#fff", font=("Courier", 9)).pack(side=tk.LEFT)

        # center canvas area
        frame = tk.Frame(self, bg="#1a1a1a")
        frame.pack(fill=tk.BOTH, expand=True)

        canvas_size = COLS * ZOOM   # 30 × 30 = 900 px

        self._canvas = tk.Canvas(frame, bg="#000", cursor="crosshair",
                                  width=canvas_size, height=canvas_size,
                                  highlightthickness=1,
                                  highlightbackground="#333")
        self._canvas.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        # mouse events
        self._canvas.bind("<ButtonPress-1>", self._on_press)        # <ButtonPress-1> : left mouse button pressed down
        self._canvas.bind("<B1-Motion>", self._on_drag)             # <B1-Motion> : left mouse button is held
        self._canvas.bind("<ButtonRelease-1>", self._on_release)    # <ButtonRelease-1> : left mouse button released

        # status label
        self._status_var = tk.StringVar(value="Ready")
        tk.Label(self, textvariable=self._status_var, bg="#0d0d0d", fg="#fff",
                 font=("Courier", 9), anchor=tk.W, padx=8, pady=3).pack(fill=tk.X, side=tk.BOTTOM)

    # rendering
    def _render(self):
        z = self.zoom
        w, h = COLS * z, ROWS * z

        # build RGB array: white cells → 255, black cells → subtle dark gray for grid
        # creating rgb array with (height, width, value per pixel) : 3 = (R, G, B)
        rgb = np.zeros((h, w, 3), dtype=np.uint8)

        # repeat pixel data to match zoom
        # zoom in the scale to be bigger with ZOOM parameter
        zoomed = np.repeat(np.repeat(self.pixels, z, axis=0), z, axis=1)
        rgb[:, :, 0] = zoomed * 255     # red channel to 255    |\
        rgb[:, :, 1] = zoomed * 255     # green channel to 255  | -(255, 255, 255) = white
        rgb[:, :, 2] = zoomed * 255     # blue channel to 255   |/

        # draw faint grid lines when zoomed in enough
        if z >= 3:
            grid_color = 50     # 50 : dark gray colour
            # draw vertical grid lines
            for c in range(0, w, 1 * z):
                rgb[:, c, :] = grid_color
            # draw horizontol grid lines
            for r in range(0, h, 1 * z):
                rgb[r, :, :] = grid_color

        img = Image.fromarray(rgb, "RGB")       # convert numpy array into a Pillow image object
        self._tk_img = ImageTk.PhotoImage(img)  # convert into tkinter format

        self._canvas.delete("all")      # clear unuse drawing
        self._canvas.create_image(0, 0, anchor=tk.NW, image=self._tk_img)   # aligning the image position same as the canvas
        self._update_stats()

    def _render_cell(self, row, col):
        """Fast single-cell repaint instead of full re-render."""
        z = self.zoom
        v = self.pixels[row, col]
        color = "#ffffff" if v else "#1e1e1e"
        x0, y0 = col * z, row * z
        # patch the existing image in-place via canvas rectangle
        tag = f"c_{row}_{col}"
        self._canvas.delete(tag)
        self._canvas.create_rectangle(x0, y0, x0 + z, y0 + z,
                                       fill=color, outline="", tags=tag)

    # interaction helpers
    def _cell_at(self, event):
        col = int(event.x // ZOOM)      # locate the cursor coordination on x-axis
        row = int(event.y // ZOOM)      # locate the cursor coordination on y-axis
        if 0 <= col < COLS and 0 <= row < ROWS:
            return row, col
        return None

    def _paint(self, row, col):
        if (row, col) == self.last_cell:    # prevent same cell painting
            return
        self.last_cell = (row, col)
        self.pixels[row, col] = 1 if self.mode.get() == "draw" else 0
        self._render_cell(row, col)

    def _on_press(self, event):
        self.painting = True        # mouse button pressed down : start drawing
        self.last_cell = (-1, -1)
        cell = self._cell_at(event)
        if cell:
            self._paint(*cell)

    def _on_drag(self, event):
        if self.painting:           # mouse button held down
            cell = self._cell_at(event)
            if cell:
                self._paint(*cell)

    def _on_release(self, event):
        self.painting = False       # mouse button released
        self._update_stats()

    # controls
    def _set_mode(self, m):
        self.mode.set(m)
        btn_style  = dict(bg="#2b2b2b", fg="#e0e0e0")
        act_style  = dict(bg="#e0e0e0", fg="#1a1a1a")
        self._draw_btn.config (**(act_style if m == "draw"  else btn_style))
        self._erase_btn.config(**(act_style if m == "erase" else btn_style))

    def _clear_all(self):
        self.pixels[:] = 0
        self._render()

    def _fill(self, color):
        self.pixels[:] = 1 if color == "white" else 0
        self._render()

    def _update_stats(self):
        cnt = int(self.pixels.sum())
        self._stats_var.set(f"{cnt:,} px white")

    # final image export
    def _create_image(self):
        self._status_var.set("Generating microCanvas")
        self.update_idletasks()

        # create a 1920x1080 black canvas
        img_array = np.zeros((IMG_H, IMG_W), dtype=np.uint8)

        # place the drawing at (OFFSET_X, OFFSET_Y) : projection area
        drawing = self.pixels * 255
        y0, y1 = OFFSET_Y, OFFSET_Y + ROWS
        x0, x1 = OFFSET_X, OFFSET_X + COLS
        img_array[y0:y1, x0:x1] = drawing

        img = Image.fromarray(img_array, mode="L")
        img.save(OUTPUT_FILE)

        self._status_var.set(f"✓ Saved: {OUTPUT_FILE}")

# main function
if __name__ == "__main__":
    app = PixelCanvas()
    canvas_px = COLS * ZOOM             # total px drawing area
    win_w = canvas_px + 180             # window width
    win_h = canvas_px + 180             # window height
    app.geometry(f"{win_w}x{win_h}")    # window size config
    app.resizable(False, False)         # fix window size
    app.mainloop()