from endstone.util import Vector

def vector_sub(a: Vector, b: Vector) -> Vector:
    return Vector(a.x - b.x, a.y - b.y, a.z - b.z)

def vector_length_squared(v: Vector) -> float:
    return v.x * v.x + v.y * v.y + v.z * v.z

def vector_dot(a: Vector, b: Vector) -> float:
    return a.x * b.x + a.y * b.y + a.z * b.z

def vector_mul_scalar(v: Vector, s: float) -> Vector:
    return Vector(v.x * s, v.y * s, v.z * s)