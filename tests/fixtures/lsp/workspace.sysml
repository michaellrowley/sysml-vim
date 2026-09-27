package SmokeModel {
  part def Engine;
  part def Vehicle {
    part engine: Engine;
    attribute mass: Real;
  }
}
