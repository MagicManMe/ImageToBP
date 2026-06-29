# Image to Lamp Blueprint

Turn any image into a [Factorio](https://factorio.com) blueprint made of coloured lamps, automatically powered with electric poles or substations. Each pixel becomes one always-on `small-lamp` tinted to that pixel's colour; the tool then lays down power infrastructure and wires it together.

**[Try it live »](http://imgtobp.magicman.dev)**

It runs entirely in your browser as a single static page — no server, no upload, nothing leaves your machine. Hosted on GitHub Pages straight from `index.html`.

---

## How it works

The whole pipeline is a client-side transform from pixels to a blueprint string:

1. **Decode** — the image is drawn to a `<canvas>` and read back with `getImageData()`, giving a flat `RGBA` byte array. Resizing is done by the canvas (`imageSmoothingEnabled` toggles high-quality downscale vs. crisp nearest-neighbour).
2. **Mask** — each pixel is classified as *lamp* or *background*. PNGs use the alpha channel (transparent → background); JPEGs can optionally skip a chosen colour within an adjustable tolerance.
3. **Place lamps** — one `small-lamp` entity per lamp pixel, coloured `(r, g, b) / 255`, `always_on: true`.
4. **Place poles** — power poles are dropped on a centered, demand-gated lattice (see below).
5. **Connect** — poles are wired to their lattice neighbours, and optional *bridge poles* stitch separated regions into a single electric network.
6. **Encode** — the entity tree is serialised to JSON, zlib-deflated via the browser's native `CompressionStream`, base64-encoded, and prefixed with the Factorio version byte.

---

## Blueprint string format

Factorio blueprint strings are produced by:

```
"0" + base64( zlib_deflate( json_utf8 ) )
```

- The leading `"0"` is the format version byte Factorio expects.
- `zlib_deflate` is RFC&nbsp;1950 (zlib-wrapped DEFLATE, **not** raw DEFLATE). The browser's `new CompressionStream("deflate")` produces exactly this format.
- The JSON is minified (no whitespace) before compression.

To read a string back, strip the leading `"0"`, base64-decode, and zlib-inflate.

### Entity JSON shape

The decompressed JSON is a standard blueprint object:

```jsonc
{
  "blueprint": {
    "item": "blueprint",
    "version": 281479276259328,
    "label": "my-image",
    "entities": [
      {
        "entity_number": 1,
        "name": "small-lamp",
        "position": { "x": 0, "y": 0 },
        "color": { "r": 0.91, "g": 0.45, "b": 0.13 },
        "always_on": true
      },
      {
        "entity_number": 42,
        "name": "medium-electric-pole",
        "position": { "x": 3, "y": 3 }
        // "quality": "legendary"   // present only when above normal
      }
    ],
    "wires": [
      [42, 5, 57, 5]   // [entity_a, connector_a, entity_b, connector_b]
    ]
  }
}
```

Notes:

- **Positions** are integer tile coordinates for lamps and medium poles. Substations are 2×2, so their position is offset by `+0.5` to sit on the footprint centre.
- **`quality`** is omitted for normal quality and set to the lowercase name (`uncommon`, `rare`, `epic`, `legendary`) otherwise.
- **Wires** use connector ID `5`, the copper/power connection. The array is `[entity_a, connector_a, entity_b, connector_b]`.

---

## Pole placement algorithm

Poles are placed on a regular **lattice** whose cell size equals the pole's supply-area width `S`. Three rules keep the result tight and gap-free:

- **Perfect tiling** — the lattice step is exactly `S`, so each cell's supply area abuts the next with no gaps and no overlap.
- **Centered** — the first pole sits at `S // 2`, so its supply area starts at the image edge instead of wasting half of it off-grid. This also guarantees the far edges are covered.
- **Demand-gated** — a pole is created for a lattice cell *only if that cell actually contains a lamp*. Empty/transparent regions get no poles.

**Wiring** is `O(P)`: each pole connects only to its `+x` and `+y` lattice neighbour. Because the lattice step (`S`) is ≤ the pole's wire reach, adjacent poles are always within connection range, and there are no duplicate or redundant wires.

### Bridge poles (single-network mode)

Demand-gating can leave separate lamp regions on separate electric networks. With **Connect into one network** enabled, the tool:

1. Finds the connected components of placed poles (4-connectivity on the lattice, matching the wiring rule).
2. Runs a 0/1 BFS across the lattice — entering an existing pole cell costs `0`, an empty cell costs `1` — to find the cheapest gap between the merged region and the nearest unconnected component.
3. Drops a pole into each empty cell along that path and merges the component.
4. Repeats until everything is one network.

This adds the *fewest* bridge poles needed for full connectivity. Bridges sit in otherwise-empty space, so a bridge crossing a blank region of the image will show as a short line of lit poles — turn the option off if you'd rather wire those regions by hand in-game.

---

## Power pole coverage

The lattice step `S` is the pole's **supply-area width** in tiles. These are the values the tool uses, reflecting Factorio 2.0 / Space Age quality scaling (roughly +2 tiles per quality level, +4 at legendary):

### Medium electric pole

| Quality   | Supply area | Lattice step | Footprint |
|-----------|:-----------:|:------------:|:---------:|
| Normal    | 7 × 7       | 7            | 1 × 1     |
| Uncommon  | 9 × 9       | 9            | 1 × 1     |
| Rare      | 11 × 11     | 11           | 1 × 1     |
| Epic      | 13 × 13     | 13           | 1 × 1     |
| Legendary | 17 × 17     | 17           | 1 × 1     |

Base wire reach: **9 tiles** (grows with quality). Since the lattice step never exceeds the wire reach, neighbouring poles always connect.

### Substation

| Quality   | Supply area | Lattice step | Footprint |
|-----------|:-----------:|:------------:|:---------:|
| Normal    | 18 × 18     | 18           | 2 × 2     |
| Uncommon  | 20 × 20     | 20           | 2 × 2     |
| Rare      | 22 × 22     | 22           | 2 × 2     |
| Epic      | 24 × 24     | 24           | 2 × 2     |
| Legendary | 28 × 28     | 28           | 2 × 2     |

Substation wire reach equals its supply-area width at every tier, so adjacent substations connect exactly at the lattice step.

> These numbers come from the live game and can change with Factorio updates. If Wube adjusts pole stats, update the `SUPPLY` table in `index.html` to match.

---

## Running and deploying

It's one file with no build step.

- **Locally:** open `index.html` in a browser, or serve the folder (`python -m http.server`) if your browser restricts `file://` canvas reads.
- **GitHub Pages:** keep `index.html` at the repo root and enable Pages on the branch. The custom domain is set via the `CNAME` file.

Requires a browser with `CompressionStream` (all current Chrome, Firefox, Safari, and Edge).

---

## Tips

- Resize large images down first. A 128×128 image is ~16k lamps; anything much larger produces a huge blueprint and can be slow to generate or import.
- For crisp pixel art, turn **Smooth resize** off so the downscale uses nearest-neighbour and keeps your palette intact.
- A pole occupies the tile it sits on, so a lamp under a pole is dropped (one "hole" per pole). This is normal for lamp art.

## Contributing

Suggestions and improvements are welcome — open an issue or PR. Bug reports for malformed blueprints should include the image dimensions, pole type, and quality used.
