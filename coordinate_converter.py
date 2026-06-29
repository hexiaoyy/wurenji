"""
WGS-84与GCJ-02坐标转换模块
WGS-84: GPS原始坐标系统
GCJ-02: 中国火星坐标系(高德、腾讯等国内地图使用)
"""

import math
from typing import Tuple


class CoordinateConverter:
    """坐标转换类"""

    A = 6378137.0
    B = 6356752.314245
    F = 1 / 298.257223563

    PI = math.pi
    AXIS = 6378245.0
    OFFSET = 0.006693421622965

    @staticmethod
    def wgs84_to_gcj02(lon: float, lat: float) -> Tuple[float, float]:
        """WGS-84转GCJ-02"""
        dlon = CoordinateConverter._transform_long(lon - 105.0, lat - 35.0)
        dlat = CoordinateConverter._transform_lat(lon - 105.0, lat - 35.0)

        radlat = lat / 180.0 * CoordinateConverter.PI
        magic = math.sin(radlat)
        magic = 1 - CoordinateConverter.OFFSET * magic * magic

        sqrtmagic = math.sqrt(magic)
        dlon = (dlon * 180.0) / (CoordinateConverter.AXIS / sqrtmagic * math.cos(radlat) * CoordinateConverter.PI)
        dlat = (dlat * 180.0) / ((CoordinateConverter.AXIS * (1 - CoordinateConverter.OFFSET)) / (magic * sqrtmagic) * CoordinateConverter.PI)

        return lon + dlon, lat + dlat

    @staticmethod
    def gcj02_to_wgs84(lon: float, lat: float) -> Tuple[float, float]:
        """GCJ-02转WGS-84"""
        dlon = CoordinateConverter._transform_long(lon - 105.0, lat - 35.0)
        dlat = CoordinateConverter._transform_lat(lon - 105.0, lat - 35.0)

        radlat = lat / 180.0 * CoordinateConverter.PI
        magic = math.sin(radlat)
        magic = 1 - CoordinateConverter.OFFSET * magic * magic

        sqrtmagic = math.sqrt(magic)
        dlon = (dlon * 180.0) / (CoordinateConverter.AXIS / sqrtmagic * math.cos(radlat) * CoordinateConverter.PI)
        dlat = (dlat * 180.0) / ((CoordinateConverter.AXIS * (1 - CoordinateConverter.OFFSET)) / (magic * sqrtmagic) * CoordinateConverter.PI)

        return lon - dlon, lat - dlat

    @staticmethod
    def _transform_long(x: float, y: float) -> float:
        ret = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * math.sqrt(math.sqrt(x * x))
        ret += (20.0 * math.sin(6.0 * x * CoordinateConverter.PI) + 20.0 * math.sin(2.0 * x * CoordinateConverter.PI)) * 2.0 / 3.0
        ret += (20.0 * math.sin(x * CoordinateConverter.PI) + 40.0 * math.sin(x / 3.0 * CoordinateConverter.PI)) * 2.0 / 3.0
        ret += (20.0 * math.sin(y * CoordinateConverter.PI) + 40.0 * math.sin(y / 3.0 * CoordinateConverter.PI)) * 2.0 / 3.0
        return ret

    @staticmethod
    def _transform_lat(x: float, y: float) -> float:
        ret = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y
        ret += (20.0 * math.sin(6.0 * x * CoordinateConverter.PI) + 20.0 * math.sin(2.0 * x * CoordinateConverter.PI)) * 2.0 / 3.0
        ret += (20.0 * math.sin(y * CoordinateConverter.PI) + 40.0 * math.sin(y / 3.0 * CoordinateConverter.PI)) * 2.0 / 3.0
        ret += (160.0 * math.sin(y / 12.0 * CoordinateConverter.PI) + 320.0 * math.sin(y / 30.0 * CoordinateConverter.PI)) * 2.0 / 3.0
        return ret

    @staticmethod
    def is_in_china(lon: float, lat: float) -> bool:
        return 72.0 <= lon <= 137.0 and 18.0 <= lat <= 55.0


NJUST_CENTER = (118.7115, 32.0642)  # 南京科技职业学院 (lon, lat) WGS-84


def test_coordinate_conversion():
    """测试坐标转换"""
    converter = CoordinateConverter()

    wgs84_lon, wgs84_lat = NJUST_CENTER

    print("=" * 50)
    print("坐标转换测试 - 南京科技职业学院")
    print("=" * 50)

    gcj02_lon, gcj02_lat = converter.wgs84_to_gcj02(wgs84_lon, wgs84_lat)
    print(f"WGS-84 -> GCJ-02")
    print(f"  原始: ({wgs84_lon:.6f}, {wgs84_lat:.6f})")
    print(f"  转换: ({gcj02_lon:.6f}, {gcj02_lat:.6f})")

    back_lon, back_lat = converter.gcj02_to_wgs84(gcj02_lon, gcj02_lat)
    print(f"\nGCJ-02 -> WGS-84")
    print(f"  原始: ({gcj02_lon:.6f}, {gcj02_lat:.6f})")
    print(f"  转换: ({back_lon:.6f}, {back_lat:.6f})")

    error_lon = abs(back_lon - wgs84_lon)
    error_lat = abs(back_lat - wgs84_lat)
    print(f"\n转换误差: 经度={error_lon:.10f}, 纬度={error_lat:.10f}")
    print(f"在中国境内: {converter.is_in_china(wgs84_lon, wgs84_lat)}")


if __name__ == "__main__":
    test_coordinate_conversion()
