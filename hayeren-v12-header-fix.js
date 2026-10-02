// Hayeren v12.1 compatibility fix.
// Older preload injectors try to remove Content-Length after writeHead().
// Node throws ERR_HTTP_HEADERS_SENT in that case, which prevented the fast translator
// script from being injected into Telegram. Make that operation harmless while keeping
// normal removeHeader behaviour before headers are sent.
const http = require('http');
const proto = http.ServerResponse.prototype;
const originalRemoveHeader = proto.removeHeader;
if (!proto.__hayerenSafeRemoveHeader) {
  proto.removeHeader = function safeRemoveHeader(name) {
    if (this.headersSent) return;
    return originalRemoveHeader.call(this, name);
  };
  proto.__hayerenSafeRemoveHeader = true;
}
console.log('HAYEREN_HEADER_FIX_READY 12.1');
