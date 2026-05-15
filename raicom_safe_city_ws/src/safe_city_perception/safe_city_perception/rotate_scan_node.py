import rclpy
from rclpy.node import Node


class RotateScanNode(Node):
    def __init__(self):
        super().__init__("rotate_scan_node")
        self.declare_parameter("angular_speed", 0.3)
        self.declare_parameter("scan_duration_sec", 4.0)
        self.get_logger().info("Rotate scan scaffold ready.")


def main():
    rclpy.init()
    node = RotateScanNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
