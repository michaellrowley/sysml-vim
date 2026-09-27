package VehiclePkg {
  part def Engine {
    port fuelIn: FuelPort;
  }

  part def Vehicle {
    part engine: Engine;
    part wheel: Wheel;
  }

  port def FuelPort;
  part def Wheel;
}
