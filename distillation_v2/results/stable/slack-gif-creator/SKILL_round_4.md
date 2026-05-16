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
- Emoji GIFs: **128x128 exactly** (do not use 64x64, 256x256, 200x200, 480x480, or 800x800)
- Message GIFs: **480x480 exactly**

**Parameters:**
- FPS: 10-30 (specify exactly in GIFBuilder; do not let PIL round it)
- Colors: 48-128 (fewer = smaller file size)
- Duration: Keep under 3 seconds for emoji GIFs
- Frame count: Match request exactly (no frame merging or removal unless explicitly requested)

## Minimal Working Template

Use this template for any new GIF. Copy and adapt:

```python
from core.gif_builder import GIFBuilder
from core.validators import validate_gif
from PIL import Image, ImageDraw
import math
import os

# SET DIMENSIONS AND PARAMETERS FIRST
WIDTH, HEIGHT = 128, 128  # Change to 480, 480 for message GIFs
FPS = 15  # Set exactly; do not let it auto-round
NUM_FRAMES = 20  # Match request exactly

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

# Validate result — ALWAYS DO THIS
passes, info = validate_gif('output.gif', is_emoji=(WIDTH==128), verbose=True)
print(f"Validation passed: {passes}")
print(f"Frame count: {info.get('frame_count')}")
print(f"FPS: {info.get('fps')}")
print(f"Dimensions: {info.get('width')}x{info.get('height')}")
```

## Core Workflow

1. **Set dimensions, FPS, and frame count exactly** — use the template above; match all numbers from the request
2. **Generate frames in a loop** — calculate animation progress as `t = i / (NUM_FRAMES - 1)`
3. **Draw using PIL primitives** — circles, lines, polygons, rectangles
4. **Save with correct parameters** — pass `num_colors`, `optimize_for_emoji`, and `remove_duplicates` only when requested
5. **Validate and print results** — always call `validate_gif()` after saving; print frame count, FPS, and dimensions from the info dict
6. **Print file size if comparing** — use `os.path.getsize()` to show KB for each file

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

**Important:** Do not pass `remove_duplicates=True` unless the task explicitly asks to optimize or reduce file size. Frame merging can reduce frame count below the request.

### Validators (`core.validators`)
Check if GIF meets Slack requirements:
```python
from core.validators import validate_gif, is_slack_ready

# Detailed validation (always use this)
passes, info = validate_gif('my.gif', is_emoji=True, verbose=True)
print(f"Passes: {passes}")
print(f"Frame count: {info.get('frame_count')}")
print(f"FPS: {info.get('fps')}")
print(f"Dimensions: {info.get('width')}x{info.get('height')}")

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
Scale object size rhythmically with pronounced change:
```python
t = i / (NUM_FRAMES - 1)
scale = 0.6 + 0.4 * math.sin(t * 2 * math.pi)  # 0.6 to 1.0, or adjust for more drama
# Redraw object at scaled size each frame
```

### Bounce
Object falls and bounces with clear acceleration/deceleration:
```python
from core.easing import interpolate
t = i / (NUM_FRAMES - 1)
y = interpolate(start=10, end=100, t=t, easing='bounce_out')
# Ensure bounce_out is used; do not use linear
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

Only implement when user explicitly asks to make file size smaller:

1. **Fewer frames** — Lower FPS (10 instead of 20) or shorter duration
2. **Fewer colors** — `num_colors=48` instead of 128
3. **Smaller dimensions** — 128x128 instead of 480x480
4. **Remove duplicates** — `remove_duplicates=True` in save() (WARNING: reduces frame count)
5. **Emoji mode** — `optimize_for_emoji=True` auto-optimizes

```python
# Maximum optimization for emoji (only when requested)
builder.save(
    'emoji.gif',
    num_colors=48,
    optimize_for_emoji=True,
    remove_duplicates=True
)
```

## Common Mistakes

### Dimensions Not Exact
**Problem:** GIF is 200x200, 64x64, 256x256, 480x480, or 800x800 instead of 128x128 or 480x480.
**Fix:** Set `width=128, height=128` in GIFBuilder constructor for emoji GIFs. Set `width=480, height=480` for message GIFs. Do not let PIL auto-scale. Verify dimensions in validation output.

### Frame Count Does Not Match Request
**Problem:** Task requests 20 frames; GIF has 10, 12, 24, or fewer frames.
**Fix:** Set `NUM_FRAMES=20` exactly. Count frames in the loop: `for i in range(NUM_FRAMES)`. Do NOT pass `remove_duplicates=True` unless the task explicitly asks to optimize. Print frame count from validation info dict to confirm: `print(f"Frame count: {info.get('frame_count')}")`.

### FPS Not Set Exactly
**Problem:** Task requests 15 fps; GIF has 16.7 fps or 10 fps.
**Fix:** Set `fps=15` exactly in GIFBuilder constructor. Do not omit the fps parameter. Print FPS from validation info dict: `print(f"FPS: {info.get('fps')}")`. If PIL rounds it, note this in output but do not claim exact match.

### Animation Not Visible or Too Subtle
**Problem:** Frames appear identical; no motion between frames, or motion is barely perceptible.
**Fix:**
- Ensure you calculate `t = i / (NUM_FRAMES - 1)` and use it to change position, scale, rotation, or alpha each frame.
- Test with a simple moving circle first.
- For pulse/bounce/rotation: make the change large enough to see (e.g., scale 0.6 to 1.0, not 0.95 to 1.05).
- Print `t` and the calculated value (e.g., `print(f"Frame {i}: t={t}, x={x}")`) to debug.

### Easing Not Applied or Appears Linear
**Problem:** Motion appears linear instead of smooth; bounce does not show clear acceleration/deceleration.
**Fix:**
- Use `interpolate()` from `core.easing` with the correct easing type.
- For bounce: use `easing='bounce_out'`, not `linear`.
- For overshoot: use `easing='back_out'`.
- Example: `y = interpolate(start=10, end=100, t=t, easing='bounce_out')`.
- Verify easing is working by printing intermediate values.

### Validation Not Called or Result Not Printed
**Problem:** GIF created but not validated; unknown if it meets Slack requirements.
**Fix:** Always call `validate_gif('output.gif', is_emoji=True, verbose=True)` after saving. Print the result including frame count, FPS, and dimensions from the info dict. Do not skip this step.

### File Size Comparison Missing or Incorrect
**Problem:** Task asks to compare original.gif and optimized.gif sizes; no output printed or comparison is wrong.
**Fix:** After saving both files, print sizes and verify optimized is smaller:
```python
import os
size1 = os.path.getsize('original.gif') / 1024
size2 = os.path.getsize('optimized.gif') / 1024
print(f"original.gif: {size1:.2f} KB")
print(f"optimized.gif: {size2:.2f} KB")
print(f"Reduction: {size1 - size2:.2f} KB")
# Verify: size2 should be smaller than size1
```

### Rotation Not Visible
**Problem:** Star or object appears in same orientation across all frames.
**Fix:** Use `image.rotate(angle)` where angle changes each frame. Example: `angle = (i / NUM_FRAMES) * 360` for full rotation. Ensure you redraw the rotated image each frame. Test with a simple shape (square or star) to confirm rotation is visible.

### Sparkles or Particles Not Visible
**Problem:** Task requests sparkles or particles; none appear in output.
**Fix:** Draw small circles or dots at calculated positions. Use `draw.ellipse()` with small radius (e.g., 2-5 pixels). Ensure they are a different color from background. Test with a single static sparkle first. Make sure particles are drawn AFTER the background so they appear on top.

### Blank or White Output
**Problem:** GIF is blank or all white; no shapes visible.
**Fix:** Ensure you call `draw = ImageDraw.Draw(frame)` for each frame. Ensure fill colors are not the same as background. Test with a bright color (red, yellow) on a dark background. Verify the frame is added to builder: `builder.add_frame(frame)`.

### Color Palette Not Applied
**Problem:** Task requests 48 colors; GIF still has 128 or 256 colors.
**Fix:** Pass `num_colors=48` to `builder.save()`. Verify in validation output that color count matches. If validation shows more colors than requested, the image may have too many unique colors; reduce them or use `optimize_for_emoji=True`. Print color count from validation info.

### Multiple Output Files Not Created
**Problem:** Task requests palette128.gif and palette32.gif; only one file exists or none exist.
**Fix:** Create and save each file separately with explicit filenames:
```python
builder.save('palette128.gif', num_colors=128)
builder.save('palette32.gif', num_colors=32)
# Validate both
validate_gif('palette128.gif', is_emoji=True, verbose=True)
validate_gif('palette32.gif', is_emoji=True, verbose=True)
# Print sizes
size128 = os.path.getsize('palette128.gif') / 1024
size32 = os.path.getsize('palette32.gif') / 1024
print(f"palette128.gif: {size128:.2f} KB")
print(f"palette32.gif: {size32:.2f} KB")
```

### Validation Passes When It Should Fail
**Problem:** Validation reports `passes: true` but color count exceeds guidelines.
**Fix:** Check the validation info dict for warnings. If color count is flagged as exceeding guidelines, manually note this in output. Print the warning to the user. Do not claim validation passed if there are warnings.

### Frame Merging Reduces Frame Count Below Request
**Problem:** Task requests 30 frames; GIF has 24 frames due to `remove_duplicates=True`.
**Fix:** Do NOT use `remove_duplicates=True` unless the task explicitly asks to optimize. If the task asks for exact frame count, omit this flag. Only use optimization flags when the user says "make it smaller" or "optimize".

## Dependencies

```bash
pip install pillow imageio numpy
```
```
