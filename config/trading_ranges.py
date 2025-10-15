from datetime import time as dtime

TRADING_RANGES = {
    'Monday': [
        # (dtime(0, 0), dtime(2, 0)),
        (dtime(2, 0), dtime(4, 0)),
        (dtime(4, 0), dtime(6, 0)),
        (dtime(6, 0), dtime(8, 0)),
        (dtime(8, 0), dtime(10, 0)),
        (dtime(10, 0), dtime(12, 0)),
        (dtime(12, 0), dtime(14, 0)),
        (dtime(14, 0), dtime(16, 0)),
        (dtime(16, 0), dtime(18, 0)),
        (dtime(18, 0), dtime(20, 0)),
        (dtime(20, 0), dtime(22, 0)),
        # (dtime(22, 0), dtime(23, 59))
    ],
    'Tuesday': [
        (dtime(0, 0), dtime(2, 0)),
        (dtime(2, 0), dtime(4, 0)),
        (dtime(4, 0), dtime(6, 0)),
        (dtime(6, 0), dtime(8, 0)),
        (dtime(8, 0), dtime(10, 0)),
        (dtime(10, 0), dtime(12, 0)),
        (dtime(12, 0), dtime(14, 0)),
        (dtime(14, 0), dtime(16, 0)),
        (dtime(16, 0), dtime(18, 0)),
        # (dtime(18, 0), dtime(20, 0)),
        (dtime(20, 0), dtime(22, 0)),
        # (dtime(22, 0), dtime(23, 59))
    ],
    'Wednesday': [
        (dtime(0, 0), dtime(2, 0)),
        (dtime(2, 0), dtime(4, 0)),
        (dtime(4, 0), dtime(6, 0)),
        (dtime(6, 0), dtime(8, 0)),
        (dtime(8, 0), dtime(10, 0)),
        (dtime(10, 0), dtime(12, 0)),
        (dtime(12, 0), dtime(14, 0)),
        (dtime(14, 0), dtime(16, 0)),
        (dtime(16, 0), dtime(18, 0)),
        (dtime(18, 0), dtime(20, 0)),
        (dtime(20, 0), dtime(22, 0)),
        # (dtime(22, 0), dtime(23, 59))
    ],
    'Thursday': [
        (dtime(0, 0), dtime(2, 0)),
        (dtime(2, 0), dtime(4, 0)),
        (dtime(4, 0), dtime(6, 0)),
        (dtime(6, 0), dtime(8, 0)),
        (dtime(8, 0), dtime(10, 0)),
        (dtime(10, 0), dtime(12, 0)),
        (dtime(12, 0), dtime(14, 0)),
        # (dtime(14, 0), dtime(16, 0)),
        (dtime(16, 0), dtime(18, 0)),
        (dtime(18, 0), dtime(20, 0)),
        (dtime(20, 0), dtime(22, 0)),
        # (dtime(22, 0), dtime(23, 59))
    ],
    'Friday': [
        (dtime(0, 0), dtime(2, 0)),
        (dtime(2, 0), dtime(4, 0)),
        (dtime(4, 0), dtime(6, 0)),
        (dtime(6, 0), dtime(8, 0)),
        (dtime(8, 0), dtime(10, 0)),
        (dtime(10, 0), dtime(12, 0)),
        (dtime(12, 0), dtime(14, 0)),
        # (dtime(14, 0), dtime(16, 0)),
        (dtime(16, 0), dtime(18, 0)),
        (dtime(18, 0), dtime(20, 0)),  
    ]
}