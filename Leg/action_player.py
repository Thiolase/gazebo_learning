#!/usr/bin/env python3
import json
import os
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.duration import Duration
from control_msgs.action import FollowJointTrajectory
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from ament_index_python.packages import get_package_share_directory

class ActionPlayer(Node):
    def __init__(self):
        super().__init__('action_player')
        self.action_client = ActionClient(
            self,
            FollowJointTrajectory,
            '/leg_joint_trajectory_controller/follow_joint_trajectory'
        )
        self.joint_names = ['joint_Leg_1', 'joint_Leg2', 'joint_Leg_3', 'joint_Leg_4']

    def map_angles(self, servo_angles):
        base_deg = 135.0
        rad_per_deg = 3.14159 / 180.0
        return [(deg - base_deg) * rad_per_deg for deg in servo_angles[:4]]

    def run(self):
        # 查找 actions 目录
        source_actions = os.path.expanduser("~/Desktop/Leg/actions")
        install_actions = os.path.join(get_package_share_directory('Leg'), 'actions')
        if os.path.isdir(source_actions):
            actions_path = source_actions
        elif os.path.isdir(install_actions):
            actions_path = install_actions
        else:
            self.get_logger().error("找不到 actions 目录")
            return

        # 加载配置文件
        config_path = os.path.join(actions_path, 'sequence.json')
        if not os.path.exists(config_path):
            self.get_logger().error(f"未找到配置文件: {config_path}")
            return

        with open(config_path, 'r') as f:
            config = json.load(f)

        fps = config.get('frames_per_second', 10)
        frame_delay = 1.0 / fps
        loop_count = config.get('loop_count', 1)

        # 加载所有帧
        all_frames = []
        for action in config.get('sequence', []):
            filename = action.get('file')
            if not filename:
                continue
            filepath = os.path.join(actions_path, filename)
            if not os.path.exists(filepath):
                self.get_logger().error(f"动作文件不存在: {filepath}")
                return
            with open(filepath, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or ':' not in line:
                        continue
                    angles_str = line.split(':', 1)[1].strip().rstrip(',')
                    angles = []
                    for part in angles_str.split(','):
                        if part.strip():
                            angles.append(int(part))
                    if len(angles) == 16:
                        all_frames.append(angles)

        if not all_frames:
            self.get_logger().error("未加载到任何帧")
            return

        # 构造轨迹点
        points = []
        current_time = 0.0
        for _ in range(loop_count):
            for frame in all_frames:
                point = JointTrajectoryPoint()
                point.positions = self.map_angles(frame[1:5])   # 取索引 1,2,3,4 共 4 个元素
                point.time_from_start = Duration(seconds=current_time).to_msg()
                points.append(point)
                current_time += frame_delay

        self.get_logger().info(f"共 {len(points)} 个点，总时长 {current_time:.2f} 秒")

        # 发送轨迹
        traj = JointTrajectory()
        traj.joint_names = self.joint_names
        traj.points = points

        goal = FollowJointTrajectory.Goal()
        goal.trajectory = traj
        goal.goal_time_tolerance = Duration(seconds=0.5).to_msg()

        self.action_client.wait_for_server()
        future = self.action_client.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, future)
        goal_handle = future.result()
        if goal_handle and goal_handle.accepted:
            self.get_logger().info("轨迹被接受")
            result_future = goal_handle.get_result_async()
            rclpy.spin_until_future_complete(self, result_future)
            self.get_logger().info("轨迹执行完成")
        else:
            self.get_logger().error("轨迹被拒绝")

def main(args=None):
    rclpy.init(args=args)
    player = ActionPlayer()
    player.run()
    rclpy.shutdown()

if __name__ == "__main__":
    main()