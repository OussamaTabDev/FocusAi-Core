from enum import Enum, auto

class StandardSubMode(Enum):
    """Sub-modes for standard mode"""
    NORMAL = auto()
    FOCUS = auto()
    
class FocusType(Enum):
    """Types of focus modes"""
    DEEP = auto()
    LIGHT = auto()
    CUSTOM = auto() 
    #option if saved gived new presets and can update
    # more presets saved by  the user 
    # WORK = auto()
    # STUDY = auto()
    # CREATIVE = auto()
    
class ModeType(Enum):
    """Enum for different top-level modes"""
    STANDARD = auto()
    KIDS = auto() 