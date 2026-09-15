# Shaft Generator — FreeCAD Workbench

The **Shaft Generator** is a FreeCAD workbench designed for the rapid creation of stepped shafts and axles, as well as the simplified generation of their 2D technical drawings. Developed independently for **personal use and learning**.

Each diameter segment functions as an individual object in the model tree, allowing you to easily reorder the shaft steps via drag-and-drop or using the built-in arrow commands.

---

## 🛠️ Features

*   **Segment Profiles:** Support for Circular, Square, and Hexagonal cross-sections.
*   **Keyways:** Radial slots customizable by width, depth, length, position, and angle (0° to 360°). Works across all profiles.
*   **Grooves:** Circumferential channels aimed at retaining rings or relief cuts (Circular profile only).
*   **Cosmetic External Threads:** Lightweight cosmetic helix lines on the 3D surface (Total or Partial extent) that won't slow down FreeCAD's performance. Includes an option to hide the visual indicator.
*   **Thread Exit Groove (DIN 76):** A real machining relief cut generated cleanly at the thread run-out transition.
*   **Automated 2D Drawing (TechDraw):** Automatic generation of a front view on an A4 sheet with standardized **ISO 6410** thread symbols (minor diameter and thread limit lines) and a callout designation legend (e.g., `M8x1.25`).

---

## 💻 Installation

1. Place the entire `AxisGenerator` folder into your FreeCAD user modules directory (`Mod`):
   * **Windows:** `%APPDATA%\FreeCAD\Mod\`
   * **Linux:** `~/.local/share/FreeCAD/Mod/`
   * **macOS:** `~/Library/Preferences/FreeCAD/Mod/`
2. Ensure the final path structure is `.../Mod/AxisGenerator/InitGui.py`.
3. Restart FreeCAD and select **Shaft Generator** from the Workbenches menu.

---

## 🤖 AI-Assisted Development

## 🤖 AI-Assisted Development (An Engineer's Approach)

I am an engineering student, not a software developer, and honestly, I didn't even know where to begin with coding a FreeCAD extension. I originally needed a quick tool like this for my internship, so I built this workbench as a personal learning project by leveraging AI tools to bridge the coding gap. 

The AI acted as my programming translator—handling the boilerplate Python scripts, refactoring code, and troubleshooting tricky FreeCAD GUI and TechDraw API bugs. However, specifications like the independency of segments, features, and technical drawings were and are being directed by me.

Any suggestions, tips, and critics are welcome.


---

## ⚠️ Important Limitation

*   **Simplified Thread Geometry:** Threads in the 3D model are conceptual representations (cosmetic lines) to keep the file lightweight. They do not cut physical V-groove filetes into the solid.
