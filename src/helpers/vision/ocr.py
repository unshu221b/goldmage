from google.cloud import vision
from django.conf import settings
import io

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