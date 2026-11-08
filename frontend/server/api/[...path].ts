export default defineEventHandler((event) => {
  const base = useRuntimeConfig(event).apiBase;
  // Fixed upstream; client never supplies a URL or a delegated identity.
  return proxyRequest(event, `${base}${event.path}`);
});
