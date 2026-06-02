import re

with open('tests/test_mixer.py', 'r') as f:
    content = f.read()

# Ah! bg_music.overlay(master_track)
# bg_music length = 14000
# master_track length = 14000
# Wait, why is it 15000?
# File 0: wav1 (3000) + silent (300) = 3300
# File 1: ring (1000) + wav2 (2000) + silent (300) = 3300
# File 2: txt_silent (2000) + silent (300) = 2300
# Total length = 3300 + 3300 + 2300 = 8900
# Wait, in the mock I overrode `mock_audio_segment.silent.return_value = MockSegment(2000)` which applies to the 300ms pause!
# So 300ms pause returns 2000 in the test!
# master = (3000+2000) + (1000+2000+2000) + (2000+2000) = 5000 + 5000 + 4000 = 14000!
# bg_music = empty (0). loop while < 14000
# bg_music += 5000 -> 5000
# bg_music += 5000 -> 10000
# bg_music += 5000 -> 15000
# 15000 is no longer < 14000, loops breaks.
# bg_music[:len(master_track)] -> stop = 14000
# MockSegment(min(self._length, stop)) -> MockSegment(min(15000, 14000)) -> 14000!
# bg_music length should be 14000.
# final_mix = bg_music.overlay(master_track)
# overlay = MockSegment(max(self._length, len(other)))
# max(14000, 14000) -> 14000.
# So why is exported_duration 15000 in the test output?

# WAIT. Look at __sub__:
# def __sub__(self, other): return self
# bg_music = bg_music[:len(master_track)] - 15
# When slicing returns MockSegment(14000), __sub__ is called.
# BUT wait! bg_music is 15000 before slicing!
# The slicing `bg_music[:len(master_track)]` wasn't actually truncating if the python parser failed me.
# Or wait, what if `bg_music[:len(master_track)]` is somehow not calling __getitem__?
# Yes, if I return `self` in __sub__ it returns the original object? No, it returns `self` of the sliced object.
# Let's add prints in MockSegment to trace!
