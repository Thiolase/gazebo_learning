#!/usr/bin/env python3
import json
import os
from rosbag2_py import SequentialReader, StorageOptions, ConverterOptions
from rclpy.serialization import deserialize_message
from sensor_msgs.msg import JointState

# 目标关节名称（你的仿真模型中的关节名）
TARGET_JOINT_NAMES = ['joint_Leg_1', 'joint_Leg2', 'joint_Leg_3', 'joint_Leg_4']
BASE_ANGLE_DEG = 135.0
RAD_TO_DEG = 180.0 / 3.141592653589793

# 打开 bag
storage_options = StorageOptions(uri=os.getcwd(), storage_id='mcap')
converter_options = ConverterOptions(
    input_serialization_format='cdr',
    output_serialization_format='cdr'
)
reader = SequentialReader()
reader.open(storage_options, converter_options)

# 读取所有消息
frames = []  # 每个元素是 {'timestamp': t, 'radians': [...]}
while reader.has_next():
    topic, data_raw, t = reader.read_next()
    if topic == '/joint_states':
        msg = deserialize_message(data_raw, JointState)
        # 构建关节名称->弧度映射
        pos_map = dict(zip(msg.name, msg.position))
        # 获取目标关节弧度（缺失则补0）
        rads = [pos_map.get(name, 0.0) for name in TARGET_JOINT_NAMES]
        frames.append({'timestamp': t, 'radians': rads})

if not frames:
    print("错误：没有找到 /joint_states 消息")
    exit(1)

# 按时间排序（一般已经是顺序的，但保险）
frames.sort(key=lambda x: x['timestamp'])

# 创建 actions 目录
actions_dir = os.path.join(os.getcwd(), 'actions')
os.makedirs(actions_dir, exist_ok=True)

# 写入动作文件（全部放一个文件，也可以分割）
out_file = os.path.join(actions_dir, 'action_1.txt')
with open(out_file, 'w') as f:
    for idx, frame in enumerate(frames):
        # 弧度 -> 角度 -> 偏移基准
        servo_deg = [rad * RAD_TO_DEG + BASE_ANGLE_DEG for rad in frame['radians']]
        # 构造16个角度的数组，索引1~4放这四个值
        full_angles = [0] * 16
        for i in range(4):
            full_angles[i+1] = int(servo_deg[i])  # 取整，你也可以保留小数
        # 写入，格式：序号: 角度1,...,角度16
        f.write(f"{idx}: {','.join(str(a) for a in full_angles)}\n")

# 生成 sequence.json
config = {
    "frames_per_second": 10,   # 这个可以根据实际录制时长和帧数调整
    "loop_count": 1,
    "sequence": [{"file": "action_1.txt"}]
}
with open(os.path.join(actions_dir, 'sequence.json'), 'w') as f:
    json.dump(config, f, indent=2)

print(f"完成！共 {len(frames)} 帧，保存在 {actions_dir}/")