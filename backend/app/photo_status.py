"""Collection labels distinguish model work from explicit human decisions."""
def status(detection_state, heads, reviewed_ids):
    if detection_state == 'failed':
        return 'Detection failed'
    if detection_state != 'complete':
        return 'Detecting Bears…'
    if not heads:
        return 'No bears detected'
    if any(h.recognition_state in ('queued', 'running') for h in heads):
        return 'Recognizing Bears…'
    reviewed = [h for h in heads if h.review_state != 'unresolved' or h.id in reviewed_ids]
    if not reviewed:
        return 'Recognition failed — retry' if any(h.recognition_state == 'failed' for h in heads) else 'Ready to Review'
    counts = [(sum(h.review_state == state for h in reviewed), label) for state, label in
              [('confirmed', 'confirmed'), ('unresolved', 'unidentified'), ('ignored', 'ignored'), ('unusable', 'unusable')]]
    summary = ', '.join(f'{count} {label}' for count, label in counts if count)
    prefix = 'Reviewed' if len(reviewed) == len(heads) else f'Partially reviewed ({len(reviewed)}/{len(heads)})'
    return f'{prefix} · {summary}'
