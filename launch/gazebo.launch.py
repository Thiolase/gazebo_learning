import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, SetEnvironmentVariable, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from launch.actions import SetEnvironmentVariable


def generate_launch_description():
    package_name = 'Leg'
    urdf_file_name = 'Leg.urdf'
    controllers_yaml = os.path.join(
        get_package_share_directory(package_name), 'config', 'leg_controllers.yaml')
    urdf_path = os.path.join(get_package_share_directory(package_name), 'urdf', urdf_file_name)

    # ��ȡ URDF Ϊ�ַ���
    with open(urdf_path, 'r') as infp:
        robot_description_content = infp.read()

    # ������Դ·����ʹ Gazebo ���ҵ������ļ���
    package_share_directory = get_package_share_directory(package_name)
    gazebo_resources_directory = os.path.dirname(package_share_directory)

    ld = LaunchDescription()

    # ���� use_sim_time
    ld.add_action(DeclareLaunchArgument(
        'use_sim_time',
        default_value='true',
        description='Use simulation (Gazebo) clock if true'
    ))

    # ���� Gazebo ��Դ·��
    ld.add_action(SetEnvironmentVariable(
        name='GZ_SIM_RESOURCE_PATH',
        value=gazebo_resources_directory
    ))

    # ���� Gazebo ������
    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(get_package_share_directory('ros_gz_sim'), 'launch', 'gz_sim.launch.py')
        ),
        launch_arguments={'gz_args': '-r empty.sdf'}.items()
    )
    ld.add_action(gz_sim)

    # ������״̬������������ tf��
    ld.add_action(Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{'robot_description': robot_description_content}]
    ))

    # ros2_control �������������ڵ㣨���ؿ�������
    ld.add_action(Node(
    package='controller_manager',
    executable='ros2_control_node',
    parameters=[{'robot_description': robot_description_content}, controllers_yaml],
    output='screen',
    ))

    # ���عؽ�״̬�㲥�������� /joint_states��
    ld.add_action(Node(
        package='controller_manager',
        executable='spawner',
        arguments=['joint_state_broadcaster'],
        output='screen',
    ))

    # ���ع켣������
    ld.add_action(Node(
        package='controller_manager',
        executable='spawner',
        arguments=['leg_joint_trajectory_controller'],
        output='screen',
    ))

    # ���ɻ�����ʵ�壨̧�� 0.05 �ף�
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
    # �� generate_launch_description ������
    ld.add_action(SetEnvironmentVariable(
        name='ROS_PLUGIN_PATH',
        value='/opt/ros/jazzy/lib:' + os.environ.get('ROS_PLUGIN_PATH', '')
    ))
    ld.add_action(SetEnvironmentVariable(
        name='LD_LIBRARY_PATH',
        value='/opt/ros/jazzy/lib:' + os.environ.get('LD_LIBRARY_PATH', '')
    ))
    return ld