"""Local cable-point annotation tool."""
from __future__ import annotations

import csv
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageDraw, ImageTk


CSV_NAME = "annotations.csv"
MAX_POINTS = 4
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}
FIELDS = ["nama", "x1", "y1", "x2", "y2", "x3", "y3", "x4", "y4"]


class Annotator:
    def __init__(self, root: tk.Tk):
        self.root = root
        root.title("Cable Point Annotator")
        root.geometry("1100x760")
        root.bind_all("<Control-s>", self.handle_save_shortcut)
        self.folder: Path | None = None
        self.files: list[Path] = []
        self.points: dict[str, list[tuple[int, int]]] = {}
        self.csv_rows: dict[str, dict[str, str]] = {}
        self.current: Path | None = None
        self.image: Image.Image | None = None
        self.csv_window = None
        self.csv_tree = None
        self.notification_timer = None
        self.tk_image = None
        self.scale = 1.0
        self.offset = (0, 0)

        bar = ttk.Frame(root, padding=8)
        bar.pack(fill="x")
        ttk.Button(bar, text="Buka folder gambar", command=self.open_folder).pack(side="left")
        ttk.Button(bar, text="Ekspor gambar ini", command=self.export_current).pack(side="left", padx=8)
        ttk.Button(bar, text="Buka CSV", command=self.open_csv_view).pack(side="left")
        ttk.Button(bar, text="Refresh gambar", command=self.refresh_images).pack(side="left", padx=(6, 0))
        self.status = ttk.Label(bar, text="Pilih folder yang berisi gambar")
        self.status.pack(side="left", padx=10)
        self.coordinates = ttk.Label(bar, text="X: —   Y: —", width=18, anchor="e")
        self.coordinates.pack(side="right", padx=8)
        body = ttk.Frame(root)
        body.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.listbox = tk.Listbox(body, width=30, exportselection=False)
        self.listbox.pack(side="left", fill="y")
        self.listbox.bind("<<ListboxSelect>>", self.select_image)
        self.canvas = tk.Canvas(body, bg="#20242b", cursor="crosshair", highlightthickness=0)
        self.canvas.pack(side="left", fill="both", expand=True, padx=(8, 0))
        self.canvas.bind("<Button-1>", self.add_point)
        self.canvas.bind("<Motion>", self.update_coordinates)
        self.canvas.bind("<Leave>", lambda _e: self.coordinates.config(text="X: —   Y: —"))
        self.canvas.bind("<Configure>", lambda _e: self.render())
        ttk.Label(root, text="Klik untuk menambah titik; klik titik yang sama untuk menghapus. Maksimal 4 titik. Koordinat piksel gambar asli.", padding=8).pack(fill="x")

    def open_folder(self):
        selected = filedialog.askdirectory(title="Pilih folder gambar")
        if not selected:
            return
        self.folder = Path(selected)
        self.csv_rows = self.read_csv_rows(self.folder / CSV_NAME)
        self.refresh_images()

    def refresh_images(self):
        if self.folder is None:
            messagebox.showinfo("Pilih folder", "Buka folder gambar terlebih dahulu.")
            return
        selected_name = self.current.name if self.current else None
        self.files = sorted((p for p in self.folder.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS), key=lambda p: p.name.lower())
        self.listbox.delete(0, "end")
        for path in self.files:
            self.listbox.insert("end", path.name)
        self.status.config(text=f"{len(self.files)} gambar — {self.folder}")
        if self.files:
            index = next((i for i, p in enumerate(self.files) if p.name == selected_name), 0)
            self.listbox.selection_set(index)
            self.load_image(self.files[index])
        else:
            self.current = None
            self.image = None
            self.canvas.delete("all")
        self.refresh_csv_view()

    def read_csv_rows(self, csv_path: Path) -> dict[str, dict[str, str]]:
        rows: dict[str, dict[str, str]] = {}
        if csv_path.exists():
            with csv_path.open("r", newline="", encoding="utf-8-sig") as f:
                for row in csv.DictReader(f):
                    if row.get("nama"):
                        rows[row["nama"]] = row
        return rows

    def open_csv_view(self):
        if self.folder is None:
            messagebox.showinfo("Pilih folder", "Buka folder gambar terlebih dahulu.")
            return
        if self.csv_window is None or not self.csv_window.winfo_exists():
            self.csv_window = tk.Toplevel(self.root)
            self.csv_window.title(CSV_NAME)
            self.csv_window.geometry("900x420")
            frame = ttk.Frame(self.csv_window, padding=8)
            frame.pack(fill="both", expand=True)
            self.csv_tree = ttk.Treeview(frame, columns=FIELDS, show="headings")
            ys = ttk.Scrollbar(frame, orient="vertical", command=self.csv_tree.yview)
            xs = ttk.Scrollbar(frame, orient="horizontal", command=self.csv_tree.xview)
            self.csv_tree.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
            self.csv_tree.grid(row=0, column=0, sticky="nsew")
            ys.grid(row=0, column=1, sticky="ns")
            xs.grid(row=1, column=0, sticky="ew")
            frame.rowconfigure(0, weight=1)
            frame.columnconfigure(0, weight=1)
        self.refresh_csv_view()

    def refresh_csv_view(self):
        if self.csv_tree is None or not self.csv_tree.winfo_exists() or self.folder is None:
            return
        self.csv_rows = self.read_csv_rows(self.folder / CSV_NAME)
        self.csv_tree.delete(*self.csv_tree.get_children())
        for col in FIELDS:
            self.csv_tree.heading(col, text=col)
            self.csv_tree.column(col, width=110, minwidth=70)
        for row in self.csv_rows.values():
            self.csv_tree.insert("", "end", values=[row.get(col, "") for col in FIELDS])

    def select_image(self, _event=None):
        selection = self.listbox.curselection()
        if selection:
            self.load_image(self.files[selection[0]])

    def load_image(self, path: Path):
        try:
            self.current = path
            with Image.open(path) as im:
                self.image = im.convert("RGB")
            self.points[path.name] = self.read_saved_points(path.name)
            self.render()
            self.status.config(text=f"{path.name} — {self.image.width} × {self.image.height} px — {len(self.points[path.name])}/4 titik")
        except Exception as exc:
            messagebox.showerror("Gagal membuka gambar", str(exc))

    def read_saved_points(self, image_name: str) -> list[tuple[int, int]]:
        """Load an existing annotation row by its original image filename."""
        row = self.csv_rows.get(image_name, {})
        pts = []
        for i in range(1, MAX_POINTS + 1):
            x, y = row.get(f"x{i}", ""), row.get(f"y{i}", "")
            if x != "" and y != "":
                pts.append((int(float(x)), int(float(y))))
        return pts

    def render(self):
        if self.image is None:
            return
        cw, ch = max(self.canvas.winfo_width(), 1), max(self.canvas.winfo_height(), 1)
        scale = min(cw / self.image.width, ch / self.image.height)
        self.scale = scale
        w, h = max(1, round(self.image.width * scale)), max(1, round(self.image.height * scale))
        self.offset = ((cw - w) / 2, (ch - h) / 2)
        view = self.image.resize((w, h), Image.Resampling.LANCZOS)
        draw = ImageDraw.Draw(view)
        for i, (x, y) in enumerate(self.points.get(self.current.name if self.current else "", []), 1):
            px, py = round(x * scale), round(y * scale)
            r = 7
            draw.ellipse((px-r, py-r, px+r, py+r), fill="#ff3b30", outline="white", width=2)
            draw.text((px+9, py-10), str(i), fill="yellow", stroke_width=2, stroke_fill="black")
        self.tk_image = ImageTk.PhotoImage(view)
        self.canvas.delete("all")
        self.canvas.create_image(*self.offset, image=self.tk_image, anchor="nw")

    def add_point(self, event):
        if self.image is None or self.current is None:
            return
        x = round((event.x - self.offset[0]) / self.scale)
        y = round((event.y - self.offset[1]) / self.scale)
        if not (0 <= x < self.image.width and 0 <= y < self.image.height):
            return
        pts = self.points.setdefault(self.current.name, [])
        tolerance = max(5, round(10 / self.scale))
        match = next((i for i, (px, py) in enumerate(pts) if (px-x)**2 + (py-y)**2 <= tolerance**2), None)
        if match is not None:
            pts.pop(match)
        elif len(pts) < MAX_POINTS:
            pts.append((x, y))
        else:
            self.status.config(text="Maksimal 4 titik; klik titik yang ada untuk menghapus")
        self.render()
        self.status.config(text=f"{self.current.name} — {self.image.width} × {self.image.height} px — {len(pts)}/4 titik")

    def update_coordinates(self, event):
        self.canvas.delete("point-tooltip")
        if self.image is None:
            self.coordinates.config(text="X: —   Y: —")
            return
        x = round((event.x - self.offset[0]) / self.scale)
        y = round((event.y - self.offset[1]) / self.scale)
        if 0 <= x < self.image.width and 0 <= y < self.image.height:
            self.coordinates.config(text=f"X: {x} px   Y: {y} px")
        else:
            self.coordinates.config(text="X: —   Y: —")
            return

        # Show the saved point coordinates when the pointer is close to a marker.
        points = self.points.get(self.current.name if self.current else "", [])
        hovered = next(
            ((px, py) for px, py in points
             if (event.x - (self.offset[0] + px * self.scale)) ** 2
             + (event.y - (self.offset[1] + py * self.scale)) ** 2 <= 14 ** 2),
            None,
        )
        if hovered:
            px, py = hovered
            label = f"X: {px} px, Y: {py} px"
            tx, ty = event.x + 14, event.y + 14
            text_id = self.canvas.create_text(
                tx + 6, ty + 5, text=label, anchor="nw", fill="white",
                font=("Segoe UI", 9), tags="point-tooltip",
            )
            box = self.canvas.bbox(text_id)
            if box:
                x1, y1, x2, y2 = box
                rect_id = self.canvas.create_rectangle(
                    x1 - 6, y1 - 4, x2 + 6, y2 + 4,
                    fill="#20242b", outline="#ffffff", tags="point-tooltip",
                )
                self.canvas.tag_lower(rect_id, text_id)

    def export_current(self):
        if self.folder is None or self.current is None or self.image is None:
            messagebox.showinfo("Belum ada gambar", "Pilih folder dan gambar terlebih dahulu.")
            return
        source = self.current
        marked_dir = self.folder / "marked_img"
        marked_dir.mkdir(exist_ok=True)
        marked_path = marked_dir / source.name
        try:
            annotated = self.image.copy()
            d = ImageDraw.Draw(annotated)
            pts = self.points.get(source.name, [])
            for i, (x, y) in enumerate(pts, 1):
                r = max(5, min(12, round(min(annotated.size) / 100)))
                d.ellipse((x-r, y-r, x+r, y+r), fill="#ff3b30", outline="white", width=2)
                d.text((x+r+2, y-r), str(i), fill="yellow", stroke_width=2, stroke_fill="black")
            if source.suffix.lower() in {".jpg", ".jpeg"}:
                annotated.save(marked_path, format="JPEG", quality=95)
            else:
                annotated.save(marked_path)
            csv_path = self.folder / CSV_NAME
            rows = dict(self.csv_rows)
            row = {field: "" for field in FIELDS}
            row["nama"] = source.name
            for i, (x, y) in enumerate(pts, 1):
                row[f"x{i}"], row[f"y{i}"] = str(x), str(y)
            rows[source.name] = row
            with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
                writer = csv.DictWriter(f, fieldnames=FIELDS)
                writer.writeheader()
                writer.writerows(rows.values())
            self.csv_rows = rows
            self.refresh_csv_view()
            self.show_notification(f"Tersimpan: {source.name}")
        except Exception as exc:
            if isinstance(exc, PermissionError):
                diagnosis = "Akses ditolak. Pastikan annotations.csv tidak sedang dibuka di Excel, folder tidak read-only, dan Anda punya izin menulis."
            elif isinstance(exc, OSError):
                diagnosis = "Masalah membaca/menulis file. Periksa ruang disk, izin folder, atau apakah file sedang dipakai aplikasi lain."
            else:
                diagnosis = "Periksa detail error di bawah; jika berulang, catat pesan ini untuk ditelusuri."
            messagebox.showerror("Ekspor gagal", f"{diagnosis}\n\nDetail: {type(exc).__name__}: {exc}")

    def handle_save_shortcut(self, _event=None):
        self.export_current()
        return "break"

    def show_notification(self, text: str):
        if self.notification_timer is not None:
            self.root.after_cancel(self.notification_timer)
        self.status.config(text=text)

        def restore_status():
            self.notification_timer = None
            if self.current and self.image:
                count = len(self.points.get(self.current.name, []))
                self.status.config(text=f"{self.current.name} — {self.image.width} × {self.image.height} px — {count}/4 titik")

        self.notification_timer = self.root.after(3000, restore_status)


if __name__ == "__main__":
    root = tk.Tk()
    Annotator(root)
    root.mainloop()
