export class RequestTimeoutError extends Error {
  constructor() {
    super('The request took too long.');
    this.name = 'RequestTimeoutError';
  }
}

// Bound both waiting for headers and reading the JSON body. Aborting alone
// is insufficient if a transport never settles its promise.
export async function fetchJson(path, options = {}, timeoutMs = 15000) {
  const controller = new AbortController();
  let timer;
  const deadline = new Promise((_, reject) => {
    timer = setTimeout(() => {
      reject(new RequestTimeoutError());
      controller.abort();
    }, timeoutMs);
  });
  const request = (async () => {
    const response = await fetch(path, { ...options, signal: controller.signal });
    return { response, data: await response.json() };
  })();
  try {
    return await Promise.race([request, deadline]);
  } finally {
    clearTimeout(timer);
  }
}
