import { NextRequest } from "next/server";

// This proxy must always run on the server at request time — never cached or
// statically optimized — so the API key is attached fresh to every request.
export const dynamic = "force-dynamic";

// Server-only configuration. These are NOT prefixed with NEXT_PUBLIC_, so Next.js
// never inlines them into client-side JavaScript: the API key stays on the server.
const API_URL = (
  process.env.API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000"
).replace(/\/+$/, "");
const API_KEY = process.env.EVAL_API_KEY || "";

/**
 * Same-origin proxy for the backend API.
 *
 * The browser calls relative paths (/api/v1/...); this handler forwards them to
 * the real API and injects the X-API-Key header from a server-only env var. The
 * key is never exposed to the browser, and because we build a fresh header set
 * the client cannot override or spoof it.
 */
async function proxy(req: NextRequest, path: string[]): Promise<Response> {
  const target = `${API_URL}/api/${path.join("/")}${req.nextUrl.search}`;

  const headers = new Headers();
  const contentType = req.headers.get("content-type");
  if (contentType) headers.set("content-type", contentType);
  if (API_KEY) headers.set("X-API-Key", API_KEY);

  const init: RequestInit = { method: req.method, headers };
  if (req.method !== "GET" && req.method !== "HEAD") {
    init.body = await req.text();
  }

  let upstream: Response;
  try {
    upstream = await fetch(target, init);
  } catch {
    return new Response(JSON.stringify({ detail: "Upstream API unreachable" }), {
      status: 502,
      headers: { "content-type": "application/json" },
    });
  }

  const body = await upstream.text();
  const respHeaders = new Headers();
  const ct = upstream.headers.get("content-type");
  if (ct) respHeaders.set("content-type", ct);
  return new Response(body, { status: upstream.status, headers: respHeaders });
}

type RouteContext = { params: { path: string[] } };

export async function GET(req: NextRequest, { params }: RouteContext) {
  return proxy(req, params.path);
}

export async function POST(req: NextRequest, { params }: RouteContext) {
  return proxy(req, params.path);
}

export async function PUT(req: NextRequest, { params }: RouteContext) {
  return proxy(req, params.path);
}

export async function PATCH(req: NextRequest, { params }: RouteContext) {
  return proxy(req, params.path);
}

export async function DELETE(req: NextRequest, { params }: RouteContext) {
  return proxy(req, params.path);
}
