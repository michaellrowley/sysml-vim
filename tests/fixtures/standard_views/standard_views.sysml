package Example {
  view bleTraceView : BrowserView { expose Root; }
  part Root {
    part Child {
      part Leaf;
    }
  }
}
