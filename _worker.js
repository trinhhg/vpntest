export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // Nếu là Link Sub hoặc API -> Bẻ lái ngầm sang con Worker Test (Nơi chứa Database)
    if (url.pathname.startsWith("/v1") || url.pathname.startsWith("/v2") || url.pathname.startsWith("/api")) {
      const workerUrl = new URL(request.url);
      workerUrl.hostname = "vpn-worker-test.doicucden.workers.dev";
      const newRequest = new Request(workerUrl.toString(), request);
      return fetch(newRequest);
    }

    // Nếu khách truy cập bình thường -> Phục vụ file giao diện tĩnh
    return env.ASSETS.fetch(request);
  }
};
