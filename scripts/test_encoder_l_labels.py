import numpy as np
from scripts.encoder_l_v1 import labels_for

def test_seen_break_requires_shortest_window_membership():
    records=[{'mechanism':'trend_break','change_point':700}]
    # origin 800: cp is 100 steps old, outside L96; must be stable.
    assert labels_for(records,np.asarray([[0,800]]),24)[0]=='stable'
    # origin 780: cp is 80 steps old and delay passed; visible.
    assert labels_for(records,np.asarray([[0,780]]),24)[0]=='visible_change'

def test_future_jump_is_horizon_scoped():
    records=[{'mechanism':'future_jump','change_point':780}]
    assert labels_for(records,np.asarray([[0,768]]),24)[0]=='unseen_change'
    assert labels_for(records,np.asarray([[0,700]]),24)[0]=='stable'
