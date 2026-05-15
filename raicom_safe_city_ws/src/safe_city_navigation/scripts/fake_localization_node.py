#!/usr/bin/env python3

import math

from geometry_msgs.msg import Quaternion
from nav_msgs.msg import Odometry
import rclpy
from rclpy.node import Node


class FakeLocalizationNode(Node):
    def __init__(self):
        super().__init__("fake_localization_node")
        self.declare_parameter("map_frame", "map")
        self.declare_parameter("odom_frame", "odom")
        self.declare_parameter("base_frame", "base_link")
        self.declare_parameter("x", 0.0)
        self.declare_parameter("y", 0.0)
        self.declare_parameter("yaw", 0.0)
        self.declare_parameter("publish_rate", 20.0)

        self.odom_frame = self.get_parameter("odom_frame").value
        self.base_frame = self.get_parameter("base_frame").value
        self.x = float(self.get_parameter("x").value)
        self.y = float(self.get_parameter("y").value)
        self.yaw = float(self.get_parameter("yaw").value)
        self.publish_rate = float(self.get_parameter("publish_rate").value)

        self.odom_pub = self.create_publisher(Odometry, "/odom", 10)
        self.timer = self.create_timer(1.0 / max(self.publish_rate, 1.0), self._publish)

        self.get_logger().info("Fake localization node ready.")
        self.get_logger().info(
            f"Publishing static pose x={self.x:.2f}, y={self.y:.2f}, yaw={self.yaw:.2f}"
        )

    def _publish(self):
        stamp = self.get_clock().now().to_msg()

        odom = Odometry()
        odom.header.stamp = stamp
        odom.header.frame_id = self.odom_frame
        odom.child_frame_id = self.base_frame
        odom.pose.pose.position.x = self.x
        odom.pose.pose.position.y = self.y
        odom.pose.pose.orientation = self._yaw_to_quaternion(self.yaw)
        self.odom_pub.publish(odom)

    def _yaw_to_quaternion(self, yaw):
        q = Quaternion()
        q.z = math.sin(yaw * 0.5)
        q.w = math.cos(yaw * 0.5)
        return q


def main():
    rclpy.init()
    node = FakeLocalizationNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
