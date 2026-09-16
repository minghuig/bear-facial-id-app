"""Collection labels distinguish model work from explicit human decisions."""
def status(detection_state, heads, reviewed_ids):
    if detection_state == 'failed':
        return 'Detection failed'
    if detection_state != 'complete':
        return 'Detecting Bears…'
    if not heads:
        return 'No bears detected'
    if any(h.crop_review_state == 'pending' for h in heads):
        return 'Review detected crops'
    accepted = [h for h in heads if h.crop_review_state == 'accepted']
    if not accepted:
        return 'No usable crops'
    if any(h.recognition_state in ('queued', 'running') for h in accepted):
        return 'Recognizing Bears…'
    reviewed = [h for h in accepted if h.review_state != 'unresolved' or h.id in reviewed_ids]
    if not reviewed:
        return ('Recognition failed — retry'
                if any(h.recognition_state == 'failed' for h in accepted) else 'Ready to Review')
    counts = [(sum(h.review_state == state for h in reviewed), label) for state, label in
              [('confirmed', 'confirmed'), ('unresolved', 'unidentified'), ('ignored', 'ignored'), ('unusable', 'unusable')]]
    summary = ', '.join(f'{count} {label}' for count, label in counts if count)
    prefix = ('Reviewed' if len(reviewed) == len(accepted)
              else f'Partially reviewed ({len(reviewed)}/{len(accepted)})')
    return f'{prefix} · {summary}'
