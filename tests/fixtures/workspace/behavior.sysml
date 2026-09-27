package BehaviorPkg {
  part def Controller {
    state def Idle;
    state def Active;
    Idle -> Active;
  }

  action def Start;
}
