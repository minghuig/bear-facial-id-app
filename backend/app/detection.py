"""Pure geometry for the released body-then-head preprocessing pipeline."""
import math
import io

BODY_THRESHOLD = 0.90
HEAD_THRESHOLD = 0.50
BODY_MARGIN = 0.03


def encode_jpeg_crop(image, box):
    """Persist body and head crops in the released preprocessing JPEG format."""
    output = io.BytesIO()
    image.crop(box).save(output, format='JPEG')
    return output.getvalue()


def body_crop(detection, width, height):
    """Validate a normalized MegaDetector xywh box and return crop metadata.

    The margin and edge behavior reproduce BrownBear_ReID/get_body_csv.py:
    add three percent of the original dimension when it fits, otherwise retain
    the unexpanded detector edge. PIL rounds float crop coordinates; recording
    those integer coordinates makes later head-to-original mapping explicit.
    """
    bbox = detection.bbox
    values = [*bbox, detection.confidence]
    if len(bbox) != 4 or not all(math.isfinite(value) for value in values):
        raise ValueError('Invalid body detector box')
    x, y, box_width, box_height = bbox
    if (x < 0 or y < 0 or box_width <= 0 or box_height <= 0 or
            x + box_width > 1.0001 or y + box_height > 1.0001):
        raise ValueError('Body detector box is outside the image')
    # CameraTraps filters the raw score strictly before truncating it to three
    # significant digits, so an emitted 0.90 can represent raw score > 0.90.
    if detection.confidence < BODY_THRESHOLD:
        return None
    x1, y1 = x * width, y * height
    x2, y2 = min(1, x + box_width) * width, min(1, y + box_height) * height
    width_margin, height_margin = width * BODY_MARGIN, height * BODY_MARGIN
    padded = [
        x1 - width_margin if x1 - width_margin >= 0 else x1,
        y1 - height_margin if y1 - height_margin >= 0 else y1,
        x2 + width_margin if x2 + width_margin <= width else x2,
        y2 + height_margin if y2 + height_margin <= height else y2,
    ]
    crop_box = [round(value) for value in padded]
    crop_box = [max(0, crop_box[0]), max(0, crop_box[1]),
                min(width, crop_box[2]), min(height, crop_box[3])]
    if crop_box[2] <= crop_box[0] or crop_box[3] <= crop_box[1]:
        raise ValueError('Body detector produced an empty crop')
    return {
        'category': detection.category,
        'confidence': detection.confidence,
        'bbox': bbox,
        'box': [x1, y1, x2, y2],
        'crop_box': crop_box,
        'width': crop_box[2] - crop_box[0],
        'height': crop_box[3] - crop_box[1],
    }


def head_crop(box, body):
    """Validate a head xyxy+score box and map it to the oriented original."""
    if len(box) != 5 or not all(math.isfinite(value) for value in box):
        raise ValueError('Invalid head detector box')
    if not 0 <= box[4] <= 1:
        raise ValueError('Invalid head detector score')
    if box[4] < HEAD_THRESHOLD:
        return None
    width, height = body['width'], body['height']
    x1, y1 = max(0, math.floor(box[0])), max(0, math.floor(box[1]))
    x2, y2 = min(width, math.ceil(box[2])), min(height, math.ceil(box[3]))
    if x2 <= x1 or y2 <= y1:
        return None
    left, top = body['crop_box'][:2]
    return {
        'local_box': [x1, y1, x2, y2],
        'box': [left + x1, top + y1, left + x2, top + y2],
        'score': box[4],
    }
