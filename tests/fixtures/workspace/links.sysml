package LinkPkg {
  import VehiclePkg::Vehicle;

  part def Fleet {
    part lead: Vehicle;
    allocate Vehicle;
    trace Vehicle;
  }
}
