import math
import pathlib

from geometry_msgs.msg import PoseStamped, Quaternion
from geometry_msgs.msg import Twist
from nav2_msgs.action import NavigateToPose
from nav_msgs.msg import Odometry
import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node
from sensor_msgs.msg import LaserScan
from std_msgs.msg import String
from tf2_msgs.msg import TFMessage
import yaml


class PatrolNavNode(Node):
    def __init__(self):
        super().__init__("patrol_nav_node")
        ws_root = pathlib.Path(__file__).resolve().parents[3]
        default_waypoints = ws_root / "safe_city_navigation" / "config" / "waypoints.yaml"
        default_plan = ws_root / "safe_city_perception" / "config" / "mission_plan.yaml"

        self.declare_parameter("waypoints_file", str(default_waypoints))
        self.declare_parameter("mission_plan_file", str(default_plan))
        self.declare_parameter("trigger_topic", "/safe_city/task/zone_trigger")
        self.declare_parameter("state_topic", "/safe_city/task/patrol_state")
        self.declare_parameter("simulate_navigation", False)
        self.declare_parameter("simple_navigation", False)
        self.declare_parameter("step_interval_sec", 4.0)
        self.declare_parameter("nav_timeout_sec", 6.0)
        self.declare_parameter("startup_delay_sec", 0.0)
        self.declare_parameter("cmd_vel_topic", "/cmd_vel")
        self.declare_parameter("odom_topic", "/odom")
        self.declare_parameter("tf_topic", "/tf")
        self.declare_parameter("scan_topic", "/scan")
        self.declare_parameter("map_to_odom_x", -1.35)
        self.declare_parameter("map_to_odom_y", -1.35)
        self.declare_parameter("recognition_settle_sec", 1.2)
        self.declare_parameter("recognition_scan_sec", 3.0)
        self.declare_parameter("recognition_scan_speed", 0.32)
        self.declare_parameter("front_stop_distance", 0.34)
        self.declare_parameter("front_slow_distance", 0.55)
        self.declare_parameter("field_soft_limit", 1.78)

        self.trigger_topic = self.get_parameter("trigger_topic").value
        self.state_topic = self.get_parameter("state_topic").value
        self.simulate_navigation = bool(self.get_parameter("simulate_navigation").value)
        self.simple_navigation = bool(self.get_parameter("simple_navigation").value)
        self.step_interval_sec = float(self.get_parameter("step_interval_sec").value)
        self.nav_timeout_sec = float(self.get_parameter("nav_timeout_sec").value)
        self.startup_delay_sec = float(self.get_parameter("startup_delay_sec").value)
        self.map_to_odom_x = float(self.get_parameter("map_to_odom_x").value)
        self.map_to_odom_y = float(self.get_parameter("map_to_odom_y").value)
        self.recognition_settle_sec = float(
            self.get_parameter("recognition_settle_sec").value
        )
        self.recognition_scan_sec = float(
            self.get_parameter("recognition_scan_sec").value
        )
        self.recognition_scan_speed = float(
            self.get_parameter("recognition_scan_speed").value
        )
        self.front_stop_distance = float(self.get_parameter("front_stop_distance").value)
        self.front_slow_distance = float(self.get_parameter("front_slow_distance").value)
        self.field_soft_limit = float(self.get_parameter("field_soft_limit").value)

        self.waypoints = self._load_waypoints(
            self.get_parameter("waypoints_file").get_parameter_value().string_value
        )
        mission = self._load_mission(
            self.get_parameter("mission_plan_file").get_parameter_value().string_value
        )
        self.ordered_zones = mission.get("ordered_zones", [])
        self.zone_to_waypoint = mission.get("zone_to_waypoint", {})
        self.zone_pre_waypoints = mission.get("zone_pre_waypoints", {})
        self.return_route = mission.get("return_route", [])
        self.index = 0
        self.goal_in_flight = False
        self.returning_home = False
        self.return_completed = False
        self.goal_serial = 0
        self.current_goal_id = None
        self.current_goal_handle = None
        self.current_goal_started_ns = None
        self.current_context = None
        self.pending_route = []
        self.current_pose = None
        self.front_clearance = None
        self.left_clearance = None
        self.right_clearance = None
        self.settle_until_ns = None
        self.scan_until_ns = None
        self.scan_completed = False
        self.started_ns = self.get_clock().now().nanoseconds

        self.trigger_pub = self.create_publisher(String, self.trigger_topic, 10)
        self.state_pub = self.create_publisher(String, self.state_topic, 10)
        self.cmd_vel_pub = self.create_publisher(
            Twist, self.get_parameter("cmd_vel_topic").value, 10
        )
        self.odom_sub = self.create_subscription(
            Odometry, self.get_parameter("odom_topic").value, self._odom_callback, 20
        )
        self.tf_sub = self.create_subscription(
            TFMessage, self.get_parameter("tf_topic").value, self._tf_callback, 50
        )
        self.scan_sub = self.create_subscription(
            LaserScan, self.get_parameter("scan_topic").value, self._scan_callback, 20
        )
        self.nav_client = ActionClient(self, NavigateToPose, "navigate_to_pose")
        self.timer = self.create_timer(self.step_interval_sec, self._tick)
        self.control_timer = self.create_timer(0.1, self._control_tick)

        self.get_logger().info("Patrol nav node ready.")
        self.get_logger().info(f"Ordered zones: {self.ordered_zones}")
        self.get_logger().info(f"Return route: {self.return_route}")
        self.get_logger().info(f"Simulate navigation: {self.simulate_navigation}")
        self.get_logger().info(f"Simple navigation: {self.simple_navigation}")

    def _load_waypoints(self, path_str):
        path = pathlib.Path(path_str)
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        points = data.get("waypoints", {}).get("ros__parameters", {}).get("points", [])
        return {item["name"]: item for item in points}

    def _load_mission(self, path_str):
        path = pathlib.Path(path_str)
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        return data.get("mission", {})

    def _tick(self):
        if not self._startup_delay_elapsed():
            return
        if self.goal_in_flight:
            if self._goal_timed_out():
                zone, waypoint_name, waypoint, trigger_on_arrival = self.current_context
                self.get_logger().warn(
                    f"[NAV] Goal timeout for {zone} via {waypoint_name}, using route fallback."
                )
                if self.current_goal_handle is not None:
                    self.current_goal_handle.cancel_goal_async()
                self._publish_stop()
                self.current_goal_id = None
                self.current_goal_handle = None
                self.current_goal_started_ns = None
                self.current_context = None
                self._on_arrival(zone, waypoint_name, waypoint, trigger_on_arrival)
            return
        if self.index >= len(self.ordered_zones):
            if not self.returning_home and not self.return_completed and self.return_route:
                self.returning_home = True
                self.pending_route = [(name, False) for name in self.return_route]
                self.get_logger().info(
                    "[NAV] Recognition tasks completed; returning through final loop route."
                )
            elif self.returning_home and self.pending_route:
                pass
            else:
                if not self.return_completed:
                    self.return_completed = True
                    self._publish_state("completed:full_map_loop")
                    self.get_logger().info(
                        "[NAV] Full PDF-map patrol loop completed; robot returned to start zone."
                    )
                self.get_logger().info("Patrol nav node finished all zones.")
                self._publish_stop()
                self.control_timer.cancel()
                self.timer.cancel()
                return

        if self.returning_home:
            zone = "return_route"
            if not self.pending_route:
                self.returning_home = False
                self.return_completed = True
                return
        else:
            zone = self.ordered_zones[self.index]

        if not self.pending_route:
            self.pending_route = self._route_for_zone(zone)

        waypoint_name, trigger_on_arrival = self.pending_route.pop(0)
        waypoint = self.waypoints.get(waypoint_name)
        if waypoint is None:
            self.get_logger().warn(f"Waypoint not found for zone {zone}: {waypoint_name}")
            if not self.pending_route and not self.returning_home:
                self.index += 1
            return

        self.goal_in_flight = True
        self.goal_serial += 1
        self.current_goal_id = self.goal_serial
        self.current_goal_handle = None
        self.current_goal_started_ns = self.get_clock().now().nanoseconds
        self.current_context = (zone, waypoint_name, waypoint, trigger_on_arrival)
        self.settle_until_ns = None
        self.scan_until_ns = None
        self.scan_completed = False
        self._publish_state(f"navigating:{zone}:{waypoint_name}")

        if self.simulate_navigation:
            self.get_logger().info(f"[NAV] Simulated arrival at {zone} via {waypoint_name}")
            self._on_arrival(zone, waypoint_name, waypoint, trigger_on_arrival)
            return

        if self.simple_navigation:
            self.get_logger().info(f"[NAV] Simple controller goal for {zone} via {waypoint_name}")
            return

        if not self.nav_client.wait_for_server(timeout_sec=1.0):
            self.get_logger().warn(
                "[NAV] NavigateToPose server unavailable, falling back to simulated arrival."
            )
            self._on_arrival(zone, waypoint_name, waypoint, trigger_on_arrival)
            return

        goal = NavigateToPose.Goal()
        goal.pose = self._to_pose_stamped(waypoint)
        goal_id = self.current_goal_id
        future = self.nav_client.send_goal_async(goal)
        future.add_done_callback(
            lambda f, zone_name=zone, wp_name=waypoint_name, wp=waypoint, gid=goal_id: self._goal_response_callback(
                f, zone_name, wp_name, wp, gid
            )
        )

    def _goal_response_callback(self, future, zone, waypoint_name, waypoint, goal_id):
        if goal_id != self.current_goal_id:
            return
        goal_handle = future.result()
        if goal_handle is None or not goal_handle.accepted:
            trigger_on_arrival = True
            if self.current_context is not None:
                trigger_on_arrival = self.current_context[3]
            self.get_logger().warn(f"[NAV] Goal rejected for {zone}, using simulated arrival.")
            self._on_arrival(zone, waypoint_name, waypoint, trigger_on_arrival)
            return

        self.current_goal_handle = goal_handle
        self.get_logger().info(f"[NAV] Goal accepted for {zone}")
        result_future = goal_handle.get_result_async()
        result_future.add_done_callback(
            lambda f, zone_name=zone, wp_name=waypoint_name, wp=waypoint, gid=goal_id: self._goal_result_callback(
                f, zone_name, wp_name, wp, gid
            )
        )

    def _goal_result_callback(self, future, zone, waypoint_name, waypoint, goal_id):
        if goal_id != self.current_goal_id:
            return
        self.get_logger().info(f"[NAV] Goal completed for {zone}")
        trigger_on_arrival = False
        if self.current_context is not None:
            trigger_on_arrival = self.current_context[3]
        self._on_arrival(zone, waypoint_name, waypoint, trigger_on_arrival)

    def _on_arrival(self, zone, waypoint_name, waypoint, trigger_on_arrival):
        self._publish_stop()
        self.current_goal_id = None
        self.current_goal_handle = None
        self.current_goal_started_ns = None
        self.current_context = None
        self.settle_until_ns = None
        self.scan_until_ns = None
        self.scan_completed = False
        self._publish_state(
            f"arrived:{zone}:{waypoint_name}:{waypoint['x']}:{waypoint['y']}:{waypoint['yaw']}"
        )
        if not trigger_on_arrival:
            self.get_logger().info(f"[NAV] Reached transit waypoint {waypoint_name} for {zone}")
            if self.returning_home and not self.pending_route:
                self.returning_home = False
                self.return_completed = True
                self._publish_state("completed:full_map_loop")
                self.get_logger().info(
                    "[NAV] Full PDF-map patrol loop completed; robot returned to start zone."
                )
            self.goal_in_flight = False
            return

        trigger = String()
        trigger.data = zone
        self.trigger_pub.publish(trigger)
        self.get_logger().info(f"[NAV] Triggered {zone} via waypoint {waypoint_name}")
        self.index += 1
        self.pending_route = []
        self.goal_in_flight = False

    def _route_for_zone(self, zone):
        route = [(name, False) for name in self.zone_pre_waypoints.get(zone, [])]
        route.append((self.zone_to_waypoint.get(zone, zone), True))
        return route

    def _odom_callback(self, msg):
        pos = msg.pose.pose.position
        ori = msg.pose.pose.orientation
        yaw = math.atan2(
            2.0 * (ori.w * ori.z + ori.x * ori.y),
            1.0 - 2.0 * (ori.y * ori.y + ori.z * ori.z),
        )
        self.current_pose = (
            pos.x + self.map_to_odom_x,
            pos.y + self.map_to_odom_y,
            yaw,
        )

    def _tf_callback(self, msg):
        for transform in msg.transforms:
            if transform.header.frame_id != "odom":
                continue
            if transform.child_frame_id not in {
                "base_link",
                "base_footprint",
                "inspection_robot/base_link",
                "inspection_robot/base_footprint",
                "turtlebot3_waffle/base_footprint",
            }:
                continue
            trans = transform.transform.translation
            rot = transform.transform.rotation
            yaw = math.atan2(
                2.0 * (rot.w * rot.z + rot.x * rot.y),
                1.0 - 2.0 * (rot.y * rot.y + rot.z * rot.z),
            )
            self.current_pose = (
                trans.x + self.map_to_odom_x,
                trans.y + self.map_to_odom_y,
                yaw,
            )
            return

    def _scan_callback(self, msg):
        def min_range(start_angle, end_angle):
            values = []
            for index, distance in enumerate(msg.ranges):
                if not math.isfinite(distance):
                    continue
                if distance < 0.14:
                    continue
                angle = msg.angle_min + index * msg.angle_increment
                if start_angle <= angle <= end_angle:
                    values.append(distance)
            return min(values) if values else None

        self.front_clearance = min_range(-0.42, 0.42)
        self.left_clearance = min_range(0.45, 1.35)
        self.right_clearance = min_range(-1.35, -0.45)

    def _control_tick(self):
        if not self.simple_navigation or not self.goal_in_flight:
            return
        if self.current_context is None or self.current_pose is None:
            return

        zone, waypoint_name, waypoint, trigger_on_arrival = self.current_context
        x, y, yaw = self.current_pose
        goal_x = float(waypoint["x"])
        goal_y = float(waypoint["y"])
        dx = goal_x - x
        dy = goal_y - y
        distance = math.hypot(dx, dy)

        goal_yaw = float(waypoint["yaw"])
        goal_yaw_error = self._normalize_angle(goal_yaw - yaw)

        safety_cmd = self._safety_override(x, y, yaw)
        if safety_cmd is not None:
            self.cmd_vel_pub.publish(safety_cmd)
            self.settle_until_ns = None
            return

        if distance <= 0.12:
            if abs(goal_yaw_error) > 0.18 and not self.scan_completed:
                cmd = Twist()
                cmd.angular.z = self._clamp(1.4 * goal_yaw_error, -0.65, 0.65)
                self.cmd_vel_pub.publish(cmd)
                self.settle_until_ns = None
                return

            now = self.get_clock().now().nanoseconds
            if (
                trigger_on_arrival
                and self.recognition_scan_sec > 0.0
                and not self.scan_completed
            ):
                if self.scan_until_ns is None:
                    self.scan_until_ns = now + int(self.recognition_scan_sec * 1e9)
                    self.get_logger().info(
                        f"[NAV] Scanning recognition target at {waypoint_name}"
                    )

                if now < self.scan_until_ns:
                    cmd = Twist()
                    cmd.angular.z = self.recognition_scan_speed
                    self.cmd_vel_pub.publish(cmd)
                    self.settle_until_ns = None
                    return
                self.scan_completed = True

            if self.settle_until_ns is None:
                self._publish_stop()
                self.settle_until_ns = now + int(self.recognition_settle_sec * 1e9)
                return

            if self.get_clock().now().nanoseconds < self.settle_until_ns:
                self._publish_stop()
                return

            self._publish_stop()
            self._on_arrival(zone, waypoint_name, waypoint, trigger_on_arrival)
            return

        target_yaw = math.atan2(dy, dx)
        yaw_error = self._normalize_angle(target_yaw - yaw)
        cmd = Twist()
        if abs(yaw_error) > 0.35:
            cmd.angular.z = self._clamp(1.4 * yaw_error, -0.75, 0.75)
        else:
            speed_limit = self._speed_limit_from_lidar()
            cmd.linear.x = self._clamp(0.9 * distance, 0.05, speed_limit)
            cmd.angular.z = self._clamp(1.8 * yaw_error, -0.60, 0.60)
        self.cmd_vel_pub.publish(cmd)

    def _safety_override(self, x, y, yaw):
        if max(abs(x), abs(y)) > self.field_soft_limit:
            target_yaw = math.atan2(-y, -x)
            yaw_error = self._normalize_angle(target_yaw - yaw)
            cmd = Twist()
            if abs(yaw_error) > 0.28:
                cmd.angular.z = self._clamp(1.8 * yaw_error, -0.55, 0.55)
            else:
                cmd.linear.x = 0.06
                cmd.angular.z = self._clamp(1.2 * yaw_error, -0.25, 0.25)
            return cmd

        return None

    def _speed_limit_from_lidar(self):
        if self.front_clearance is None:
            return 0.17
        if self.front_clearance < self.front_slow_distance:
            return 0.11
        return 0.17

    def _publish_stop(self):
        self.cmd_vel_pub.publish(Twist())

    def _normalize_angle(self, angle):
        while angle > math.pi:
            angle -= 2.0 * math.pi
        while angle < -math.pi:
            angle += 2.0 * math.pi
        return angle

    def _clamp(self, value, low, high):
        return max(low, min(high, value))

    def _goal_timed_out(self):
        if self.current_goal_started_ns is None:
            return False
        elapsed = self.get_clock().now().nanoseconds - self.current_goal_started_ns
        return elapsed >= int(self.nav_timeout_sec * 1e9)

    def _startup_delay_elapsed(self):
        if self.startup_delay_sec <= 0.0:
            return True
        elapsed = self.get_clock().now().nanoseconds - self.started_ns
        return elapsed >= int(self.startup_delay_sec * 1e9)

    def _publish_state(self, state):
        msg = String()
        msg.data = state
        self.state_pub.publish(msg)

    def _to_pose_stamped(self, waypoint):
        pose = PoseStamped()
        pose.header.frame_id = "map"
        pose.header.stamp = self.get_clock().now().to_msg()
        pose.pose.position.x = float(waypoint["x"])
        pose.pose.position.y = float(waypoint["y"])
        pose.pose.position.z = 0.0
        pose.pose.orientation = self._yaw_to_quaternion(float(waypoint["yaw"]))
        return pose

    def _yaw_to_quaternion(self, yaw):
        q = Quaternion()
        q.z = math.sin(yaw * 0.5)
        q.w = math.cos(yaw * 0.5)
        return q


def main():
    rclpy.init()
    node = PatrolNavNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()
