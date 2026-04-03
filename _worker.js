export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // Nếu là Link Sub hoặc API -> Bẻ lái ngầm sang con Worker (Nơi chứa Database)
    if (url.pathname.startsWith("/v1") || url.pathname.startsWith("/v2") || url.pathname.startsWith("/api")) {
      const workerUrl = new URL(request.url);
      
      // Đổi đích đến thành con Worker của ông
      workerUrl.hostname = "vpn-api.doicucden.workers.dev";
      
      // Chuyển tiếp toàn bộ gói tin sang Worker xử lý
      const newRequest = new Request(workerUrl.toString(), request);
      return fetch(newRequest);
    }

    // Nếu khách truy cập bình thường -> Phục vụ file giao diện tĩnh (index.html, admin.html)
    return env.ASSETS.fetch(request);
  }
};
