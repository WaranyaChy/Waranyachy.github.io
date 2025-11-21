import math
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from matplotlib.widgets import PolygonSelector, Button
from matplotlib.path import Path
from matplotlib.lines import Line2D

# ======================================
# 1) ตั้งค่าพื้นฐาน
# ======================================

DATA_FILE = "synthetic_well_dataset.xlsx"   # ชื่อไฟล์ Excel ในโฟลเดอร์เดียวกับโค้ด

# ชื่อคอลัมน์ log ใน Excel (ต้องตรงชื่อเป๊ะ)
LOG_COLUMNS = [
    "GR",
    "RHOB",
    "NPHI",
    "DT",
    "RES",
    "Chekshot",
]


# ======================================
# 2) โหลดข้อมูลหลุมจาก Excel
# ======================================
def load_well_data():
    df = pd.read_excel(DATA_FILE, engine="openpyxl")
    print("โหลดข้อมูลสำเร็จ:", df.shape[0], "หลุม")
    return df


# ======================================
# 3) แอปสำหรับวาด polygon และวิเคราะห์
# ======================================
class WellPolygonApp:
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()

        # สถานะ
        self.df["in_polygon"] = False
        self.df["logs_complete"] = False

        # ผลล่าสุด (ใช้ตอน export)
        self.last_subset = None
        self.last_area_km2 = 0.0
        self.last_verts = None

        # figure / axes หลัก
        self.fig, self.ax = plt.subplots(figsize=(6, 6))
        self.fig.subplots_adjust(right=0.78, bottom=0.22)  # เผื่อที่ legend + ปุ่ม

        # กล่องข้อความสรุปด้านล่างรูป (อยู่ระดับ figure)
        self.info_text = self.fig.text(
            0.01, 0.02, "",
            fontsize=8,
            va="bottom",
            ha="left",
            family="monospace",
        )

        # ตัวแปรสำหรับเก็บ scatter, labels, selector
        self.scatter = None
        self.labels = []
        self.selector = None

        # วาดเนื้อหาใน axes ครั้งแรก
        self._init_axes_contents()

        # ---------- ปุ่ม Clear / Export ----------
        clear_ax = self.fig.add_axes([0.60, 0.03, 0.12, 0.06])
        export_ax = self.fig.add_axes([0.75, 0.03, 0.12, 0.06])

        self.btn_clear = Button(clear_ax, "Clear")
        self.btn_export = Button(export_ax, "Export")

        self.btn_clear.on_clicked(self.on_clear_clicked)
        self.btn_export.on_clicked(self.on_export_clicked)

    # ---------- วาด scatter + legend + selector ----------
    def _init_axes_contents(self):
        """รีเซ็ตเนื้อหาภายในกราฟให้เหมือนตอนเริ่มโปรแกรม"""

        # ล้างทุกอย่างใน axes
        self.ax.clear()

        # ตั้งค่าหน้าตา
        self.ax.set_facecolor("#f7f7f7")
        self.ax.grid(False)
        self.ax.set_xlabel("Longitude")
        self.ax.set_ylabel("Latitude")
        self.ax.set_title("Interactive Well Log Availability Analyzer")

        # วาดจุดหลุม (เริ่มต้นสีเทา)
        self.scatter = self.ax.scatter(
            self.df["lon"],
            self.df["lat"],
            s=16,
            alpha=0.9,
            edgecolor="black",
            linewidth=0.4,
            c="lightgray",
        )

        # legend อยู่นอกกราฟด้านขวา
        legend_elements = [
            Line2D([0], [0], marker='o', color='w',
                   label='Outside polygon',
                   markerfacecolor='lightgray', markeredgecolor='black',
                   markersize=6),
            Line2D([0], [0], marker='o', color='w',
                   label='Inside polygon, logs complete',
                   markerfacecolor='green', markeredgecolor='black',
                   markersize=6),
            Line2D([0], [0], marker='o', color='w',
                   label='Inside polygon, logs incomplete',
                   markerfacecolor='orange', markeredgecolor='black',
                   markersize=6),
        ]
        self.ax.legend(
            handles=legend_elements,
            loc="center left",
            bbox_to_anchor=(1.02, 0.5),
            borderaxespad=0.0,
        )

        # ลบ label ชื่อหลุม (ถ้ามีเก่า)
        self.labels = []

        # รีเซ็ต / สร้าง PolygonSelector ใหม่
        if self.selector is not None:
            try:
                self.selector.disconnect_events()
            except Exception:
                pass
        self.selector = PolygonSelector(
            self.ax,
            self.onselect,
            useblit=True,
        )

        # วาดใหม่
        self.fig.canvas.draw_idle()

    # ---------- คำนวณพื้นที่ polygon (km² แบบ approx) ----------
    def compute_area_km2(self, verts):
        if len(verts) < 3:
            return 0.0

        lats = [v[1] for v in verts]
        lat0 = sum(lats) / len(lats)
        lat0_rad = math.radians(lat0)

        km_per_deg_lat = 111.32
        km_per_deg_lon = 111.32 * math.cos(lat0_rad)

        xs = [v[0] * km_per_deg_lon for v in verts]
        ys = [v[1] * km_per_deg_lat for v in verts]

        area = 0.0
        n = len(xs)
        for i in range(n):
            j = (i + 1) % n
            area += xs[i] * ys[j] - xs[j] * ys[i]
        area = abs(area) * 0.5  # km²
        return area

    # ---------- callback เมื่อวาด polygon เสร็จ ----------
    def onselect(self, verts):
        print("\n==============================")
        print("Polygon updated")
        print("จำนวนจุด:", len(verts))

        self.last_verts = verts

        # point-in-polygon
        poly_path = Path(verts)
        points = self.df[["lon", "lat"]].to_numpy()
        inside = poly_path.contains_points(points)
        self.df["in_polygon"] = inside

        # log ครบ = ทุกคอลัมน์ใน LOG_COLUMNS เป็น "Yes"
        self.df["logs_complete"] = self.df[LOG_COLUMNS].eq("Yes").all(axis=1)

        subset = self.df[self.df["in_polygon"]]
        print("หลุมใน polygon:", len(subset))

        # พื้นที่ polygon
        area_km2 = self.compute_area_km2(verts)
        print(f"พื้นที่ polygon (ประมาณ): {area_km2:.2f} km²")

        # เก็บไว้ใช้ตอน export
        self.last_subset = subset.copy()
        self.last_area_km2 = area_km2

        # ---------- print รายละเอียดใน terminal ----------
        if len(subset) == 0:
            print("ไม่มีหลุมในพื้นที่นี้")
        else:
            print("\nจำนวนประเภทหลุม:")
            print(subset["type"].value_counts())

            print("\nLog completeness:")
            print("ครบ:", subset["logs_complete"].sum())
            print("ไม่ครบ:", len(subset) - subset["logs_complete"].sum())

            print("\nรายละเอียดหลุม:")
            cols = ["well_name", "type"] + LOG_COLUMNS + ["logs_complete"]
            print(subset[cols].to_string(index=False))

        # ---------- ลบ label เก่า ----------
        for txt in self.labels:
            txt.remove()
        self.labels = []

        # ---------- เขียนชื่อหลุมบนจุด (เฉพาะใน polygon) ----------
        for _, row in subset.iterrows():
            txt = self.ax.text(
                row["lon"],
                row["lat"],
                row["well_name"],
                fontsize=7,
                ha="left",
                va="bottom",
            )
            self.labels.append(txt)

        # ---------- ข้อความสรุปด้านล่าง ----------
        lines = []
        lines.append(f"Wells in polygon: {len(subset)}")
        lines.append(f"Approx. area: {area_km2:.2f} km²")
        if len(subset) > 0:
            lines.append("")
            for _, row in subset.iterrows():
                log_status = [col for col in LOG_COLUMNS if row[col] == "Yes"]
                log_str = ", ".join(log_status) if log_status else "No logs"
                lines.append(f"{row['well_name']} ({row['type']}): {log_str}")

        self.info_text.set_text("\n".join(lines))

        # ---------- อัปเดตสีจุด ----------
        colors = []
        for _, row in self.df.iterrows():
            if row["in_polygon"]:
                if row["logs_complete"]:
                    colors.append("green")
                else:
                    colors.append("orange")
            else:
                colors.append("lightgray")

        self.scatter.set_color(colors)
        self.fig.canvas.draw_idle()

    # ---------- ปุ่ม Clear ----------
    def on_clear_clicked(self, event):
        print("\n[Clear] ล้าง polygon และรีเซ็ตผลทั้งหมด")

        # reset status
        self.df["in_polygon"] = False
        self.df["logs_complete"] = False
        self.last_subset = None
        self.last_area_km2 = 0.0
        self.last_verts = None

        # ล้างข้อความ summary
        self.info_text.set_text("")

        # วาด axes ใหม่ให้เหมือนตอนเริ่มโปรแกรม
        self._init_axes_contents()

    # ---------- ปุ่ม Export ----------
    def on_export_clicked(self, event):
        self.export_report()

    def export_report(self):
        print("\n[Export] Export clicked...")
        if self.last_subset is None or self.last_subset.empty:
            print("[Export] ยังไม่มี polygon หรือไม่มีหลุมใน polygon เลย → ยัง export ไม่ได้")
            return

        wells_filename = "wells_in_polygon_report.xlsx"
        fig_filename = "wells_in_polygon_figure.png"

        print(f"[Export] กำลังบันทึกไฟล์: {wells_filename} และ {fig_filename}")

        subset = self.last_subset
        n_wells = len(subset)
        n_complete = subset["logs_complete"].sum()
        n_incomplete = n_wells - n_complete
        type_counts = subset["type"].value_counts()

        summary_rows = [
            {"item": "n_wells", "value": n_wells},
            {"item": "area_km2", "value": round(self.last_area_km2, 3)},
            {"item": "logs_complete", "value": int(n_complete)},
            {"item": "logs_incomplete", "value": int(n_incomplete)},
        ]
        for t, c in type_counts.items():
            summary_rows.append({"item": f"type_{t}", "value": int(c)})

        summary_df = pd.DataFrame(summary_rows)

        # --- เซฟข้อมูลเป็น Excel ---
        with pd.ExcelWriter(wells_filename, engine="openpyxl") as writer:
            subset.to_excel(writer, index=False, sheet_name="wells")
            summary_df.to_excel(writer, index=False, sheet_name="summary")

        # --- เซฟรูปกราฟปัจจุบันเป็น PNG ---
        self.fig.savefig(fig_filename, dpi=300, bbox_inches="tight")
        print(f"[Export] บันทึกรายงานเสร็จแล้วเป็นไฟล์ '{wells_filename}' และ '{fig_filename}'")

    # ---------- run แอป ----------
    def run(self):
        print("\n✔ วิธีใช้:")
        print("- คลิกทีละจุดเพื่อวาด polygon")
        print("- ดับเบิลคลิก เพื่อปิด polygon และให้โปรแกรมคำนวณ")
        print("- คลิกปุ่ม 'Export' → ได้ Excel (wells + summary) และ PNG รูปกราฟ")
        print("- คลิกปุ่ม 'Clear' → ล้างทุกอย่างให้เหมือนตอนเปิดโปรแกรมใหม่")
        plt.show()


# ======================================
# 4) main program
# ======================================
def main():
    df = load_well_data()
    app = WellPolygonApp(df)
    app.run()


if __name__ == "__main__":
    main()




