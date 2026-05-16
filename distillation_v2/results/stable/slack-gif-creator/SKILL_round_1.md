```markdown
---
name: slack-gif-creator
description: Knowledge and utilities for creating animated GIFs optimized for Slack. Provides constraints, validation tools, and animation concepts. Use when users request animated GIFs for Slack like "make me a GIF of X doing Y for Slack."
license: Complete terms in LICENSE.txt
---

# Slack GIF Creator

A toolkit providing utilities and knowledge for creating animated GIFs optimized for Slack.

## Slack Requirements

**Dimensions (CRITICAL):**
- Emoji GIFs: **128x128 exactly** (do not use 64x64, 256x256, or 800x800)
- Message GIFs: **480x480 exactly**

**Parameters:**
- FPS: 10-30 (specify exactly; do not let PIL round it)
- Colors: 48-128 (fewer = smaller file size)
- Duration: Keep under 3 seconds for emoji GIFs

## Minimal Working Template

Use this template for any new GIF. Copy and adapt:

```python
from core.gif_builder import GIFBuilder
from PIL import Image, ImageDraw
import math

# SET DIMENSIONS FIRST
WIDTH, HEIGHT = 128, 128  # Change to 480, 480 for message GIFs
FPS = 15
NUM_FRAMES = 20

# Create builder with exact dimensions and FPS
builder = GIFBuilder(width=WIDTH, height=HEIGHT, fps=FPS)

# Generate frames
for i in range(NUM_FRAMES):
    # Create frame with background
    frame = Image.new('RGB', (WIDTH, HEIGHT), (240, 248, 255))
    draw = ImageDraw.Draw(frame)

    # Calculate animation progress (0.0 to 1.0)
    t = i / (NUM_FRAMES - 1)

    # Draw your animation here
    # Example: draw a circle that moves
    x = int(64 + 30 * math.cos(t * 2 * math.pi))
    y = int(64 + 30 * math.sin(t * 2 * math.pi))
    draw.ellipse([x-10, y-10, x+10, y+10], fill=(255, 0, 0))

    builder.add_frame(frame)

# Save with validation
builder.save('output.gif', num_colors=128, optimize_for_emoji=(WIDTH==128))

# Validate result
from core.validators import validate_gif
passes, info = validate_gif('output.gif', is_emoji=(WIDTH==128), verbose=True)
print(f"Validation passed: {passes}")
```

## Core Workflow

1. **Set dimensions and FPS exactly** — use the template above
2. **Generate frames in a loop** — calculate animation progress as `t = i / (NUM_FRAMES - 1)`
3. **Draw using PIL primitives** — circles, lines, polygons, rectangles
4. **Save and validate** — always call `validate_gif()` after saving

## Drawing Graphics

### Working with User-Uploaded Images
If a user uploads an image:
- **Use it directly** (e.g., "animate this", "split this into frames")
- **Use it as inspiration** (e.g., "make something like this")

Load with PIL:
```python
from PIL import Image
uploaded = Image.open('file.png')
# Resize if needed: uploaded = uploaded.resize((128, 128))
```

### Drawing from Scratch
Use PIL ImageDraw primitives:

```python
from PIL import ImageDraw

draw = ImageDraw.Draw(frame)

# Circles/ovals
draw.ellipse([x1, y1, x2, y2], fill=(r, g, b), outline=(r, g, b), width=3)

# Polygons (stars, triangles, etc.)
points = [(x1, y1), (x2, y2), (x3, y3), ...]
draw.polygon(points, fill=(r, g, b), outline=(r, g, b), width=3)

# Lines
draw.line([(x1, y1), (x2, y2)], fill=(r, g, b), width=5)

# Rectangles
draw.rectangle([x1, y1, x2, y2], fill=(r, g, b), outline=(r, g, b), width=3)
```

**Do not use:** Emoji fonts, assume pre-packaged graphics exist, or hardcode colors without checking the request.

### Making Graphics Look Good

**Use thicker lines** — Always set `width=2` or higher. Thin lines (width=1) look choppy.

**Add visual depth:**
- Use gradients for backgrounds (`create_gradient_background`)
- Layer multiple shapes (star with smaller star inside)
- Add highlights or rings

**Make shapes interesting:**
- Don't draw plain circles — add rings, highlights, or patterns
- Stars can have glows (draw larger semi-transparent versions behind)
- Combine shapes (stars + sparkles, circles + rings)

**Pay attention to colors:**
- Use vibrant, complementary colors
- Add contrast (dark outlines on light shapes, light outlines on dark)
- Consider overall composition

**For complex shapes** (hearts, snowflakes, etc.):
- Use combinations of polygons and ellipses
- Calculate points carefully for symmetry
- Add details (heart highlight curve, snowflake branches)

## Available Utilities

### GIFBuilder (`core.gif_builder`)
Assembles frames and optimizes for Slack:
```python
builder = GIFBuilder(width=128, height=128, fps=15)
builder.add_frame(frame)  # Add single PIL Image
builder.add_frames(frames)  # Add list of frames
builder.save('out.gif', num_colors=48, optimize_for_emoji=True, remove_duplicates=True)
```

### Validators (`core.validators`)
Check if GIF meets Slack requirements:
```python
from core.validators import validate_gif, is_slack_ready

# Detailed validation (always use this)
passes, info = validate_gif('my.gif', is_emoji=True, verbose=True)
print(f"Passes: {passes}")
print(f"Info: {info}")

# Quick check
if is_slack_ready('my.gif'):
    print("Ready!")
```

### Easing Functions (`core.easing`)
Smooth motion instead of linear:
```python
from core.easing import interpolate

# Progress from 0.0 to 1.0
t = i / (num_frames - 1)

# Apply easing
y = interpolate(start=0, end=400, t=t, easing='ease_out')

# Available: linear, ease_in, ease_out, ease_in_out,
#           bounce_out, elastic_out, back_out
```

### Frame Helpers (`core.frame_composer`)
Convenience functions:
```python
from core.frame_composer import (
    create_blank_frame,         # Solid color background
    create_gradient_background,  # Vertical gradient
    draw_circle,                # Helper for circles
    draw_text,                  # Simple text rendering
    draw_star                   # 5-pointed star
)
```

## Animation Concepts

### Shake/Vibrate
Offset object position with oscillation:
```python
t = i / (NUM_FRAMES - 1)
offset_x = int(5 * math.sin(t * 4 * math.pi))  # Oscillate 2 times
x = center_x + offset_x
```

### Pulse/Heartbeat
Scale object size rhythmically:
```python
t = i / (NUM_FRAMES - 1)
scale = 0.8 + 0.4 * math.sin(t * 2 * math.pi)  # 0.8 to 1.2
```

### Bounce
Object falls and bounces:
```python
from core.easing import interpolate
t = i / (NUM_FRAMES - 1)
y = interpolate(start=10, end=100, t=t, easing='bounce_out')
```

### Spin/Rotate
Rotate object around center:
```python
t = i / (NUM_FRAMES - 1)
angle = t * 360  # Full rotation
rotated = image.rotate(angle, resample=Image.BICUBIC)
```

### Fade In/Out
Gradually appear or disappear:
```python
t = i / (NUM_FRAMES - 1)
alpha = int(255 * t)  # Fade in
# Use Image.blend() or adjust RGBA alpha channel
```

### Slide
Move object from off-screen to position:
```python
from core.easing import interpolate
t = i / (NUM_FRAMES - 1)
x = interpolate(start=-50, end=64, t=t, easing='ease_out')
```

### Zoom
Scale and position for zoom effect:
```python
t = i / (NUM_FRAMES - 1)
scale = 0.1 + 1.9 * t  # 0.1 to 2.0
zoomed = image.resize((int(128*scale), int(128*scale)))
```

### Explode/Particle Burst
Create particles radiating outward:
```python
for particle in particles:
    particle['x'] += particle['vx']
    particle['y'] += particle['vy']
    particle['vy'] += 0.1  # Gravity
    particle['alpha'] = max(0, particle['alpha'] - 10)  # Fade
```

## Optimization Strategies

Only implement when user asks to make file size smaller:

1. **Fewer frames** — Lower FPS (10 instead of 20) or shorter duration
2. **Fewer colors** — `num_colors=48` instead of 128
3. **Smaller dimensions** — 128x128 instead of 480x480
4. **Remove duplicates** — `remove_duplicates=True` in save()
5. **Emoji mode** — `optimize_for_emoji=True` auto-optimizes

```python
# Maximum optimization for emoji
builder.save(
    'emoji.gif',
    num_colors=48,
    optimize_for_emoji=True,
    remove_duplicates=True
)
```

## Common Mistakes

### Dimensions Not Exact
**Problem:** GIF is 800x800, 64x64, or 256x256 instead of 128x128 or 480x480.
**Fix:** Set `width=128, height=128` in GIFBuilder constructor. Do not let PIL auto-scale. Check the template above.

### Animation Not Visible
**Problem:** Frames appear identical; no motion between frames.
**Fix:** Ensure you calculate `t = i / (NUM_FRAMES - 1)` and use it to change position, scale, or rotation each frame. Test with a simple moving circle first.

### Easing Not Applied
**Problem:** Motion appears linear instead of smooth.
**Fix:** Use `interpolate()` from `core.easing` with the correct easing type. Example: `interpolate(start=0, end=100, t=t, easing='ease_out')`.

### Validation Not Called
**Problem:** GIF created but not validated; unknown if it meets Slack requirements.
**Fix:** Always call `validate_gif('output.gif', is_emoji=True, verbose=True)` after saving. Print the result.

### FPS or Frame Count Wrong
**Problem:** Task requests 15 fps and 20 frames; GIF has 16.7 fps and 24 frames.
**Fix:** Set `fps=15` exactly in GIFBuilder. Set `NUM_FRAMES=20` exactly. Count frames in the loop: `for i in range(NUM_FRAMES)`.

### File Size Comparison Missing
**Problem:** Task asks to compare original.gif and optimized.gif sizes; no output printed.
**Fix:** After saving both files, print sizes:
```python
import os
size1 = os.path.getsize('original.gif') / 1024
size2 = os.path.getsize('optimized.gif') / 1024
print(f"original.gif: {size1:.2f} KB")
print(f"optimized.gif: {size2:.2f} KB")
print(f"Reduction: {size1 - size2:.2f} KB")
```

### Rotation Not Visible
**Problem:** Star or object appears in same orientation across all frames.
**Fix:** Use `image.rotate(angle)` where angle changes each frame. Example: `angle = (i / NUM_FRAMES) * 360` for full rotation.

### Sparkles or Particles Not Visible
**Problem:** Task requests sparkles or particles; none appear in output.
**Fix:** Draw small circles or dots at calculated positions. Use `draw.ellipse()` with small radius. Ensure they are a different color from background. Test with a single static sparkle first.

### Blank or White Output
**Problem:** GIF is blank or all white; no shapes visible.
**Fix:** Ensure you call `draw = ImageDraw.Draw(frame)` for each frame. Ensure fill colors are not the same as background. Test with a bright color (red, yellow) on a dark background.

## Dependencies

```bash
pip install pillow imageio numpy
```
```
