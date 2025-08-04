from PIL import Image, ImageDraw, ImageFont



new_image = Image.new('RGB', (200, 200), color='white')

draw = ImageDraw.Draw(new_image)

font = ImageFont.truetype("arial.ttf", 16)

info_lines = [
    "Product Name: Example Product",
    "Category: Example Category",
    "Price: $10.00",
    "Size: M",
    "Unit: pcs",
]
label_width = 180
label_height = 180
y_offset = 10

for line in info_lines:
    print(line)
    bbox = draw.textbbox((0, 0), line, font = font)
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]

new_image.save('asdw.jpg')