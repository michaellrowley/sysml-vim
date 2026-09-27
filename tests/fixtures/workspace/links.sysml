package LinkPkg {
  private import VehiclePkg::Vehicle;

  part def Fleet {
    part lead: Vehicle;
    allocate lead to Vehicle;
    dependency from Fleet to Vehicle;
  }
}
