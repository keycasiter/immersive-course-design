// XY paper model. z thickness belongs to rendering and does not change area.
export function geometry({base = 6, height = 4, shear = 2, offset = 0} = {}) {
  if (![base, height, shear, offset].every(Number.isFinite)
      || base <= 0 || height <= 0 || shear <= 0 || shear >= base
      || offset < 0 || offset > base) throw new RangeError('Invalid paper parameters');
  const triangle = [[0, 0], [shear, 0], [shear, height]];
  return {
    original: [[0, 0], [base, 0], [base + shear, height], [shear, height]],
    remaining: [[shear, 0], [base, 0], [base + shear, height], [shear, height]],
    moved: triangle.map(([x, y]) => [x + offset, y]),
    baseAnchor: [base / 2, 0], heightAnchor: [shear, height / 2],
    area: base * height, width: base, height
  };
}
export function polygonArea(points) {
  return Math.abs(points.reduce((sum, p, i) => {
    const q = points[(i + 1) % points.length];
    return sum + p[0] * q[1] - q[0] * p[1];
  }, 0)) / 2;
}
