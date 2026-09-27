package ReqPkg {
  requirement def R1;
  requirement req1: R1;

  part def VerificationRig {
    satisfy R1;
    verify R1;
  }
}
