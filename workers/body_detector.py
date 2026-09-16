"""MegaDetector v4.1 adapter for the BrownBear_ReID body stage.

Inference and significant-digit truncation follow Microsoft CameraTraps v4.1
(`059dc0ebdd00ddf22c2c1ecdf13e8f0b36b7fc66`), released under the MIT
license. Only the small service adapter is maintained here; the frozen graph is
kept outside Git and verified before loading.
"""
import io
import math

import httpx
import numpy as np
from PIL import Image

from trusted import checkpoint

BODY_THRESHOLD = 0.90
_model = None


def truncate_float(value, precision):
    """Match CameraTraps' significant-digit truncation."""
    value = float(value)
    if np.isclose(value, 0):
        return 0.0
    factor = math.pow(10, precision - 1 - math.floor(math.log10(abs(value))))
    return math.floor(value * factor) / factor


class MegaDetector:
    def __init__(self, model_path):
        import tensorflow.compat.v1 as tf
        tf.disable_eager_execution()
        graph = tf.Graph()
        with graph.as_default():
            graph_def = tf.GraphDef()
            with tf.gfile.GFile(str(model_path), 'rb') as stream:
                graph_def.ParseFromString(stream.read())
            tf.import_graph_def(graph_def, name='')
        config = tf.ConfigProto(intra_op_parallelism_threads=2,
                                inter_op_parallelism_threads=2)
        self.session = tf.Session(graph=graph, config=config)
        self.image = graph.get_tensor_by_name('image_tensor:0')
        self.boxes = graph.get_tensor_by_name('detection_boxes:0')
        self.scores = graph.get_tensor_by_name('detection_scores:0')
        self.classes = graph.get_tensor_by_name('detection_classes:0')

    def detect(self, image):
        pixels = np.expand_dims(np.asarray(image, dtype=np.uint8), axis=0)
        boxes, scores, classes = self.session.run(
            [self.boxes, self.scores, self.classes],
            feed_dict={self.image: pixels})
        results = []
        for box, score, category in zip(boxes[0], scores[0], classes[0]):
            if float(score) <= BODY_THRESHOLD:
                continue
            y1, x1, y2, x2 = box
            results.append({
                'category': int(category),
                'confidence': truncate_float(score, 3),
                'bbox': [truncate_float(value, 4) for value in
                         (x1, y1, x2 - x1, y2 - y1)],
            })
        return results


def model():
    global _model
    if _model is None:
        _model = MegaDetector(checkpoint('md_v4.1.0.pb'))
    return _model


def detect(job):
    response = httpx.get(job['url'], timeout=120)
    response.raise_for_status()
    image = Image.open(io.BytesIO(response.content)).convert('RGB')
    return {'body_detection': {
        'width': image.width,
        'height': image.height,
        'detections': model().detect(image),
    }}
