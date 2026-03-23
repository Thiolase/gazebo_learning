import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import SetEnvironmentVariable, IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node

def generate_launch_description():
    package_name = 'Leg'
    urdf_file_name = 'Leg.urdf'
    controllers_yaml = os.path.join(
        get_package_share_directory(package_name), 'config', 'leg_controllers.yaml')
    urdf_path = os.path.join(get_package_share_directory(package_name), 'urdf', urdf_file_name)

    with open(urdf_path, 'r') as infp:
        robot_description_content = infp.read()

    package_share_directory = get_package_share_directory(package_name)

    ld = LaunchDescription()

    # 设置环境变量
    ld.add_action(SetEnvironmentVariable(
        name='GZ_SIM_RESOURCE_PATH',
        value=os.path.dirname(package_share_directory)
    ))

    # 启动 Gazebo
    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('ros_gz_sim'), 'launch', 'gz_sim.launch.py')
        ),
        launch_arguments={'gz_args': '-r empty.sdf'}.items()
    )
    ld.add_action(gz_sim)

    # 启动 robot_state_publisher（会发布 robot_description）
    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': robot_description_content,
            'use_sim_time': True
        }]
    )
    ld.add_action(robot_state_publisher)

    # 生成机器人实体（等待 robot_state_publisher 就绪）
    spawn_entity = TimerAction(
        period=3.0,
        actions=[
            Node(
                package='ros_gz_sim',
                executable='create',
                arguments=[
                    '-name', 'Leg',
                    '-topic', 'robot_description',
                    '-z', '0.05'
                ],
                output='screen'
            )
        ]
    )
    ld.add_action(spawn_entity)

    # 延迟启动 ros2_control_node（等待 robot_description 话题有数据）
    ros2_control_node = TimerAction(
        period=4.0,
        actions=[
            Node(
                package='controller_manager',
                executable='ros2_control_node',
                parameters=[{'robot_description': robot_description_content}, controllers_yaml],
                output='screen',
            )
        ]
    )
    ld.add_action(ros2_control_node)

    # 延迟启动控制器 spawner
    spawn_joint_state_broadcaster = TimerAction(
        period=5.0,
        actions=[
            Node(
                package='controller_manager',
                executable='spawner',
                arguments=['joint_state_broadcaster'],
                output='screen',
            )
        ]
    )
    ld.add_action(spawn_joint_state_broadcaster)

    spawn_leg_controller = TimerAction(
        period=5.0,
        actions=[
            Node(
                package='controller_manager',
                executable='spawner',
                arguments=['leg_joint_trajectory_controller'],
                output='screen',
            )
        ]
    )
    ld.add_action(spawn_leg_controller)

    return ld