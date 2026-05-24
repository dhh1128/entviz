# entviz
Entviz is a simple way to visualize values with high entropy &mdash; cryptographic keys and signatures, UUIDs, blockchain payment addresses, post-quantum keys, genomes, and so forth &mdash; so a human can compare them visually. The goal is to allow an untrained adult with reasonably good vision to easily decide whether two chunks of entropy are the same or different.

This is version 2 of the algorithm. It differs from version 1 in several ways: it introduces a **fingerprint** (a hash of the input) as the basis for most calculations, closing a security hole for input entropy that lacks an avalanche effect; it supports arbitrarily large inputs; it adds redundant gestalt channels (a color bar, a shape count summary, and an ellipse overlay); and it renames the edge shapes.

![example entviz](assets/example.png)

Compare [entmotif](https://dhh1128.github.io/entmotif), which turns entropy into music. The excellent [randomart](http://www.dirk-loss.de/sshvis/drunken_bishop.pdf) algorithm used with SSH keys is also related; it has a similar goal to entviz, but accepts different constraints and uses a different approach.

## Requirements
* Work in environments that can draw bitmapped or vector graphics.
* Losslessly represent all bits of entropy up to 512 bits. For larger inputs, losslessly represent the first and last 256 bits in the text channel, and bind the entire input through the fingerprint.
* Make it easy to read the entropy value out loud without the reader losing track of where they are.
* Support efficient partial comparisons (spot-checking).
* Guarantee that input entropy with even minor differences produces obvious visual differences, even when the input lacks an avalanche effect of its own.
* Uses 16 million colors (R*256, G*256, B*256). However, guarantee that entropy with even minor differences continues to have obvious visual differences in 256-color environments and in 256 shades of gray.
* Be usable by people with red-green, blue-yellow, and complete color blindness.
* Be trivial to implement correctly, with no significant dependencies.

## Nonrequirements
* Make it easy to remember all the details in a visualization. (Remembering a few arbitrarily chosen features of an entviz should be easy, but remembering all its details is unrealistic. The more appropriate goal is easy comparison to a saved copy.)
* Work in pure text environments. (Few pure text environments exist; even linux shells can save a file for viewing in a browser. Use randomart or invent a variation on this algorithm instead.)

## Concepts
A diagram produced by this algorithm is called an **entviz**. Entvizes can be categorized according to the dimensions of the grid into which they render: a "3x4 entviz", a "5x9 entviz", etc. Dimensions are given in <var>Width</var> x <var>Height</var> order. The maximum expressive **capacity** of an entviz of dimensions NxM is equal to 24 * N * M bits, although slightly less information may be communicated, depending on how the entropy is serialized to text.

The input being visualized is the **entropy**. The entropy is serialized to text and chopped into **tokens**, each of which represents 24 bits of entropy (or as close as possible on even character boundaries). The number of tokens is the **token count**.

The **fingerprint** is the SHA-512 hash of the normalized entropy. Because the fingerprint is produced by a cryptographic hash, it exhibits a strong avalanche effect: a single-bit change anywhere in the entropy changes roughly half the bits of the fingerprint. This is what lets entviz amplify differences even when the entropy itself is chosen rather than generated (for example, a UUID, a raw hex string, or a base64url blob), and what lets entviz handle inputs of any size. The fingerprint is tokenized exactly as the entropy is &mdash; into 24-bit chunks of base64url text. A token of the fingerprint is called an **ftok**. Because SHA-512 is always 512 bits (64 bytes), the fingerprint always yields exactly 22 ftoks: 21 full ftoks of 24 bits each, plus one partial ftok formed from the trailing byte and extended to 24 bits as described below.

Most of the entviz is drawn from the fingerprint rather than from the entropy directly. Specifically, the text of each cell and the background color of each cell's nucleus are derived from the **entropy**, preserving losslessness for inputs of 512 bits or less. Everything else &mdash; edge colors, edge shapes, the median and quartile calculations, blank cell placement, the entviz background color, the color bar, the shape count summary, and the ellipse overlay &mdash; is derived from the **fingerprint**.

## Guarantees
Each entviz conveys its entropy fully and independently, in a first visual channel, as text. If the text in an entviz is read aloud, *taking into account case-sensitivity*, all information is transferred. Text is tokenized into cells for efficient and reliable reading, and the cells are organized into a grid, which should be read left-to-right and top-to-bottom. For inputs of 512 bits or less, this text channel is fully lossless. For inputs greater than 512 bits, the text channel displays the first 256 bits and the last 256 bits of the entropy, separated by a blank cell; the full input is still bound into the visualization through the fingerprint, which drives all other channels.

The text channel does not, by itself, provide a visual avalanche effect: two inputs that differ by a single character will show nearly identical text. Avalanche is provided by the fingerprint-driven channels. The text channel's role is verbatim fidelity, not difference amplification, and it should be understood as one channel among several rather than a sole comparison method.

![text channel](assets/text-channel.png)

Each entviz also conveys its entropy, in a second visual channel, via the shapes and colors in the edges of its cells. These are derived from the fingerprint. Shapes in edges are carefully chosen to be visually distinct from one another even when they are quite small and pixelated. Shapes in edges sometimes connect to each other to make larger patterns. This allows some valid gestalt judgments and decreases the arbitrary noise that makes QR codes unmemorable for humans. Each edge shape is filled with a gradient that runs from the nucleus background color at the nucleus boundary to the nominal edge color at the cell boundary, so the nucleus color appears to bleed outward into the surrounding shapes. This ties each cell together as a single perceived object.

![edge channel](assets/edge-channel.png)

The colors used with edges are selected so their differences are detectable to someone who has difficulty perceiving colors, and also so they remain quite distinct when rendered in print in grayscale.

![edge channel grayscale](assets/edge-channel-grayscale.png)

Each entviz conveys its entropy, in a third visual channel, via the color that provides the background for the text in each cell. This nucleus background color is derived from the entropy, so for inputs of 512 bits or less it remains lossless. However, fine gradations in the colors of the nucleus may not be perceptible to the human eye, and these gradations will disappear if less than 16 million colors are displayable. Therefore, the colors in the nucleus are a partially redundant hint; they will never be misleading, but they should not be a primary comparison method.

![nucleus color channel](assets/nucleus-channel.png)

Zero or more cells in an entviz may be blank. The positioning of blank cells derives from the fingerprint. An entviz also contains small *quartile* marks on four cells. Blank cells and quartile marks are easily checked by viewers, and act as a sort of visual CRC. They surface differences that may be otherwise hidden in the middle of long strings and at the end of individual tokens.

![visual CRC](assets/crc.png)

Each entviz displays a **color bar** along its left edge and a **shape count summary** along its bottom. Both are derived from the fingerprint. They provide redundant channels that allow rapid gestalt comparison: two entvizes with different color or shape distributions will differ visibly in these summary regions even before a cell-by-cell comparison begins.

Each entviz also displays a partially transparent **ellipse overlay** derived from the fingerprint. The ellipse is anchored near a corner of one of the grid's perimeter edge rects, sized so that it always extends beyond the bounding rect (which clips it to an arc), and it darkens or lightens the edge shapes beneath it without affecting the nuclei or text. This creates a large, organic shape that contributes to the overall gestalt identity of the entviz and makes a quick, high-level glance more informative.

## Thoughts About Comparing

*Note: when reading entviz text aloud, the convention is to precede each capital letter with the one-syllable prefix "cap", to read the hyphen character - as "dash", and to read the underscore character as "under". This minimizes the number of syllables while eliminating all ambiguity. This convention applies only to the token text in the grid; the letters in the shape count summary are shape names, not text to be read with this convention.*

* display counts of each shape and each color
* allow toggling off each channel, each color, each shape, CRC
* spotcheck by reading a row or column or by having a column / row slider
* render with a legend for rows and columns

## Entviz Algorithm
1. Normalize the input.
    * Remove all whitespace.
    * Detect the entropy type, if possible, and split the input into prefix, core, and suffix, with all three pieces of data normalized. This should eliminate case differences, putting the entropy in canonical case, with canonical punctuation. It should identify prefixes that are not true entropy (e.g., the "0x" prefix on an Ethereum address, the "AAAA" at the front of an SSH key, etc.). It should identify suffixes that are checksums or derivations of the true entropy. The reference implementation in python has an `entropy` module with a `parse(txt)` method that can be used as an oracle, and it has unit tests that can provide a test vector.
    * If the input entropy has an unrecognized type, treat it as an arbitrary bag of bits, and render it as URL-safe base64 string.

1. Compute the **fingerprint** as the SHA-512 hash of the normalized entropy bytes. Serialize the 64-byte fingerprint to base64url text and split it into **ftoks** using exactly the same tokenization rule applied to the entropy: each ftok represents 3 bytes (24 bits) of the fingerprint. This yields 21 full ftoks plus one partial ftok formed from the trailing byte; extend the partial ftok to 24 bits by repeating its low-order bits, exactly as for a partial token. The fingerprint therefore always provides 22 ftoks. Assign each ftok an **ftok index** between 0 and 21, inclusive. The fingerprint is never displayed as text.

1. Split the entropy string into tokens, such that each token represents 3 bytes (24 bits) of binary entropy &mdash; or as close to that amount as possible on even character boundaries. For base64 and base58 strings, token length = 4. For hex, token length = 6. Call the number of tokens the **token count**. Assign to each token a **token index** between 0 and *token count* - 1, inclusive. If the entropy is greater than 512 bits, do not tokenize the whole input; instead tokenize only the first 256 bits and the last 256 bits of the entropy, and treat the two groups as separated by a single blank cell. In all cases, *token count* will be at most 22.

    ![split string into tokens](assets/tokens.png)

    Also, if a token represents less than 24 bits of entropy, extend the bits of the token by repeating low-order bits until a full 24 bits is used. Call the 24-bit value associated with the token its **quant**.

1. The complete entropy is visualized as a rectangular **grid** consisting of a certain number of **cells**. Call this number of cells the **cell count**. Each token is rendered into one cell in the grid, and if the rectangle of the grid has more cells than *token count*, one or more cells will be empty.

    Grids of a single row or a single column are invalid: the minimum grid is 2 columns by 2 rows. Each cell touches its neighbors directly and has an aspect ratio of 2:1. Given a **target aspect ratio** for the entviz (or, if none is given, using 1:1 as the target), choose the grid layout that produces an overall rectangle with an aspect ratio closest to the target, without being less than the target when the ratios are written as fractions, and with at least 2 columns and 2 rows.

    >Using more entropy than the example we've been building, just to show how this works in more complicated situations: 256 bits of entropy is 44 base-64 characters or 11 tokens. 11 tokens can be rendered as a grid with 6 columns and 2 rows (rounding *token count* to 12; aspect ratio 12:2), 4 columns and 3 rows (8:3), 3 columns and 4 rows (6:4), or 2 columns and 6 rows (4:6). Given a *target aspect ratio* of 1:1, the grid layout with an aspect ratio closest to 1:1 but not less than 1:1 is the one with 3 columns and 4 rows, aspect ratio 6:4.

    ![grid options](assets/grid-options.png)

1. Moving from left to right and top to bottom &mdash; which is how ASCII text should read if it wraps &mdash; number the cells from 0 to N, and call the number associated with each cell its **cell index**. Assign a *cell index* to each token. Unless changed, the *cell index* of a token will equal its *token index*.

    ![grid and cells](assets/grid-and-cells.png)

1. Define the **used ftoks** as the first *token count* ftoks of the fingerprint, taken in ftok index order. The used ftoks map one-to-one to tokens: the used ftok at index *i* corresponds to the token with *token index* *i*. (Because *token count* is at most 22 and the fingerprint provides 22 ftoks, there are always enough.) Any ftoks beyond *token count* are not used. From here on, all fingerprint-based calculations operate on the used ftoks. The 24-bit value of an ftok is its **quant**, defined exactly as for a token.

1. Sort the used ftoks in ASCII order (with a secondary sort by their *ftok index*, in case the same ftok appears in more than one place). Identify the first ftok in the sorted list that contains the median value. (If the count is even, use the first ftok from the middle pair.) Call this the **median ftok**.

1. Also sort the used ftoks by the ASCII order of their mirror image (with a secondary sort on the ftok index, in case the same ftok appears in more than one place). For example, if an ftok is "a4W6", its sort key would be "6W4a". If the number of used ftoks is not evenly divisible by 4, act as if 4 - (*token count* mod 4) blank items existed at the bottom of the list. Now divide the sorted list into 4 sections and call each section a **quartile**. Identify the first ftok in each quartile and call it the **first quartile ftok**, the **second quartile ftok**, and so on.

1. If *token count* is less than *cell count*, the grid will have blank cells. We want to use blank cells to create visual gaps in a consistent way that is more meaningful than simply putting all the blanks at the beginning or end, because this will aid comparison. Each used ftok corresponds to a token (and therefore to a cell); use that correspondence to locate the cells named below. Insert a blank cell at the *cell index* of the token corresponding to the *median ftok* by incrementing the *cell index* of all tokens whose *token index* >= that token's *token index*. This essentially shifts these tokens to the right or down in the grid. If *token count* + 1 is still less than *cell count*, insert a second blank cell before the cell of the last ftok in the ASCII-sorted list, again shifting cells that render after. If *token count* + 2 is still less than *cell count*, insert a third blank cell before the cell of the first ftok in the ASCII-sorted list, again shifting cells that render after. Do not perform more than 3 shifts. (For inputs greater than 512 bits, the blank cell separating the first and last 256-bit groups is in addition to these.)

1. Choose a fixed-width font such as Courier, and an appropriate font size for reading. In our example, we will use 12 point, but the algorithm will work at any reasonable font size. The size of the font determines the scale of the entviz.

1. Convert the point size of the font into pixels and call this value the **nucleus height**. Use the formula: pixels = (points * DPI) / 72. Most devices use 96 DPI, although other values are possible. At 96 DPI, a 12-point font = 16 pixels. This is the distance between the font's tallest ascender to its lowest descender, with a line height of 1.0, which allows some extra vertical space. It means that a 12-point font will render nicely, with appropriate extra space, in a rectangle that is 16 pixels high.

1. Calculate the **cell width** by multiplying *nucleus height* by 4, and calculate **cell height** by multiplying *nucleus height* by 2. Calculate the **grid width** by multiplying *cell width* by number of columns, and **grid height** by multiplying *cell height* by number of rows. Calculate the **nucleus width** by multiplying *nucleus height* by 3. Calculate the **edge size** by dividing *nucleus height* by 2. Calculate the **edge rect length** by dividing *nucleus width* by 2. Calculate the **grid margin** (abbreviated GM) by dividing *edge size* by 2; this equals half the width of a left or right edge rect. At 96 DPI with a 12-point font, *edge size* = 8 pixels and GM = 4 pixels.

    ![basic measurements for cell and grid](assets/cell-layout.png)

1. Allocate the **grid rect**, a rectangle of dimensions *grid width* x *grid height* that contains only the cells of the grid. We will assume that the top left corner of the *grid rect* is at position (0, 0) on the canvas for the purpose of the cell calculations, but its actual position is determined by the bounding rect below.

1. Allocate the **bounding rect**, the outermost rectangle of the entviz. It contains the *color bar* at its left, the *grid rect*, and the *shape count summary*. Its dimensions are:

    * width = GM + GM + *grid width* + GM + 1
    * height = 1 + GM + *grid height* + GM + *nucleus height* + GM + 1

    The leading GM in the width is the *color bar*; the next GM is the margin between the color bar and the grid rect; then the grid rect; then a GM margin; then a 1-pixel black line on the right edge. In the height, the leading 1 is a 1-pixel black line on the top edge; then a GM margin; then the grid rect; then a GM margin; then one line (*nucleus height*) for the shape count summary; then a GM margin; then a 1-pixel black line on the bottom edge.

    Fill the bounding rect with white. Draw a 1-pixel black line along its top, right, and bottom edges. Do not draw any black line around the *color bar*; the top and bottom black lines stop at the color bar's right edge, and the color bar forms the entire left edge of the bounding rect. Position the *grid rect* with its top-left corner at (GM + GM, 1 + GM) within the bounding rect.

    Use the bounding rect as a clipping region for all drawing, so that any element extending beyond it (notably the ellipse overlay) is truncated at its boundary. Draw the clipped content before the black border lines so the borders are never overwritten.

1. Let the array of **possible edge colors** be [white - `#ffffff`, gold - `#ffd966`, red - `#ff3f2f`, blue - `#2f3fbf`, black - `#000000`].

    ![colors](assets/colors.png)

    Select the 2 low-order bits of the *quant* of the *median ftok*. Use this 2-bit number as an index into the *possible edge colors* array to select the background color for the entviz. For example, if the 2-bit number == 1, the background color is gold. Remove the selected color from the array to generate a new array consisting of 4 colors, and call this the **edge colors** array.

1. Let *array 0* of possible edge shapes be [fin, axe, brick, inf]:

    ![array 0](assets/edge-shapes-0.png)

    Let *array 1* of possible edge shapes be [wave, hole, keel, mound]:

    ![array 1](assets/edge-shapes-1.png)

    Each shape's name begins with a distinct letter &mdash; F, A, B, I, W, H, K, M &mdash; and that capital letter identifies the shape in the *shape count summary*.

    Create a new array called the **edge shapes** array. Now iterate over the low-order 4 bits (bits 0 to 3) of the *quant* of the *second quartile ftok*. Call the selected bit the **selector** and the index of the bit the **bit index**. If the selector is 0, make the **selected shape array** array 0; otherwise, make it array 1. Copy the shape at *bit index* of *selected shape array* into *edge shapes*. This populates the *edge shapes* array with 4 shapes, each of which may come from either source array.

1. Define two integers, **shape shift** and **color shift**, and set both of their values to 0.

1. Inside the *grid rect*, render each token T into its appropriate cell in the grid, using its corresponding used ftok, *edge colors*, *edge shapes*, *shape shift* and *color shift*, according to the [cell rendering algorithm](#cell-rendering-algorithm) below.

1. Draw a circle with diameter = *edge size* / 2, centered vertically and horizontally, in a corner rect of each *quartile ftok*'s corresponding cell. For the first quartile ftok, place the circle in the top left corner of the cell, and use the first item in the *edge colors* array as its fill color. For the second, place the circle in the top right, using the second edge color. For the third, place the circle in the bottom right, using the third edge color. For the fourth, in the bottom left, using the fourth edge color.

1. Draw the **color bar** along the entire left edge of the bounding rect (width = GM, height = bounding rect height). Tally how many times each of the four *edge colors* is used across all edge rects actually drawn, excluding the edge rects of blank cells. Divide the color bar's height into horizontal bands, one for each color whose count is greater than zero, with each band's height proportional to that color's share of the total tally. Order the bands by descending count, most frequent at the top; break ties by the order of the color in the *edge colors* array. Fill each band with its color.

1. Draw the **shape count summary** (abbreviated SCS) below the grid. Tally how many times each of the (up to 8) *edge shapes* is used across all edge rects actually drawn, excluding the edge rects of blank cells. For each shape whose count is greater than zero, form a token of the form `X##`, where `X` is the shape's identifying letter and `##` is its count, zero-padded to two digits. (Counts will not exceed 99 for any practical grid; the field is two digits wide.) Sort these tokens by descending count, breaking ties alphabetically by shape letter. Join them with single spaces and render the resulting string in the same fixed-width font and size used for the cell text. Right-justify the string so its right edge aligns with the right edge of the *grid rect*, and position its baseline so the line occupies the *nucleus height* reserved for it, with its top edge at *grid rect* bottom + GM. The string extends left only as far as its content requires; it is at most about 16 characters wide and never wider than two columns of cells.

    In interactive environments, hovering over an edge shape should reveal a tooltip giving the shape's full name.

1. Draw the **ellipse overlay**. Derive its parameters from fingerprint bytes (the 64 bytes of the raw SHA-512 digest, numbered 0 to 63):

    * **anchor**: enumerate the candidate anchor points by walking the *perimeter cells* (every cell whose row is 0 or *row count* - 1, or whose column is 0 or *column count* - 1) in *cell index* order. For each such cell, visit its four corners in the order top-left, top-right, bottom-left, bottom-right. Emit each corner point the first time it is seen and skip it on every subsequent visit, so that points shared between adjacent perimeter cells appear in the enumeration exactly once. The resulting list contains both points on the outer boundary of the *grid rect* and interior grid intersections that are corners of perimeter cells; it does not contain any corners of purely interior cells. Use fingerprint byte 60, taken modulo the number of points in this list, to select the anchor. Mod by a byte is uniform here and needs no special arithmetic library.
    * **axis ratio**: map fingerprint byte 61 onto the range 1:1 to 1:2.5 to set the ratio of the ellipse's two semi-axes.
    * **rotation**: map fingerprint byte 62 onto the range 0&deg; to 180&deg; to set the ellipse's rotation.
    * **opacity**: map fingerprint byte 63 onto the range 10% to 30%.

    Center the ellipse on the anchor corner and size it so that its smaller semi-axis is at least half the diagonal of the bounding rect. This guarantees the ellipse always reaches beyond the bounding rect and is therefore always clipped to an arc rather than appearing as a closed ellipse. Choose the fill: convert the entviz background color to HLS; if its luminosity is greater than 0.5, fill the ellipse with black; otherwise fill it with white. Apply the fill at the derived opacity. Draw the overlay above the edge layer but below the nucleus layer, so that nucleus background colors and text are never affected by it.

## Cell Rendering Algorithm

A cell is rendered from a token T and the used ftok F that corresponds to it. The token supplies the cell's text and nucleus background color; the ftok supplies the edge colors and shapes.

1. For a given token T, identify the **origin point** within the *grid rect* with coordinates *x*, *y* with the following formulas: *x* = (*T.cell index* mod *column count*) * *cell width*; *y* = int(*T.cell index* / *column count*) * *cell height*.

1. Convert the *quant* for T into an RGB value the same way CSS does it &mdash; red in the low-order byte, and so forth &mdash; and call this RGB value the **nucleus background color**. Also convert the *nucleus background color* into the HLS color system and call the result the **HLS nucleus background color**. If the luminosity of the *HLS nucleus background color* is < 0.5, let the **foreground color** be white (#ffffff). Otherwise, let it be black (#000000).

1. Draw a **nucleus rect**. Dimensions are *nucleus width* x *nucleus height*. Top left corner is at *x* + *edge size*, *y* + *edge size*. Fill color = *nucleus background color*.

1. Using the *foreground color*, write the text of the token on top of the *nucleus rect*, centering it vertically and horizontally.

1. Convert the *quant* of the used ftok F into 6 4-bit numbers and call these the **edge nums**. Assign the edge numbers an **edge index**, with index 0 for bits 0-3 and continuing up to index 5 for bits 20-23.

1. Divide the region surrounding the *nucleus rect* into 6 **edge rects** &mdash; two above the nucleus, two below, and one on either side. The 4 corners of the cell are **corner rects** and are not included in any *edge rect*. The *edge rects* above and below the nucleus will have a width of *edge rect length* (= *nucleus width* / 2) and a height of *edge size*. The *edge rects* on either side will have a width of *edge size* and a height of *nucleus height*. Beginning with the top left *edge rect*, and moving clockwise, assign an **edge index** to each *edge rect*.

1. For each *edge num*, select the 2 low-order bits and call this the **color base**. XOR the *color base* with the 2 low-order bits of the *color shift* and call the result the **color index**. Select a color from the *edge colors* array using the *color index*, and call it the **edge color**. Increment *color shift* by 1.

1. For each *edge num*, select the 2 high-order bits and call this the **shape base**. XOR the *shape base* with the 2 low-order bits of the *shape shift* and call the result the **shape index**. Select a shape from the *edge shapes* array using the *shape index*, and call it the **edge shape**. If (T.*cell index* mod *column count*) != *column count* - 1, increment *shape shift* by 1.

1. After all 6 *edge nums* for the cell have been processed, if (T.*cell index* mod *column count*) == *column count* - 1 (i.e., this cell is in the last column of the grid), add *shape shift* to *color shift*. This adjustment runs once per cell, not once per edge.

1. Inside the logical region belonging to each *edge rect*, draw the *edge shape* using a linear gradient as its fill. The gradient runs from the *nucleus background color* at the boundary the edge rect shares with the *nucleus rect* to the *edge color* at the opposite (outer) boundary of the edge rect, perpendicular to the shared boundary. This makes the nucleus color appear to bleed outward into the shape before resolving to the edge color. All triangles are 45&deg;x45&deg;x90&deg;. Shapes are considered standard in edge 0 and edge 1. They rotate 90&deg; (and, in some cases, compress) for edge 2. They rotate 180&deg; from standard in edges 3 and 4. They rotate 270&deg; from standard (and, in some cases, compress) for edge 5. The shape diagrams above show the dimensions and orientations of each shape.

1. The 4 *corner rects* of each cell (each of size *edge size* x *edge size*) touch the nucleus only at a point, not along any side. Quartile marks are drawn in the corner rects of the four quartile cells as described above. In this version of the algorithm, all other corner rects are left empty. They are reserved as an extension point for future gestalt features, such as connectors that join the shapes of adjacent edge rects into larger emergent patterns; the specific behavior is deliberately left undefined pending visual testing.
