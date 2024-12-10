# Factorio Image to Lamp Blueprint

This is a python script using streamlit (converted to stlite to be a static webpage for github pages) to take any image and convert(and optionally resize) it into a factorio lamp blueprint.
It reads the RGB (or RGBA for png) of each pixel and assigns those colors to a lamp and places it accordingly in a factorio blueprint.
It also places medium power poles or substations of any quality to power the lamps.

I am open to any suggestions for features and open to any changes to the code if someone would like to improve upon it.

Note: If you find a bug please report it, I recently tried to fix it crashing with an Index Out of Bounds error for really large images when placing substations. Should be fixed but let me know if it still causes issues.
