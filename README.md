# TopoBathy Profiles

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![GitHub Release](https://img.shields.io/github/v/release/evecchi/topobathy_profiles)](https://github.com/evecchi/topobathy_profiles/releases)
[![Download Plugin](https://img.shields.io/badge/Install%20on-QGIS-brightgreen)](https://github.com/evecchi/topobathy_profiles/releases/download/v0.1.0/topobathy_profiles.zip)
[![Issues](https://img.shields.io/github/issues/evecchi/topobathy_profiles)](https://github.com/evecchi/topobathy_profiles/issues)

**TopoBathy Profiles** is a QGIS plugin for creating topo-bathymetric profiles from point layers along selected cross-section lines. The plugin allows you to preview, customize, and export profiles as graphs and CSV files.


## Features
- Add multiple point layers and assign labels and colors.
- Select a line layer to define cross sections nd choose a section identifier field.
- Use elevation fields or Z geometry for each point layer.
- Configurable buffer distance to filter points along the section line.
- Minimum distance filtering to reduce point density in plots.
- Option to split profile lines when large gaps occur between points.
- Interactive profile preview inside the plugin.
- Buffer distance displayed in the plot header.
- Highlight the selected cross-section feature in the map canvas.
- Export profiles as high-resolution images (PNG) and CSV files, with option to export only points visible in the graph.

---

## Installation
1. Download or clone this repository.
2. Copy the `topobathy_profiles` folder into your QGIS plugin directory:
   - **Windows:**  
     `C:\Users\<YourUsername>\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\`
   - **Linux:**  
     `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`
   - **macOS:**  
     `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/`
3. Open QGIS.
4. Go to **Plugins → Manage and Install Plugins**.
5. Enable **TopoBathy Profiles**.

---

## Usage
1. Add your point layers using the **Add** button.
2. Assign labels and colors in the table.
3. Select a cross-section line layer and choose a feature via the **section identifier field** dropdown.
4. Set options such as **Split line**, **Filter nearby points**, or adjust **buffer distance**.
5. Click **Run** to generate profiles.
6. Preview the profiles in the preview window, with buffer distance visible in the header.
7. Highlighted cross-section features appear on the map.
8. Export the profiles using **Save image** or **Save CSV**.

### Plugin interface
<img src="screenshots/interface.png" width="400">

---

## Requirements
- QGIS 3.22 or higher
- Python 3
- PyQt5 (included with QGIS)
- NumPy
- Matplotlib

---

## License
This plugin is licensed under the MIT License. See the `LICENSE` file for details.

---

## Author
Enrica Vecchi  
Email: enrica.vecchi@unica.it  
GitHub: [https://github.com/evecchi/topobathy_profiles](https://github.com/evecchi/topobathy_profiles)
