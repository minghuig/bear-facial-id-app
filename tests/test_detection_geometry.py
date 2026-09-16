from types import SimpleNamespace

import pytest

from app.detection import body_crop, head_crop


def detection(bbox, confidence=.95, category=1):
    return SimpleNamespace(bbox=bbox, confidence=confidence, category=category)


def test_body_crop_reproduces_three_percent_margin_and_edge_behavior():
    centered = body_crop(detection([.2, .25, .5, .5]), 100, 80)
    assert centered['crop_box'] == [17, 18, 73, 62]
    assert (centered['width'], centered['height']) == (56, 44)

    edge = body_crop(detection([0, .1, 1, .8]), 100, 80)
    assert edge['crop_box'] == [0, 6, 100, 74]


def test_body_threshold_accepts_cameratraps_truncated_point_nine():
    assert body_crop(detection([0, 0, 1, 1], confidence=.90), 100, 80) is not None
    assert body_crop(detection([0, 0, 1, 1], confidence=.899), 100, 80) is None


def test_head_crop_clips_locally_and_maps_to_oriented_original():
    body = {'width':56, 'height':44, 'crop_box':[17,18,73,62]}
    result = head_crop([-2.2, 3.2, 20.1, 60, .8], body)
    assert result == {'local_box':[0,3,21,44], 'box':[17,21,38,62], 'score':.8}
    assert head_crop([0,0,10,10,.49], body) is None


@pytest.mark.parametrize('bbox', [[0,0,-1,1], [-.1,0,.5,.5], [0,0,1.1,1]])
def test_invalid_body_boxes_are_rejected(bbox):
    with pytest.raises(ValueError):
        body_crop(detection(bbox), 100, 80)
