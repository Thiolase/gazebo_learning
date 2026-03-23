import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import SetEnvironmentVariable, IncludeLaunchDescription, RegisterEventHandler, TimerAction
from launch.event_handlers import OnProcessStart
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from launch.substitutions import LaunchConfiguration

def generate_launch_description():
    package_name = 'Leg'
    urdf_file_name = 'Leg.urdf'
    use_sim_time = LaunchConfiguration('use_sim_time', default=True)
    gz_args = LaunchConfiguration('gz_args', default='')

    package_share_directory = get_package_share_directory(package_name)
    urdf_path = os.path.join(package_share_directory, 'urdf', urdf_file_name)

    with open(urdf_path, 'r', encoding='utf-8') as infp:
        robot_description_content = infp.read()

    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('ros_gz_sim'),
                'launch',
                'gz_sim.launch.py'
            )
        ),
        launch_arguments={'gz_args': '-r empty.sdf'}.items()
    )

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

    spawn_entity = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-name', 'Leg',
            '-topic', 'robot_description',
            '-z', '0.05'
        ],
        output='screen'
    )

    joint_state_broadcaster_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=[
            'joint_state_broadcaster',
            '--controller-manager', '/controller_manager'
        ],
        output='screen',
    )

    leg_controller_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=[
            'leg_joint_trajectory_controller',
            '--controller-manager', '/controller_manager'
        ],
        output='screen',
    )

    clock_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=['/clock@rosgraph_msgs/msg/Clock@gz.msgs.Clock]'],   # 方向改为 ]
        parameters=[{'qos_overrides./clock.subscriber.reliability': 'best_effort'}],
        output='screen'
    )

    return LaunchDescription([
        SetEnvironmentVariable(
            name='GZ_SIM_RESOURCE_PATH',
            value=os.path.dirname(package_share_directory)
        ),

        gz_sim,
        robot_state_publisher,

        TimerAction(
            period=2.0,
            actions=[spawn_entity]
        ),

        RegisterEventHandler(
            OnProcessStart(
                target_action=spawn_entity,
                on_start=[
                    TimerAction(period=5.0, actions=[joint_state_broadcaster_spawner]),
                    TimerAction(period=7.0, actions=[leg_controller_spawner]),
                ]
            )
        ),
    ])