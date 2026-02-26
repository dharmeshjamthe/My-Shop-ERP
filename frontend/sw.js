self.addEventListener("install", event => {
  console.log("Service Worker Installed");
});

self.addEventListener("fetch", event => {
  // basic pass-through (no offline cache yet)
});