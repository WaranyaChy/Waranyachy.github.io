import os
import pandas as pd
import matplotlib.pyplot as plt


base_dir = os.path.dirname(__file__)
excel_path = os.path.join(base_dir, "Checkshot_data.xlsx")

df = pd.read_excel(excel_path)


df = df[["Well", "MD", "TWT"]].dropna()


fig, ax = plt.subplots(figsize=(8, 6))

for well, sub_df in df.groupby("Well"):
    sub_df = sub_df.sort_values("MD")
    ax.plot(
        sub_df["TWT"],
        sub_df["MD"],
        marker="o",
        linestyle="-",
        linewidth=1.2,
        label=well
    )


ax.set_xlabel("Two-way time (ms)")
ax.set_ylabel("Measured depth (m)")
ax.set_title("Checkshot Time–Depth Curves")


ax.invert_yaxis()


ax.grid(True, linestyle="--", alpha=0.4)


ax.legend(title="Well", fontsize=8)


plt.tight_layout()


output_path = os.path.join(base_dir, "checkshot_time_depth.png")
plt.savefig(output_path, dpi=300)


plt.show()

print("Plot saved to:", output_path)

