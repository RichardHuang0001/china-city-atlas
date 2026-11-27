"""Shared GRS80 Albers Equal-Area Conic projection parameters and pure-stdlib math."""
import math

MAIN_PROJ = {"lon_0": 105, "lat_0": 36, "lat_1": 25, "lat_2": 47, "scale": 4000.0}
INSET_PROJ = {"lon_0": 114, "lat_0": 14, "lat_1": 5, "lat_2": 24, "scale": 4000.0}


def make_albers_projector(lon_0: float, lat_0: float, lat_1: float, lat_2: float, scale: float = 4000.0):
    """Build a pure-stdlib GRS80 Albers Equal-Area Conic projector matching pyproj."""
    a = 6378137.0
    f = 1 / 298.257222101
    e2 = 2 * f - f * f
    e = math.sqrt(e2)
    q = lambda phi: (1 - e2) * (
        math.sin(phi) / (1 - e2 * math.sin(phi) ** 2)
        - math.log((1 - e * math.sin(phi)) / (1 + e * math.sin(phi))) / (2 * e)
    )
    m = lambda phi: math.cos(phi) / math.sqrt(1 - e2 * math.sin(phi) ** 2)
    phi0, phi1, phi2, lam0 = map(math.radians, (lat_0, lat_1, lat_2, lon_0))
    q0, q1, q2 = q(phi0), q(phi1), q(phi2)
    m1, m2 = m(phi1), m(phi2)
    n = (m1 * m1 - m2 * m2) / (q2 - q1)
    c = m1 * m1 + n * q1
    rho0 = a * math.sqrt(c - n * q0) / n

    def project(lon: float, lat: float) -> tuple[float, float]:
        rho = a * math.sqrt(c - n * q(math.radians(lat))) / n
        theta = n * (math.radians(lon) - lam0)
        return rho * math.sin(theta) / scale, -(rho0 - rho * math.cos(theta)) / scale

    return project


project_main = make_albers_projector(**MAIN_PROJ)
project_inset = make_albers_projector(**INSET_PROJ)
