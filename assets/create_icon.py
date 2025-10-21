"""Generate temporary icon for system tray."""

from PIL import Image, ImageDraw, ImageFont

# Create a simple 256x256 icon with "CC" text
size = 256
img = Image.new('RGB', (size, size), color='#1e293b')  # Dark blue background

# Draw
draw = ImageDraw.Draw(img)

# Draw a rounded rectangle background
margin = 20
draw.rounded_rectangle(
    [(margin, margin), (size - margin, size - margin)],
    radius=30,
    fill='#0ea5e9'  # Light blue
)

# Try to add text (may fail if font not available, that's okay)
try:
    # Try to use a nice font
    font = ImageFont.truetype("segoeui.ttf", 120)
except:
    # Fallback to default font
    font = ImageFont.load_default()

# Draw "CC" text
text = "CC"
bbox = draw.textbbox((0, 0), text, font=font)
text_width = bbox[2] - bbox[0]
text_height = bbox[3] - bbox[1]
position = ((size - text_width) // 2, (size - text_height) // 2 - 10)
draw.text(position, text, fill='white', font=font)

# Save at different sizes
img.save('icon_256.png')
img.resize((64, 64), Image.Resampling.LANCZOS).save('icon_64.png')
img.resize((32, 32), Image.Resampling.LANCZOS).save('icon_32.png')
img.resize((16, 16), Image.Resampling.LANCZOS).save('icon_16.png')

# Save as ICO (for Windows)
img.save('icon.ico', format='ICO', sizes=[(256, 256), (64, 64), (32, 32), (16, 16)])

print("Icons created successfully!")
print("- icon.ico (multi-size)")
print("- icon_256.png")
print("- icon_64.png")
print("- icon_32.png")
print("- icon_16.png")