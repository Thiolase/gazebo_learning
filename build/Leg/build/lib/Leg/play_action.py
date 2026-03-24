#!/usr/bin/env python3
import os
import sys
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.duration import Duration
from control_msgs.action import FollowJointTrajectory
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint

# 这里导入真实机器人的模块（假设仍在 ~/Desktop/Robot）
REAL_ROBOT_PATH = os.path.expanduser("~/Desktop/Robot")
if REAL_ROBOT_PATH not in sys.path:
    sys.path.insert(0, REAL_ROBOT_PATH)

from file_manager import FileManager
from servo_controller import ServoController
from pca9685 import PCA9685
from air_system import AirSystem

class ActionPlayer(Node):
    def __init__(self):
        super().__init__('action_player')
        self.action_client = ActionClient(
            self,
            FollowJointTrajectory,
            '/leg_joint_trajectory_controller/follow_joint_trajectory'
        )
        self.joint_names = ['joint_Leg_1', 'joint_Leg2', 'joint_Leg_3', 'joint_Leg_4']

        # 初始化真实机器人模块（模拟硬件，仅用于角度转换）
        pca9685 = PCA9685()
        servo_controller = ServoController(pca9685)
        air_system = AirSystem()
        self.file_manager = FileManager(servo_controller, air_system, base_path="~/Desktop/Leg")

    def map_angles(self, servo_angles):
        """将前四个舵机角度映射为四个关节弧度（135°→0 弧度）"""
        base_deg = 135.0
        scale = 3.14159 / 180.0
        return [(deg - base_deg) * scale for deg in servo_angles[:4]]

    def load_sequence_points(self, folder_name, frame_delay=None, loop_count=1):
        config = self.file_manager.load_sequence_config(folder_name)
        if not config:
            self.get_logger().error(f"无法加载序列配置: {folder_name}")
            return None

        if frame_delay is None:
            fps = config.get('frames_per_second', 10)
            frame_delay = 1.0 / fps

        points = []
        current_time = 0.0
        for _ in range(loop_count):
            for action in config.get('sequence', []):
                filename = action.get('file')
                if not filename:
                    continue
                frames = self.file_manager.load_action_file(os.path.join(folder_name, filename))
                if not frames:
                    self.get_logger().error(f"无法加载动作文件: {filename}")
                    return None
                for frame in frames:
                    point = JointTrajectoryPoint()
                    point.positions = self.map_angles(frame)
                    point.time_from_start = Duration(seconds=current_time).to_msg()
                    points.append(point)
                    current_time += frame_delay
        self.get_logger().info(f"加载 {len(points)} 个点，总时长 {current_time:.2f} 秒")
        return points

    def send_trajectory(self, points):
        if not points:
            return False
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
            return True
        else:
            self.get_logger().error("轨迹被拒绝")
            return False

def main(args=None):
    rclpy.init(args=args)
    player = ActionPlayer()
    # 在这里修改动作文件夹名称
    folder_name = "your_action_folder"   # 替换为实际文件夹名
    points = player.load_sequence_points(folder_name, frame_delay=None, loop_count=1)
    if points:
        player.send_trajectory(points)
    else:
        player.get_logger().error("加载序列失败")
    rclpy.shutdown()

if __name__ == "__main__":
    main()