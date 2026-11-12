// فلتر One Euro: نفس engine/airengine/one_euro.py بالضبط، بس بـ JavaScript.
const alpha = (cutoff, dt) => 1 / (1 + 1 / (2 * Math.PI * cutoff) / dt);

export class OneEuroFilter {
  constructor({ min_cutoff = 1.0, beta = 0.007, d_cutoff = 1.0 } = {}) {
    Object.assign(this, { minCutoff: min_cutoff, beta, dCutoff: d_cutoff });
    this.reset();
  }

  reset() {
    this.x = null;
    this.dx = 0;
    this.t = null;
  }

  // x = القيمة الجديدة، t = الوقت بالثواني
  filter(x, t) {
    if (this.x === null) {
      this.x = x;
      this.t = t;
      return x;
    }
    const dt = t - this.t;
    if (dt <= 0) return this.x;
    this.dx += alpha(this.dCutoff, dt) * ((x - this.x) / dt - this.dx);
    const cutoff = this.minCutoff + this.beta * Math.abs(this.dx);
    this.x += alpha(cutoff, dt) * (x - this.x);
    this.t = t;
    return this.x;
  }
}
