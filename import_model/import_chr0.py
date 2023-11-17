import collada
from collada import *
from helper import *
import numpy as np
from helper_classes import *
from chr0 import *
import random

CHR0_FILENAME = 'import/lucas/Run.chr0'
CHR0_FILEPATH = '/'.join(CHR0_FILENAME.split('/')[:-1])

class CHR0Import():
    def __init__(self, filenames, bones={}):
        self.filenames = filenames
        self.bones = bones
        
    def binary(self):
        out = bytearray()
        # version number
        out.extend(itb(0x01321AFD, 4))
        # sequence array ptr
        out.extend(itb(0x18, 4))
        # bank id (?)
        out.extend(itb(0, 2))
        # sequence count
        out.extend(itb(len(self.filenames), 2))
        sequences = []
        track_count = 0
        keyframe_count = 0
        for filename in self.filenames:
            chr0_parser = CHR0(open(filename, 'rb'), 0, 0, '')
            chr0_parser.analyze()
            tracks = chr0_parser.tracks
            sequence = ANMSequence(tracks, self.bones)
            sequences.append(sequence)
            track_count += sequence.track_count()
            keyframe_count += sequence.keyframe_count()
        # track count
        out.extend(itb(track_count, 2))
        # print('track count ' + str(track_count))
        # keyframe count
        out.extend(itb(keyframe_count, 2))
        # print('keyframe count ' + str(keyframe_count))
        # user data size and ptr
        out.extend(itb(0, 4))
        out.extend(itb(0, 4))
        running_ptr = 0x18 + 0xc * len(sequences)
        tracks = []
        for sequence in sequences:
            sequence_binary = sequence.binary(running_ptr)
            out.extend(sequence_binary)
            for track in sequence.tracks:
                tracks.append(ANMTrack(sequence.tracks[track], sequence.track_id_map[track], track))
            running_ptr += len(sequence.tracks) * 0x10
        keyframes = []
        for track in tracks:
            track_binary = track.binary(running_ptr)
            out.extend(track_binary)
            n = 'import/bone_txt/' + str(track.name)
            # f = open(n, 'wb')
            # f.close()
            for keyframe in track.keyframes:
                keyframes.append(ANMKeyframe(keyframe, track.keyframes[keyframe], track.quantization, track, n))
            running_ptr += len(track.keyframes) * 0xc
        settings_data = bytearray()
        self.first_states = {}
        for keyframe in keyframes:
            keyframe_binary, settings_binary = keyframe.binary(running_ptr)
            out.extend(keyframe_binary)
            if keyframe.time == 0:
                self.first_states[keyframe.track.track_id - 4] = {'s': keyframe.s, 'r': keyframe.r, 't': keyframe.t}
            settings_data.extend(settings_binary)
            running_ptr += len(settings_binary)
        out = out + settings_data
        if len(out) % 0x20 != 0:
            out = out + itb(0, 0x20 - len(out) % 0x20)
        stack = []
        for bone in self.bones.values():
            if bone.parent is None:
                stack.append([bone, 0])
        while len(stack):
            a = stack.pop()
            bone = a[0]
            indent = a[1]
            # print('  ' * indent + str(bone.name))
            # f = open('import/bone_txt/' + bone.name, 'a')
            # f.write('s: ' + ','.join([str(round(x, 3)) for x in bone.s]) + '\n')
            # f.write('r: ' + ','.join([str(round(x, 3)) for x in bone.r]) + '\n')
            # f.write('t: ' + ','.join([str(round(x, 3)) for x in bone.t]) + '\n')
            # f.write('\n')
            # f.write('\n'.join([', '.join([str(round(y, 3)) for y in x]) for x in bone.orientation]))
            # f.close()
            for child in bone.children:
                stack.append([self.bones[child], indent + 1])
        return out
    
    def toFile(self, name):
        with open(CHR0_FILEPATH + '/' + name, 'wb') as f:
            f.write(self.binary())

class ANMSequence():
    def __init__(self, tracks, bones):
        self.tracks = tracks
        self.bones = bones
        self.track_id_map = {}
        self.end = 0
        for track in self.tracks.values():
            for component in track.values():
                for axis in component.values():
                    for keyframe in axis.keys():
                        if keyframe > self.end:
                            self.end = keyframe
        self.prepare()

    def binary(self, tracks_ptr):
        out = bytearray()
        # name ptr
        out.extend(itb(0, 4))
        # track array ptr
        out.extend(itb(tracks_ptr, 4))
        # track count
        out.extend(itb(len(self.tracks), 2))
        out.extend(itb(0, 2))
        return out

    def prepare(self):
        new_tracks = {}
        for bone in self.bones.values():
            track_name = bone.name
            data = {}
            if track_name in self.tracks:
                data = self.tracks[track_name]
            # if 't' in data:
            #     del data['t']
            if len(data) == 0:
                data = {'t':{'x':{0:bone.t[0], self.end:bone.t[0]}, 'y':{0:bone.t[1], self.end:bone.t[1]}, 'z':{0:bone.t[2], self.end:bone.t[2]}}}
            self.track_id_map[bone.name] = bone.id
            changes = {}
            new_data = {}
            for component in data:
                new_data[component] = {}
                for axis in ['x', 'y', 'z']:
                    axis_data = data[component][axis]
                    for keyframe in axis_data:
                        timestamp = math.floor(keyframe * 10) / 10
                        value = axis_data[keyframe]
                        if timestamp not in changes:
                            changes[timestamp] = {}
                            for component_ in data:
                                changes[timestamp][component_] = {}
                        changes[timestamp][component][axis] = value
            new_track = {}
            # changes[0] ought to contain a base value for all axes for each component being animated
            new_track[0] = changes[0]
            change_timestamps = list(changes.keys())
            change_timestamps.sort()
            for i, timestamp in enumerate(change_timestamps[1:]):
                keyframe = {}
                for component in data:
                    keyframe[component] = {}
                for component in data:
                    for axis in ['x', 'y', 'z']:
                        if axis in changes[timestamp][component]:
                            keyframe[component][axis] = changes[timestamp][component][axis]
                        else:
                            keyframe[component][axis] = new_track[change_timestamps[i]][component][axis]
                new_track[timestamp] = keyframe
            new_tracks[track_name] = new_track
        self.tracks = new_tracks

    def keyframe_count(self):
        keyframe_count = 0
        for track in self.tracks:
            keyframe_count += len(self.tracks[track])
        return keyframe_count

    def track_count(self):
        return len(self.tracks)

    def size(self):
        return self.keyframe_count() * 0xc + self.track_count() * 0x10 + 0xc

class ANMTrack():
    def __init__(self, keyframes, track_id, name = ''):
        self.keyframes = keyframes
        self.track_id = track_id
        self.name = name

    def binary(self, keyframes_ptr):
        out = bytearray()
        # animation time
        out.extend(ftb(list(self.keyframes.keys())[-1]))
        # ptr to keyframes
        out.extend(itb(keyframes_ptr, 4))
        # keyframe count
        out.extend(itb(len(self.keyframes), 2))
        # track id
        out.extend(itb(self.track_id, 2))
        # quantization
        max_shift = 0xe
        keyframe_objs = []
        for keyframe in self.keyframes:
            keyframe_obj = ANMKeyframe(keyframe, self.keyframes[keyframe])
            keyframe_objs.append(keyframe_obj)
            max_shift = min(max_shift, keyframe_obj.maxShift())
        self.quantization = 0x30 + max_shift
        # print(hex(self.quantization))
        out.extend(itb(self.quantization, 1))
        anm_types = 0
        if 's' in self.keyframes[0]:
            anm_types += 2
        if 'r' in self.keyframes[0]:
            anm_types += 8
        if 't' in self.keyframes[0]:
            anm_types += 1
        # components being animated
        out.extend(itb(anm_types, 1))
        # interpolation method (slerp, linear, linear)
        out.extend(itb(0b01100101, 1))
        # out.extend(itb(0, 1))
        # replace hierarchy control (what is this)
        out.extend(itb(1, 1))
        return out

class ANMKeyframe():
    def __init__(self, time, keyframe, quantization=0, track=None, fname = 'adsfd'):
        self.time = time
        self.keyframe = keyframe
        self.quantization = quantization
        self.track = track
        self.fname = fname

    def binary(self, setting_bank_ptr):
        out = bytearray()
        setting_out = bytearray()
        # keyframe time
        out.extend(ftb(self.time))
        # setting bank pointer (relative to start of file)
        out.extend(itb(setting_bank_ptr, 4))
        # interpolation info pointer (null if none or linear)
        out.extend(itb(0, 4))
        # f = open(self.fname, 'a')
        # f.write(str(self.time) + '\n')
        if 's' in self.keyframe:
            scale = [self.keyframe['s']['x'], self.keyframe['s']['y'], self.keyframe['s']['z']]
            self.s = scale
            # f.write('s: ' + ','.join([str(round(x, 3)) for x in scale]) + '\n')
            setting_out.extend(writeQuantizedData(self.quantization, scale))
        else:
            self.s = [1, 1, 1]
        if 'r' in self.keyframe:
            rotation = [self.keyframe['r']['x'], self.keyframe['r']['y'], self.keyframe['r']['z']]
            # print(' '.join([str(round(x, 3)) for x in rotation]))
            # f.write('r: ' + ','.join([str(round(x, 3)) for x in rotation]) + '\n')
            rotation = [x*math.pi/180 for x in rotation]
            # print(' '.join([str(round(x, 3)) for x in rotation]))
            quaternion = euler_to_quaternion(*rotation)
            self.r = quaternion
            # print(' '.join([str(round(x, 3)) for x in quaternion]))
            quaternion = [quaternion[1], quaternion[2], quaternion[3], quaternion[0]]
            # print(quaternion)
            setting_out.extend(writeQuantizedData(self.quantization, quaternion))
        else:
            self.r = [1, 0, 0, 0]
        if 't' in self.keyframe:
            translation = [self.keyframe['t']['x'] * MODEL_SCALE, self.keyframe['t']['y'] * MODEL_SCALE, self.keyframe['t']['z'] * MODEL_SCALE]
            self.t = translation
            # f.write('t: ' + ','.join([str(round(x, 3)) for x in translation]) + '\n')
            setting_out.extend(writeQuantizedData(self.quantization, translation))
        else:
            self.t = [0, 0, 0]
        # f.close()
        return out, setting_out

    def maxShift(self):
        shift = 0xe
        if 's' in self.keyframe:
            scale = [self.keyframe['s']['x'], self.keyframe['s']['y'], self.keyframe['s']['z']]
            shift = min(shift, maxHalfShift(scale))
        if 'r' in self.keyframe:
            rotation = [self.keyframe['r']['x'], self.keyframe['r']['y'], self.keyframe['r']['z']]
            quaternion = euler_to_quaternion(*rotation)
            quaternion = [quaternion[1], quaternion[2], quaternion[3], quaternion[0]]
            shift = min(shift, maxHalfShift(quaternion))
        if 't' in self.keyframe:
            translation = [self.keyframe['t']['x'], self.keyframe['t']['y'], self.keyframe['t']['z']]
            shift = min(shift, maxHalfShift(translation))
        return shift

if __name__ == '__main__':
    my_import = CHR0Import([CHR0_FILENAME])