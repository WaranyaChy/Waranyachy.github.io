---
title: 'Interactive Well Selection Tool'
date: 2025-11-21
Categories: [Education, Python]
tags:
  - Python
---

I developed an interactive Python tool designed to identify which wells fall inside a user-defined polygon on a map. Users can draw the polygon directly on an interactive map, and the system automatically determines which wells and their associated attributes lie within the selected boundary. The tool also supports exporting the selected wells as a CSV file and saving the resulting map image for documentation or further analysis.
###
The tool operates using mock well data that includes well names, latitude–longitude coordinates, and log availability information. It leverages key libraries such as pandas and matplotlib for data processing and interactive mapping. A Clear function is also provided to reset the polygon and refresh the map, allowing the user to define new boundaries easily.
###
<img src='/images/wells_in_polygon_figure.png'>

### Dowload
- [Python script](/files/Code_well_analyzer.py)
- [Input data](/files/synthetic_well_dataset.xlsx)
