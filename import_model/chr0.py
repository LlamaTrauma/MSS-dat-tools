from base import *
import numpy as np
from helper import *

addrs = {}

class CHR0(FileChunk):
     def analyze(self):
          # magic (CHR0)
          magic = self.word()
          self.len = self.word()
          # this parses version 4 files, that's what brawlbox gave me
          self.version = self.word()
          self.brres_offset = self.word()
          self.section_1_ptr = self.word()
          self.section_name_ptr = self.word()
          self.header = self.add_child(0x18, 0x10, CHR0Header)
          self.header.analyze()
          self.read(0x10)
          self.index_group = self.add_child(self.section_1_ptr, 0, BRRESIndexGroup)
          self.index_group.analyze()
          self.tracks = {}
          for entry in self.index_group.entries:
               self.tracks[entry.data.bone_str] = entry.data.track_data

class CHR0Header(FileChunk):
     def analyze(self):
          self.word()
          self.frame_count = self.half()
          self.anm_data_count = self.half()
          self.looping = self.word()
          self.word()

class BRRESIndexGroup(FileChunk):
     def analyze(self):
          self.size = self.word()
          self.entry_count = self.word()
          self.entries = [self.add_child(0x18 + 0x10 * i, 0x10, BRRESIndexEntry).analyze() for i in range(self.entry_count)]
          uniques = {}
          for entry in self.entries:
               uniques[entry.data.anm_type_code] = 1
          for key in uniques.keys():
               stri = ''
               for i in range(0, 32, 8):
                    stri += format((key >> i) & 0b11111111, "08b") + ' '
               # print(stri)

class CHR0AnmData(FileChunk):
     def analyze(self):
          global addrs
          addrs[self.absolute] = 'ANMData'
          self.bone_str_ptr = self.word()
          self.anm_type_code = self.word()
          self.frame_count = self.parent.parent.header.frame_count
          anm_type_code = self.anm_type_code
          # why is this relative to the data entry when it's reading from the BRRES string table
          # seems weird but maybe that's okay
          self.bone_str = self.readStr(self.bone_str_ptr)
          # print('--------------')
          # print(self.bone_str)
          # print(bin(anm_type_code)[2:].rjust(32, '0'))

          # (1) always set
          anm_type_code >>= 1

          # (2) unset in Run
          self.identity = anm_type_code & 0b1
          anm_type_code >>= 1

          # (3) unset in Run
          self.rt_isotropic = anm_type_code & 0b1
          anm_type_code >>= 1
          
          # (4) sometimes set in Run
          self.s_isotropic = anm_type_code & 0b1
          anm_type_code >>= 1

          # (5) unset in Run
          self.s_uniform = anm_type_code & 0b1
          anm_type_code >>= 1

          # (6) sometimes set in Run
          self.r_isotropic = anm_type_code & 0b1
          anm_type_code >>= 1

          # (7) sometimes set in Run
          self.t_isotropic = anm_type_code & 0b1
          anm_type_code >>= 1

          # (8) sometimes set in Run
          self.use_model_s = anm_type_code & 0b1
          anm_type_code >>= 1

          # (9) sometimes set in Run
          self.use_model_r = anm_type_code & 0b1
          anm_type_code >>= 1

          # (10) sometimes set in Run
          self.use_model_t = anm_type_code & 0b1
          anm_type_code >>= 1

          # (11) sometimes set in Run
          self.s_compensate = anm_type_code & 0b1
          anm_type_code >>= 1

          # (12) sometimes set in Run
          self.child_s_compensate = anm_type_code & 0b1
          anm_type_code >>= 1

          # (13) sometimes set in Run
          self.disable_classic_s = anm_type_code & 0b1
          anm_type_code >>= 1

          # (14) sometimes set in Run
          self.s_x_fixed = anm_type_code & 0b1
          anm_type_code >>= 1

          # (15) unset in Run
          self.s_y_fixed = anm_type_code & 0b1
          anm_type_code >>= 1

          # (16) sometimes set in Run
          self.s_z_fixed = anm_type_code & 0b1
          anm_type_code >>= 1

          # (17) unset in Run
          self.r_x_fixed = anm_type_code & 0b1
          anm_type_code >>= 1

          # (18) unset in Run
          self.r_y_fixed = anm_type_code & 0b1
          anm_type_code >>= 1

          # (19) unset in Run
          self.r_z_fixed = anm_type_code & 0b1
          anm_type_code >>= 1

          # (20) unset in Run
          self.t_x_fixed = anm_type_code & 0b1
          anm_type_code >>= 1

          # (21) unset in Run
          self.t_y_fixed = anm_type_code & 0b1
          anm_type_code >>= 1

          # (22) always set in Run
          self.t_z_fixed = anm_type_code & 0b1
          anm_type_code >>= 1

          # (23) always set in Run
          self.has_s = anm_type_code & 0b1
          anm_type_code >>= 1

          # (24) always set in Run
          self.has_r = anm_type_code & 0b1
          anm_type_code >>= 1

          # (25) always set in Run
          self.has_t = anm_type_code & 0b1
          anm_type_code >>= 1

          # (26-27)
          self.s_format = anm_type_code & 0b11
          anm_type_code >>= 2

          # (28-30)
          self.r_format = anm_type_code & 0b111
          anm_type_code >>= 3

          # (31-32)
          self.t_format = anm_type_code & 0b11
          anm_type_code >>= 2

          track_data = {}

          # print('has s ' + hex(self.has_s))
          # print('has r ' + hex(self.has_r))
          # print('has t ' + hex(self.has_t))
          # print('s_format ' + hex(self.s_format))
          # print('r_format ' + hex(self.r_format))
          # print('t_format ' + hex(self.t_format))
          # print('s_isotropic ' + hex(self.s_isotropic))
          # print('r_isotropic ' + hex(self.r_isotropic))
          # print('t_isotropic ' + hex(self.t_isotropic))
          # print('rt_isotropic ' + hex(self.rt_isotropic))
          # print('s_fixed ' + ','.join([hex(self.s_x_fixed), hex(self.s_y_fixed), hex(self.s_z_fixed)]))
          # print('r_fixed ' + ','.join([hex(self.r_x_fixed), hex(self.r_y_fixed), hex(self.r_z_fixed)]))
          # print('t_fixed ' + ','.join([hex(self.t_x_fixed), hex(self.t_y_fixed), hex(self.t_z_fixed)]))

          f = open('import/bone_txt/' + self.bone_str, 'w')
          descs = {}

          if self.has_s:
               track_data['s'] = {}
               if self.s_isotropic:
                    data, descs['s'] = self.next_data(self.s_format, 0)
                    track_data['s']['x'] = data
                    track_data['s']['y'] = data
                    track_data['s']['z'] = data
               else:
                    track_data['s']['x'], descs['sx'] = self.next_data(self.s_format, self.s_x_fixed)
                    track_data['s']['y'], descs['sy'] = self.next_data(self.s_format, self.s_y_fixed)
                    track_data['s']['z'], descs['sx'] = self.next_data(self.s_format, self.s_z_fixed)

          if self.has_r:
               track_data['r'] = {}
               if self.r_isotropic:
                    data, descs['r'] = self.next_data(self.r_format, 0)
                    track_data['r']['x'] = data
                    track_data['r']['y'] = data
                    track_data['r']['z'] = data
               else:
                    track_data['r']['x'], descs['rx'] = self.next_data(self.r_format, self.r_x_fixed)
                    track_data['r']['y'], descs['ry'] = self.next_data(self.r_format, self.r_y_fixed)
                    track_data['r']['z'], descs['rz'] = self.next_data(self.r_format, self.r_z_fixed)
               # for axis in track_data['r']:
               #      data = track_data['r'][axis]
               #      for keyframe in data:
               #           print(str(round(data[keyframe], 3)) + ' / ' + str(keyframe))
               #      print('-----')
               # print('-----')
          
          if self.has_t:
               track_data['t'] = {}
               if self.t_isotropic:
                    data, descs['t'] = self.next_data(self.t_format, 0)
                    track_data['t']['x'] = data
                    track_data['t']['y'] = data
                    track_data['t']['z'] = data
               else:
                    track_data['t']['x'], descs['tx'] = self.next_data(self.t_format, self.t_x_fixed)
                    track_data['t']['y'], descs['ty'] = self.next_data(self.t_format, self.t_y_fixed)
                    track_data['t']['z'], descs['tz'] = self.next_data(self.t_format, self.t_z_fixed)

          # if self.t_format == 3:
          #      print(self.bone_str)

          for component in track_data:
               f.write(component + '\n')
               # f.write('format: ' + hex(getattr(self, component + '_format')) + '\n')
               for axis in track_data[component]:
                    f.write('  ' + axis + '\n')
                    # f.write('  fixed: ' + hex(getattr(self, component + '_' + axis + '_fixed')) + '\n')
                    data = track_data[component][axis]
                    for keyframe in data:
                         f.write('    ' + str(keyframe) + ': ' + str(round(data[keyframe], 3)) + '\n')
          f.write('\n')
          for desc in descs:
               f.write(desc + '\n')
               f.write(''.join(['  ' + x + '\n' for x in descs[desc].split('\n')]))

          self.track_data = track_data
          return self

     def next_data(self, format, fixed):
          r = self.read(4)
          # print(hex(bti(r)))
          if format == 0 or fixed:
               # print('immediate')
               v = struct.unpack('>f', r)[0]
               d = {}
               d[0] = v
               d[self.frame_count - 1] = v
               return d, 'fixed'
          else:
               # print('relative')
               addr = bti(r)
               # print(hex(self.absolute))
               # print(hex(addr))
               # print('--------------')
               data = self.add_child(addr, 0, ANMFrameData)
               return data.vals(format, self.frame_count)

class ANMFrameData(FileChunk):
     def vals(self, format, frame_count):
          global addrs
          vals = {}
          addrs[self.absolute] = 'format ' + str(format)
          desc = ''
          desc += 'format ' + str(format) + '\n'
          if format in (1, 2):
               # interpolated 4 or 6
               data_count = self.half()
               desc += 'data count: ' + str(data_count) + '\n'
               shrug = self.half()
               frame_scale = self.float()
               desc += 'frame scale: ' + str(frame_scale) + '\n'
               # print(frame_scale)
               step = self.float()
               desc += 'step: ' + str(step) + '\n'
               base = self.float()
               desc += 'base: ' + str(base) + '\n'
               for _ in range(data_count):
                    frame_ = 0
                    step_ = 0
                    tangent_ = 0
                    if format == 1:
                         frame_ = self.byte()
                         # print(hex(self.absolute + self.tell()))
                         b = self.read(3)
                         # desc += '  ' + str(b) + '\n'
                         b = bti(b)
                         # tangent_ = it2c(b & 0xFFF, 12) / 32
                         tangent_ = (b & 0xFFF) / 32
                         b >>= 12
                         # step_ = it2c(b, 12)
                         step_ = b
                    else:
                         frame_ = self.half() / 32
                         step_ = self.half()
                         tangent_ = self.half() / 256
                    desc += '  frame: ' + str(frame_) + '\n'
                    desc += '  step: ' + str(step_) + '\n'
                    desc += '  tangent: ' + str(tangent_) + '\n'
                    desc += '  -----\n'
                    vals[frame_] = base + step * step_
          elif format == 3:
               data_count = self.half()
               shrug = self.half()
               frame_scale = self.float()
               val = 0
               for _ in range(data_count):
                    frame_ = self.float()
                    val = self.float()
                    tangent_ = self.float()
                    vals[frame_] = val
          elif format == 4:
               step = self.float()
               base = self.float()
               for i in range(frame_count):
                    vals[i] = base + step * self.byte()
          elif format == 6:
               print ('Format 6 used, havent encountered this yet')
               for i in range(frame_count):
                    vals[i] = self.float()
                    print(vals[i])
          else:
               print('format ' + hex(format + str(' not recognized')))
          # print('-----')
          return vals, desc

class BRRESIndexEntry(FileChunk):
     def analyze(self):
          self.id = self.half()
          shrug = self.half()
          self.left_index = self.half()
          self.right_index = self.half()
          self.name_ptr = self.word()
          self.name = self.parent.readStr(self.name_ptr)
          self.data_ptr = self.word()
          self.data = self.parent.add_child(self.data_ptr, 0, CHR0AnmData).analyze()
          return self

if __name__ == '__main__':
     chr = CHR0(open('import/lucas/Run.chr0', 'rb'), 0, 0, '')
     chr.analyze()
     sorted_addrs = list(addrs.keys())
     sorted_addrs.sort()
     # for addr in sorted_addrs:
     #      print(hex(addr))
     #      print('    ' + addrs[addr])