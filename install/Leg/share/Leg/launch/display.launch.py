import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    package_name = 'Leg'
    urdf_file_name = 'Leg.urdf'
    rviz_config_file = 'robot_disp.rviz'

    rviz_config_path = os.path.join(get_package_share_directory(package_name), 'rviz', rviz_config_file)
    urdf = os.path.join(
        get_package_share_directory(package_name),
        'urdf',
        urdf_file_name)
    
    # 读取 URDF 文件内容
    with open(urdf, 'r') as infp:
        robot_description_content = infp.read()

    ld = LaunchDescription()

    ld.add_action(DeclareLaunchArgument(
        'use_sim_time',
        default_value='false',
        description='Use simulation (Gazebo) clock if true'
    ))

    # robot_state_publisher - 使用 URDF 文件内容
    ld.add_action(Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': robot_description_content,
            'use_sim_time': LaunchConfiguration('use_sim_time')
        }]
    ))

    # joint_state_publisher_gui - 用于手动控制关节
    ld.add_action(Node(
        package='joint_state_publisher_gui',
        executable='joint_state_publisher_gui',
        name='joint_state_publisher_gui',
        output='screen',
        parameters=[{
            'robot_description': robot_description_content,
            'use_sim_time': LaunchConfiguration('use_sim_time')
        }]
    ))

    # RViz2
    ld.add_action(Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', rviz_config_path],
        parameters=[{'use_sim_time': LaunchConfiguration('use_sim_time')}]
    ))
    
    # 静态 TF：map -> base_link
    ld.add_action(Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='static_transform_publisher',
        arguments=['0', '0', '0', '0', '0', '0', 'map', 'base_link'],
    ))

    return ld