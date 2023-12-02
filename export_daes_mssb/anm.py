from base import *
from act import *
import numpy as np
from helper import *
from xml_helper import *
from model0 import *

class ANMVector(FileChunk):
    def analyze(self, quantization):
        # Ugh why'd I make this function return a 2d array
        # Not a big enough deal to refactor it atm
        self.data = getQuantizedData(self.f, self.absolute, 1, 3, quantization)[0]
        self.length = quantizedDataSize(quantization) * 3
        return self

class ANMMatrix(SRT):
    def analyze(self):
        super().analyze()
        self.length = 44
        return self.transformation

class ANMQuaternion(FileChunk):
    def analyze(self, quantization):
        quantization = 0x3e
        self.data = getQuantizedData(self.f, self.absolute, 1, 4, quantization)[0]
        self.data = [-self.data[3], self.data[0], self.data[1], self.data[2]]
        self.length = quantizedDataSize(quantization) * 4
        return self

class ANMInterpolationDummy(FileChunk):
    length = 0
    def analyze(self, quantization=0):
        return self

class ANMBezier(FileChunk):
    length = 24
    def analyze(self, quantization=0x3E):
        self.in_ctrl = self.add_child(0, 0, ANMVector).analyze(quantization).data
        self.out_ctrl = self.add_child(quantizedDataSize(quantization) * 3, 0, ANMVector).analyze(quantization).data
        return self

class ANMHermite(FileChunk):
    length = 28
    def analyze(self, quantization=0x3E):
        self.in_ctrl = self.add_child(0, 0, ANMVector).analyze(quantization).data
        self.out_ctrl = self.add_child(quantizedDataSize(quantization) * 3, 0, ANMVector).analyze(quantization).data
        # ease in and out values are probably wrong, fix later if needed
        self.ease_in = self.half() / (1 << 14)
        self.ease_out = self.half() / (1 << 14)
        return self

class ANMSQUAD(FileChunk):
    length = 32
    def analyze(self, quantization=0x3E):
        self.in_quat = self.add_child(0, 0, ANMQuaternion).analyze(quantization).data
        self.out_quat = self.add_child(quantizedDataSize(quantization) * 4, 0, ANMQuaternion).analyze(quantization).data
        return self

class ANMSQUADEE(FileChunk):
    length = 36
    def analyze(self, quantization=0x3E):
        self.in_quat = self.add_child(0, 0, ANMQuaternion).analyze(quantization).data
        self.out_quat = self.add_child(quantizedDataSize(quantization) * 4, 0, ANMQuaternion).analyze(quantization).data
        self.ease_in = self.half() / (1 << 14)
        self.ease_out = self.half() / (1 << 14)
        return self

class ANMKeyframe(FileChunk):
    setting_classes = {
        0: ANMVector,
        1: ANMVector,
        2: ANMVector,
        3: ANMQuaternion,
        4: ANMMatrix
    }
    def analyze(self):
        self.time = int(self.float())
        self.setting_bank_ptr = self.word()
        # print('time is ' + str(self.time))
        # print('setting bank ptr is ' + hex(self.setting_bank_ptr))
        self.interpolation_info_ptr = self.word()
        # print(hex(self.interpolation_info_ptr))
        self.settings = {}
        self.interpolations = {}
        setting_length = 0
        interpolation_length = 0
        for anm_type in self.parent.anm_types:
            # print(hex(self.setting_bank_ptr))
            # print(hex(setting_length))
            # print(hex(self.interpolation_info_ptr))
            # print(hex(interpolation_length))
            # print('_____')
            setting = self.add_child(
                self.setting_bank_ptr + setting_length,
                0,
                self.setting_classes[anm_type],
                relative=ANM)
            setting.analyze(self.parent.quantize_info)
            setting_length += setting.length
            self.settings[anm_type] = setting.data
            interpolation = self.add_child(
                self.interpolation_info_ptr + interpolation_length,
                0,
                self.parent.interpolation_types[anm_type],
                relative=ANM
            )
            # print(self.parent.interpolation_types[anm_type])
            interpolation_length += interpolation.length
            interpolation.analyze(self.parent.quantize_info)
            self.interpolations[anm_type] = interpolation
        # print('--------')
        return self

class ANMTrack(FileChunk):
    interpolation_classes = {
        0b00:  ANMInterpolationDummy,
        0b01:  ANMInterpolationDummy,
        0b10:  ANMBezier,
        0b11:  ANMHermite,
        0b100: ANMSQUAD,
        0b101: ANMSQUADEE,
        0b110: ANMInterpolationDummy
    }
    def analyze(self):
        self.anm_time = int(self.float())
        self.keyframe_arr_ptr = self.word()
        self.keyframe_cnt = self.half()
        # print('keyframe count ' + str(self.keyframe_cnt))
        self.track_id = self.half()
        self.quantize_info = self.byte()
        self.anm_type = self.byte() & 0b11111
        self.anm_types = []
        # 0 is translation, 1 is scale, 2 is euler rotation, 3 is quaternion rotation, 4 is matrix
        for i in [3, 0]:
        # for i in range(5):
            if self.anm_type & (1 << i):
                self.anm_types.append(i)
        self.interpolation_type = self.byte()
        self.interpolation_types = {}
        self.interpolation_types[0] = self.interpolation_classes[self.interpolation_type & 0b11]
        self.interpolation_types[1] = self.interpolation_classes[(self.interpolation_type >> 2) & 0b11]
        self.interpolation_types[2] = self.interpolation_classes[(self.interpolation_type >> 4) & 0b111]
        self.interpolation_types[3] = self.interpolation_types[2]
        self.interpolation_types[4] = ANMInterpolationDummy
        self.replace_hierarchy_ctrl = self.byte()
        # print(self.replace_hierarchy_ctrl)
        # if self.track_id != 8:
        #     self.keyframes = []
        #     return self
        self.keyframes = [self.add_child(self.keyframe_arr_ptr + 12 * i, 0, ANMKeyframe, relative=ANM).analyze() for i in range(self.keyframe_cnt)]
        return self

class ANMSequence(FileChunk):
    def analyze(self):
        self.name_ptr = self.word()
        self.track_arr_ptr = self.word()
        self.track_cnt = self.half()
        # print('track count ' + str(self.track_cnt))
        self.pad = self.half()
        self.tracks = [self.add_child(self.track_arr_ptr + 16 * i, 0, ANMTrack, relative=ANM).analyze() for i in range(self.track_cnt)]
        # would be better if I had made the base class analyze in the init but whatever
        return self

class ANM(FileChunk):
    def analyze(self):
        # 01321AFD
        self.version_number = self.word()
        self.sequence_arr_ptr = self.word()
        self.bank_id = self.half()
        self.sequence_cnt = self.half()
        self.track_cnt = self.half()
        self.keyframe_cnt = self.half()
        self.user_data_sze = self.word()
        self.user_data_ptr = self.word()
        self.sequences = [self.add_child(self.sequence_arr_ptr + 12 * i, 0, ANMSequence, relative=ANM).analyze() for i in range(self.sequence_cnt)]
        # first = self.sequences[1]
        # for track in first.tracks:
        #     if track.track_id != 4:
        #         continue
        #     print(hex(0x04d7b200 + track.absolute + 13))
        #     print(track.anm_types)
        #     for keyframe in track.keyframes:
        #         print(keyframe.time)
        #         print(hex(0x04d7b200 + keyframe.setting_bank_ptr))
        return self

    def toFile(self, dir):
        log_file_dir = dir + 'anim_info'
        if not os.path.exists(log_file_dir):
            return
        f = open(log_file_dir, 'r')
        log_contents = f.readlines()
        f.close()
        model_dae = log_contents[0]
        model_dae = model_dae.split('\n')[0]
        bone_tracks = log_contents[1:]
        track_dict = {}
        bone_dict = {}
        for ind in range(0, len(bone_tracks), 3):
            pair = bone_tracks[ind].split(' ')
            bone_str, track_id = pair[0], int(pair[1])
            if track_id == 65535:
                continue
            track_dict[track_id] = bone_str
            bone_dict[bone_str] = {}
            bone_dict[bone_str]['translation'] = [float(x) for x in bone_tracks[ind+1].split(' ')]
            bone_dict[bone_str]['quaternion'] = [float(x) for x in bone_tracks[ind+2].split(' ')]
        for i, sequence in enumerate(self.sequences):
            sequence_dict = {}
            for track in sequence.tracks:
                track_id = track.track_id
                if track_id not in track_dict:
                    continue
                if (3 not in track.anm_types) and (0 not in track.anm_types):
                    continue
                keyframe_dict = {}
                for keyframe in track.keyframes:
                    if 3 in track.anm_types:
                        quaternion = keyframe.settings[3]
                    else:
                        quaternion = bone_dict[track_dict[track_id]]['quaternion']
                    if 0 in track.anm_types:
                        translation = keyframe.settings[0]
                    else:
                        translation = bone_dict[track_dict[track_id]]['translation']
                    final_transform = np.matmul(quaternion_rotation_matrix(quaternion), translation_matrix(translation))
                    # final_transform = np.array([[keyframe.time, 0, 0, 0], [0, keyframe.time, 0, 0], [0, 0, keyframe.time, 0], [0, 0, 0, keyframe.time]])
                    keyframe_dict[keyframe.time] = final_transform
                sequence_dict[track_id] = keyframe_dict

            if len(sequence_dict):
                out_name = '/'.join(model_dae.split('/')[:-1]) + '/anm_'+str(self.absolute)+'_'+str(i)+'.dae'
                animate_dae(model_dae, out_name, sequence_dict, track_dict)

# Wanted to do the same thing I did with the model data seperating it from the file reading classes completely
# Turned out to be mainly just copying over attributes that I wanted
class ANMData():
    def __init__(self, anm):
        self.anm = anm
        self.bank_id = anm.bank_id
        self.sequence_cnt = anm.sequence_cnt
        self.track_cnt = anm.track_cnt
        self.keyframe_cnt = anm.keyframe_cnt
        self.sequences = []
        appearances = {}
        for sequence in anm.sequences:
            sequence_obj = Object()
            sequence_obj.track_cnt = sequence.track_cnt
            tracks = []
            for track in sequence.tracks:
                track_obj = Object()
                track_obj.time = track.anm_time
                track_obj.keyframe_cnt = track.keyframe_cnt
                track_obj.id = track.track_id
                if track.keyframe_cnt > 0:
                    if track.track_id not in appearances:
                        appearances[track.track_id] = 1
                    else:
                        appearances[track.track_id] += 1
                # translate, scale, rotate (euler), rotate (quaternion), matrix
                track_obj.anm_types = track.anm_types
                # none, linear, bezier, hermite, squad, squadee, slerp
                track_obj.interpolation_type = track.interpolation_type
                keyframes = []
                for keyframe in track.keyframes:
                    keyframe_obj = Object()
                    keyframe_obj.time = keyframe.time
                    keyframe_obj.settings = keyframe.settings
                    keyframe_obj.interpolations = keyframe.interpolations
                    keyframes.append(keyframe_obj)
                track_obj.keyframes = keyframes
                tracks.append(track_obj)
            sequence_obj.tracks = tracks
            self.sequences.append(sequence_obj)
        track_id_keys = list(appearances.keys())
        track_id_keys.sort()
        for sequence in self.sequences:
            cnt = 0
            for track in sequence.tracks:
                if len(track.keyframes) > 0:
                    cnt += 1
        #     print("track len is " + str(cnt))
        # for track_id in track_id_keys:
        #     print (hex(track_id) + ': ' + str(appearances[track_id]))


if __name__ == '__main__':
    anm = ANM(open(
        # 'import/lucas/anm',
        # '../mario_files/mario_animations_2nd',
        'rb'), 0, 0, '')
    anm.analyze()
    data = ANMData(anm)
    # print(len(data.sequences))
    print([hex(x.id) for x in data.sequences[0].tracks])
