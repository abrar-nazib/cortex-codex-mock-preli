/**
 * Server-side proxy for /sort-ticket.
 *
 * The browser cannot reach the backend's internal Docker URL, and we don't
 * want to expose a cross-origin fetch (CORS) + bake a public URL into the
 * client bundle at build time. Instead the browser POSTs same-origin to
 * `/api/sort-ticket`; this route handler forwards the body to the backend
 * at request time using the runtime `BACKEND_URL` env var.
 *
 * Backend logs the forwarded request like any other `POST /sort-ticket`.
 */
export const runtime = "nodejs";

export async function POST(req: Request) {
  const backend = (process.env.BACKEND_URL || "http://backend:8000").replace(/\/$/, "");
  try {
    const body = await req.text();
    const upstream = await fetch(`${backend}/sort-ticket`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
    });
    const text = await upstream.text();
    return new Response(text, {
      status: upstream.status,
      headers: { "Content-Type": "application/json" },
    });
  } catch (err) {
    return new Response(
      JSON.stringify({ error: "backend unreachable", detail: String(err) }),
      { status: 502, headers: { "Content-Type": "application/json" } },
    );
  }
}