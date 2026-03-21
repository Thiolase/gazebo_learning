import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, SetEnvironmentVariable, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node

def generate_launch_description():
    package_name = 'Leg'
    urdf_file_name = 'Leg.urdf'
    controllers_yaml = os.path.join(
        get_package_share_directory(package_name), 'config', 'leg_controllers.yaml')
    urdf_path = os.path.join(get_package_share_directory(package_name), 'urdf', urdf_file_name)

    # 读取 URDF 为字符串
    with open(urdf_path, 'r') as infp:
        robot_description_content = infp.read()

    # 设置资源路径（使 Gazebo 能找到网格文件）
    package_share_directory = get_package_share_directory(package_name)
    gazebo_resources_directory = os.path.dirname(package_share_directory)

    ld = LaunchDescription()

    # 声明 use_sim_time
    ld.add_action(DeclareLaunchArgument(
        'use_sim_time',
        default_value='true',
        description='Use simulation (Gazebo) clock if true'
    ))

    # 设置 Gazebo 资源路径
    ld.add_action(SetEnvironmentVariable(
        name='GZ_SIM_RESOURCE_PATH',
        value=gazebo_resources_directory
    ))

    # 启动 Gazebo 空世界
    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('ros_gz_sim'), 'launch', 'gz_sim.launch.py')
        ),
        launch_arguments={'gz_args': '-r empty.sdf'}.items()
    )
    ld.add_action(gz_sim)

    # 机器人状态发布器（发布 tf）
    ld.add_action(Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_description_content}]
    ))

    # ros2_control 控制器管理器节点（加载控制器）
    ld.add_action(Node(
        package='controller_manager',
        executable='ros2_control_node',
        parameters=[{'robot_description': robot_description_content}, controllers_yaml],
        output='screen',
        # 如果需要调试，可取消下一行的注释（需先安装 gdb）
        # prefix=['gdb', '-ex', 'run', '--args'],
    ))

    # 加载关节状态广播器（发布 /joint_states）
    ld.add_action(Node(
        package='controller_manager',
        executable='spawner',
        arguments=['joint_state_broadcaster'],
        output='screen',
    ))

    # 加载轨迹控制器
    ld.add_action(Node(
        package='controller_manager',
        executable='spawner',
        arguments=['leg_joint_trajectory_controller'],
        output='screen',
    ))

    # 生成机器人实体（抬高 0.05 米）
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
    ld.add_action(spawn_entity)

    return ld