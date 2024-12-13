import streamlit as st
from PIL import Image
import json
import zlib as z
import base64 as b

st.set_page_config(page_title='Image to Blueprint', initial_sidebar_state='collapsed')
st.title('Image to Lamps Blueprint Maker')
#st.title('Testing')

st.link_button('Source Code', 'https://github.com/MagicManMe/ImageToBP')

#Remove useless side options and deploy button
st.markdown("""
    <style>
        .reportview-container {
            margin-top: -2em;
        }
        #MainMenu {visibility: hidden;}
        .stAppDeployButton {display:none;}
        footer {visibility: hidden;}
        #stDecoration {display:none;}
    </style>
""", unsafe_allow_html=True)


#Image upload, rest of program only runs if an image has been uploaded
image_file = st.file_uploader("Upload Image (Max Dimensions: 10000x10000)", type=['png', 'jpg', 'jpeg'], accept_multiple_files=False, key='test')
st.write("If using an image larger than 128x128 it is HIGHLY RECOMMENDED to resize it after uploading")

if image_file is not None:
    image_name = image_file.name.split('.')[0]
    image_file = Image.open(image_file)
    st.image(image_file, caption='Uploaded Image.')
    st.write(
        f"This is a {image_file.format} image and will skip lamps for transparent parts" if image_file.format == 'PNG'
        else f"This is a {image_file.format} image and will use the blank color to skip lamps"
    )

    #Check if img is PNG, if it is, use RGBA for transparency to skip lamp placement
    if image_file.format == 'PNG':
        image_file = image_file.convert('RGBA')
    else:
        image_file = image_file.convert('RGB')
        blank_color = st.color_picker('Pick a color for the script to skip lamp placement (white appears as grey in the color picker and is the default to ignore)', '#FFFFFF')
        blank_color = tuple(int(blank_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))
        st.write(f'Blank color is {blank_color}')

    #If image is uploaded, display its dimensions and allow change
    image_dimensions_section = st.columns((1, .2, 1, 1))
    with image_dimensions_section[0]:
        imgHeight = st.number_input('Height', min_value=1, max_value=10000, value=image_file.height)

        with image_dimensions_section[2]:
            imgWidth = st.number_input('Width', min_value=1, max_value=10000, value=image_file.width)

    if imgHeight != image_file.height or imgWidth != image_file.width:
        image_file = image_file.resize((imgWidth, imgHeight))
        st.image(image_file, caption='Resized Image.')

    if image_file.width > 128 or image_file.height > 128:
        st.warning("Images not resized to 128x128 or smaller may take VERY LONG to generate a BP and will most likely crash")

    #Selection columns for quality and powerpole_type
    radios = st.columns(2, gap='small')
    with radios[0]:
        # Select powerpole type
        powerpole_type = st.radio('Select Powerpole Type', ('Medium Power Pole', 'Substation'), index=0)
    with radios[1]:
        # Select quality
        quality = st.radio('Select Quality', ('Normal', 'Uncommon', 'Rare', 'Epic', 'Legendary'), index=0)




#Literally just bpcreate.py but in the main file because it doesn't work otherwise for some fucking reason
#This whole section was previously its own file to make it more readable but I kept running into issues sharing variables between the 2...so now it lives here

    # Various variables used
    poleObjList = []
    poleList = []
    entNum = 1
    imgHeight = image_file.height
    imgWidth = image_file.width

    # Base blueprint object we will append lamps and powerpoles to
    blueprint = {
        "blueprint": {
            "entities": [],
            "item": "blueprint",
            "version": 281479276259328,
            "label": f" Blueprint",  # Factorio blueprint version
            "wires": []
        }
    }


    class Lamp:
        def __init__(self, x, y, r, g, b, entity_number):
            self.x = x
            self.y = y
            self.r = r
            self.g = g
            self.b = b
            self.entity_number = entity_number
            self.label = "L"
            self.jsonData = {
                "entity_number": entity_number,
                "name": "small-lamp",
                "position": {"x": x, "y": y},
                "color": {"r": r / 255, "g": g / 255, "b": b / 255},
                "always_on": True
            }


    class Powerpole:
        def __init__(self, x, y, entity_number, quality):
            self.x = x
            self.y = y
            self.entity_number = entity_number
            self.quality = quality
            self.label = "P"
            self.jsonData = {
                "entity_number": entity_number,
                "name": "medium-electric-pole",
                "position": {"x": x, "y": y},
                "quality": quality.lower()
            }


    class Substation:
        def __init__(self, x, y, entity_number, quality):
            self.x = x
            self.y = y
            self.entity_number = entity_number
            self.quality = quality
            self.label = "S"
            self.jsonData = {
                "entity_number": entity_number,
                "name": "substation",
                "position": {"x": x, "y": y},
                "quality": quality.lower()
            }


    class GridObj:
        def __init__(self, cols, rows):
            self.grid = [[None for _ in range(rows)] for _ in range(cols)]

        def addLamp(self, x, y, r, g, b, entity_number):
            self.grid[x][y] = Lamp(x, y, r, g, b, entity_number)
            blueprint['blueprint']['entities'].append(self.grid[x][y].jsonData)

        def addPowerPole(self, x, y, entity_number, quality):
            self.grid[x][y] = Powerpole(x, y, entity_number, quality)
            blueprint['blueprint']['entities'].append(self.grid[x][y].jsonData)

        def addSubstation(self, x, y, entity_number, quality):
            global entNum
            self.grid[x][y] = Substation(x, y, entity_number, quality)
            blueprint['blueprint']['entities'].append(self.grid[x][y].jsonData)

            # Safely check and remove surrounding grid cells
            try:
                # Check grid boundaries before attempting to remove cells
                if x + 1 < len(self.grid):
                    if y < len(self.grid[x + 1]):
                        self.grid[x + 1][y] = None
                    if y + 1 < len(self.grid[x + 1]):
                        self.grid[x + 1][y + 1] = None

                if y + 1 < len(self.grid[x]):
                    self.grid[x][y + 1] = None
            except IndexError:
                st.write(f"Out of Range, skipping placement at X:{x} Y:{y} Entity Number:{entity_number}")


    def placelamps():
        global entNum
        pixels = image_file.load()
        if image_file.mode == 'RGBA':  # Check for transparency (RGBA)
            for y in range(imgHeight):
                for x in range(imgWidth):
                    r, g, b, a = pixels[x, y]  # Get RGBA values
                    if a == 0:  # Transparent pixel
                        continue  # Skip this pixel, treat it as background
                    imgGrid.addLamp(x, y, r, g, b, entNum)
                    entNum += 1
        else:
            for y in range(imgHeight):
                for x in range(imgWidth):
                    r, g, b = pixels[x, y]
                    if blank_color and (r == blank_color[0] and g == blank_color[1] and b == blank_color[2]):
                        continue  # Skip if the pixel matches the blank color
                    imgGrid.addLamp(x, y, r, g, b, entNum)
                    entNum += 1


    def placeMediumPoles(coverage):
        global entNum
        global poleList

        for l in range(0, len(imgGrid.grid), coverage):
            for w in range(0, len(imgGrid.grid[l]), coverage):
                imgGrid.addPowerPole(l, w, entNum, quality)
                #print(f"Added power pole at {l},{w},{entNum}")
                poleObjList.append(imgGrid.grid[l][w])
                poleList.append(entNum)
                entNum += 1


    def placesubstations(coverage):
        global entNum
        global poleList

        for l in range(0, len(imgGrid.grid), coverage):
            for w in range(0, len(imgGrid.grid[l]), coverage):
                imgGrid.addSubstation(l, w, entNum, quality)
                #print(f"Added substation at {l},{w},{entNum}")
                poleObjList.append(imgGrid.grid[l][w])
                poleList.append(entNum)
                entNum += 1


    def makewires4():
        global blueprint
        global poleObjList

        max_distance = coverage  # Define the maximum range based on pole type and quality.

        # Iterate over all poles to find connections
        for i, pole in enumerate(poleObjList):
            if pole is None:
                continue
            for j, other_pole in enumerate(poleObjList):
                if i == j or other_pole is None:
                    continue

                # Calculate Manhattan distance between poles
                distance = abs(pole.x - other_pole.x) + abs(pole.y - other_pole.y)

                # Ensure the poles are aligned (horizontal or vertical) and within range
                if distance <= max_distance and (pole.x == other_pole.x or pole.y == other_pole.y):
                    blueprint['blueprint']['wires'].append([
                        pole.entity_number, 5, other_pole.entity_number, 5
                    ])


    # Places powerpoles and assigns coverage value based on selections made
    def placePowerPoles():
        global coverage
        if powerpole_type == 'Medium Power Pole':
            if quality == "Normal":
                coverage = 7
            elif quality == "Uncommon":
                coverage = 9
            elif quality == "Rare":
                coverage = 11
            elif quality == "Epic":
                coverage = 13
            elif quality == "Legendary":
                coverage = 17
            placeMediumPoles(coverage)

        elif powerpole_type == 'Substation':
            if quality == "Normal":
                coverage = 18
            elif quality == "Uncommon":
                coverage = 20
            elif quality == "Rare":
                coverage = 22
            elif quality == "Epic":
                coverage = 24
            elif quality == "Legendary":
                coverage = 28
            placesubstations(coverage)


    def getBlueprintJSON():
        return json.dumps(blueprint, indent=2)


    def getBlueprintObj():
        return blueprint


    imgGrid = None


    def createBP():
        global imgGrid
        imgGrid = GridObj(rows=image_file.height, cols=image_file.width)

        placelamps()
        placePowerPoles()
        makewires4()
        return blueprint


    #Compression functions
    def BPDict_to_string(data):
        return "0" + b.b64encode(
            z.compress(json.dumps(data, separators=(",", ":"), indent=2).encode("utf-8"), 9)
        ).decode("utf-8")


    def JSON_to_string(data):
        return "0" + b.b64encode(
            z.compress(data.encode("utf-8"), 9)
        ).decode("utf-8")
#END OF original BPCREATE


    #Run the bp creation program once user submits all options
    if st.button('Create Blueprint',type='primary'):
        st.write("Creating Blueprint String...")
        st.write(f'Final Dimensions {image_file.width}x{image_file.height}')
        createBP()
        st.write("Done! See Blueprint String Below:")
        st.code(BPDict_to_string(blueprint), language=None)
        st.download_button(
            label="Download Blueprint",
            data=BPDict_to_string(blueprint),
            file_name=f'{image_name} Blueprint.txt',
            mime='text/plain',
        )

