from google.cloud import vision
from django.conf import settings
import io
from PIL import Image

def get_crop_hints(image_file, aspect_ratio=1.0):
    client = vision.ImageAnnotatorClient()
    content = image_file.read()
    image = vision.Image(content=content)
    crop_hints_params = vision.CropHintsParams(aspect_ratios=[aspect_ratio])
    image_context = vision.ImageContext(crop_hints_params=crop_hints_params)
    response = client.crop_hints(image=image, image_context=image_context)
    # Get the first crop hint
    if response.crop_hints_annotation.crop_hints:
        bounding_box = response.crop_hints_annotation.crop_hints[0].bounding_poly.vertices
        return [(v.x, v.y) for v in bounding_box]
    return None

def crop_image(original_image_file, bounding_box):
    # Reset file pointer and open image with PIL
    original_image_file.seek(0)
    image = Image.open(original_image_file)
    # bounding_box: [(x1, y1), (x2, y2), (x3, y3), (x4, y4)]
    # Get min/max for rectangle crop
    xs = [v[0] for v in bounding_box]
    ys = [v[1] for v in bounding_box]
    left, upper, right, lower = min(xs), min(ys), max(xs), max(ys)
    cropped = image.crop((left, upper, right, lower))
    # Save cropped image to bytes
    cropped_bytes = io.BytesIO()
    cropped.save(cropped_bytes, format='PNG')
    cropped_bytes.seek(0)
    return cropped_bytes

def extract_text_blocks_from_image(image_file):
    client = vision.ImageAnnotatorClient()
    content = image_file.read()
    image = vision.Image(content=content)
    response = client.document_text_detection(image=image)

    if response.error.message:
        raise Exception(
            f'{response.error.message}\nSee https://cloud.google.com/apis/design/errors'
        )

    blocks = []
    for page in response.full_text_annotation.pages:
        for block in page.blocks:
            block_text = ""
            for paragraph in block.paragraphs:
                for word in paragraph.words:
                    word_text = "".join([symbol.text for symbol in word.symbols])
                    block_text += word_text
                block_text += " "
            # Optionally, get bounding box
            bounding_box = [(vertex.x, vertex.y) for vertex in block.bounding_box.vertices]
            blocks.append({
                "text": block_text.strip(),
                "bounding_box": bounding_box
            })
    return blocks

# Usage in your view:
def analyze_image_with_crop(request):
    image_file = request.FILES['image']
    # Step 1: Get crop hints
    bounding_box = get_crop_hints(image_file)
    if bounding_box:
        # Step 2: Crop the image
        cropped_image = crop_image(image_file, bounding_box)
        # Step 3: Extract text blocks from cropped image
        blocks = extract_text_blocks_from_image(cropped_image)
    else:
        # Fallback: use original image
        image_file.seek(0)
        blocks = extract_text_blocks_from_image(image_file)
    return blocks